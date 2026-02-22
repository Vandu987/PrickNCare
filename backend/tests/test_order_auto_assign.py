"""API tests for auto-assignment algorithm — task 6.5."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.orders import Order, OrderStatus
from app.models.phlebotomist_leaves import PhlebotomistLeave
from app.models.phlebotomists import Phlebotomist
from app.models.users import User, UserRole
from app.models.zones import Pincode

# ── Helpers ──────────────────────────────────────────────────────────────

ZONE_ID = uuid.uuid4()
PINCODE_ID = uuid.uuid4()
PHLEB_ID_1 = uuid.uuid4()
PHLEB_ID_2 = uuid.uuid4()
PHLEB_USER_ID_1 = uuid.uuid4()
PHLEB_USER_ID_2 = uuid.uuid4()
ORDER_ID_1 = uuid.uuid4()
ORDER_ID_2 = uuid.uuid4()


def _fake_user(role: UserRole = UserRole.SUPER_ADMIN) -> User:
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = f"{role.value}@test.com"
    user.phone = "+911234567890"
    user.role = role
    user.is_active = True
    return user


ADMIN_USER = _fake_user(UserRole.SUPER_ADMIN)


def _override_auth(user: User) -> None:
    from app.api.deps import get_current_active_user, get_current_user

    app.dependency_overrides[get_current_active_user] = lambda: user
    app.dependency_overrides[get_current_user] = lambda: user


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def _make_order(
    order_id: uuid.UUID = ORDER_ID_1,
    status: OrderStatus = OrderStatus.PENDING,
    pincode_id: uuid.UUID = PINCODE_ID,
    appt_date: date | None = None,
) -> MagicMock:
    order = MagicMock(spec=Order)
    order.id = order_id
    order.status = status
    order.pincode_id = pincode_id
    order.appointment_date = appt_date or date(2026, 3, 1)
    order.appointment_time_slot = "9:00-10:00"
    order.assigned_phlebotomist_id = None
    order.assigned_at = None
    order.booking_id = f"PNC-20260301-{order_id.int % 10000:04d}"
    order.client_id = uuid.uuid4()
    order.locality_id = None
    order.patient_title = "Mr"
    order.patient_name = "Test Patient"
    order.patient_age = 30
    order.patient_gender = "M"
    order.patient_phone = "+911234567890"
    order.address = "Test Address"
    order.landmark = None
    order.priority = "normal"
    order.special_instructions = None
    order.amount = 0.0
    order.payment_mode = "cash"
    order.payment_status = "pending"
    order.created_at = datetime(2026, 2, 22, tzinfo=UTC)
    return order


def _make_pincode(zone_id: uuid.UUID | None = ZONE_ID) -> MagicMock:
    p = MagicMock(spec=Pincode)
    p.id = PINCODE_ID
    p.zone_id = zone_id
    return p


def _make_phlebotomist(
    phleb_id: uuid.UUID = PHLEB_ID_1,
    user_id: uuid.UUID = PHLEB_USER_ID_1,
    is_available: bool = True,
) -> MagicMock:
    p = MagicMock(spec=Phlebotomist)
    p.id = phleb_id
    p.user_id = user_id
    p.is_available = is_available
    return p


def _make_phleb_user(
    user_id: uuid.UUID = PHLEB_USER_ID_1, is_active: bool = True
) -> MagicMock:
    u = MagicMock(spec=User)
    u.id = user_id
    u.is_active = is_active
    return u


@pytest.fixture(autouse=True)
def _cleanup():
    _override_auth(ADMIN_USER)
    yield
    _clear_overrides()


# ── Tests ────────────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_auto_assign_success_single_order():
    """Single PENDING order gets assigned to the only eligible phleb."""
    order = _make_order()
    pincode = _make_pincode()
    phleb = _make_phlebotomist()
    phleb_user = _make_phleb_user()

    mock_db = AsyncMock()
    call_count = 0

    async def fake_execute(stmt, *a, **kw):
        nonlocal call_count
        call_count += 1
        r = MagicMock()

        if call_count == 1:
            # Fetch PENDING orders
            r.scalars.return_value.all.return_value = [order]
        elif call_count == 2:
            # Pincode lookup
            r.scalar_one_or_none.return_value = pincode
        elif call_count == 3:
            # Zone phleb IDs
            r.all.return_value = [(PHLEB_ID_1,)]
        elif call_count == 4:
            # Available phlebotomists
            r.scalars.return_value.all.return_value = [phleb]
        elif call_count == 5:
            # User is_active check
            r.scalar_one_or_none.return_value = phleb_user
        elif call_count == 6:
            # Leave check
            r.scalar_one_or_none.return_value = None
        elif call_count == 7:
            # Workload count
            r.scalar_one.return_value = 0
        return r

    mock_db.execute = AsyncMock(side_effect=fake_execute)
    mock_db.commit = AsyncMock()
    mock_db.add = MagicMock()

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.post("/api/v1/orders/auto-assign", json={})

    assert resp.status_code == 200
    data = resp.json()
    assert data["total_processed"] == 1
    assert data["assigned"] == 1
    assert data["failed"] == 0


@pytest.mark.anyio
async def test_auto_assign_no_zone():
    """Order with pincode having no zone fails gracefully."""
    order = _make_order()
    pincode = _make_pincode(zone_id=None)

    mock_db = AsyncMock()
    call_count = 0

    async def fake_execute(stmt, *a, **kw):
        nonlocal call_count
        call_count += 1
        r = MagicMock()
        if call_count == 1:
            r.scalars.return_value.all.return_value = [order]
        elif call_count == 2:
            r.scalar_one_or_none.return_value = pincode
        return r

    mock_db.execute = AsyncMock(side_effect=fake_execute)
    mock_db.commit = AsyncMock()
    mock_db.add = MagicMock()

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.post("/api/v1/orders/auto-assign", json={})

    assert resp.status_code == 200
    data = resp.json()
    assert data["assigned"] == 0
    assert data["failed"] == 1
    assert "no zone" in data["failures"][0]["reason"].lower()


@pytest.mark.anyio
async def test_auto_assign_no_eligible_phlebotomists():
    """All phlebotomists on leave → failure."""
    order = _make_order()
    pincode = _make_pincode()
    phleb = _make_phlebotomist()
    phleb_user = _make_phleb_user()

    mock_db = AsyncMock()
    call_count = 0

    async def fake_execute(stmt, *a, **kw):
        nonlocal call_count
        call_count += 1
        r = MagicMock()
        if call_count == 1:
            r.scalars.return_value.all.return_value = [order]
        elif call_count == 2:
            r.scalar_one_or_none.return_value = pincode
        elif call_count == 3:
            r.all.return_value = [(PHLEB_ID_1,)]
        elif call_count == 4:
            r.scalars.return_value.all.return_value = [phleb]
        elif call_count == 5:
            r.scalar_one_or_none.return_value = phleb_user
        elif call_count == 6:
            # On leave
            r.scalar_one_or_none.return_value = MagicMock(spec=PhlebotomistLeave)
        return r

    mock_db.execute = AsyncMock(side_effect=fake_execute)
    mock_db.commit = AsyncMock()
    mock_db.add = MagicMock()

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.post("/api/v1/orders/auto-assign", json={})

    assert resp.status_code == 200
    data = resp.json()
    assert data["assigned"] == 0
    assert data["failed"] == 1
    assert "no eligible" in data["failures"][0]["reason"].lower()


@pytest.mark.anyio
async def test_auto_assign_workload_balancing():
    """Phleb with lower workload gets assigned."""
    order = _make_order()
    pincode = _make_pincode()
    phleb1 = _make_phlebotomist(PHLEB_ID_1, PHLEB_USER_ID_1)
    phleb2 = _make_phlebotomist(PHLEB_ID_2, PHLEB_USER_ID_2)
    phleb_user1 = _make_phleb_user(PHLEB_USER_ID_1)
    phleb_user2 = _make_phleb_user(PHLEB_USER_ID_2)

    mock_db = AsyncMock()
    call_count = 0

    async def fake_execute(stmt, *a, **kw):
        nonlocal call_count
        call_count += 1
        r = MagicMock()
        if call_count == 1:
            r.scalars.return_value.all.return_value = [order]
        elif call_count == 2:
            r.scalar_one_or_none.return_value = pincode
        elif call_count == 3:
            r.all.return_value = [(PHLEB_ID_1,), (PHLEB_ID_2,)]
        elif call_count == 4:
            r.scalars.return_value.all.return_value = [phleb1, phleb2]
        elif call_count == 5:
            # user check phleb1
            r.scalar_one_or_none.return_value = phleb_user1
        elif call_count == 6:
            # leave check phleb1 (none)
            r.scalar_one_or_none.return_value = None
        elif call_count == 7:
            # user check phleb2
            r.scalar_one_or_none.return_value = phleb_user2
        elif call_count == 8:
            # leave check phleb2 (none)
            r.scalar_one_or_none.return_value = None
        elif call_count == 9:
            # workload phleb1 = 5
            r.scalar_one.return_value = 5
        elif call_count == 10:
            # workload phleb2 = 2
            r.scalar_one.return_value = 2
        return r

    mock_db.execute = AsyncMock(side_effect=fake_execute)
    mock_db.commit = AsyncMock()
    mock_db.add = MagicMock()

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.post("/api/v1/orders/auto-assign", json={})

    assert resp.status_code == 200
    data = resp.json()
    assert data["assigned"] == 1
    # Verify phleb2 was chosen (lower workload)
    assert order.assigned_phlebotomist_id == PHLEB_ID_2


@pytest.mark.anyio
async def test_auto_assign_with_specific_order_ids():
    """Passing order_ids filters to only those orders."""
    order = _make_order()
    pincode = _make_pincode()
    phleb = _make_phlebotomist()
    phleb_user = _make_phleb_user()

    mock_db = AsyncMock()
    call_count = 0

    async def fake_execute(stmt, *a, **kw):
        nonlocal call_count
        call_count += 1
        r = MagicMock()
        if call_count == 1:
            r.scalars.return_value.all.return_value = [order]
        elif call_count == 2:
            r.scalar_one_or_none.return_value = pincode
        elif call_count == 3:
            r.all.return_value = [(PHLEB_ID_1,)]
        elif call_count == 4:
            r.scalars.return_value.all.return_value = [phleb]
        elif call_count == 5:
            r.scalar_one_or_none.return_value = phleb_user
        elif call_count == 6:
            r.scalar_one_or_none.return_value = None
        elif call_count == 7:
            r.scalar_one.return_value = 0
        return r

    mock_db.execute = AsyncMock(side_effect=fake_execute)
    mock_db.commit = AsyncMock()
    mock_db.add = MagicMock()

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.post(
            "/api/v1/orders/auto-assign",
            json={"order_ids": [str(ORDER_ID_1)]},
        )

    assert resp.status_code == 200
    assert resp.json()["assigned"] == 1


@pytest.mark.anyio
async def test_auto_assign_rbac_phlebotomist_forbidden():
    """Phlebotomist role cannot access auto-assign."""
    _override_auth(_fake_user(UserRole.PHLEBOTOMIST))

    mock_db = AsyncMock()
    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.post("/api/v1/orders/auto-assign", json={})

    assert resp.status_code == 403


@pytest.mark.anyio
async def test_auto_assign_empty_pending():
    """No pending orders → zero processed."""
    mock_db = AsyncMock()
    call_count = 0

    async def fake_execute(stmt, *a, **kw):
        nonlocal call_count
        call_count += 1
        r = MagicMock()
        if call_count == 1:
            r.scalars.return_value.all.return_value = []
        return r

    mock_db.execute = AsyncMock(side_effect=fake_execute)
    mock_db.commit = AsyncMock()

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.post("/api/v1/orders/auto-assign", json={})

    assert resp.status_code == 200
    data = resp.json()
    assert data["total_processed"] == 0
    assert data["assigned"] == 0
    assert data["failed"] == 0
