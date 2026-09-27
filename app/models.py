from __future__ import annotations

import enum
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from app.database import Base


class UTCDateTime(TypeDecorator[datetime]):
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("Datetime values must include a timezone")
        return value

    def process_result_value(self, value: datetime | None, dialect):
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value


class Role(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    OPS_AGENT = "ops_agent"
    CUSTOMER = "customer"
    AUTOMATION_WORKER = "automation_worker"


class Cabin(str, enum.Enum):
    FIRST = "First"
    BUSINESS = "Business"
    ECONOMY = "Economy"


class FlightStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    BOARDING = "boarding"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class SeatStatus(str, enum.Enum):
    AVAILABLE = "available"
    HELD = "held"
    BOOKED = "booked"


class FareRule(str, enum.Enum):
    BASIC_ECONOMY = "basic_economy"
    FLEXIBLE = "flexible"
    REFUNDABLE = "refundable"
    CREDIT_ONLY = "credit_only"
    NON_REFUNDABLE = "non_refundable"


class BookingStatus(str, enum.Enum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    REFUND_PENDING = "refund_pending"
    REBOOKING_REQUIRED = "rebooking_required"
    CREDIT_ISSUED = "credit_issued"


class WorkflowStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(Enum(Role, name="admin_role"), default=Role.OPS_AGENT)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, server_default=func.now())


class Flight(Base):
    __tablename__ = "flights"
    __table_args__ = (
        UniqueConstraint("flight_number", "origin_code", "destination_code", "departure_day", name="uq_flight_number_route_day"),
        CheckConstraint("capacity > 0", name="ck_flight_capacity_positive"),
        CheckConstraint("origin_code <> destination_code", name="ck_flight_distinct_airports"),
        Index("ix_flights_search", "origin_code", "destination_code", "departure_day", "status"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    flight_number: Mapped[str] = mapped_column(String(12))
    origin: Mapped[str] = mapped_column(String(160))
    destination: Mapped[str] = mapped_column(String(160))
    origin_code: Mapped[str] = mapped_column(String(3))
    destination_code: Mapped[str] = mapped_column(String(3))
    origin_timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    destination_timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    departure_at: Mapped[datetime] = mapped_column(UTCDateTime)
    arrival_at: Mapped[datetime] = mapped_column(UTCDateTime)
    departure_day: Mapped[date] = mapped_column(Date)
    capacity: Mapped[int] = mapped_column(Integer)
    status: Mapped[FlightStatus] = mapped_column(Enum(FlightStatus, name="flight_status"), default=FlightStatus.SCHEDULED)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    first_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("1840.00"))
    business_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("980.00"))
    economy_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("420.00"))
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, server_default=func.now())
    inventories: Mapped[list[Inventory]] = relationship(back_populates="flight", cascade="all, delete-orphan")
    seats: Mapped[list[Seat]] = relationship(back_populates="flight", cascade="all, delete-orphan")


class Inventory(Base):
    __tablename__ = "seat_inventory"
    __table_args__ = (
        CheckConstraint("capacity > 0", name="ck_inventory_capacity_positive"),
        CheckConstraint("booked >= 0 AND held >= 0 AND overbooking_buffer >= 0", name="ck_inventory_counts_nonnegative"),
        CheckConstraint("booked + held <= capacity + overbooking_buffer", name="ck_inventory_never_exceeds_limit"),
        UniqueConstraint("flight_id", "cabin", name="uq_inventory_flight_cabin"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    flight_id: Mapped[int] = mapped_column(ForeignKey("flights.id", ondelete="CASCADE"), index=True)
    cabin: Mapped[Cabin] = mapped_column(Enum(Cabin, name="cabin_class"))
    capacity: Mapped[int] = mapped_column(Integer)
    booked: Mapped[int] = mapped_column(Integer, default=0)
    held: Mapped[int] = mapped_column(Integer, default=0)
    overbooking_buffer: Mapped[int] = mapped_column(Integer, default=0)
    flight: Mapped[Flight] = relationship(back_populates="inventories")


class Seat(Base):
    __tablename__ = "seats"
    __table_args__ = (UniqueConstraint("flight_id", "seat_number", name="uq_seat_flight_number"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    flight_id: Mapped[int] = mapped_column(ForeignKey("flights.id", ondelete="CASCADE"), index=True)
    seat_number: Mapped[str] = mapped_column(String(5))
    cabin: Mapped[Cabin] = mapped_column(Enum(Cabin, name="cabin_class", create_type=False))
    passenger_name: Mapped[str | None] = mapped_column(String(160))
    status: Mapped[SeatStatus] = mapped_column(Enum(SeatStatus, name="seat_status"), default=SeatStatus.AVAILABLE)
    hold_id: Mapped[int | None] = mapped_column(ForeignKey("seat_holds.id", ondelete="SET NULL"))
    booking_id: Mapped[int | None] = mapped_column(ForeignKey("bookings.id", ondelete="SET NULL"))
    flight: Mapped[Flight] = relationship(back_populates="seats")


class SeatHold(Base):
    __tablename__ = "seat_holds"
    __table_args__ = (
        CheckConstraint("passenger_count > 0", name="ck_hold_passenger_count_positive"),
        Index("ix_seat_holds_payment_session_id", "payment_session_id"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    flight_id: Mapped[int] = mapped_column(ForeignKey("flights.id"), index=True)
    cabin: Mapped[Cabin] = mapped_column(Enum(Cabin, name="cabin_class", create_type=False))
    fare_rule: Mapped[FareRule] = mapped_column(Enum(FareRule, name="fare_rule"))
    passenger_count: Mapped[int] = mapped_column(Integer)
    passengers: Mapped[list[str]] = mapped_column(JSON)
    email: Mapped[str] = mapped_column(String(320))
    price_each: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3))
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    status: Mapped[str] = mapped_column(String(24), default="held")
    payment_session_id: Mapped[str | None] = mapped_column(String(255))
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True)
    group_id: Mapped[str | None] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, server_default=func.now())


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (CheckConstraint("passenger_count > 0", name="ck_booking_passengers_positive"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    flight_id: Mapped[int] = mapped_column(ForeignKey("flights.id"), index=True)
    cabin: Mapped[Cabin] = mapped_column(Enum(Cabin, name="cabin_class", create_type=False))
    fare_rule: Mapped[FareRule] = mapped_column(Enum(FareRule, name="fare_rule", create_type=False))
    status: Mapped[BookingStatus] = mapped_column(Enum(BookingStatus, name="booking_status"), default=BookingStatus.CONFIRMED)
    passenger_count: Mapped[int] = mapped_column(Integer)
    passenger_names: Mapped[list[str]] = mapped_column(JSON)
    email: Mapped[str] = mapped_column(String(320))
    price_each: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3))
    schedule_notice: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True)
    itinerary_reference: Mapped[str | None] = mapped_column(String(24), index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, server_default=func.now())


class Refund(Base):
    __tablename__ = "refunds"
    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"), index=True)
    passenger_names: Mapped[list[str]] = mapped_column(JSON)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3))
    status: Mapped[str] = mapped_column(String(24), default="pending")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(UTCDateTime)


class TravelCredit(Base):
    __tablename__ = "travel_credits"
    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"), index=True)
    passenger_email: Mapped[str] = mapped_column(String(320))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3))
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)
    status: Mapped[str] = mapped_column(String(24), default="issued")


class WaitlistEntry(Base):
    __tablename__ = "waitlist_entries"
    __table_args__ = (Index("ix_waitlist_priority", "flight_id", "cabin", "status", "loyalty_rank", "created_at"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    flight_id: Mapped[int] = mapped_column(ForeignKey("flights.id"), index=True)
    cabin: Mapped[Cabin] = mapped_column(Enum(Cabin, name="cabin_class", create_type=False))
    passenger_name: Mapped[str] = mapped_column(String(160))
    passenger_email: Mapped[str] = mapped_column(String(320))
    loyalty_tier: Mapped[str] = mapped_column(String(24), default="standard")
    loyalty_rank: Mapped[int] = mapped_column(Integer, default=0)
    fare_rule: Mapped[FareRule] = mapped_column(Enum(FareRule, name="fare_rule", create_type=False))
    status: Mapped[str] = mapped_column(String(24), default="waiting")
    claim_until: Mapped[datetime | None] = mapped_column(UTCDateTime)
    promotion_hold_id: Mapped[int | None] = mapped_column(ForeignKey("seat_holds.id"))
    booking_id: Mapped[int | None] = mapped_column(ForeignKey("bookings.id"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, server_default=func.now())


class Approval(Base):
    __tablename__ = "approvals"
    id: Mapped[int] = mapped_column(primary_key=True)
    action_type: Mapped[str] = mapped_column(String(48))
    subject: Mapped[str] = mapped_column(String(255))
    rationale: Mapped[str] = mapped_column(Text)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(24), default="pending")
    requested_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, server_default=func.now())


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    actor_label: Mapped[str] = mapped_column(String(320))
    action: Mapped[str] = mapped_column(String(96))
    entity_type: Mapped[str] = mapped_column(String(48))
    entity_id: Mapped[str] = mapped_column(String(96))
    before_state: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    after_state: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    rationale: Mapped[str] = mapped_column(Text)
    decision_rule: Mapped[str | None] = mapped_column(String(160))
    correlation_id: Mapped[str | None] = mapped_column(String(128), index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, server_default=func.now(), index=True)


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    request_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(24), default="processing")
    response_status: Mapped[int | None] = mapped_column(Integer)
    response_body: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, server_default=func.now())


class AutomationOutbox(Base):
    __tablename__ = "automation_outbox"
    __table_args__ = (Index("ix_outbox_poll", "status", "available_at", "created_at"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    topic: Mapped[str] = mapped_column(String(80))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    status: Mapped[WorkflowStatus] = mapped_column(Enum(WorkflowStatus, name="workflow_status"), default=WorkflowStatus.PENDING)
    available_at: Mapped[datetime] = mapped_column(UTCDateTime, server_default=func.now())
    lease_until: Mapped[datetime | None] = mapped_column(UTCDateTime)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, server_default=func.now())


class AutomationRun(Base):
    __tablename__ = "automation_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    workflow: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(24))
    summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    started_at: Mapped[datetime] = mapped_column(UTCDateTime, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime)


class PriceAlert(Base):
    __tablename__ = "price_alerts"
    __table_args__ = (UniqueConstraint("email", "flight_id", "cabin", name="uq_price_alert_subscriber_offer"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320))
    flight_id: Mapped[int] = mapped_column(ForeignKey("flights.id"))
    cabin: Mapped[Cabin] = mapped_column(Enum(Cabin, name="cabin_class", create_type=False))
    target_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    last_notified_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    materiality_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("10.00"))


class PolicyDocument(Base):
    __tablename__ = "policy_documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    document_key: Mapped[str] = mapped_column(String(255), unique=True)
    version: Mapped[str] = mapped_column(String(64))
    content_hash: Mapped[str] = mapped_column(String(64))
    source_uri: Mapped[str] = mapped_column(Text)
    indexed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, server_default=func.now())


class FraudScore(Base):
    __tablename__ = "fraud_scores"
    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"), index=True)
    score: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    signals: Mapped[dict[str, Any]] = mapped_column(JSON)
    source: Mapped[str] = mapped_column(String(32))
    reviewed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, server_default=func.now())


class CurrencyRate(Base):
    __tablename__ = "currency_rates"
    currency: Mapped[str] = mapped_column(String(3), primary_key=True)
    usd_per_unit: Mapped[Decimal] = mapped_column(Numeric(16, 8))
    updated_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, server_default=func.now(), onupdate=func.now())
