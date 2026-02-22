"""API tests for manual order assignment — task 6.4."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.orders import Order, OrderStatus
from app.models.phlebotomist_leaves import PhlebotomistLeave
from app.models.phlebotomists import Phlebotomist, PhlebotomistZoneAssignment
from app.models.users import User, UserRole
from app.models.zones import Pincode

# ── Helpers ──────────────────────────────────────────────────────────────

ORDER_ID = uuid.uuid4()
PHLEB_ID = uuid.uuid4()
PHLEB_USER_ID = uuid.uuid4()
ZONE_ID = uuid.uuid4()
PINCODE_ID = uuid.uuid4()


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


def _get_detail(resp) -> str:
    """Extract error detail from response, handling custom error handler."""
    body = resp.json()
    return body.get("detail", body.get("error", {}).get("message", ""))


ADMIN_USER = _fake_user(UserRole.SUPER_ADMIN)


def _override_auth(user: User) -> None:
    from app.api.deps import get_current_active_user, get_current_user

    app.dependency_overrides[get_current_active_user] = lambda: user
    app.dependency_overrides[get_current_user] = lambda: user


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def _make_order(
    status: OrderStatus = OrderStatus.PENDING,
    pincode_id: uuid.UUID = PINCODE_ID,
    appointment_date: date | None = None,
) -> MagicMock:
    order = MagicMock(spec=Order)
    order.id = ORDER_ID
    order.status = status
    order.pincode_id = pincode_id
    order.appointment_date = appointment_date or date(2026, 3, 1)
    order.assigned_phlebotomist_id = None
    order.assigned_at = None
    order.booking_id = "PNC-20260301-0001"
    order.client_id = uuid.uuid4()
    order.locality_id = None
    order.patient_title = "Mr"
    order.patient_name = "Test Patient"
    order.patient_age = 30
    order.patient_gender = "M"
    order.patient_phone = "+911234567890"
    order.appointment_time_slot = "9:00-10:00"
    order.address = "Test Address"
    order.landmark = None
    order.priority = "normal"
    order.special_instructions = None
    order.amount = 0.0
    order.payment_mode = "cash"
    order.payment_status = "pending"
    order.created_at = datetime(2026, 2, 22, tzinfo=UTC)
    return order


def _make_phlebotomist(
    is_available: bool = True,
    phleb_id: uuid.UUID = PHLEB_ID,
) -> MagicMock:
    p = MagicMock(spec=Phlebotomist)
    p.id = phleb_id
    p.user_id = PHLEB_USER_ID
    p.is_available = is_available
    return p


def _make_phleb_user(is_active: bool = True) -> MagicMock:
    u = MagicMock(spec=User)
    u.id = PHLEB_USER_ID
    u.is_active = is_active
    return u


def _make_pincode(zone_id: uuid.UUID = ZONE_ID) -> MagicMock:
    p = MagicMock(spec=Pincode)
    p.id = PINCODE_ID
    p.zone_id = zone_id
    return p


def _make_zone_assignment() -> MagicMock:
    za = MagicMock(spec=PhlebotomistZoneAssignment)
    za.phlebotomist_id = PHLEB_ID
    za.zone_id = ZONE_ID
    return za


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _cleanup():
    _override_auth(ADMIN_USER)
    yield
    _clear_overrides()


# ── Tests ────────────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_assign_order_success():
    """Successful assignment with all validations passing."""
    order = _make_order()
    phleb = _make_phlebotomist()
    phleb_user = _make_phleb_user()
    pincode = _make_pincode()
    zone_assign = _make_zone_assignment()

    mock_db = AsyncMock()
    # Sequence of execute calls:
    # 1. order lookup
    # 2. phlebotomist lookup
    # 3. user lookup
    # 4. pincode lookup
    # 5. zone assignment check
    # 6. leave check
    results = []
    for obj in [order, phleb, phleb_user, pincode, zone_assign, None]:
        r = MagicMock()
        r.scalar_one_or_none.return_value = obj
        if obj is pincode:
            r.scalar_one.return_value = obj
        results.append(r)

    # pincode lookup uses scalar_one (not scalar_one_or_none)
    results[3].scalar_one.return_value = pincode

    mock_db.execute = AsyncMock(side_effect=results)
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.put(
            f"/api/v1/orders/{ORDER_ID}/assign",
            json={"phlebotomist_id": str(PHLEB_ID)},
        )

    assert resp.status_code == 200
    mock_db.commit.assert_awaited_once()


@pytest.mark.anyio
async def test_assign_order_not_found():
    mock_db = AsyncMock()
    r = MagicMock()
    r.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=r)

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.put(
            f"/api/v1/orders/{ORDER_ID}/assign",
            json={"phlebotomist_id": str(PHLEB_ID)},
        )

    assert resp.status_code == 404
    assert "Order not found" in _get_detail(resp)


@pytest.mark.anyio
async def test_assign_order_not_pending():
    order = _make_order(status=OrderStatus.ASSIGNED)
    mock_db = AsyncMock()
    r = MagicMock()
    r.scalar_one_or_none.return_value = order
    mock_db.execute = AsyncMock(return_value=r)

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.put(
            f"/api/v1/orders/{ORDER_ID}/assign",
            json={"phlebotomist_id": str(PHLEB_ID)},
        )

    assert resp.status_code == 400
    assert "must be pending" in _get_detail(resp)


@pytest.mark.anyio
async def test_assign_phlebotomist_not_found():
    order = _make_order()
    mock_db = AsyncMock()
    results = []
    # order found
    r1 = MagicMock()
    r1.scalar_one_or_none.return_value = order
    results.append(r1)
    # phleb not found
    r2 = MagicMock()
    r2.scalar_one_or_none.return_value = None
    results.append(r2)
    mock_db.execute = AsyncMock(side_effect=results)

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.put(
            f"/api/v1/orders/{ORDER_ID}/assign",
            json={"phlebotomist_id": str(PHLEB_ID)},
        )

    assert resp.status_code == 404
    assert "Phlebotomist not found" in _get_detail(resp)


@pytest.mark.anyio
async def test_assign_phlebotomist_not_available():
    order = _make_order()
    phleb = _make_phlebotomist(is_available=False)
    mock_db = AsyncMock()
    results = []
    for obj in [order, phleb]:
        r = MagicMock()
        r.scalar_one_or_none.return_value = obj
        results.append(r)
    mock_db.execute = AsyncMock(side_effect=results)

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.put(
            f"/api/v1/orders/{ORDER_ID}/assign",
            json={"phlebotomist_id": str(PHLEB_ID)},
        )

    assert resp.status_code == 400
    assert "not available" in _get_detail(resp)


@pytest.mark.anyio
async def test_assign_phlebotomist_user_inactive():
    order = _make_order()
    phleb = _make_phlebotomist()
    phleb_user = _make_phleb_user(is_active=False)
    mock_db = AsyncMock()
    results = []
    for obj in [order, phleb, phleb_user]:
        r = MagicMock()
        r.scalar_one_or_none.return_value = obj
        results.append(r)
    mock_db.execute = AsyncMock(side_effect=results)

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.put(
            f"/api/v1/orders/{ORDER_ID}/assign",
            json={"phlebotomist_id": str(PHLEB_ID)},
        )

    assert resp.status_code == 400
    assert "not active" in _get_detail(resp)


@pytest.mark.anyio
async def test_assign_zone_mismatch():
    order = _make_order()
    phleb = _make_phlebotomist()
    phleb_user = _make_phleb_user()
    pincode = _make_pincode()
    mock_db = AsyncMock()
    results = []
    for obj in [order, phleb, phleb_user]:
        r = MagicMock()
        r.scalar_one_or_none.return_value = obj
        results.append(r)
    # pincode scalar_one
    r_pin = MagicMock()
    r_pin.scalar_one.return_value = pincode
    results.append(r_pin)
    # zone assignment not found
    r_zone = MagicMock()
    r_zone.scalar_one_or_none.return_value = None
    results.append(r_zone)
    mock_db.execute = AsyncMock(side_effect=results)

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.put(
            f"/api/v1/orders/{ORDER_ID}/assign",
            json={"phlebotomist_id": str(PHLEB_ID)},
        )

    assert resp.status_code == 400
    assert "zone" in _get_detail(resp).lower()


@pytest.mark.anyio
async def test_assign_phlebotomist_on_leave():
    order = _make_order()
    phleb = _make_phlebotomist()
    phleb_user = _make_phleb_user()
    pincode = _make_pincode()
    zone_assign = _make_zone_assignment()
    leave = MagicMock(spec=PhlebotomistLeave)
    mock_db = AsyncMock()
    results = []
    for obj in [order, phleb, phleb_user]:
        r = MagicMock()
        r.scalar_one_or_none.return_value = obj
        results.append(r)
    r_pin = MagicMock()
    r_pin.scalar_one.return_value = pincode
    results.append(r_pin)
    r_zone = MagicMock()
    r_zone.scalar_one_or_none.return_value = zone_assign
    results.append(r_zone)
    r_leave = MagicMock()
    r_leave.scalar_one_or_none.return_value = leave
    results.append(r_leave)
    mock_db.execute = AsyncMock(side_effect=results)

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.put(
            f"/api/v1/orders/{ORDER_ID}/assign",
            json={"phlebotomist_id": str(PHLEB_ID)},
        )

    assert resp.status_code == 400
    assert "leave" in _get_detail(resp).lower()


@pytest.mark.anyio
async def test_assign_rbac_phlebotomist_forbidden():
    """Phlebotomist role should not be able to assign."""
    phleb_user = _fake_user(UserRole.PHLEBOTOMIST)
    _override_auth(phleb_user)

    mock_db = AsyncMock()

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.put(
            f"/api/v1/orders/{ORDER_ID}/assign",
            json={"phlebotomist_id": str(PHLEB_ID)},
        )

    assert resp.status_code == 403


@pytest.mark.anyio
async def test_assign_rbac_city_admin_allowed():
    """City admin should be able to assign."""
    city_admin = _fake_user(UserRole.CITY_ADMIN)
    _override_auth(city_admin)

    order = _make_order()
    phleb = _make_phlebotomist()
    phleb_user = _make_phleb_user()
    pincode = _make_pincode()
    zone_assign = _make_zone_assignment()

    mock_db = AsyncMock()
    results = []
    for obj in [order, phleb, phleb_user]:
        r = MagicMock()
        r.scalar_one_or_none.return_value = obj
        results.append(r)
    r_pin = MagicMock()
    r_pin.scalar_one.return_value = pincode
    results.append(r_pin)
    r_zone = MagicMock()
    r_zone.scalar_one_or_none.return_value = zone_assign
    results.append(r_zone)
    r_leave = MagicMock()
    r_leave.scalar_one_or_none.return_value = None
    results.append(r_leave)
    mock_db.execute = AsyncMock(side_effect=results)
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.put(
            f"/api/v1/orders/{ORDER_ID}/assign",
            json={"phlebotomist_id": str(PHLEB_ID)},
        )

    assert resp.status_code == 200
