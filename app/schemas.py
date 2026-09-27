from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.models import BookingStatus, Cabin, FareRule, FlightStatus, Role


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=256)


class StaffCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=256)
    role: Literal["ops_agent", "automation_worker"]


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    role: Role


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    role: Role


class FlightInput(BaseModel):
    flight_number: str = Field(min_length=2, max_length=12, pattern=r"^[A-Za-z0-9-]+$")
    origin: str = Field(min_length=2, max_length=160)
    destination: str = Field(min_length=2, max_length=160)
    origin_code: str = Field(min_length=3, max_length=3, pattern=r"^[A-Za-z]{3}$")
    destination_code: str = Field(min_length=3, max_length=3, pattern=r"^[A-Za-z]{3}$")
    origin_timezone: str = Field(default="UTC", max_length=64)
    destination_timezone: str = Field(default="UTC", max_length=64)
    departure_at: datetime
    arrival_at: datetime
    capacity: int = Field(gt=0)
    first_seats: int = Field(gt=0)
    business_seats: int = Field(gt=0)
    economy_seats: int = Field(gt=0)
    first_price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    business_price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    economy_price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    currency: str = Field(default="USD", pattern=r"^[A-Za-z]{3}$")

    @field_validator("departure_at", "arrival_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Datetime must include a UTC offset or timezone")
        return value

    @field_validator("flight_number", "origin_code", "destination_code", "currency")
    @classmethod
    def uppercase_codes(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def validate_schedule_and_capacity(self):
        if self.origin_code == self.destination_code:
            raise ValueError("Origin and destination airport codes must differ")
        if self.arrival_at <= self.departure_at:
            raise ValueError("Arrival must be later than departure")
        if self.first_seats + self.business_seats + self.economy_seats != self.capacity:
            raise ValueError("Cabin seat counts must sum exactly to aircraft capacity")
        return self


class FlightUpdate(BaseModel):
    flight_number: str | None = Field(default=None, min_length=2, max_length=12, pattern=r"^[A-Za-z0-9-]+$")
    origin: str | None = Field(default=None, min_length=2, max_length=160)
    destination: str | None = Field(default=None, min_length=2, max_length=160)
    origin_code: str | None = Field(default=None, min_length=3, max_length=3, pattern=r"^[A-Za-z]{3}$")
    destination_code: str | None = Field(default=None, min_length=3, max_length=3, pattern=r"^[A-Za-z]{3}$")
    origin_timezone: str | None = Field(default=None, max_length=64)
    destination_timezone: str | None = Field(default=None, max_length=64)
    departure_at: datetime | None = None
    arrival_at: datetime | None = None
    capacity: int | None = Field(default=None, gt=0)
    first_seats: int | None = Field(default=None, gt=0)
    business_seats: int | None = Field(default=None, gt=0)
    economy_seats: int | None = Field(default=None, gt=0)
    first_price: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    business_price: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    economy_price: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    currency: str | None = Field(default=None, pattern=r"^[A-Za-z]{3}$")
    airline_initiated: bool = False

    @field_validator("departure_at", "arrival_at")
    @classmethod
    def require_timezone_when_present(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("Datetime must include a UTC offset or timezone")
        return value


class FlightResponse(BaseModel):
    id: int
    flight_number: str
    origin: str
    destination: str
    origin_code: str
    destination_code: str
    origin_timezone: str
    destination_timezone: str
    departure_at: datetime
    arrival_at: datetime
    capacity: int
    status: FlightStatus
    currency: str
    prices: dict[Cabin, Decimal]
    available_by_class: dict[Cabin, int]
    seats_by_class: dict[Cabin, int]
    requested_currency: str | None = None
    currency_conversion_applied: bool | None = None


class SearchResponse(BaseModel):
    date: date
    results: list[FlightResponse]


class PassengerInput(BaseModel):
    name: str = Field(min_length=2, max_length=160)


class HoldCreate(BaseModel):
    flight_id: int
    cabin: Cabin
    fare_rule: FareRule
    passengers: list[PassengerInput] = Field(min_length=1, max_length=9)
    email: EmailStr
    group_behavior: Literal["partial", "all_or_nothing"] = "all_or_nothing"

    @model_validator(mode="after")
    def unique_passenger_names(self):
        names = [passenger.name.strip().casefold() for passenger in self.passengers]
        if len(names) != len(set(names)):
            raise ValueError("Passenger names must be unique in a group hold")
        return self


class ItineraryHoldCreate(BaseModel):
    flight_ids: list[int] = Field(min_length=2, max_length=4)
    cabin: Cabin
    fare_rule: FareRule
    passengers: list[PassengerInput] = Field(min_length=1, max_length=9)
    email: EmailStr

    @model_validator(mode="after")
    def unique_legs(self):
        if len(set(self.flight_ids)) != len(self.flight_ids):
            raise ValueError("An itinerary cannot contain a flight more than once")
        names = [passenger.name.strip().casefold() for passenger in self.passengers]
        if len(names) != len(set(names)):
            raise ValueError("Passenger names must be unique in a group hold")
        return self


class HoldResponse(BaseModel):
    id: int
    flight_id: int
    cabin: Cabin
    fare_rule: FareRule
    passengers: list[str]
    passenger_count: int
    email: EmailStr
    price_each: Decimal
    currency: str
    expires_at: datetime
    status: str


class CheckoutConfirm(BaseModel):
    checkout_session_id: str = Field(min_length=8, max_length=255)


class BookingResponse(BaseModel):
    id: int
    reference: str
    flight_id: int
    cabin: Cabin
    fare_rule: FareRule
    status: BookingStatus
    passenger_count: int
    passenger_names: list[str]
    email: EmailStr
    price_each: Decimal
    currency: str
    schedule_notice: str | None
    created_at: datetime


class HoldListResponse(BaseModel):
    group_id: str
    holds: list[HoldResponse]


class BookingConfirmResponse(BaseModel):
    bookings: list[BookingResponse]
    transactional_email_configured: bool


class BookingCancelResponse(BaseModel):
    booking: BookingResponse
    cancelled_passengers: list[str]
    amount: Decimal
    resolution: str


class SimpleStatusResponse(BaseModel):
    id: int
    status: str


class FlightCancelResponse(BaseModel):
    flight_id: int
    status: str
    resolution: str
    affected_bookings: int


class WaitlistResponse(BaseModel):
    id: int
    flight_id: int
    cabin: Cabin
    passenger_name: str
    passenger_email: EmailStr
    loyalty_tier: str
    fare_rule: FareRule
    status: str
    claim_until: datetime | None = None
    created_at: datetime


class WaitlistPromotionResponse(BaseModel):
    promoted: bool
    entry: WaitlistResponse | None


class WaitlistClaimResponse(BaseModel):
    booking: BookingResponse
    waitlist: WaitlistResponse


class ApprovalResponse(BaseModel):
    id: int
    status: str


class AutomationResponse(BaseModel):
    workflow: str
    processed: int
    details: dict[str, Any]
    started_at: datetime
    finished_at: datetime | None


class BookingCancelRequest(BaseModel):
    passenger_names: list[str] = Field(min_length=1)
    treatment: Literal["apply_fare_rule", "refund_exception", "travel_credit"] = "apply_fare_rule"


class FlightCancelRequest(BaseModel):
    resolution: Literal["refund", "rebooking", "travel_credit"]


class RebookRequest(BaseModel):
    destination_flight_id: int
    fare_policy_override: bool = True


class RefundResolveRequest(BaseModel):
    status: Literal["succeeded", "failed"]
    provider_reference: str | None = Field(default=None, max_length=255)
    reason: str = Field(min_length=4, max_length=1000)


class WaitlistCreate(BaseModel):
    flight_id: int
    cabin: Cabin
    passenger_name: str = Field(min_length=2, max_length=160)
    passenger_email: EmailStr
    loyalty_tier: Literal["standard", "silver", "gold", "platinum"] = "standard"
    fare_rule: FareRule = FareRule.FLEXIBLE


class ApprovalDecision(BaseModel):
    rationale: str = Field(min_length=4, max_length=2000)
    decision: Literal["approved", "rejected"]


class ApprovalCreate(BaseModel):
    action_type: str = Field(min_length=2, max_length=48)
    subject: str = Field(min_length=2, max_length=255)
    rationale: str = Field(min_length=4, max_length=2000)
    evidence: dict[str, Any] = Field(default_factory=dict)


class PriceAlertCreate(BaseModel):
    email: EmailStr
    flight_id: int
    cabin: Cabin
    target_price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    materiality_amount: Decimal = Field(default=Decimal("10.00"), gt=0, max_digits=12, decimal_places=2)


class PriceAlertResponse(BaseModel):
    id: int
    status: str


class PolicyAnswerResponse(BaseModel):
    answer: str
    fare_rule: FareRule
    approval_id: int
    email_sent: bool


class RefundResolveResponse(BaseModel):
    id: int
    status: str



class CurrencyRateUpdate(BaseModel):
    usd_per_unit: Decimal = Field(gt=0, max_digits=16, decimal_places=8)


class CurrencyRateResponse(BaseModel):
    currency: str
    usd_per_unit: Decimal
    updated_at: datetime | None


class AutomationResult(BaseModel):
    workflow: str
    processed: int
    details: dict[str, Any]


class BootstrapResponse(BaseModel):
    current_user: UserResponse
    flights: list[dict[str, Any]]
    bookings: list[dict[str, Any]]
    holds: list[dict[str, Any]]
    waitlist: list[dict[str, Any]]
    approvals: list[dict[str, Any]]
    refunds: list[dict[str, Any]]
    audit: list[dict[str, Any]]
