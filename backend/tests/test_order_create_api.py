"""API tests for order creation — task 6.1."""

from __future__ import annotations

import uuid
from datetime import UTC, date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.nsa import NSARecord
from app.models.orders import Order, OrderStatus, OrderStatusHistory
from app.models.users import User, UserRole
from app.models.zones import Pincode

# ── Helpers ──────────────────────────────────────────────────────────────


def _fake_user(
    role: UserRole = UserRole.SUPER_ADMIN,
    user_id: uuid.UUID | None = None,
) -> User:
    user = MagicMock(spec=User)
    user.id = user_id or uuid.uuid4()
    user.email = f"{role.value}@test.com"
    user.phone = "+911234567890"
    user.role = role
    user.is_active = True
    return user


ADMIN_USER = _fake_user(UserRole.SUPER_ADMIN)
CLIENT_USER = _fake_user(UserRole.CLIENT_USER)
PHLEB_USER = _fake_user(UserRole.PHLEBOTOMIST)

FAKE_PINCODE_ID = uuid.uuid4()
FAKE_CLIENT_ID = uuid.uuid4()


def _override_auth(user: User) -> None:
    from app.api.deps import get_current_active_user, get_current_user

    async def _fake_active() -> User:
        return user

    async def _fake_current() -> User:
        return user

    app.dependency_overrides[get_current_active_user] = _fake_active
    app.dependency_overrides[get_current_user] = _fake_current


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def _valid_payload() -> dict:
    return {
        "client_id": str(FAKE_CLIENT_ID),
        "patient_title": "Mr",
        "patient_name": "Test Patient",
        "patient_age": 30,
        "patient_gender": "M",
        "patient_phone": "+911234567890",
        "appointment_date": (date.today() + timedelta(days=1)).isoformat(),
        "appointment_time_slot": "09:00-11:00",
        "address": "123 Test Street",
        "pincode": "400001",
        "priority": "normal",
        "payment_mode": "cash",
    }


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    _clear_overrides()


@pytest.fixture
async def admin_client():
    _override_auth(ADMIN_USER)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def client_user_client():
    _override_auth(CLIENT_USER)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def phleb_client():
    _override_auth(PHLEB_USER)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _mock_pincode():
    p = MagicMock(spec=Pincode)
    p.id = FAKE_PINCODE_ID
    p.pincode = "400001"
    return p


def _mock_order(booking_id: str = "PNC-20260223-0001") -> MagicMock:
    from datetime import datetime

    order = MagicMock(spec=Order)
    order.id = uuid.uuid4()
    order.booking_id = booking_id
    order.client_id = FAKE_CLIENT_ID
    order.pincode_id = FAKE_PINCODE_ID
    order.locality_id = None
    order.patient_title = "Mr"
    order.patient_name = "Test Patient"
    order.patient_age = 30
    order.patient_gender = "M"
    order.patient_phone = "+911234567890"
    order.appointment_date = date.today() + timedelta(days=1)
    order.appointment_time_slot = "09:00-11:00"
    order.address = "123 Test Street"
    order.landmark = None
    order.status = "pending"
    order.priority = "normal"
    order.special_instructions = None
    order.amount = 0
    order.payment_mode = "cash"
    order.payment_status = "pending"
    order.assigned_phlebotomist_id = None
    order.created_at = datetime.now(UTC)
    order.status_history = []
    return order


# ── Mock DB helpers ──────────────────────────────────────────────────────


def _setup_db_mock(
    mock_get_db: AsyncMock,
    pincode_exists: bool = True,
    nsa_active: bool = False,
    order_count: int = 0,
) -> AsyncMock:
    """Set up mock DB session with chained execute results."""
    db = AsyncMock()

    # We need to handle multiple execute calls:
    # 1. Pincode lookup
    # 2. NSA check
    # 3. Count for booking_id
    pincode_result = MagicMock()
    pincode_result.scalar_one_or_none.return_value = (
        _mock_pincode() if pincode_exists else None
    )

    nsa_result = MagicMock()
    nsa_record = MagicMock(spec=NSARecord) if nsa_active else None
    nsa_result.scalar_one_or_none.return_value = nsa_record

    count_result = MagicMock()
    count_result.scalar_one.return_value = order_count

    db.execute = AsyncMock(side_effect=[pincode_result, nsa_result, count_result])
    db.add = MagicMock()
    db.commit = AsyncMock()

    # After commit, refresh should populate order-like attributes
    async def fake_refresh(obj: object) -> None:
        pass

    db.refresh = AsyncMock(side_effect=fake_refresh)

    async def _fake_db():
        yield db

    mock_get_db.return_value = _fake_db()
    # For FastAPI dependency override
    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: db

    return db


# ── Tests ────────────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_create_order_valid(admin_client: AsyncClient):
    """Create order with valid data returns 201."""
    with patch("app.api.v1.orders.get_db") as mock_get_db:
        db = AsyncMock()

        pincode_result = MagicMock()
        pincode_result.scalar_one_or_none.return_value = _mock_pincode()

        nsa_result = MagicMock()
        nsa_result.scalar_one_or_none.return_value = None

        count_result = MagicMock()
        count_result.scalar_one.return_value = 0

        db.execute = AsyncMock(side_effect=[pincode_result, nsa_result, count_result])
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        from app.core.database import get_db

        app.dependency_overrides[get_db] = lambda: db

        resp = await admin_client.post("/api/v1/orders", json=_valid_payload())

    # The endpoint returns the Order ORM object; with mocked db.refresh
    # doing nothing, the response depends on serialization.
    # With our mock, we expect 201 (the endpoint ran without error).
    assert resp.status_code == 201
    data = resp.json()
    assert data["booking_id"].startswith("PNC-")
    assert data["status"] == "pending"


@pytest.mark.anyio
async def test_create_order_invalid_pincode(admin_client: AsyncClient):
    """Pincode not found returns 400."""
    db = AsyncMock()

    pincode_result = MagicMock()
    pincode_result.scalar_one_or_none.return_value = None

    db.execute = AsyncMock(side_effect=[pincode_result])

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: db

    resp = await admin_client.post("/api/v1/orders", json=_valid_payload())
    assert resp.status_code == 400
    body = resp.json()
    msg = body.get("detail", "") or body.get("error", {}).get("message", "")
    assert "not found" in msg.lower()


@pytest.mark.anyio
async def test_create_order_nsa_pincode(admin_client: AsyncClient):
    """NSA pincode returns 400."""
    db = AsyncMock()

    pincode_result = MagicMock()
    pincode_result.scalar_one_or_none.return_value = _mock_pincode()

    nsa_result = MagicMock()
    nsa_result.scalar_one_or_none.return_value = MagicMock(spec=NSARecord)

    db.execute = AsyncMock(side_effect=[pincode_result, nsa_result])

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: db

    resp = await admin_client.post("/api/v1/orders", json=_valid_payload())
    assert resp.status_code == 400
    body = resp.json()
    msg = body.get("detail", "") or body.get("error", {}).get("message", "")
    assert "non-serviceable" in msg.lower()


@pytest.mark.anyio
async def test_create_order_missing_fields(admin_client: AsyncClient):
    """Missing required fields returns 422."""
    resp = await admin_client.post("/api/v1/orders", json={})
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_booking_id_format(admin_client: AsyncClient):
    """Booking ID follows PNC-YYYYMMDD-NNNN format."""
    db = AsyncMock()

    pincode_result = MagicMock()
    pincode_result.scalar_one_or_none.return_value = _mock_pincode()

    nsa_result = MagicMock()
    nsa_result.scalar_one_or_none.return_value = None

    count_result = MagicMock()
    count_result.scalar_one.return_value = 5

    db.execute = AsyncMock(side_effect=[pincode_result, nsa_result, count_result])
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: db

    resp = await admin_client.post("/api/v1/orders", json=_valid_payload())
    assert resp.status_code == 201
    booking_id = resp.json()["booking_id"]
    # Should be PNC-YYYYMMDD-0006 (count=5, so next is 6)
    import re

    assert re.fullmatch(r"PNC-\d{8}-\d{4}", booking_id)
    assert booking_id.endswith("-0006")


@pytest.mark.anyio
async def test_status_history_created(admin_client: AsyncClient):
    """Creating an order adds an initial status history entry."""
    db = AsyncMock()

    pincode_result = MagicMock()
    pincode_result.scalar_one_or_none.return_value = _mock_pincode()

    nsa_result = MagicMock()
    nsa_result.scalar_one_or_none.return_value = None

    count_result = MagicMock()
    count_result.scalar_one.return_value = 0

    db.execute = AsyncMock(side_effect=[pincode_result, nsa_result, count_result])
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: db

    resp = await admin_client.post("/api/v1/orders", json=_valid_payload())
    assert resp.status_code == 201

    # Verify db.add was called twice (Order + OrderStatusHistory)
    assert db.add.call_count == 2
    added_objects = [call.args[0] for call in db.add.call_args_list]
    assert isinstance(added_objects[0], Order)
    assert isinstance(added_objects[1], OrderStatusHistory)
    assert added_objects[1].status == OrderStatus.PENDING
    assert added_objects[1].notes == "Order created"


@pytest.mark.anyio
async def test_create_order_unauthorized_phlebotomist(phleb_client: AsyncClient):
    """Phlebotomist cannot create orders — returns 403."""
    resp = await phleb_client.post("/api/v1/orders", json=_valid_payload())
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_create_order_client_user_allowed(client_user_client: AsyncClient):
    """Client user can create orders."""
    db = AsyncMock()

    pincode_result = MagicMock()
    pincode_result.scalar_one_or_none.return_value = _mock_pincode()

    nsa_result = MagicMock()
    nsa_result.scalar_one_or_none.return_value = None

    count_result = MagicMock()
    count_result.scalar_one.return_value = 0

    db.execute = AsyncMock(side_effect=[pincode_result, nsa_result, count_result])
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: db

    resp = await client_user_client.post("/api/v1/orders", json=_valid_payload())
    assert resp.status_code == 201


@pytest.mark.anyio
async def test_get_order_not_found(admin_client: AsyncClient):
    """GET non-existent order returns 404."""
    db = AsyncMock()

    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result)

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: db

    fake_id = uuid.uuid4()
    resp = await admin_client.get(f"/api/v1/orders/{fake_id}")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_get_order_success(admin_client: AsyncClient):
    """GET existing order returns 200 with detail."""
    db = AsyncMock()
    order = _mock_order()

    result = MagicMock()
    result.scalar_one_or_none.return_value = order
    db.execute = AsyncMock(return_value=result)

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: db

    resp = await admin_client.get(f"/api/v1/orders/{order.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["booking_id"] == order.booking_id


@pytest.mark.anyio
async def test_create_order_past_date(admin_client: AsyncClient):
    """Past appointment date returns 422."""
    payload = _valid_payload()
    payload["appointment_date"] = (date.today() - timedelta(days=1)).isoformat()
    resp = await admin_client.post("/api/v1/orders", json=payload)
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_create_order_invalid_gender(admin_client: AsyncClient):
    """Invalid gender returns 422."""
    payload = _valid_payload()
    payload["patient_gender"] = "X"
    resp = await admin_client.post("/api/v1/orders", json=payload)
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_create_order_invalid_pincode_format(admin_client: AsyncClient):
    """Invalid pincode format returns 422."""
    payload = _valid_payload()
    payload["pincode"] = "12345"
    resp = await admin_client.post("/api/v1/orders", json=payload)
    assert resp.status_code == 422
