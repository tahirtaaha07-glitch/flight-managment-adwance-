from __future__ import annotations

import smtplib
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from email.message import EmailMessage
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import (
    Approval,
    AuditEvent,
    AutomationOutbox,
    Cabin,
    Flight,
    FlightStatus,
    Inventory,
    Seat,
    SeatHold,
    SeatStatus,
    WorkflowStatus,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


def validate_timezone(value: str) -> None:
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        raise HTTPException(status_code=422, detail=f"Unknown timezone: {value}") from exc


def audit(
    db: Session,
    *,
    actor_id: int | None,
    actor_label: str,
    action: str,
    entity_type: str,
    entity_id: str | int,
    rationale: str,
    before: dict | None = None,
    after: dict | None = None,
    decision_rule: str | None = None,
    correlation_id: str | None = None,
) -> AuditEvent:
    event = AuditEvent(
        actor_id=actor_id,
        actor_label=actor_label,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        before_state=before,
        after_state=after,
        rationale=rationale,
        decision_rule=decision_rule,
        correlation_id=correlation_id,
    )
    db.add(event)
    return event


def enqueue(
    db: Session,
    topic: str,
    payload: dict,
    available_at: datetime | None = None,
) -> AutomationOutbox:
    row = AutomationOutbox(
        topic=topic,
        payload=payload,
        status=WorkflowStatus.PENDING,
        available_at=available_at or utc_now(),
    )
    db.add(row)
    return row


def expire_holds_for_flight(db: Session, flight_id: int, now: datetime | None = None) -> int:
    now = now or utc_now()
    holds = db.scalars(
        select(SeatHold).where(
            SeatHold.flight_id == flight_id,
            SeatHold.status == "held",
            SeatHold.expires_at <= now,
        ).with_for_update(skip_locked=True)
    ).all()
    expired = 0
    for hold in holds:
        inventory = db.scalar(
            select(Inventory).where(
                Inventory.flight_id == flight_id,
                Inventory.cabin == hold.cabin,
            ).with_for_update()
        )
        if inventory:
            inventory.held -= hold.passenger_count
        db.query(Seat).filter(Seat.hold_id == hold.id, Seat.status == SeatStatus.HELD).update(
            {Seat.status: SeatStatus.AVAILABLE, Seat.hold_id: None},
            synchronize_session=False,
        )
        hold.status = "expired"
        expired += 1
    return expired


def inventory_payload(db: Session, flight: Flight) -> tuple[dict[Cabin, int], dict[Cabin, int]]:
    expire_holds_for_flight(db, flight.id)
    available: dict[Cabin, int] = {}
    seats: dict[Cabin, int] = {}
    for row in db.scalars(select(Inventory).where(Inventory.flight_id == flight.id)).all():
        available[row.cabin] = max(0, row.capacity + row.overbooking_buffer - row.booked - row.held) if flight.status != FlightStatus.CANCELLED else 0
        seats[row.cabin] = row.capacity
    return available, seats


def flight_response(db: Session, flight: Flight) -> dict:
    available, seats = inventory_payload(db, flight)
    return {
        "id": flight.id,
        "flight_number": flight.flight_number,
        "origin": flight.origin,
        "destination": flight.destination,
        "origin_code": flight.origin_code,
        "destination_code": flight.destination_code,
        "origin_timezone": flight.origin_timezone,
        "destination_timezone": flight.destination_timezone,
        "departure_at": flight.departure_at,
        "arrival_at": flight.arrival_at,
        "capacity": flight.capacity,
        "status": flight.status,
        "currency": flight.currency,
        "prices": {
            Cabin.FIRST.value: flight.first_price,
            Cabin.BUSINESS.value: flight.business_price,
            Cabin.ECONOMY.value: flight.economy_price,
        },
        "available_by_class": available,
        "seats_by_class": seats,
    }


def reserve_seats(db: Session, flight_id: int, cabin: Cabin, quantity: int) -> tuple[Inventory, list[Seat]]:
    inventory = db.scalar(
        select(Inventory)
        .where(Inventory.flight_id == flight_id, Inventory.cabin == cabin)
        .with_for_update()
    )
    if inventory is None:
        raise HTTPException(status_code=404, detail="Cabin inventory was not found")
    if inventory.booked + inventory.held + quantity > inventory.capacity + inventory.overbooking_buffer:
        raise HTTPException(status_code=409, detail="Not enough seats remain in this cabin")
    seats = db.scalars(
        select(Seat)
        .where(Seat.flight_id == flight_id, Seat.cabin == cabin, Seat.status == SeatStatus.AVAILABLE)
        .order_by(Seat.seat_number)
        .limit(quantity)
        .with_for_update(skip_locked=True)
    ).all()
    if len(seats) != quantity:
        raise HTTPException(status_code=409, detail="Physical seats changed during allocation; retry the request")
    inventory.held += quantity
    return inventory, seats


def make_seat_numbers(count: int, prefix: str) -> list[str]:
    if count > 2000:
        raise HTTPException(status_code=422, detail="Seat map is limited to 2,000 physical seats per cabin")
    return [f"{prefix}{number:03d}" for number in range(1, count + 1)]


def email_enabled() -> bool:
    settings = get_settings()
    return bool(settings.gmail_username and settings.gmail_app_password and settings.gmail_from)


def send_transactional_email(recipient: str, subject: str, body: str) -> bool:
    settings = get_settings()
    if not email_enabled():
        return False
    message = EmailMessage()
    message["From"] = settings.gmail_from
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)
    with smtplib.SMTP(settings.gmail_smtp_host, settings.gmail_smtp_port, timeout=15) as smtp:
        smtp.starttls()
        smtp.login(settings.gmail_username, settings.gmail_app_password)
        smtp.send_message(message)
    return True


def issue_credit_expiry() -> datetime:
    return utc_now() + timedelta(days=365)


def class_cutoff(cabin: Cabin) -> timedelta:
    hours = {Cabin.FIRST: 2, Cabin.BUSINESS: 3, Cabin.ECONOMY: 6}[cabin]
    return timedelta(hours=hours)


def assert_departure_open(flight: Flight, cabin: Cabin) -> None:
    if flight.status == FlightStatus.CANCELLED:
        raise HTTPException(status_code=409, detail="Flight is cancelled")
    validate_timezone(flight.origin_timezone)
    if flight.departure_at <= utc_now() + class_cutoff(cabin):
        raise HTTPException(status_code=409, detail=f"Booking cutoff reached for {cabin.value} cabin")


def create_approval(db: Session, action_type: str, subject: str, rationale: str, evidence: dict, user_id: int | None) -> Approval:
    approval = Approval(
        action_type=action_type,
        subject=subject,
        rationale=rationale,
        evidence=evidence,
        requested_by=user_id,
        status="pending",
    )
    db.add(approval)
    return approval
