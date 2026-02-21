"""API tests for order listing — task 6.2."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.orders import Order
from app.models.users import User, UserRole

# ── Helpers ──────────────────────────────────────────────────────────────

FAKE_CLIENT_ID = uuid.uuid4()
FAKE_CLIENT_ID_2 = uuid.uuid4()
FAKE_PHLEB_ID = uuid.uuid4()
FAKE_PINCODE_ID = uuid.uuid4()


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
CITY_ADMIN_USER = _fake_user(UserRole.CITY_ADMIN)
CLIENT_USER_OBJ = _fake_user(UserRole.CLIENT_USER)
PHLEB_USER = _fake_user(UserRole.PHLEBOTOMIST)


def _override_auth(user: User) -> None:
    from app.api.deps import get_current_active_user, get_current_user

    app.dependency_overrides[get_current_active_user] = lambda: user
    app.dependency_overrides[get_current_user] = lambda: user


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def _mock_order(
    booking_id: str = "PNC-20260222-0001",
    client_id: uuid.UUID | None = None,
    phleb_id: uuid.UUID | None = None,
    status: str = "pending",
    priority: str = "normal",
    appt_date: date | None = None,
    patient_name: str = "Test Patient",
    patient_phone: str = "+911234567890",
) -> MagicMock:
    order = MagicMock(spec=Order)
    order.id = uuid.uuid4()
    order.booking_id = booking_id
    order.client_id = client_id or FAKE_CLIENT_ID
    order.pincode_id = FAKE_PINCODE_ID
    order.locality_id = None
    order.patient_title = "Mr"
    order.patient_name = patient_name
    order.patient_age = 30
    order.patient_gender = "M"
    order.patient_phone = patient_phone
    order.appointment_date = appt_date or date.today()
    order.appointment_time_slot = "09:00-11:00"
    order.address = "123 Test Street"
    order.landmark = None
    order.status = status
    order.priority = priority
    order.special_instructions = None
    order.amount = 0
    order.payment_mode = "cash"
    order.payment_status = "pending"
    order.assigned_phlebotomist_id = phleb_id
    order.created_at = datetime.now(UTC)
    order.status_history = []
    return order


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    _clear_overrides()


def _make_client(user):
    _override_auth(user)
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


def _setup_db_for_list(
    orders: list[MagicMock],
    total: int | None = None,
    rbac_lookups: list | None = None,
):
    """Set up mock DB for list endpoint.

    rbac_lookups: list of scalar results for RBAC queries (ClientUser/Phlebotomist).
    """
    db = AsyncMock()

    if total is None:
        total = len(orders)

    call_results = []

    # Add RBAC lookup results first if any
    if rbac_lookups:
        for val in rbac_lookups:
            r = MagicMock()
            r.scalar_one_or_none.return_value = val
            call_results.append(r)

    # Count query result
    count_result = MagicMock()
    count_result.scalar_one.return_value = total
    call_results.append(count_result)

    # Orders query result
    orders_result = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = orders
    orders_result.scalars.return_value = scalars_mock
    call_results.append(orders_result)

    db.execute = AsyncMock(side_effect=call_results)

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: db
    return db


# ── Tests: Basic listing & pagination ────────────────────────────────────


@pytest.mark.anyio
async def test_list_orders_empty(client=None):
    """Empty result returns correct structure."""
    _override_auth(ADMIN_USER)
    _setup_db_for_list([], total=0)

    async with _make_client(ADMIN_USER) as ac:
        resp = await ac.get("/api/v1/orders")

    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["skip"] == 0
    assert data["limit"] == 20
    assert data["has_more"] is False


@pytest.mark.anyio
async def test_list_orders_returns_items():
    """List returns order items."""
    orders = [_mock_order(booking_id=f"PNC-20260222-{i:04d}") for i in range(3)]
    _override_auth(ADMIN_USER)
    _setup_db_for_list(orders, total=3)

    async with _make_client(ADMIN_USER) as ac:
        resp = await ac.get("/api/v1/orders")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 3
    assert data["total"] == 3
    assert data["has_more"] is False


@pytest.mark.anyio
async def test_list_orders_pagination():
    """Pagination parameters work correctly."""
    orders = [_mock_order()]
    _override_auth(ADMIN_USER)
    _setup_db_for_list(orders, total=50)

    async with _make_client(ADMIN_USER) as ac:
        resp = await ac.get("/api/v1/orders?skip=0&limit=10")

    assert resp.status_code == 200
    data = resp.json()
    assert data["skip"] == 0
    assert data["limit"] == 10
    assert data["total"] == 50
    assert data["has_more"] is True


@pytest.mark.anyio
async def test_list_orders_pagination_no_more():
    """has_more is False when at end."""
    _override_auth(ADMIN_USER)
    _setup_db_for_list([], total=5)

    async with _make_client(ADMIN_USER) as ac:
        resp = await ac.get("/api/v1/orders?skip=5&limit=5")

    assert resp.status_code == 200
    data = resp.json()
    assert data["has_more"] is False


# ── Tests: Filters ───────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_filter_by_status():
    """Filter by status query param."""
    orders = [_mock_order(status="pending")]
    _override_auth(ADMIN_USER)
    _setup_db_for_list(orders, total=1)

    async with _make_client(ADMIN_USER) as ac:
        resp = await ac.get("/api/v1/orders?status=pending")

    assert resp.status_code == 200
    assert resp.json()["total"] == 1


@pytest.mark.anyio
async def test_filter_by_date_from():
    """Filter by date_from."""
    _override_auth(ADMIN_USER)
    _setup_db_for_list([_mock_order()], total=1)

    async with _make_client(ADMIN_USER) as ac:
        resp = await ac.get(f"/api/v1/orders?date_from={date.today().isoformat()}")

    assert resp.status_code == 200


@pytest.mark.anyio
async def test_filter_by_date_to():
    """Filter by date_to."""
    _override_auth(ADMIN_USER)
    _setup_db_for_list([_mock_order()], total=1)

    async with _make_client(ADMIN_USER) as ac:
        resp = await ac.get(f"/api/v1/orders?date_to={date.today().isoformat()}")

    assert resp.status_code == 200


@pytest.mark.anyio
async def test_filter_by_client_id():
    """Filter by client_id."""
    _override_auth(ADMIN_USER)
    _setup_db_for_list([_mock_order()], total=1)

    async with _make_client(ADMIN_USER) as ac:
        resp = await ac.get(f"/api/v1/orders?client_id={FAKE_CLIENT_ID}")

    assert resp.status_code == 200


@pytest.mark.anyio
async def test_filter_by_phlebotomist_id():
    """Filter by phlebotomist_id."""
    _override_auth(ADMIN_USER)
    _setup_db_for_list([_mock_order(phleb_id=FAKE_PHLEB_ID)], total=1)

    async with _make_client(ADMIN_USER) as ac:
        resp = await ac.get(f"/api/v1/orders?phlebotomist_id={FAKE_PHLEB_ID}")

    assert resp.status_code == 200


@pytest.mark.anyio
async def test_filter_by_priority():
    """Filter by priority."""
    _override_auth(ADMIN_USER)
    _setup_db_for_list([_mock_order(priority="high")], total=1)

    async with _make_client(ADMIN_USER) as ac:
        resp = await ac.get("/api/v1/orders?priority=high")

    assert resp.status_code == 200


@pytest.mark.anyio
async def test_filter_combined():
    """Multiple filters together."""
    _override_auth(ADMIN_USER)
    _setup_db_for_list([_mock_order(status="pending", priority="high")], total=1)

    async with _make_client(ADMIN_USER) as ac:
        resp = await ac.get("/api/v1/orders?status=pending&priority=high")

    assert resp.status_code == 200
    assert resp.json()["total"] == 1


# ── Tests: Search ────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_search_by_booking_id():
    """Search matches booking_id."""
    _override_auth(ADMIN_USER)
    _setup_db_for_list([_mock_order(booking_id="PNC-20260222-0001")], total=1)

    async with _make_client(ADMIN_USER) as ac:
        resp = await ac.get("/api/v1/orders?search=PNC-20260222")

    assert resp.status_code == 200
    assert resp.json()["total"] == 1


@pytest.mark.anyio
async def test_search_by_patient_name():
    """Search matches patient_name."""
    _override_auth(ADMIN_USER)
    _setup_db_for_list([_mock_order(patient_name="John Doe")], total=1)

    async with _make_client(ADMIN_USER) as ac:
        resp = await ac.get("/api/v1/orders?search=John")

    assert resp.status_code == 200
    assert resp.json()["total"] == 1


@pytest.mark.anyio
async def test_search_by_patient_phone():
    """Search matches patient_phone."""
    _override_auth(ADMIN_USER)
    _setup_db_for_list([_mock_order(patient_phone="+919876543210")], total=1)

    async with _make_client(ADMIN_USER) as ac:
        resp = await ac.get("/api/v1/orders?search=9876543210")

    assert resp.status_code == 200
    assert resp.json()["total"] == 1


# ── Tests: RBAC ──────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_admin_sees_all():
    """Super admin sees all orders."""
    orders = [_mock_order() for _ in range(5)]
    _override_auth(ADMIN_USER)
    _setup_db_for_list(orders, total=5)

    async with _make_client(ADMIN_USER) as ac:
        resp = await ac.get("/api/v1/orders")

    assert resp.status_code == 200
    assert resp.json()["total"] == 5


@pytest.mark.anyio
async def test_city_admin_sees_all():
    """City admin sees all orders."""
    orders = [_mock_order() for _ in range(3)]
    _override_auth(CITY_ADMIN_USER)
    _setup_db_for_list(orders, total=3)

    async with _make_client(CITY_ADMIN_USER) as ac:
        resp = await ac.get("/api/v1/orders")

    assert resp.status_code == 200
    assert resp.json()["total"] == 3


@pytest.mark.anyio
async def test_client_user_sees_own_orders_only():
    """Client user sees only their client's orders."""
    own_orders = [_mock_order(client_id=FAKE_CLIENT_ID)]
    _override_auth(CLIENT_USER_OBJ)
    # RBAC lookup returns client_id
    _setup_db_for_list(own_orders, total=1, rbac_lookups=[FAKE_CLIENT_ID])

    async with _make_client(CLIENT_USER_OBJ) as ac:
        resp = await ac.get("/api/v1/orders")

    assert resp.status_code == 200
    assert resp.json()["total"] == 1


@pytest.mark.anyio
async def test_client_user_no_client_link():
    """Client user with no ClientUser link gets empty results."""
    _override_auth(CLIENT_USER_OBJ)
    # RBAC lookup returns None (no ClientUser row)
    db = AsyncMock()
    rbac_result = MagicMock()
    rbac_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=rbac_result)

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: db

    async with _make_client(CLIENT_USER_OBJ) as ac:
        resp = await ac.get("/api/v1/orders")

    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.anyio
async def test_phlebotomist_sees_assigned_only():
    """Phlebotomist sees only assigned orders."""
    assigned_orders = [_mock_order(phleb_id=FAKE_PHLEB_ID)]
    _override_auth(PHLEB_USER)
    # RBAC lookup returns phlebotomist id
    _setup_db_for_list(assigned_orders, total=1, rbac_lookups=[FAKE_PHLEB_ID])

    async with _make_client(PHLEB_USER) as ac:
        resp = await ac.get("/api/v1/orders")

    assert resp.status_code == 200
    assert resp.json()["total"] == 1


@pytest.mark.anyio
async def test_phlebotomist_no_profile():
    """Phlebotomist with no Phlebotomist profile gets empty results."""
    _override_auth(PHLEB_USER)
    db = AsyncMock()
    rbac_result = MagicMock()
    rbac_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=rbac_result)

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: db

    async with _make_client(PHLEB_USER) as ac:
        resp = await ac.get("/api/v1/orders")

    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


# ── Tests: Empty results ────────────────────────────────────────────────


@pytest.mark.anyio
async def test_filter_returns_empty():
    """Filter that matches nothing returns empty list."""
    _override_auth(ADMIN_USER)
    _setup_db_for_list([], total=0)

    async with _make_client(ADMIN_USER) as ac:
        resp = await ac.get("/api/v1/orders?status=cancelled")

    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["has_more"] is False
