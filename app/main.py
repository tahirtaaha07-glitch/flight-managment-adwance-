from __future__ import annotations

import hashlib
import json
import secrets
import enum
import smtplib
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import jwt
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import Base, SessionLocal, engine, get_db
from app.models import (
    Approval,
    AuditEvent,
    AutomationOutbox,
    Booking,
    BookingStatus,
    Cabin,
    CurrencyRate,
    FareRule,
    Flight,
    FlightStatus,
    FraudScore,
    IdempotencyRecord,
    Inventory,
    PriceAlert,
    Role,
    Refund,
    Seat,
    SeatHold,
    SeatStatus,
    TravelCredit,
    User,
    WaitlistEntry,
    WorkflowStatus,
)
from app.schemas import (
    ApprovalCreate,
    ApprovalResponse,
    ApprovalDecision,
    AutomationResponse,
    BookingCancelResponse,
    BookingCancelRequest,
    BookingConfirmResponse,
    BookingResponse,
    CheckoutConfirm,
    CurrencyRateResponse,
    CurrencyRateUpdate,
    FlightCancelResponse,
    FlightCancelRequest,
    FlightResponse,
    FlightInput,
    FlightUpdate,
    HoldCreate,
    HoldListResponse,
    HoldResponse,
    ItineraryHoldCreate,
    LoginRequest,
    RegisterRequest,
    StaffCreate,
    PriceAlertCreate,
    PriceAlertResponse,
    PolicyAnswerResponse,
    SimpleStatusResponse,
    RebookRequest,
    RefundResolveRequest,
    RefundResolveResponse,
    SearchResponse,
    TokenResponse,
    UserResponse,
    WaitlistCreate,
    WaitlistClaimResponse,
    WaitlistPromotionResponse,
    WaitlistResponse,
)
from app.security import create_access_token, current_user, hash_password, require_admin, require_automation, require_super_admin, verify_password
from app.services import (
    assert_departure_open,
    audit,
    create_approval,
    enqueue,
    expire_holds_for_flight,
    flight_response,
    issue_credit_expiry,
    make_seat_numbers,
    reserve_seats,
    send_transactional_email,
    utc_now,
    validate_timezone,
)

settings = get_settings()
app = FastAPI(
    title="Northstar Flight Operations API",
    version="1.0.0",
    description="PostgreSQL-backed flight inventory, booking, approvals, and automation outbox.",
)
WEB_ROOT = Path(__file__).resolve().parent.parent


@app.get("/", include_in_schema=False)
def serve_frontend() -> FileResponse:
    return FileResponse(WEB_ROOT / "index.html")


@app.get("/script.js", include_in_schema=False)
def serve_frontend_script() -> FileResponse:
    return FileResponse(WEB_ROOT / "script.js", media_type="text/javascript")


@app.get("/styles.css", include_in_schema=False)
def serve_frontend_styles() -> FileResponse:
    return FileResponse(WEB_ROOT / "styles.css", media_type="text/css")


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Correlation-ID", "Accept-Language"],
)

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
IDEMPOTENCY_SKIP_PATHS = {"/api/auth/login", "/api/webhooks/stripe"}


@app.middleware("http")
async def idempotency_contract(request: Request, call_next):
    if not request.url.path.startswith("/api/") or request.method not in WRITE_METHODS or request.url.path in IDEMPOTENCY_SKIP_PATHS:
        return await call_next(request)
    key = request.headers.get("Idempotency-Key", "")
    if len(key) < 8 or len(key) > 100:
        return JSONResponse(
            status_code=400,
            content={"detail": "Every write requires an Idempotency-Key header of 8-100 characters"},
        )
    body = await request.body()
    auth = request.headers.get("Authorization", "")
    subject = "anonymous"
    if auth.startswith("Bearer "):
        try:
            claims = jwt.decode(auth[7:], settings.jwt_secret, algorithms=["HS256"])
            subject = str(claims.get("sub", "anonymous"))
        except jwt.InvalidTokenError:
            subject = hashlib.sha256(auth.encode()).hexdigest()[:16]
    record_key = f"{subject}:{key}"
    request_hash = hashlib.sha256(
        b"\0".join(
            (
                request.method.encode(),
                request.url.path.encode(),
                request.url.query.encode(),
                body,
            )
        )
    ).hexdigest()
    with SessionLocal() as db:
        existing = db.get(IdempotencyRecord, record_key)
        if existing:
            if existing.request_hash != request_hash:
                return JSONResponse(status_code=409, content={"detail": "Idempotency-Key was already used with a different request"})
            if existing.status == "completed" and existing.response_body is not None:
                return JSONResponse(status_code=existing.response_status or 200, content=existing.response_body)
            if existing.created_at and existing.created_at < utc_now() - timedelta(minutes=5):
                db.delete(existing)
                db.commit()
            else:
                return JSONResponse(status_code=409, content={"detail": "An operation with this Idempotency-Key is still processing"})
        db.add(IdempotencyRecord(key=record_key, request_hash=request_hash, status="processing"))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            return JSONResponse(status_code=409, content={"detail": "An operation with this Idempotency-Key is already processing"})

    delivered = False

    async def replay_body():
        nonlocal delivered
        if not delivered:
            delivered = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.disconnect"}

    request._receive = replay_body
    response = await call_next(request)
    response_body = b"".join([chunk async for chunk in response.body_iterator])
    content_type = response.headers.get("content-type", "")
    if response.status_code >= 500:
        with SessionLocal.begin() as db:
            db.delete(db.get(IdempotencyRecord, record_key))
    elif "application/json" in content_type:
        try:
            payload = json.loads(response_body)
        except json.JSONDecodeError:
            payload = {"detail": response_body.decode("utf-8", errors="replace")}
        with SessionLocal.begin() as db:
            record = db.get(IdempotencyRecord, record_key)
            if record:
                record.status = "completed"
                record.response_status = response.status_code
                record.response_body = payload if isinstance(payload, dict) else {"result": payload}
    headers = dict(response.headers)
    headers.pop("content-length", None)
    return Response(
        content=response_body,
        status_code=response.status_code,
        headers=headers,
        media_type=response.media_type,
        background=response.background,
    )


@app.on_event("startup")
def initialize_database() -> None:
    if settings.auto_create_schema:
        Base.metadata.create_all(bind=engine)
    if settings.bootstrap_admin_email and settings.bootstrap_admin_password:
        with SessionLocal.begin() as db:
            existing = db.scalar(select(User).where(User.email == settings.bootstrap_admin_email.lower()))
            if existing is None:
                db.add(
                    User(
                        email=settings.bootstrap_admin_email.lower(),
                        password_hash=hash_password(settings.bootstrap_admin_password),
                        role=Role.SUPER_ADMIN,
                    )
                )


def flight_or_404(db: Session, flight_id: int, *, lock: bool = False) -> Flight:
    statement = select(Flight).where(Flight.id == flight_id)
    if lock:
        statement = statement.with_for_update()
    flight = db.scalar(statement)
    if flight is None:
        raise HTTPException(status_code=404, detail="Flight not found")
    return flight


def booking_or_404(db: Session, booking_id: int, *, lock: bool = False) -> Booking:
    statement = select(Booking).where(Booking.id == booking_id)
    if lock:
        statement = statement.with_for_update()
    booking = db.scalar(statement)
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


def check_booking_access(booking: Booking, user: User) -> None:
    if user.role not in {Role.CUSTOMER, Role.SUPER_ADMIN, Role.OPS_AGENT} or (
        user.role == Role.CUSTOMER and booking.email.lower() != user.email.lower()
    ):
        raise HTTPException(status_code=403, detail="This booking does not belong to the authenticated user")


def hold_dict(hold: SeatHold) -> dict:
    return {
        "id": hold.id,
        "flight_id": hold.flight_id,
        "cabin": hold.cabin.value,
        "fare_rule": hold.fare_rule.value,
        "passengers": hold.passengers,
        "passenger_count": hold.passenger_count,
        "email": hold.email,
        "price_each": hold.price_each,
        "currency": hold.currency,
        "expires_at": hold.expires_at,
        "status": hold.status,
    }


def booking_dict(booking: Booking) -> dict:
    return {
        "id": booking.id,
        "reference": booking.reference,
        "flight_id": booking.flight_id,
        "cabin": booking.cabin.value,
        "fare_rule": booking.fare_rule.value,
        "status": booking.status.value,
        "passenger_count": booking.passenger_count,
        "passenger_names": booking.passenger_names,
        "email": booking.email,
        "price_each": booking.price_each,
        "currency": booking.currency,
        "schedule_notice": booking.schedule_notice,
        "itinerary_reference": booking.itinerary_reference,
        "created_at": booking.created_at,
    }


def waitlist_dict(entry: WaitlistEntry) -> dict:
    return {
        "id": entry.id,
        "flight_id": entry.flight_id,
        "cabin": entry.cabin.value,
        "passenger_name": entry.passenger_name,
        "passenger_email": entry.passenger_email,
        "loyalty_tier": entry.loyalty_tier,
        "fare_rule": entry.fare_rule.value,
        "status": entry.status,
        "claim_until": entry.claim_until,
        "created_at": entry.created_at,
    }


def audit_dict(event: AuditEvent) -> dict:
    return {
        "id": event.id,
        "actor": event.actor_label,
        "action": event.action,
        "entity_type": event.entity_type,
        "entity_id": event.entity_id,
        "before": event.before_state,
        "after": event.after_state,
        "rationale": event.rationale,
        "decision_rule": event.decision_rule,
        "correlation_id": event.correlation_id,
        "created_at": event.created_at,
    }


@app.get("/api/health")
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(select(1))
    return {"status": "ok", "database": "connected"}


@app.post("/api/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return TokenResponse(access_token=create_access_token(user), role=user.role)


@app.post("/api/auth/register", response_model=TokenResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = User(email=payload.email.lower(), password_hash=hash_password(payload.password), role=Role.CUSTOMER)
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account already exists for this email") from exc
    db.refresh(user)
    return TokenResponse(access_token=create_access_token(user), role=user.role)


@app.get("/api/auth/me", response_model=UserResponse)
def me(user: User = Depends(current_user)) -> User:
    return user


@app.post("/api/admin/users", status_code=201)
def create_staff(payload: StaffCreate, db: Session = Depends(get_db), _: User = Depends(require_super_admin)) -> dict:
    user = User(email=payload.email.lower(), password_hash=hash_password(payload.password), role=Role(payload.role))
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account already exists for this email") from exc
    db.refresh(user)
    return {"id": user.id, "email": user.email, "role": user.role.value}


@app.get("/api/bootstrap")
def bootstrap(db: Session = Depends(get_db), user: User = Depends(require_admin)) -> dict[str, Any]:
    flights = db.scalars(select(Flight).order_by(Flight.departure_at)).all()
    bookings = db.scalars(select(Booking).order_by(Booking.created_at.desc()).limit(300)).all()
    holds = db.scalars(select(SeatHold).where(SeatHold.status == "held").order_by(SeatHold.created_at.desc())).all()
    waitlist = db.scalars(select(WaitlistEntry).order_by(WaitlistEntry.created_at.desc()).limit(300)).all()
    approvals = db.scalars(select(Approval).order_by(Approval.created_at.desc()).limit(300)).all()
    refunds = db.scalars(select(Refund).order_by(Refund.created_at.desc()).limit(300)).all()
    audit_rows = db.scalars(select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(500)).all()
    return {
        "current_user": UserResponse.model_validate(user).model_dump(mode="json"),
        "flights": [flight_response(db, item) for item in flights],
        "bookings": [booking_dict(item) for item in bookings],
        "holds": [hold_dict(item) for item in holds],
        "waitlist": [waitlist_dict(item) for item in waitlist],
        "approvals": [
            {"id": item.id, "type": item.action_type, "subject": item.subject, "detail": item.rationale, "evidence": item.evidence, "status": item.status, "created_at": item.created_at}
            for item in approvals
        ],
        "refunds": [
            {"id": item.id, "booking_id": item.booking_id, "passenger_names": item.passenger_names, "amount": item.amount, "currency": item.currency, "status": item.status, "created_at": item.created_at, "resolved_at": item.resolved_at}
            for item in refunds
        ],
        "audit": [audit_dict(item) for item in audit_rows],
        "policy": {
            "price_hold_minutes": settings.price_hold_minutes,
            "waitlist_claim_minutes": settings.waitlist_claim_minutes,
            "refund_escalation_days": settings.refund_escalation_days,
            "overbooking": settings.overbooking_policy,
            "currency_conversion": "No exchange-rate provider configured; fares remain in the flight's stored currency.",
        },
    }


@app.get("/api/flights")
def list_flights(
    origin: str | None = None,
    destination: str | None = None,
    travel_date: date | None = None,
    status_filter: FlightStatus | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[dict]:
    statement = select(Flight).order_by(Flight.departure_at)
    if origin:
        statement = statement.where(Flight.origin_code == origin.upper())
    if destination:
        statement = statement.where(Flight.destination_code == destination.upper())
    if travel_date:
        statement = statement.where(Flight.departure_day == travel_date)
    if status_filter:
        statement = statement.where(Flight.status == status_filter)
    return [flight_response(db, item) for item in db.scalars(statement).all()]


@app.get("/api/flights/{flight_id}/seats")
def seat_map(flight_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> dict:
    flight = flight_or_404(db, flight_id)
    seats = db.scalars(select(Seat).where(Seat.flight_id == flight.id).order_by(Seat.cabin, Seat.seat_number)).all()
    return {
        "flight_id": flight.id,
        "flight_number": flight.flight_number,
        "layout": [
            {"seat_number": seat.seat_number, "cabin": seat.cabin.value, "status": seat.status.value}
            for seat in seats
        ],
    }


@app.get("/api/flights/search", response_model=SearchResponse)
def search_flights(
    origin: str = Query(min_length=3, max_length=3, pattern=r"^[A-Za-z]{3}$"),
    destination: str = Query(min_length=3, max_length=3, pattern=r"^[A-Za-z]{3}$"),
    travel_date: date = Query(...),
    passengers: int = Query(default=1, ge=1, le=9),
    currency: str | None = Query(default=None, pattern=r"^[A-Za-z]{3}$"),
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
) -> dict:
    if origin.upper() == destination.upper():
        raise HTTPException(status_code=422, detail="Origin and destination must differ")
    flights = db.scalars(
        select(Flight).where(
            Flight.origin_code == origin.upper(),
            Flight.destination_code == destination.upper(),
            Flight.departure_day == travel_date,
            Flight.status == FlightStatus.SCHEDULED,
        ).order_by(Flight.departure_at)
    ).all()
    results = []
    target_currency = currency.upper() if currency else None
    target_rate = Decimal("1") if target_currency == "USD" else None
    if target_currency and target_currency != "USD":
        target_rate_row = db.get(CurrencyRate, target_currency)
        if target_rate_row is None:
            raise HTTPException(status_code=409, detail=f"No configured exchange rate for {target_currency}")
        target_rate = target_rate_row.usd_per_unit
    for flight in flights:
        result = flight_response(db, flight)
        result["available_by_class"] = {
            cabin: count for cabin, count in result["available_by_class"].items() if count >= passengers
        }
        if result["available_by_class"]:
            result["requested_currency"] = target_currency or flight.currency
            result["currency_conversion_applied"] = False
            if target_currency and target_currency != flight.currency:
                source_rate_row = db.get(CurrencyRate, flight.currency) if flight.currency != "USD" else None
                source_rate = Decimal("1") if flight.currency == "USD" else (source_rate_row.usd_per_unit if source_rate_row else None)
                if source_rate is None:
                    raise HTTPException(status_code=409, detail=f"No configured exchange rate for source currency {flight.currency}")
                result["prices"] = {
                    cabin: (Decimal(str(price)) * source_rate / target_rate).quantize(Decimal("0.01"))
                    for cabin, price in result["prices"].items()
                }
                result["currency"] = target_currency
                result["currency_conversion_applied"] = True
            elif target_currency:
                result["currency_conversion_applied"] = True
            result["locale"] = accept_language or "en-US"
            results.append(result)
    return {"date": travel_date, "results": results}


@app.get("/api/itineraries/search")
def search_itineraries(
    origin: str = Query(min_length=3, max_length=3),
    destination: str = Query(min_length=3, max_length=3),
    travel_date: date = Query(...),
    cabin: Cabin = Query(...),
    passengers: int = Query(default=1, ge=1, le=9),
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
) -> dict:
    origin, destination = origin.upper(), destination.upper()
    flights = db.scalars(select(Flight).where(Flight.departure_day == travel_date, Flight.status == FlightStatus.SCHEDULED).order_by(Flight.departure_at)).all()
    available = []
    for flight in flights:
        row = db.scalar(select(Inventory).where(Inventory.flight_id == flight.id, Inventory.cabin == cabin))
        free = max(0, row.capacity - row.booked - row.held) if row and flight.status != FlightStatus.CANCELLED else 0
        if free >= passengers:
            available.append((flight, free))
    direct = [{"legs": [flight_response(db, flight)], "connection_minutes": 0} for flight, _ in available if flight.origin_code == origin and flight.destination_code == destination]
    connections = []
    for first, _ in available:
        if first.origin_code != origin:
            continue
        for second, _ in available:
            if second.origin_code != first.destination_code or second.destination_code != destination or second.id == first.id:
                continue
            gap = (second.departure_at - first.arrival_at).total_seconds() / 60
            if 45 <= gap <= 720:
                connections.append({"legs": [flight_response(db, first), flight_response(db, second)], "connection_minutes": int(gap)})
    return {"date": travel_date, "results": direct + connections}


def build_flight(db: Session, payload: FlightInput, creator: User) -> Flight:
    validate_timezone(payload.origin_timezone)
    validate_timezone(payload.destination_timezone)
    flight = Flight(
        flight_number=payload.flight_number,
        origin=payload.origin.strip(),
        destination=payload.destination.strip(),
        origin_code=payload.origin_code,
        destination_code=payload.destination_code,
        origin_timezone=payload.origin_timezone,
        destination_timezone=payload.destination_timezone,
        departure_at=payload.departure_at.astimezone(UTC),
        arrival_at=payload.arrival_at.astimezone(UTC),
        departure_day=payload.departure_at.astimezone(ZoneInfo(payload.origin_timezone)).date(),
        capacity=payload.capacity,
        currency=payload.currency,
        first_price=payload.first_price,
        business_price=payload.business_price,
        economy_price=payload.economy_price,
        created_by=creator.id,
    )
    db.add(flight)
    db.flush()
    allocations = [
        (Cabin.FIRST, payload.first_seats, payload.first_price, "F"),
        (Cabin.BUSINESS, payload.business_seats, payload.business_price, "B"),
        (Cabin.ECONOMY, payload.economy_seats, payload.economy_price, "E"),
    ]
    flight_prices = {}
    for cabin, seats_count, price, prefix in allocations:
        db.add(Inventory(flight_id=flight.id, cabin=cabin, capacity=seats_count, booked=0, held=0, overbooking_buffer=0))
        db.add_all(Seat(flight_id=flight.id, seat_number=seat, cabin=cabin) for seat in make_seat_numbers(seats_count, prefix))
        flight_prices[cabin.value] = str(price)
    audit(
        db,
        actor_id=creator.id,
        actor_label=f"{creator.email} · {creator.role.value}",
        action="flight.created",
        entity_type="flight",
        entity_id=flight.id,
        after={"flight_number": flight.flight_number, "route": f"{flight.origin_code}-{flight.destination_code}", "capacity": flight.capacity, "seats": flight_prices},
        rationale="Admin created flight; seat-class totals validated against aircraft capacity.",
        decision_rule="seat-class-sum-equals-capacity; no-overbooking",
    )
    return flight


@app.post("/api/flights", status_code=201, response_model=FlightResponse)
def create_flight(
    payload: FlightInput,
    db: Session = Depends(get_db),
    user: User = Depends(require_super_admin),
    correlation_id: str | None = Header(default=None, alias="X-Correlation-ID"),
) -> dict:
    try:
        flight = build_flight(db, payload, user)
        db.flush()
        enqueue(db, "flight.created", {"flight_id": flight.id, "flight_number": flight.flight_number})
        db.commit()
        return flight_response(db, flight)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Duplicate flight number for this departure day and route") from exc


@app.patch("/api/flights/{flight_id}", response_model=FlightResponse)
def update_flight(
    flight_id: int,
    payload: FlightUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
    correlation_id: str | None = Header(default=None, alias="X-Correlation-ID"),
) -> dict:
    flight = flight_or_404(db, flight_id, lock=True)
    update = payload.model_dump(exclude_unset=True)
    airline_initiated = bool(update.pop("airline_initiated", False))
    declared_capacity = update.pop("capacity", None)
    original_capacity = flight.capacity
    before = {
        "flight_number": flight.flight_number,
        "origin_code": flight.origin_code,
        "destination_code": flight.destination_code,
        "departure_at": flight.departure_at.isoformat(),
        "arrival_at": flight.arrival_at.isoformat(),
        "capacity": flight.capacity,
    }
    inventory_updates = {
        "First": update.pop("first_seats", None),
        "Business": update.pop("business_seats", None),
        "Economy": update.pop("economy_seats", None),
    }
    price_fields = {"First": "first_price", "Business": "business_price", "Economy": "economy_price"}
    price_updates = {cabin: update.pop(field, None) for cabin, field in price_fields.items()}
    new_currency = update.get("currency")
    if user.role != Role.SUPER_ADMIN and (any(value is not None for value in inventory_updates.values()) or declared_capacity is not None or new_currency):
        raise HTTPException(status_code=403, detail="Operations agents can edit route and schedule, not inventory, pricing, or currency")
    for key, value in update.items():
        if value is not None and key in {"origin_code", "destination_code", "flight_number", "currency"}:
            value = value.upper()
        if value is not None:
            setattr(flight, key, value)
    if flight.arrival_at <= flight.departure_at:
        raise HTTPException(status_code=422, detail="Arrival must be later than departure")
    if flight.origin_code == flight.destination_code:
        raise HTTPException(status_code=422, detail="Origin and destination must differ")
    flight.departure_at = flight.departure_at.astimezone(UTC)
    flight.arrival_at = flight.arrival_at.astimezone(UTC)
    flight.departure_day = flight.departure_at.astimezone(ZoneInfo(flight.origin_timezone)).date()
    if flight.origin_timezone:
        validate_timezone(flight.origin_timezone)
    if flight.destination_timezone:
        validate_timezone(flight.destination_timezone)
    rows = {
        row.cabin: row
        for row in db.scalars(select(Inventory).where(Inventory.flight_id == flight.id).with_for_update()).all()
    }
    totals = {}
    for cabin in Cabin:
        row = rows[cabin]
        requested = inventory_updates[cabin.value]
        new_capacity = row.capacity if requested is None else requested
        if new_capacity < row.booked + row.held:
            raise HTTPException(status_code=409, detail=f"{cabin.value} capacity cannot be reduced below booked and held seats")
        row.capacity = new_capacity
        totals[cabin.value] = new_capacity
    new_total = sum(totals.values())
    if new_total != (declared_capacity if declared_capacity is not None else original_capacity):
        raise HTTPException(status_code=422, detail="First + Business + Economy must equal aircraft capacity")
    flight.capacity = new_total
    if any(value is not None for value in inventory_updates.values()):
        for cabin in Cabin:
            row = rows[cabin]
            prefix = {Cabin.FIRST: "F", Cabin.BUSINESS: "B", Cabin.ECONOMY: "E"}[cabin]
            existing_seats = db.scalars(
                select(Seat).where(Seat.flight_id == flight.id, Seat.cabin == cabin).order_by(Seat.seat_number).with_for_update()
            ).all()
            requested = row.capacity
            if requested < len(existing_seats):
                removable = [seat for seat in existing_seats if seat.status == SeatStatus.AVAILABLE][: len(existing_seats) - requested]
                if len(removable) < len(existing_seats) - requested:
                    raise HTTPException(status_code=409, detail=f"Cannot shrink {cabin.value} seat map below assigned seat count")
                for seat in removable:
                    db.delete(seat)
            elif requested > len(existing_seats):
                start = max((int(seat.seat_number[1:]) for seat in existing_seats), default=0) + 1
                db.add_all(Seat(flight_id=flight.id, cabin=cabin, seat_number=f"{prefix}{number:03d}") for number in range(start, requested + 1))
    for cabin, price in price_updates.items():
        if price is not None:
            setattr(flight, price_fields[cabin], price)
            enqueue(db, "fare.price_changed", {"flight_id": flight.id, "cabin": cabin, "new_price": str(price)})
    schedule_changed = before["departure_at"] != flight.departure_at.isoformat() or before["arrival_at"] != flight.arrival_at.isoformat()
    route_changed = before["origin_code"] != flight.origin_code or before["destination_code"] != flight.destination_code
    affected = db.scalars(select(Booking).where(Booking.flight_id == flight.id, Booking.status == BookingStatus.CONFIRMED).with_for_update()).all()
    for booking in affected:
        if schedule_changed or route_changed:
            booking.schedule_notice = f"Airline schedule update: {flight.origin_code} → {flight.destination_code}, {flight.departure_at.isoformat()}"
            if airline_initiated:
                enqueue(db, "booking.airline_schedule_change", {"booking_id": booking.id, "flight_id": flight.id, "fare_rule": booking.fare_rule.value, "automatic_rebook": True, "fare_policy_override": True})
    after = {"flight_number": flight.flight_number, "origin_code": flight.origin_code, "destination_code": flight.destination_code, "departure_at": flight.departure_at.isoformat(), "arrival_at": flight.arrival_at.isoformat(), "capacity": flight.capacity, "seats": totals}
    audit(
        db,
        actor_id=user.id,
        actor_label=f"{user.email} · {user.role.value}",
        action="flight.updated",
        entity_type="flight",
        entity_id=flight.id,
        before=before,
        after=after,
        rationale=f"Flight change cascaded to {len(affected)} confirmed booking(s); schedule and route notices recorded.",
        decision_rule="class-capacity>=booked+held; class-sum-equals-aircraft-capacity",
        correlation_id=correlation_id,
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Flight number conflicts with an existing flight on this day and route") from exc
    return flight_response(db, flight)


@app.post("/api/flights/{flight_id}/cancel", response_model=FlightCancelResponse)
def cancel_flight(
    flight_id: int,
    payload: FlightCancelRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_super_admin),
    correlation_id: str | None = Header(default=None, alias="X-Correlation-ID"),
) -> dict:
    flight = flight_or_404(db, flight_id, lock=True)
    if flight.status == FlightStatus.CANCELLED:
        return {"flight_id": flight.id, "status": flight.status.value, "resolution": payload.resolution, "affected_bookings": 0}
    before = {"status": flight.status.value}
    flight.status = FlightStatus.CANCELLED
    expire_holds_for_flight(db, flight.id, datetime.max.replace(tzinfo=UTC))
    holds = db.scalars(select(SeatHold).where(SeatHold.flight_id == flight.id, SeatHold.status.in_(["held", "waitlist_claim"])).with_for_update()).all()
    for hold in holds:
        inventory = db.scalar(select(Inventory).where(Inventory.flight_id == flight.id, Inventory.cabin == hold.cabin).with_for_update())
        if inventory:
            inventory.held -= hold.passenger_count
        for seat in db.scalars(select(Seat).where(Seat.hold_id == hold.id).with_for_update()).all():
            seat.status, seat.hold_id = SeatStatus.AVAILABLE, None
        hold.status = "cancelled"
    for entry in db.scalars(select(WaitlistEntry).where(WaitlistEntry.flight_id == flight.id, WaitlistEntry.status.in_(["waiting", "claim_window"])).with_for_update()).all():
        entry.status = "cancelled"
    affected = db.scalars(select(Booking).where(Booking.flight_id == flight.id, Booking.status == BookingStatus.CONFIRMED).with_for_update()).all()
    for booking in affected:
        inventory = db.scalar(
            select(Inventory)
            .where(Inventory.flight_id == flight.id, Inventory.cabin == booking.cabin)
            .with_for_update()
        )
        if inventory:
            inventory.booked -= booking.passenger_count
        for seat in db.scalars(
            select(Seat)
            .where(Seat.booking_id == booking.id, Seat.status == SeatStatus.BOOKED)
            .with_for_update()
        ).all():
            seat.status, seat.booking_id, seat.passenger_name = SeatStatus.AVAILABLE, None, None
        booking.schedule_notice = f"Flight cancelled; resolution: {payload.resolution}"
        if payload.resolution == "refund":
            booking.status = BookingStatus.REFUND_PENDING
            db.add(Refund(booking_id=booking.id, passenger_names=booking.passenger_names, amount=booking.price_each * booking.passenger_count, currency=booking.currency, status="pending"))
            enqueue(db, "refund.requested", {"booking_id": booking.id, "reason": "flight_cancellation", "fare_policy_override": True})
        elif payload.resolution == "rebooking":
            booking.status = BookingStatus.REBOOKING_REQUIRED
            enqueue(db, "booking.rebooking_requested", {"booking_id": booking.id, "cancelled_flight_id": flight.id, "fare_policy_override": True})
        else:
            booking.status = BookingStatus.CREDIT_ISSUED
            db.add(TravelCredit(booking_id=booking.id, passenger_email=booking.email, amount=booking.price_each * booking.passenger_count, currency=booking.currency, expires_at=issue_credit_expiry()))
            enqueue(db, "travel_credit.issued", {"booking_id": booking.id})
    audit(db, actor_id=user.id, actor_label=f"{user.email} · {user.role.value}", action="flight.cancelled", entity_type="flight", entity_id=flight.id, before=before, after={"status": "cancelled", "resolution": payload.resolution, "affected_bookings": len(affected)}, rationale="Flight cancellation takes precedence over waitlist promotion; bookings queued for selected resolution.", decision_rule="cancel-wins-over-seat-promotion", correlation_id=correlation_id)
    enqueue(db, "flight.cancelled", {"flight_id": flight.id, "resolution": payload.resolution, "booking_count": len(affected)})
    db.commit()
    return {"flight_id": flight.id, "status": flight.status.value, "resolution": payload.resolution, "affected_bookings": len(affected)}


@app.post("/api/holds", status_code=201, response_model=HoldResponse)
def create_hold(payload: HoldCreate, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    flight = flight_or_404(db, payload.flight_id, lock=True)
    assert_departure_open(flight, payload.cabin)
    expired = expire_holds_for_flight(db, flight.id)
    db.flush()
    requested = len(payload.passengers)
    inventory = db.scalar(select(Inventory).where(Inventory.flight_id == flight.id, Inventory.cabin == payload.cabin).with_for_update())
    if inventory is None:
        raise HTTPException(status_code=404, detail="Cabin inventory was not found")
    remaining = inventory.capacity - inventory.booked - inventory.held
    if remaining < requested:
        if payload.group_behavior == "all_or_nothing" or remaining <= 0:
            raise HTTPException(status_code=409, detail=f"Requested {requested} seats but only {max(remaining, 0)} are available")
        passengers = payload.passengers[:remaining]
    else:
        passengers = payload.passengers
    inventory, seats = reserve_seats(db, flight.id, payload.cabin, len(passengers))
    key = secrets.token_urlsafe(24)
    hold = SeatHold(
        flight_id=flight.id,
        cabin=payload.cabin,
        fare_rule=payload.fare_rule,
        passenger_count=len(passengers),
        passengers=[passenger.name for passenger in passengers],
        email=str(payload.email),
        price_each=flight_price(flight, payload.cabin),
        currency=flight.currency,
        expires_at=utc_now() + timedelta(minutes=settings.price_hold_minutes),
        status="held",
        idempotency_key=key,
    )
    db.add(hold)
    db.flush()
    for seat in seats:
        seat.status, seat.hold_id = SeatStatus.HELD, hold.id
    audit(db, actor_id=user.id, actor_label=user.email, action="seat_hold.created", entity_type="seat_hold", entity_id=hold.id, after={"flight_id": flight.id, "cabin": payload.cabin.value, "quantity": len(passengers), "fare_rule": payload.fare_rule.value, "price_each": str(hold.price_each), "expires_at": hold.expires_at.isoformat()}, rationale="Atomic inventory row lock reserved physical seats and fare price.", decision_rule="hard-no-oversell;idempotent-write")
    enqueue(db, "booking.hold_created", {"hold_id": hold.id, "flight_id": flight.id, "passenger_count": len(passengers), "expired_holds_released": expired})
    db.commit()
    db.refresh(hold)
    return hold_dict(hold)


def flight_price(flight: Flight, cabin: Cabin) -> Decimal:
    return {
        Cabin.FIRST: flight.first_price,
        Cabin.BUSINESS: flight.business_price,
        Cabin.ECONOMY: flight.economy_price,
    }[cabin]


@app.post("/api/itineraries/holds", status_code=201, response_model=HoldListResponse)
def create_itinerary_hold(payload: ItineraryHoldCreate, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    locked = {flight.id: flight for flight in (flight_or_404(db, flight_id, lock=True) for flight_id in sorted(payload.flight_ids))}
    flights = [locked[flight_id] for flight_id in payload.flight_ids]
    ordered = sorted(flights, key=lambda flight: flight.departure_at)
    for current, following in zip(ordered, ordered[1:]):
        if current.destination_code != following.origin_code or following.departure_at - current.arrival_at < timedelta(minutes=45):
            raise HTTPException(status_code=422, detail="Itinerary legs must connect with at least 45 minutes")
    group_id = secrets.token_urlsafe(18)
    created: list[SeatHold] = []
    try:
        for flight in ordered:
            assert_departure_open(flight, payload.cabin)
            expire_holds_for_flight(db, flight.id)
            db.flush()
            inventory, seats = reserve_seats(db, flight.id, payload.cabin, len(payload.passengers))
            hold = SeatHold(
                flight_id=flight.id,
                cabin=payload.cabin,
                fare_rule=payload.fare_rule,
                passenger_count=len(payload.passengers),
                passengers=[passenger.name for passenger in payload.passengers],
                email=str(payload.email),
                price_each=flight_price(flight, payload.cabin),
                currency=flight.currency,
                expires_at=utc_now() + timedelta(minutes=settings.price_hold_minutes),
                status="held",
                idempotency_key=f"{group_id}-{flight.id}",
                group_id=group_id,
            )
            db.add(hold)
            db.flush()
            for seat in seats:
                seat.status, seat.hold_id = SeatStatus.HELD, hold.id
            created.append(hold)
        enqueue(db, "itinerary.hold_created", {"group_id": group_id, "hold_ids": [hold.id for hold in created]})
        audit(db, actor_id=user.id, actor_label=user.email, action="itinerary.hold_created", entity_type="itinerary", entity_id=group_id, after={"flights": [flight.id for flight in ordered], "passengers": len(payload.passengers)}, rationale="All flight legs reserved in one transaction; failure rolls back every leg.", decision_rule="all-legs-or-none;hard-no-oversell")
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"group_id": group_id, "holds": [hold_dict(hold) for hold in created]}


def confirm_hold_locked(db: Session, hold: SeatHold, user: User | None) -> list[Booking]:
    holds = db.scalars(
        select(SeatHold)
        .where(SeatHold.group_id == hold.group_id if hold.group_id else SeatHold.id == hold.id)
        .with_for_update()
    ).all()
    existing_bookings = [
        booking
        for item in holds
        if (booking := db.scalar(select(Booking).where(Booking.idempotency_key == item.idempotency_key))) is not None
    ]
    if len(existing_bookings) == len(holds):
        return existing_bookings
    if existing_bookings:
        raise HTTPException(status_code=409, detail="Only some itinerary legs are booked; reconciliation is required")
    if not holds or any(item.status != "held" or item.expires_at <= utc_now() for item in holds):
        raise HTTPException(status_code=409, detail="One or more itinerary legs are no longer held; no booking was confirmed")
    bookings = []
    itinerary_ref = secrets.token_hex(6).upper() if len(holds) > 1 else None
    for item in holds:
        flight = flight_or_404(db, item.flight_id, lock=True)
        if flight.status != FlightStatus.SCHEDULED:
            raise HTTPException(status_code=409, detail=f"Flight {flight.flight_number} is no longer bookable")
        inventory = db.scalar(select(Inventory).where(Inventory.flight_id == item.flight_id, Inventory.cabin == item.cabin).with_for_update())
        if not inventory or inventory.held < item.passenger_count:
            raise HTTPException(status_code=409, detail="Held inventory was changed; no booking was confirmed")
        booking = Booking(
            reference=secrets.token_urlsafe(8).replace("-", "").upper()[:12],
            flight_id=item.flight_id,
            cabin=item.cabin,
            fare_rule=item.fare_rule,
            status=BookingStatus.CONFIRMED,
            passenger_count=item.passenger_count,
            passenger_names=item.passengers,
            email=item.email,
            price_each=item.price_each,
            currency=item.currency,
            idempotency_key=item.idempotency_key,
            itinerary_reference=itinerary_ref,
        )
        db.add(booking)
        db.flush()
        seats = db.scalars(select(Seat).where(Seat.hold_id == item.id, Seat.status == SeatStatus.HELD).with_for_update()).all()
        if len(seats) != item.passenger_count:
            raise HTTPException(status_code=409, detail="Physical seat hold is incomplete; no booking was confirmed")
        for seat_index, seat in enumerate(seats):
            seat.status, seat.booking_id, seat.hold_id = SeatStatus.BOOKED, booking.id, None
            seat.passenger_name = item.passengers[seat_index]
        inventory.held -= item.passenger_count
        inventory.booked += item.passenger_count
        item.status = "confirmed"
        bookings.append(booking)
        enqueue(db, "booking.confirmed", {"booking_id": booking.id, "flight_id": flight.id, "itinerary_reference": itinerary_ref})
        audit(db, actor_id=user.id if user else None, actor_label=user.email if user else "Stripe payment webhook", action="booking.confirmed", entity_type="booking", entity_id=booking.reference, after={"flight_id": flight.id, "cabin": item.cabin.value, "passenger_count": item.passenger_count, "fare_rule": item.fare_rule.value, "price_each": str(item.price_each)}, rationale="Confirmed from paid Stripe checkout and active price hold; inventory converted atomically from held to booked.", decision_rule="stripe-paid;idempotent-key;row-locked-inventory")
    return bookings


def stripe_client():
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe checkout is not configured; set STRIPE_SECRET_KEY")
    import stripe

    stripe.api_key = settings.stripe_secret_key
    return stripe


@app.post("/api/holds/{hold_id}/checkout")
def create_checkout_session(hold_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    hold = db.get(SeatHold, hold_id)
    if hold is None:
        raise HTTPException(status_code=404, detail="Seat hold not found")
    flight_ids = [hold.flight_id]
    if hold.group_id:
        flight_ids = db.scalars(select(SeatHold.flight_id).where(SeatHold.group_id == hold.group_id)).all()
    for flight_id in sorted(set(flight_ids)):
        flight_or_404(db, flight_id, lock=True)
    hold = db.scalar(select(SeatHold).where(SeatHold.id == hold_id).with_for_update())
    if hold is None:
        raise HTTPException(status_code=404, detail="Seat hold not found")
    if user.role == Role.CUSTOMER and hold.email.lower() != user.email.lower():
        raise HTTPException(status_code=403, detail="This hold does not belong to the authenticated user")
    holds = [hold]
    if hold.group_id:
        holds = db.scalars(
            select(SeatHold)
            .where(SeatHold.group_id == hold.group_id)
            .order_by(SeatHold.id)
            .with_for_update()
        ).all()
    if not holds or any(item.status != "held" or item.expires_at <= utc_now() for item in holds):
        raise HTTPException(status_code=410, detail="One or more seat/price holds expired")
    if len({item.currency for item in holds}) != 1:
        raise HTTPException(status_code=422, detail="Connecting itinerary legs must use one currency for checkout")
    expires_at = min(item.expires_at for item in holds)
    if expires_at < utc_now() + timedelta(minutes=30):
        raise HTTPException(status_code=409, detail="Hold has less than Stripe's 30-minute checkout window remaining; create a new hold")
    stripe = stripe_client()
    try:
        checkout = stripe.checkout.Session.create(
            mode="payment",
            customer_email=hold.email,
            line_items=[
                {
                    "quantity": item.passenger_count,
                    "price_data": {
                        "currency": item.currency.lower(),
                        "unit_amount": int(item.price_each * 100),
                        "product_data": {
                            "name": f"Flight {flight_or_404(db, item.flight_id).flight_number} · {item.cabin.value}"
                        },
                    },
                }
                for item in holds
            ],
            metadata={"hold_id": str(hold.id), "group_id": hold.group_id or ""},
            success_url=f"{settings.frontend_base_url.rstrip('/')}/?payment_session_id={{CHECKOUT_SESSION_ID}}&hold_id={hold.id}",
            cancel_url=f"{settings.frontend_base_url.rstrip('/')}/?payment_cancelled=1&hold_id={hold.id}",
            expires_at=int(expires_at.timestamp()),
        )
    except stripe.StripeError as exc:
        raise HTTPException(status_code=502, detail="Payment provider could not create checkout session") from exc
    for item in holds:
        item.payment_session_id = checkout.id
    total = sum((item.price_each * item.passenger_count for item in holds), Decimal("0.00"))
    audit(db, actor_id=user.id, actor_label=user.email, action="payment.checkout_created", entity_type="seat_hold", entity_id=hold.group_id or hold.id, after={"checkout_session_id": checkout.id, "amount": str(total), "currency": hold.currency, "hold_ids": [item.id for item in holds]}, rationale="Stripe-hosted checkout includes every held itinerary leg; booking is not confirmed until signed/verified paid status.", decision_rule="payment-provider-confirmation-required")
    db.commit()
    return {"checkout_url": checkout.url, "expires_at": hold.expires_at}


@app.post("/api/holds/{hold_id}/confirm", response_model=BookingConfirmResponse)
def confirm_hold(hold_id: int, payload: CheckoutConfirm, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    hold = db.get(SeatHold, hold_id)
    if hold is None:
        raise HTTPException(status_code=404, detail="Seat hold not found")
    flight_ids = [hold.flight_id]
    if hold.group_id:
        flight_ids = db.scalars(select(SeatHold.flight_id).where(SeatHold.group_id == hold.group_id).order_by(SeatHold.flight_id)).all()
    for flight_id in sorted(set(flight_ids)):
        flight_or_404(db, flight_id, lock=True)
    hold = db.scalar(select(SeatHold).where(SeatHold.id == hold_id).with_for_update())
    if hold is None:
        raise HTTPException(status_code=404, detail="Seat hold not found")
    if user.role == Role.CUSTOMER and hold.email.lower() != user.email.lower():
        raise HTTPException(status_code=403, detail="This hold does not belong to the authenticated user")
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe checkout is not configured")
    stripe = stripe_client()
    try:
        checkout = stripe.checkout.Session.retrieve(payload.checkout_session_id)
    except stripe.StripeError as exc:
        raise HTTPException(status_code=502, detail="Unable to verify payment session") from exc
    if checkout.id != hold.payment_session_id or str(checkout.metadata.get("hold_id")) != str(hold.id):
        raise HTTPException(status_code=403, detail="Payment session does not match this seat hold")
    if checkout.payment_status != "paid":
        raise HTTPException(status_code=409, detail="Payment is not completed; the seat remains on hold until expiry")
    expected_total = sum((item.price_each * item.passenger_count for item in db.scalars(
        select(SeatHold).where(SeatHold.group_id == hold.group_id) if hold.group_id else select(SeatHold).where(SeatHold.id == hold.id)
    ).all()), Decimal("0.00"))
    if checkout.amount_total != int(expected_total * 100) or checkout.currency != hold.currency.lower():
        raise HTTPException(status_code=409, detail="Paid checkout total does not match the active price hold")
    bookings = confirm_hold_locked(db, hold, user)
    db.commit()
    response = [booking_dict(booking) for booking in bookings]
    for booking in bookings:
        try:
            sent = send_transactional_email(
                booking.email,
                f"Booking confirmation {booking.reference}",
                f"Your booking {booking.reference} is confirmed for flight {booking.flight_id}. Fare: {booking.fare_rule.value}.",
            )
            if sent:
                enqueue(db, "email.transactional_sent", {"booking_reference": booking.reference, "recipient": booking.email})
        except (OSError, smtplib.SMTPException) as exc:  # type: ignore[name-defined]
            enqueue(db, "email.transactional_failed", {"booking_reference": booking.reference, "error": str(exc)})
    db.commit()
    return {"bookings": response, "transactional_email_configured": bool(settings.gmail_username and settings.gmail_app_password)}


@app.post("/api/webhooks/stripe")
async def stripe_webhook(request: Request, stripe_signature: str | None = Header(default=None, alias="Stripe-Signature")) -> dict[str, bool]:
    if not settings.stripe_webhook_secret or not stripe_signature:
        raise HTTPException(status_code=503, detail="Stripe webhook signing secret is not configured")
    stripe = stripe_client()
    body = await request.body()
    try:
        event = stripe.Webhook.construct_event(body, stripe_signature, settings.stripe_webhook_secret)
    except stripe.SignatureVerificationError as exc:
        raise HTTPException(status_code=400, detail="Invalid Stripe webhook signature or payload") from exc
    if event.type == "checkout.session.completed":
        session_data = event.data.object
        if session_data.payment_status != "paid":
            return {"received": True}
        if not session_data.metadata or not session_data.metadata.get("hold_id"):
            raise HTTPException(status_code=400, detail="Stripe session is missing hold metadata")
        hold_id = int(session_data.metadata.hold_id)
        with SessionLocal.begin() as db:
            hold = db.get(SeatHold, hold_id)
            if hold is None:
                raise HTTPException(status_code=404, detail="Seat hold not found")
            flight_ids = [hold.flight_id]
            if hold.group_id:
                flight_ids = db.scalars(select(SeatHold.flight_id).where(SeatHold.group_id == hold.group_id).order_by(SeatHold.flight_id)).all()
            for flight_id in sorted(set(flight_ids)):
                flight_or_404(db, flight_id, lock=True)
            hold = db.scalar(select(SeatHold).where(SeatHold.id == hold_id).with_for_update())
            if hold is None:
                raise HTTPException(status_code=404, detail="Seat hold not found")
            if hold.payment_session_id != session_data.id:
                raise HTTPException(status_code=403, detail="Stripe session does not match this hold")
            bookings = confirm_hold_locked(db, hold, None)
            references = [booking.reference for booking in bookings]
        with SessionLocal() as db:
            confirmed = db.scalars(select(Booking).where(Booking.reference.in_(references))).all()
            for booking in confirmed:
                try:
                    send_transactional_email(
                        booking.email,
                        f"Booking confirmation {booking.reference}",
                        f"Your booking {booking.reference} is confirmed. Fare: {booking.fare_rule.value}.",
                    )
                except (OSError, smtplib.SMTPException) as exc:
                    enqueue(db, "email.transactional_failed", {"booking_reference": booking.reference, "error": str(exc)})
            db.commit()
    elif event.type == "checkout.session.expired":
        session_data = event.data.object
        if not session_data.metadata or not session_data.metadata.get("hold_id"):
            return {"received": True}
        hold_id = int(session_data.metadata.hold_id)
        with SessionLocal.begin() as db:
            hold = db.get(SeatHold, hold_id)
            if hold:
                flight_or_404(db, hold.flight_id, lock=True)
            hold = db.scalar(select(SeatHold).where(SeatHold.id == hold_id).with_for_update())
            if hold and hold.payment_session_id == session_data.id and hold.status == "held":
                expire_holds_for_flight(db, hold.flight_id, datetime.max.replace(tzinfo=UTC))
    return {"received": True}


@app.delete("/api/holds/{hold_id}", response_model=SimpleStatusResponse)
def release_hold(hold_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    hold = db.get(SeatHold, hold_id)
    if hold is None:
        raise HTTPException(status_code=404, detail="Seat hold not found")
    flight_or_404(db, hold.flight_id, lock=True)
    hold = db.scalar(select(SeatHold).where(SeatHold.id == hold_id).with_for_update())
    if hold is None:
        raise HTTPException(status_code=404, detail="Seat hold not found")
    if user.role == Role.CUSTOMER and hold.email.lower() != user.email.lower():
        raise HTTPException(status_code=403, detail="This hold does not belong to the authenticated user")
    if hold.status == "held":
        inventory = db.scalar(select(Inventory).where(Inventory.flight_id == hold.flight_id, Inventory.cabin == hold.cabin).with_for_update())
        if inventory:
            inventory.held -= hold.passenger_count
        for seat in db.scalars(select(Seat).where(Seat.hold_id == hold.id).with_for_update()).all():
            seat.status, seat.hold_id = SeatStatus.AVAILABLE, None
        hold.status = "released"
        audit(db, actor_id=user.id, actor_label=user.email, action="seat_hold.released", entity_type="seat_hold", entity_id=hold.id, rationale="Unpaid checkout hold released; seats returned to availability.")
    db.commit()
    return {"id": hold.id, "status": hold.status}


@app.get("/api/bookings", response_model=list[BookingResponse])
def list_bookings(db: Session = Depends(get_db), _: User = Depends(require_admin)) -> list[dict]:
    return [booking_dict(item) for item in db.scalars(select(Booking).order_by(Booking.created_at.desc())).all()]


@app.get("/api/bookings/mine", response_model=list[BookingResponse])
def my_bookings(db: Session = Depends(get_db), user: User = Depends(current_user)) -> list[dict]:
    return [booking_dict(item) for item in db.scalars(select(Booking).where(Booking.email == user.email).order_by(Booking.created_at.desc())).all()]


@app.post("/api/bookings/{booking_id}/rebook", response_model=BookingResponse)
def rebook_booking(
    booking_id: int,
    payload: RebookRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> dict:
    booking = booking_or_404(db, booking_id, lock=True)
    if booking.status != BookingStatus.REBOOKING_REQUIRED:
        raise HTTPException(status_code=409, detail="Booking is not awaiting rebooking")
    target = flight_or_404(db, payload.destination_flight_id, lock=True)
    if target.status != FlightStatus.SCHEDULED:
        raise HTTPException(status_code=409, detail="Replacement flight is not scheduled")
    if (target.origin_code, target.destination_code) != (
        flight_or_404(db, booking.flight_id).origin_code,
        flight_or_404(db, booking.flight_id).destination_code,
    ):
        raise HTTPException(status_code=422, detail="Replacement flight must use the same route")
    inventory, seats = reserve_seats(db, target.id, booking.cabin, booking.passenger_count)
    inventory.held -= booking.passenger_count
    inventory.booked += booking.passenger_count
    for index, seat in enumerate(seats):
        seat.status = SeatStatus.BOOKED
        seat.booking_id = booking.id
        seat.passenger_name = booking.passenger_names[index]
    previous_flight_id = booking.flight_id
    booking.flight_id = target.id
    booking.status = BookingStatus.CONFIRMED
    booking.schedule_notice = f"Rebooked on {target.flight_number}; original fare preserved."
    booking.currency = target.currency
    audit(db, actor_id=user.id, actor_label=user.email, action="booking.rebooked", entity_type="booking", entity_id=booking.reference, before={"flight_id": previous_flight_id}, after={"flight_id": target.id, "fare_policy_override": payload.fare_policy_override, "fare_rule": booking.fare_rule.value}, rationale="Airline-initiated schedule disruption; replacement seat atomically allocated and original fare rule preserved.", decision_rule="airline-rebooking-fare-policy-override")
    enqueue(db, "booking.rebooked", {"booking_id": booking.id, "from_flight_id": previous_flight_id, "to_flight_id": target.id})
    db.commit()
    return booking_dict(booking)


@app.post("/api/bookings/{booking_id}/cancel", response_model=BookingCancelResponse)
def cancel_booking(
    booking_id: int,
    payload: BookingCancelRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> dict:
    booking = booking_or_404(db, booking_id, lock=True)
    check_booking_access(booking, user)
    if booking.status != BookingStatus.CONFIRMED:
        raise HTTPException(status_code=409, detail="Only confirmed bookings can be cancelled")
    selected = set(payload.passenger_names)
    if len(selected) != len(payload.passenger_names) or not selected.issubset(set(booking.passenger_names)):
        raise HTTPException(status_code=422, detail="Passenger list contains duplicates or names not on this booking")
    remaining_names = [name for name in booking.passenger_names if name not in selected]
    inventory = db.scalar(select(Inventory).where(Inventory.flight_id == booking.flight_id, Inventory.cabin == booking.cabin).with_for_update())
    if inventory:
        inventory.booked -= len(selected)
    assigned_seats = db.scalars(
        select(Seat)
        .where(Seat.booking_id == booking.id, Seat.status == SeatStatus.BOOKED, Seat.passenger_name.in_(selected))
        .order_by(Seat.seat_number)
        .limit(len(selected))
        .with_for_update()
    ).all()
    if len(assigned_seats) != len(selected):
        raise HTTPException(status_code=409, detail="Passenger seat assignments are inconsistent; reconcile before cancellation")
    for seat in assigned_seats:
        seat.status, seat.booking_id, seat.passenger_name = SeatStatus.AVAILABLE, None, None
    amount = booking.price_each * len(selected)
    resolution = "non_refundable"
    if payload.treatment == "refund_exception":
        approval = create_approval(db, "refund_exception", f"Booking {booking.reference}", "Manual refund exception requested; fare rule does not grant automatic refund.", {"requested_amount": str(amount), "fare_rule": booking.fare_rule.value, "passengers": list(selected)}, user.id)
        db.flush()
        enqueue(db, "approval.created", {"approval_id": approval.id})
        resolution = "human_approval_required"
    elif payload.treatment == "travel_credit" or booking.fare_rule == FareRule.CREDIT_ONLY:
        db.add(TravelCredit(booking_id=booking.id, passenger_email=booking.email, amount=amount, currency=booking.currency, expires_at=issue_credit_expiry()))
        resolution = "travel_credit_issued"
    elif booking.fare_rule == FareRule.REFUNDABLE or booking.fare_rule == FareRule.FLEXIBLE:
        refund = Refund(booking_id=booking.id, passenger_names=list(selected), amount=amount, currency=booking.currency, status="pending")
        db.add(refund)
        enqueue(db, "refund.requested", {"refund_id": refund.id, "booking_id": booking.id, "amount": str(amount), "fare_rule": booking.fare_rule.value})
        resolution = "standard_refund_auto_approved"
    booking.passenger_names = remaining_names
    booking.passenger_count = len(remaining_names)
    if not remaining_names:
        booking.status = BookingStatus.CANCELLED
    audit(db, actor_id=user.id, actor_label=user.email, action="booking.passengers_cancelled", entity_type="booking", entity_id=booking.reference, before={"passengers": payload.passenger_names, "fare_rule": booking.fare_rule.value}, after={"remaining_passengers": remaining_names, "treatment": resolution, "amount": str(amount), "remaining_fare_each": str(booking.price_each)}, rationale="Fare-aware partial cancellation; remaining passengers retain their booked per-passenger fare because no group-discount rule is configured.", decision_rule=f"fare-rule:{booking.fare_rule.value}")
    enqueue(db, "booking.cancelled", {"booking_id": booking.id, "passengers": list(selected), "resolution": resolution})
    db.commit()
    return {"booking": booking_dict(booking), "cancelled_passengers": list(selected), "amount": amount, "resolution": resolution}


@app.get("/api/waitlist", response_model=list[WaitlistResponse])
def list_waitlist(db: Session = Depends(get_db), _: User = Depends(require_admin)) -> list[dict]:
    query = select(WaitlistEntry).order_by(WaitlistEntry.loyalty_rank.desc(), WaitlistEntry.created_at.asc())
    return [waitlist_dict(item) for item in db.scalars(query).all()]


@app.post("/api/waitlist", status_code=201, response_model=WaitlistResponse)
def join_waitlist(payload: WaitlistCreate, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    flight = flight_or_404(db, payload.flight_id, lock=True)
    if flight.status != FlightStatus.SCHEDULED:
        raise HTTPException(status_code=409, detail="Waitlist is only available for scheduled flights")
    inventory = db.scalar(select(Inventory).where(Inventory.flight_id == flight.id, Inventory.cabin == payload.cabin).with_for_update())
    if not inventory:
        raise HTTPException(status_code=404, detail="Cabin inventory was not found")
    expire_holds_for_flight(db, flight.id)
    db.flush()
    if inventory.capacity - inventory.booked - inventory.held > 0:
        raise HTTPException(status_code=409, detail="Seats are still available; book instead of joining the waitlist")
    duplicate = db.scalar(select(WaitlistEntry).where(WaitlistEntry.flight_id == flight.id, WaitlistEntry.cabin == payload.cabin, WaitlistEntry.passenger_email == str(payload.passenger_email), WaitlistEntry.status.in_(["waiting", "claim_window"])))
    if duplicate:
        raise HTTPException(status_code=409, detail="Passenger is already on this flight/cabin waitlist")
    loyalty_rank = {"standard": 0, "silver": 1, "gold": 2, "platinum": 3}[payload.loyalty_tier]
    entry = WaitlistEntry(
        flight_id=flight.id,
        cabin=payload.cabin,
        passenger_name=payload.passenger_name,
        passenger_email=str(payload.passenger_email),
        loyalty_tier=payload.loyalty_tier,
        loyalty_rank=loyalty_rank,
        fare_rule=payload.fare_rule,
    )
    db.add(entry)
    db.flush()
    audit(db, actor_id=user.id, actor_label=user.email, action="waitlist.joined", entity_type="waitlist", entity_id=entry.id, after={"flight_id": flight.id, "cabin": payload.cabin.value, "loyalty_tier": payload.loyalty_tier, "priority": "loyalty desc, created_at asc"}, rationale="Flight/cabin sold out; passenger added to priority queue.")
    db.commit()
    return waitlist_dict(entry)


def promote_one(db: Session, user: User | None = None) -> dict | None:
    now = utc_now()
    expired_ids = db.scalars(
        select(WaitlistEntry.id)
        .where(WaitlistEntry.status == "claim_window", WaitlistEntry.claim_until <= now)
        .order_by(WaitlistEntry.flight_id, WaitlistEntry.id)
    ).all()
    for entry_id in expired_ids:
        candidate = db.get(WaitlistEntry, entry_id)
        if candidate is None:
            continue
        flight = db.scalar(select(Flight).where(Flight.id == candidate.flight_id).with_for_update(skip_locked=True))
        if flight is None:
            continue
        entry = db.scalar(
            select(WaitlistEntry)
            .where(WaitlistEntry.id == entry_id, WaitlistEntry.status == "claim_window", WaitlistEntry.claim_until <= now)
            .with_for_update(skip_locked=True)
        )
        if entry is None:
            continue
        hold = db.get(SeatHold, entry.promotion_hold_id) if entry.promotion_hold_id else None
        if hold is not None:
            db.refresh(hold, with_for_update=True)
        if hold and hold.status == "waitlist_claim":
            inventory = db.scalar(select(Inventory).where(Inventory.flight_id == hold.flight_id, Inventory.cabin == hold.cabin).with_for_update())
            if inventory:
                inventory.held -= hold.passenger_count
            for seat in db.scalars(select(Seat).where(Seat.hold_id == hold.id).with_for_update()).all():
                seat.status, seat.hold_id = SeatStatus.AVAILABLE, None
            hold.status = "expired"
        entry.status = "waiting"
        entry.claim_until = None
        entry.promotion_hold_id = None
    candidates = db.execute(
        select(WaitlistEntry.id, WaitlistEntry.flight_id)
        .join(Flight, Flight.id == WaitlistEntry.flight_id)
        .where(WaitlistEntry.status == "waiting", Flight.status == FlightStatus.SCHEDULED)
        .order_by(WaitlistEntry.loyalty_rank.desc(), WaitlistEntry.created_at.asc())
    ).all()
    for entry_id, candidate_flight_id in candidates:
        flight = db.scalar(select(Flight).where(Flight.id == candidate_flight_id).with_for_update(skip_locked=True))
        if not flight or flight.status != FlightStatus.SCHEDULED:
            continue
        entry = db.scalar(
            select(WaitlistEntry)
            .where(WaitlistEntry.id == entry_id, WaitlistEntry.status == "waiting")
            .with_for_update(skip_locked=True)
        )
        if not entry:
            continue
        inventory = db.scalar(select(Inventory).where(Inventory.flight_id == flight.id, Inventory.cabin == entry.cabin).with_for_update(skip_locked=True))
        if not inventory or inventory.capacity - inventory.booked - inventory.held < 1:
            continue
        seat = db.scalar(
            select(Seat)
            .where(Seat.flight_id == flight.id, Seat.cabin == entry.cabin, Seat.status == SeatStatus.AVAILABLE)
            .order_by(Seat.seat_number)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if not seat:
            continue
        inventory.held += 1
        entry.status = "claim_window"
        entry.claim_until = now + timedelta(minutes=settings.waitlist_claim_minutes)
        hold = SeatHold(
            flight_id=flight.id,
            cabin=entry.cabin,
            fare_rule=entry.fare_rule,
            passenger_count=1,
            passengers=[entry.passenger_name],
            email=entry.passenger_email,
            price_each=flight_price(flight, entry.cabin),
            currency=flight.currency,
            expires_at=entry.claim_until,
            status="waitlist_claim",
            idempotency_key=f"waitlist-{entry.id}-{secrets.token_hex(8)}",
        )
        db.add(hold)
        db.flush()
        entry.promotion_hold_id = hold.id
        seat.status, seat.hold_id = SeatStatus.HELD, hold.id
        audit(db, actor_id=user.id if user else None, actor_label=user.email if user else "n8n waitlist worker", action="waitlist.promoted", entity_type="waitlist", entity_id=entry.id, after={"status": "claim_window", "claim_until": entry.claim_until.isoformat(), "seat_number": seat.seat_number}, rationale="Seat and queue row locked in one transaction; claim offer expires before the next eligible passenger is selected.", decision_rule="loyalty-desc-created-asc;for-update-skip-locked;cancel-wins")
        enqueue(db, "waitlist.seat_offered", {"waitlist_id": entry.id, "flight_id": flight.id, "claim_until": entry.claim_until.isoformat()})
        return waitlist_dict(entry)
    return None


@app.post("/api/automations/waitlist/promote", response_model=WaitlistPromotionResponse)
def promote_waitlist(db: Session = Depends(get_db), user: User = Depends(require_automation)) -> dict:
    entry = promote_one(db, user)
    db.commit()
    return {"promoted": entry is not None, "entry": entry}


@app.post("/api/waitlist/{entry_id}/claim", response_model=WaitlistClaimResponse)
def claim_waitlist(entry_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    entry = db.get(WaitlistEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Waitlist entry not found")
    flight = flight_or_404(db, entry.flight_id, lock=True)
    entry = db.scalar(select(WaitlistEntry).where(WaitlistEntry.id == entry_id).with_for_update())
    if entry is None or entry.status != "claim_window" or not entry.claim_until or entry.claim_until <= utc_now():
        raise HTTPException(status_code=410, detail="Waitlist offer is expired or no longer available")
    if flight.status != FlightStatus.SCHEDULED:
        raise HTTPException(status_code=409, detail="Flight was cancelled; the promotion has been invalidated")
    hold = db.get(SeatHold, entry.promotion_hold_id) if entry.promotion_hold_id else None
    if hold is not None:
        db.refresh(hold, with_for_update=True)
    if hold is None or hold.status != "waitlist_claim":
        raise HTTPException(status_code=409, detail="Promotion seat reservation is missing")
    inventory = db.scalar(select(Inventory).where(Inventory.flight_id == flight.id, Inventory.cabin == entry.cabin).with_for_update())
    seat = db.scalar(select(Seat).where(Seat.hold_id == hold.id, Seat.status == SeatStatus.HELD).with_for_update())
    if inventory is None or seat is None or inventory.held < 1:
        raise HTTPException(status_code=409, detail="Promotion seat was already assigned")
    booking = Booking(
        reference=secrets.token_urlsafe(8).replace("-", "").upper()[:12],
        flight_id=flight.id,
        cabin=entry.cabin,
        fare_rule=entry.fare_rule,
        status=BookingStatus.CONFIRMED,
        passenger_count=1,
        passenger_names=[entry.passenger_name],
        email=entry.passenger_email,
        price_each=hold.price_each,
        currency=hold.currency,
        idempotency_key=f"waitlist-claim-{entry.id}",
    )
    db.add(booking)
    db.flush()
    inventory.held -= 1
    inventory.booked += 1
    seat.status, seat.hold_id, seat.booking_id = SeatStatus.BOOKED, None, booking.id
    seat.passenger_name = entry.passenger_name
    entry.status = "claimed"
    entry.booking_id = booking.id
    hold.status = "confirmed"
    audit(db, actor_id=user.id, actor_label=user.email, action="waitlist.claimed", entity_type="waitlist", entity_id=entry.id, after={"booking_reference": booking.reference}, rationale="Claimed within offer window; reserved physical seat atomically converted to booked.")
    enqueue(db, "booking.confirmed", {"booking_id": booking.id, "source": "waitlist"})
    db.commit()
    return {"booking": booking_dict(booking), "waitlist": waitlist_dict(entry)}


@app.post("/api/approvals", status_code=201, response_model=ApprovalResponse)
def create_approval_endpoint(payload: ApprovalCreate, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    approval = create_approval(db, payload.action_type, payload.subject, payload.rationale, payload.evidence, user.id)
    db.flush()
    audit(db, actor_id=user.id, actor_label=user.email, action="approval.requested", entity_type="approval", entity_id=approval.id, after={"action_type": approval.action_type, "subject": approval.subject, "evidence": approval.evidence}, rationale=approval.rationale, decision_rule="human-signoff-required")
    enqueue(db, "approval.created", {"approval_id": approval.id})
    db.commit()
    return {"id": approval.id, "status": approval.status}


@app.get("/api/approvals")
def list_approvals(db: Session = Depends(get_db), _: User = Depends(require_admin)) -> list[dict]:
    rows = db.scalars(select(Approval).order_by(Approval.created_at.desc())).all()
    return [{"id": row.id, "type": row.action_type, "subject": row.subject, "detail": row.rationale, "evidence": row.evidence, "status": row.status, "created_at": row.created_at} for row in rows]


@app.post("/api/approvals/{approval_id}/decision", response_model=ApprovalResponse)
def decide_approval(
    approval_id: int,
    payload: ApprovalDecision,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> dict:
    approval = db.scalar(select(Approval).where(Approval.id == approval_id).with_for_update())
    if approval is None:
        raise HTTPException(status_code=404, detail="Approval request not found")
    if approval.status != "pending":
        raise HTTPException(status_code=409, detail="Approval has already been decided")
    approval.status = payload.decision
    approval.reviewed_by = user.id
    approval.reviewed_at = utc_now()
    audit(db, actor_id=user.id, actor_label=user.email, action=f"approval.{payload.decision}", entity_type="approval", entity_id=approval.id, before={"status": "pending"}, after={"status": payload.decision, "reviewer": user.email}, rationale=payload.rationale, decision_rule="human-review-before-customer-email")
    if payload.decision == "approved" and approval.action_type == "rag_response":
        enqueue(db, "email.approved_rag_response", {"approval_id": approval.id, "subject": approval.subject, "draft": approval.evidence.get("draft"), "recipient": approval.evidence.get("recipient"), "fare_rule": approval.evidence.get("fare_rule")})
    db.commit()
    return {"id": approval.id, "status": approval.status}


@app.post("/api/bookings/{booking_id}/policy-answer", response_model=PolicyAnswerResponse)
def draft_fare_aware_answer(booking_id: int, question: str = Query(min_length=5, max_length=1000), db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    booking = booking_or_404(db, booking_id)
    check_booking_access(booking, user)
    fare = booking.fare_rule
    rules = {
        FareRule.BASIC_ECONOMY: "Your Basic Economy fare does not allow voluntary changes or advance seat selection. Voluntary cancellation is non-refundable.",
        FareRule.FLEXIBLE: "Your Flexible fare allows changes subject to any fare difference. Cancellation follows the purchased fare terms.",
        FareRule.REFUNDABLE: "Your Refundable fare is eligible for a refund under the fare conditions; processing time depends on payment provider.",
        FareRule.CREDIT_ONLY: "Your fare is eligible for travel credit, not a refund to the original payment method. Credit expiration is shown in the booking terms.",
        FareRule.NON_REFUNDABLE: "Your fare is non-refundable for voluntary cancellation. Airline-initiated cancellations may have separate rebooking/refund protections.",
    }
    answer = f"Based on booking {booking.reference} and its actual {fare.value} fare: {rules[fare]}\n\nFor your question: {question}\n\nA policy reviewer must approve this draft before it is emailed."
    approval = create_approval(db, "rag_response", f"Booking {booking.reference} · policy response", "Fare-aware answer drafted from the booking's stored fare rule; verify cited policy and customer context.", {"booking_id": booking.id, "fare_rule": fare.value, "question": question, "draft": answer, "recipient": booking.email}, user.id)
    db.flush()
    audit(db, actor_id=user.id, actor_label=user.email, action="policy.answer_drafted", entity_type="booking", entity_id=booking.reference, after={"approval_id": approval.id, "fare_rule": fare.value}, rationale="Draft grounded in the fare rule actually stored on this booking; human approval required before outbound email.", decision_rule="fare-aware-rag-human-approval")
    enqueue(db, "approval.created", {"approval_id": approval.id, "type": "rag_response"})
    db.commit()
    return {"answer": answer, "fare_rule": fare.value, "approval_id": approval.id, "email_sent": False}


@app.post("/api/price-alerts", status_code=201, response_model=PriceAlertResponse)
def create_price_alert(payload: PriceAlertCreate, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    flight = flight_or_404(db, payload.flight_id)
    try:
        alert = PriceAlert(email=str(payload.email), flight_id=flight.id, cabin=payload.cabin, target_price=payload.target_price, materiality_amount=payload.materiality_amount)
        db.add(alert)
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Price alert already exists for this email/flight/cabin") from exc
    audit(db, actor_id=user.id, actor_label=user.email, action="price_alert.created", entity_type="price_alert", entity_id=alert.id, after={"flight_id": flight.id, "cabin": payload.cabin.value, "target": str(payload.target_price), "materiality": str(payload.materiality_amount)}, rationale="Deduped by subscriber, flight, and cabin; notify only on material price change.")
    db.commit()
    return {"id": alert.id, "status": "active"}


@app.get("/api/currency-rates", response_model=list[CurrencyRateResponse])
def list_currency_rates(db: Session = Depends(get_db), _: User = Depends(require_admin)) -> list[dict]:
    rows = db.scalars(select(CurrencyRate).order_by(CurrencyRate.currency)).all()
    return [{"currency": "USD", "usd_per_unit": Decimal("1.00000000"), "updated_at": None}] + [
        {"currency": row.currency, "usd_per_unit": row.usd_per_unit, "updated_at": row.updated_at} for row in rows if row.currency != "USD"
    ]


@app.put("/api/currency-rates/{currency}", response_model=CurrencyRateResponse)
def update_currency_rate(
    currency: str,
    payload: CurrencyRateUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_super_admin),
) -> dict:
    currency = currency.upper()
    if not currency.isalpha() or len(currency) != 3:
        raise HTTPException(status_code=422, detail="Currency must be a three-letter ISO code")
    if currency == "USD" and payload.usd_per_unit != Decimal("1"):
        raise HTTPException(status_code=422, detail="USD is the base currency and must have a rate of 1")
    if currency == "USD":
        raise HTTPException(status_code=409, detail="USD is the fixed base currency")
    rate = db.get(CurrencyRate, currency)
    if rate is None:
        rate = CurrencyRate(currency=currency, usd_per_unit=payload.usd_per_unit, updated_by=user.id)
        db.add(rate)
    else:
        rate.usd_per_unit = payload.usd_per_unit
        rate.updated_by = user.id
    audit(db, actor_id=user.id, actor_label=user.email, action="currency_rate.updated", entity_type="currency_rate", entity_id=currency, after={"usd_per_unit": str(payload.usd_per_unit)}, rationale="Exchange rate explicitly configured by super-admin; no implicit or stale third-party rate is assumed.")
    db.commit()
    db.refresh(rate)
    return {"currency": rate.currency, "usd_per_unit": rate.usd_per_unit, "updated_at": rate.updated_at}


@app.get("/api/audit")
def get_audit(limit: int = Query(default=200, ge=1, le=1000), db: Session = Depends(get_db), _: User = Depends(require_admin)) -> list[dict]:
    rows = db.scalars(select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(limit)).all()
    return [audit_dict(row) for row in rows]


@app.get("/api/reports/operations")
def operations_report(
    start: date | None = None,
    end: date | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict:
    statement = select(Flight).order_by(Flight.departure_at)
    if start:
        statement = statement.where(Flight.departure_day >= start)
    if end:
        statement = statement.where(Flight.departure_day <= end)
    rows = []
    for flight in db.scalars(statement).all():
        booked = db.scalar(select(func.coalesce(func.sum(Inventory.booked), 0)).where(Inventory.flight_id == flight.id)) or 0
        sold = db.scalars(select(Booking).where(Booking.flight_id == flight.id, Booking.status == BookingStatus.CONFIRMED)).all()
        revenue = sum((booking.price_each * booking.passenger_count for booking in sold), Decimal("0.00"))
        rows.append({"flight_id": flight.id, "flight_number": flight.flight_number, "route": f"{flight.origin_code}-{flight.destination_code}", "status": flight.status.value, "load_factor": round(int(booked) / flight.capacity, 4), "booked": int(booked), "capacity": flight.capacity, "revenue": revenue, "currency": flight.currency})
    return {"start": start, "end": end, "flights": rows}


@app.get("/api/refunds")
def get_refunds(db: Session = Depends(get_db), _: User = Depends(require_admin)) -> list[dict]:
    rows = db.scalars(select(Refund).order_by(Refund.created_at.desc())).all()
    return [{"id": row.id, "booking_id": row.booking_id, "passengers": row.passenger_names, "amount": row.amount, "currency": row.currency, "status": row.status, "created_at": row.created_at, "resolved_at": row.resolved_at} for row in rows]


@app.post("/api/refunds/{refund_id}/resolve", response_model=RefundResolveResponse)
def resolve_refund(
    refund_id: int,
    payload: RefundResolveRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> dict:
    refund = db.scalar(select(Refund).where(Refund.id == refund_id).with_for_update())
    if refund is None:
        raise HTTPException(status_code=404, detail="Refund not found")
    if refund.status not in {"pending", "processing"}:
        raise HTTPException(status_code=409, detail="Refund has already been resolved")
    refund.status = payload.status
    if payload.status == "succeeded":
        refund.resolved_at = utc_now()
    else:
        enqueue(db, "refund.failed", {"refund_id": refund.id, "reason": payload.reason, "provider_reference": payload.provider_reference})
    audit(db, actor_id=user.id, actor_label=user.email, action=f"refund.{payload.status}", entity_type="refund", entity_id=refund.id, before={"status": "pending"}, after={"status": payload.status, "provider_reference": payload.provider_reference}, rationale=payload.reason, decision_rule="refund-state-transition")
    db.commit()
    return {"id": refund.id, "status": refund.status}


@app.post("/api/automations/{workflow}", response_model=AutomationResponse)
def run_automation(workflow: str, db: Session = Depends(get_db), user: User = Depends(require_automation)) -> dict:
    allowed = {    "checkin_reminders", "price_drop_alerts", "operations_report", "refund_escalation", "fraud_recent", "fraud_historical", "policy_ingestion", "waitlist_promotion", "reconciliation", "expire_holds"}
    if workflow not in allowed:
        raise HTTPException(status_code=404, detail="Unknown automation workflow")
    started = utc_now()
    summary: dict[str, Any] = {}
    processed = 0
    if workflow == "checkin_reminders":
        flights = db.scalars(select(Flight).where(Flight.status == FlightStatus.SCHEDULED)).all()
        for flight in flights:
            validate_timezone(flight.origin_timezone)
            local_departure = flight.departure_at.astimezone(__import__("zoneinfo").ZoneInfo(flight.origin_timezone))
            if started <= local_departure - timedelta(hours=24) < started + timedelta(hours=1):
                bookings = db.scalars(select(Booking).where(Booking.flight_id == flight.id, Booking.status == BookingStatus.CONFIRMED)).all()
                for booking in bookings:
                    enqueue(db, "notification.checkin_reminder", {"booking_id": booking.id, "flight_id": flight.id, "origin_timezone": flight.origin_timezone, "destination_timezone": flight.destination_timezone})
                    processed += 1
        summary = {"cancelled_flights_suppressed": True, "timezone": "origin airport"}
    elif workflow == "refund_escalation":
        threshold = started - timedelta(days=settings.refund_escalation_days)
        refunds = db.scalars(select(Refund).where(Refund.status.in_(["pending", "processing"]), Refund.created_at <= threshold)).all()
        for refund in refunds:
            enqueue(db, "notification.refund_escalation", {"refund_id": refund.id, "days_open": (started - refund.created_at).days})
        processed = len(refunds)
        summary = {"escalation_days": settings.refund_escalation_days, "refund_ids": [item.id for item in refunds]}
    elif workflow == "operations_report":
        report = operations_report(None, None, db, user)
        processed = len(report["flights"])
        summary = {"flights": report["flights"], "source": "PostgreSQL"}
        enqueue(db, "report.daily_operations", {"report": json_safe(summary)})
    elif workflow == "waitlist_promotion":
        promoted = promote_one(db, user)
        processed = int(promoted is not None)
        summary = {"promotion": promoted}
    elif workflow in {"fraud_recent", "fraud_historical"}:
        enqueue(db, f"n8n.{workflow}", {"requested_by": user.email, "requested_at": started.isoformat()})
        summary = {"delegated_to_n8n": True, "scoring": "review-only; n8n writes fraud_scores"}
        processed = 1
    elif workflow == "price_drop_alerts":
        alerts = db.scalars(select(PriceAlert)).all()
        for alert in alerts:
            flight = flight_or_404(db, alert.flight_id)
            price = flight_price(flight, alert.cabin)
            if alert.target_price - price >= alert.materiality_amount and (alert.last_notified_price is None or alert.last_notified_price - price >= alert.materiality_amount):
                enqueue(db, "notification.price_drop", {"alert_id": alert.id, "flight_id": flight.id, "price": str(price), "currency": flight.currency})
                alert.last_notified_price = price
                processed += 1
        summary = {"materiality_threshold": "per subscriber alert", "deduplicated": True}
    else:
        enqueue(db, f"n8n.{workflow}", {"requested_by": user.email, "requested_at": started.isoformat()})
        summary = {"delegated_to_n8n": True, "note": "n8n credentialed worker owns Pinecone ingestion or reconciliation"}
        processed = 1
    finished = utc_now()
    audit(db, actor_id=user.id, actor_label=user.email, action="automation.run", entity_type="automation", entity_id=workflow, after={"processed": processed, "summary": json_safe(summary)}, rationale="Authorized scheduled/manual workflow run; effects written to transactional outbox.", decision_rule="durable-outbox;workflow-idempotency")
    db.commit()
    return {"workflow": workflow, "processed": processed, "details": json_safe(summary), "started_at": started, "finished_at": finished}


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key.value if isinstance(key, Cabin) else key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, enum.Enum):  # type: ignore[name-defined]
        return value.value
    return value


@app.post("/api/reconciliation/run")
def reconciliation(db: Session = Depends(get_db), user: User = Depends(require_admin)) -> dict:
    issues: list[dict[str, Any]] = []
    inventories = db.scalars(select(Inventory).with_for_update()).all()
    for inventory in inventories:
        held_seats = db.scalar(select(func.count(Seat.id)).where(Seat.flight_id == inventory.flight_id, Seat.cabin == inventory.cabin, Seat.status == SeatStatus.HELD)) or 0
        booked_seats = db.scalar(select(func.count(Seat.id)).where(Seat.flight_id == inventory.flight_id, Seat.cabin == inventory.cabin, Seat.status == SeatStatus.BOOKED)) or 0
        if inventory.held != held_seats or inventory.booked != booked_seats:
            issues.append({"flight_id": inventory.flight_id, "cabin": inventory.cabin.value, "inventory_held": inventory.held, "seat_held": held_seats, "inventory_booked": inventory.booked, "seat_booked": booked_seats})
        if inventory.booked + inventory.held > inventory.capacity + inventory.overbooking_buffer:
            issues.append({"flight_id": inventory.flight_id, "cabin": inventory.cabin.value, "invariant": "over_capacity"})
    expired_processing = db.scalars(select(AutomationOutbox).where(AutomationOutbox.status == WorkflowStatus.PROCESSING, AutomationOutbox.lease_until < utc_now())).all()
    audit(db, actor_id=user.id, actor_label=user.email, action="reconciliation.completed", entity_type="automation", entity_id="reconciliation", after={"issues": issues, "expired_leases": [item.id for item in expired_processing]}, rationale="Compared inventory counters to physical seat states and reported expired outbox leases; n8n owns and requeues workflow status.")
    db.commit()
    return {"issue_count": len(issues), "issues": issues, "expired_leases": [item.id for item in expired_processing]}


@app.get("/api/system/ownership")
def ownership(_: User = Depends(require_admin)) -> dict:
    return {
        "source_of_truth": "PostgreSQL",
        "tables": {
            "fastapi_write_only": ["flights", "seat_inventory", "seats", "seat_holds", "bookings", "refunds", "travel_credits", "approvals", "audit_events", "idempotency_records"],
            "n8n_write_only": ["automation_runs", "policy_documents", "fraud_scores", "price_alerts"],
            "shared_contract": ["automation_outbox", "waitlist_entries"],
        },
        "change_detection": "Transactional outbox polling; PostgreSQL NOTIFY is optional wake-up, never the durable queue.",
        "claim_sql": "SELECT id FROM automation_outbox WHERE status='pending' AND available_at <= now() ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 25",
        "conflict_resolution": "Flight cancellation locks flight before inventory and waitlist rows; cancellation status wins, promotion must recheck within the same transaction.",
        "reconciliation": "/api/reconciliation/run checks seat/inventory counters and requeues expired n8n leases.",
    }
