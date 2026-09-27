from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import AuditEvent, Booking, Flight, Inventory, Role, Seat, SeatHold, User
from app.security import create_access_token, hash_password


@pytest.fixture
def api(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with factory.begin() as db:
        user = User(email="admin@example.com", password_hash=hash_password("correct-horse-battery"), role=Role.SUPER_ADMIN)
        db.add(user)
    with factory() as db:
        user = db.scalar(select(User).where(User.email == "admin@example.com"))
        token = create_access_token(user)

    def override_db():
        with factory() as db:
            yield db

    monkeypatch.setattr("app.main.SessionLocal", factory)
    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as client:
        client.headers.update({"Authorization": f"Bearer {token}"})
        yield client, factory
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


def payload(**changes):
    departure = datetime.now(UTC) + timedelta(days=2)
    values = {
        "flight_number": "NS900",
        "origin": "London Heathrow",
        "destination": "Dubai International",
        "origin_code": "LHR",
        "destination_code": "DXB",
        "origin_timezone": "Europe/London",
        "destination_timezone": "Asia/Dubai",
        "departure_at": departure.isoformat(),
        "arrival_at": (departure + timedelta(hours=7)).isoformat(),
        "capacity": 10,
        "first_seats": 2,
        "business_seats": 3,
        "economy_seats": 5,
        "first_price": "1840.00",
        "business_price": "980.00",
        "economy_price": "420.00",
        "currency": "USD",
    }
    return {**values, **changes}


def test_flight_create_is_idempotent_and_builds_physical_inventory(api):
    client, factory = api
    key = "create-flight-ns900"
    request = payload()
    first = client.post("/api/flights", json=request, headers={"Idempotency-Key": key})
    retry = client.post("/api/flights", json=request, headers={"Idempotency-Key": key})
    assert first.status_code == 201, first.text
    assert retry.status_code == 201, retry.text
    assert retry.json()["id"] == first.json()["id"]
    assert first.json()["seats_by_class"] == {"First": 2, "Business": 3, "Economy": 5}
    with factory() as db:
        assert db.scalar(select(Flight)).capacity == 10
        assert len(db.scalars(select(Seat)).all()) == 10
        assert len(db.scalars(select(Inventory)).all()) == 3
        assert len(db.scalars(select(AuditEvent)).all()) == 1


@pytest.mark.parametrize(
    "changes",
    [
        {"economy_seats": 4},
        {"first_seats": 0, "business_seats": 4, "economy_seats": 6},
        {"first_seats": -1, "business_seats": 5, "economy_seats": 6},
        {"first_seats": 2.5},
        {"arrival_at": datetime.now(UTC).isoformat()},
    ],
)
def test_flight_create_rejects_invalid_capacity_or_seat_counts(api, changes):
    client, _ = api
    response = client.post(
        "/api/flights",
        json=payload(**changes),
        headers={"Idempotency-Key": "invalid-flight-900"},
    )
    assert response.status_code == 422, response.text


def test_duplicate_flight_number_route_day_returns_conflict(api):
    client, _ = api
    created = client.post("/api/flights", json=payload(), headers={"Idempotency-Key": "first-flight-ns900"})
    assert created.status_code == 201, created.text
    duplicate = client.post("/api/flights", json=payload(), headers={"Idempotency-Key": "second-flight-ns900"})
    assert duplicate.status_code == 409


def test_hold_reserves_seats_and_group_behavior_is_explicit(api):
    client, factory = api
    created = client.post("/api/flights", json=payload(), headers={"Idempotency-Key": "create-flight-hold"})
    assert created.status_code == 201, created.text
    flight_id = created.json()["id"]
    request = {
        "flight_id": flight_id,
        "cabin": "Economy",
        "fare_rule": "flexible",
        "passengers": [{"name": f"Passenger {number}"} for number in range(1, 7)],
        "email": "admin@example.com",
        "group_behavior": "partial",
    }
    held = client.post("/api/holds", json=request, headers={"Idempotency-Key": "hold-partial-group"})
    assert held.status_code == 201, held.text
    assert held.json()["passenger_count"] == 5
    with factory() as db:
        row = db.scalar(select(Inventory).where(Inventory.flight_id == flight_id, Inventory.cabin == "ECONOMY"))
        assert row.held == 5
    failed = client.post(
        "/api/holds",
        json={**request, "group_behavior": "all_or_nothing"},
        headers={"Idempotency-Key": "hold-all-or-nothing"},
    )
    assert failed.status_code == 409


def test_itinerary_checkout_charges_every_leg(api, monkeypatch):
    client, factory = api
    departure = datetime.now(UTC) + timedelta(days=2)
    first = client.post(
        "/api/flights",
        json=payload(departure_at=departure.isoformat(), arrival_at=(departure + timedelta(hours=7)).isoformat()),
        headers={"Idempotency-Key": "itinerary-leg-first"},
    )
    second = client.post(
        "/api/flights",
        json=payload(
            flight_number="NS902",
            origin="Dubai International",
            destination="Singapore Changi",
            origin_code="DXB",
            destination_code="SIN",
            origin_timezone="Asia/Dubai",
            destination_timezone="Asia/Singapore",
            departure_at=(departure + timedelta(hours=8)).isoformat(),
            arrival_at=(departure + timedelta(hours=13)).isoformat(),
        ),
        headers={"Idempotency-Key": "itinerary-leg-second"},
    )
    assert first.status_code == second.status_code == 201
    hold_response = client.post(
        "/api/itineraries/holds",
        json={
            "flight_ids": [first.json()["id"], second.json()["id"]],
            "cabin": "Economy",
            "fare_rule": "flexible",
            "passengers": [{"name": "Passenger One"}, {"name": "Passenger Two"}],
            "email": "admin@example.com",
        },
        headers={"Idempotency-Key": "itinerary-hold-group"},
    )
    assert hold_response.status_code == 201, hold_response.text
    created_arguments = {}

    def create_checkout(**kwargs):
        created_arguments.update(kwargs)
        return SimpleNamespace(id="cs_test_itinerary", url="https://checkout.example/session")

    fake_stripe = SimpleNamespace(checkout=SimpleNamespace(Session=SimpleNamespace(create=create_checkout)))
    monkeypatch.setattr("app.main.stripe_client", lambda: fake_stripe)
    checkout = client.post(
        f"/api/holds/{hold_response.json()['holds'][0]['id']}/checkout",
        json={},
        headers={"Idempotency-Key": "itinerary-checkout-session"},
    )
    assert checkout.status_code == 200, checkout.text
    assert len(created_arguments["line_items"]) == 2
    assert [line["quantity"] for line in created_arguments["line_items"]] == [2, 2]
    with factory() as db:
        holds = db.scalars(select(SeatHold).where(SeatHold.group_id == hold_response.json()["group_id"])).all()
        assert len(holds) == 2
        assert {hold.payment_session_id for hold in holds} == {"cs_test_itinerary"}


def test_all_writes_require_idempotency_key(api):
    client, _ = api
    response = client.post("/api/flights", json=payload())
    assert response.status_code == 400
    assert "Idempotency-Key" in response.json()["detail"]


def test_operations_agent_cannot_create_flight(api):
    client, db_factory = api
    with db_factory.begin() as db:
        ops = User(email="ops@example.com", password_hash=hash_password("another-correct-password"), role=Role.OPS_AGENT)
        db.add(ops)
    with db_factory() as db:
        ops = db.scalar(select(User).where(User.email == "ops@example.com"))
        token = create_access_token(ops)
    response = client.post(
        "/api/flights",
        json=payload(flight_number="NS901"),
        headers={"Authorization": f"Bearer {token}", "Idempotency-Key": "ops-create-flight-901"},
    )
    assert response.status_code == 403


def test_frontend_serves_only_explicit_asset_paths(api):
    client, _ = api
    assert client.get("/").status_code == 200
    assert "Northstar Air" in client.get("/").text
    assert client.get("/script.js").headers["content-type"].startswith("text/javascript")
    assert client.get("/styles.css").headers["content-type"].startswith("text/css")
    assert client.get("/requirements.txt").status_code == 404
