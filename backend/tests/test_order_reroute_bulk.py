"""API tests for re-routing and bulk assignment — task 6.6."""

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
ORDER_ID_2 = uuid.uuid4()
PHLEB_ID = uuid.uuid4()
NEW_PHLEB_ID = uuid.uuid4()
PHLEB_USER_ID = uuid.uuid4()
NEW_PHLEB_USER_ID = uuid.uuid4()
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


ADMIN_USER = _fake_user(UserRole.SUPER_ADMIN)


def _override_auth(user: User) -> None:
    from app.api.deps import get_current_active_user, get_current_user

    app.dependency_overrides[get_current_active_user] = lambda: user
    app.dependency_overrides[get_current_user] = lambda: user


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def _get_detail(resp) -> str:
    body = resp.json()
    return body.get("detail", body.get("error", {}).get("message", ""))


def _make_order(
    order_id: uuid.UUID = ORDER_ID,
    status: OrderStatus = OrderStatus.ASSIGNED,
    phleb_id: uuid.UUID | None = PHLEB_ID,
    pincode_id: uuid.UUID = PINCODE_ID,
    appointment_date: date | None = None,
) -> MagicMock:
    order = MagicMock(spec=Order)
    order.id = order_id
    order.status = status
    order.assigned_phlebotomist_id = phleb_id
    order.pincode_id = pincode_id
    order.appointment_date = appointment_date or date(2026, 3, 1)
    order.assigned_at = None
    order.booking_id = "PNC-20260301-0001"
    order.client_id = uuid.uuid4()
    order.locality_id = None
    order.patient_title = "MR"
    order.patient_name = "Test Patient"
    order.patient_age = 30
    order.patient_gender = "M"
    order.patient_phone = "+911234567890"
    order.appointment_time_slot = "09:00"
    order.address = "123 Test"
    order.landmark = None
    order.priority = "normal"
    order.special_instructions = None
    order.amount = 0
    order.payment_mode = "cash"
    order.payment_status = "pending"
    order.created_at = datetime.now(UTC)
    return order


def _make_phleb(
    phleb_id: uuid.UUID = NEW_PHLEB_ID,
    user_id: uuid.UUID = NEW_PHLEB_USER_ID,
    available: bool = True,
) -> MagicMock:
    phleb = MagicMock(spec=Phlebotomist)
    phleb.id = phleb_id
    phleb.user_id = user_id
    phleb.is_available = available
    return phleb


def _make_phleb_user(
    user_id: uuid.UUID = NEW_PHLEB_USER_ID, active: bool = True
) -> MagicMock:
    u = MagicMock(spec=User)
    u.id = user_id
    u.is_active = active
    u.email = "phleb@test.com"
    u.full_name = "Test Phlebotomist"
    return u


def _make_pincode(zone_id: uuid.UUID = ZONE_ID) -> MagicMock:
    p = MagicMock(spec=Pincode)
    p.id = PINCODE_ID
    p.zone_id = zone_id
    return p


def _make_zone_assignment() -> MagicMock:
    return MagicMock(spec=PhlebotomistZoneAssignment)


# ── Reroute Tests ────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_reroute_success():
    """Reroute an ASSIGNED order to a new phlebotomist."""
    order = _make_order(status=OrderStatus.ASSIGNED)
    phleb = _make_phleb()
    phleb_user = _make_phleb_user()
    pincode = _make_pincode()
    zone_assign = _make_zone_assignment()

    mock_db = AsyncMock()
    call_count = 0

    async def fake_execute(stmt):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:  # Order lookup
            result.scalar_one_or_none.return_value = order
        elif call_count == 2:  # Phlebotomist lookup
            result.scalar_one_or_none.return_value = phleb
        elif call_count == 3:  # Phleb user lookup
            result.scalar_one_or_none.return_value = phleb_user
        elif call_count == 4:  # Pincode lookup
            result.scalar_one.return_value = pincode
        elif call_count == 5:  # Zone check
            result.scalar_one_or_none.return_value = zone_assign
        elif call_count == 6:  # Leave check
            result.scalar_one_or_none.return_value = None
        return result

    mock_db.execute = fake_execute
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db
    _override_auth(ADMIN_USER)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                f"/api/v1/orders/{ORDER_ID}/reroute",
                json={
                    "new_phlebotomist_id": str(NEW_PHLEB_ID),
                    "reason": "Closer to patient",
                },
            )
        assert resp.status_code == 200
        assert order.assigned_phlebotomist_id == NEW_PHLEB_ID
        assert order.status == OrderStatus.ASSIGNED
    finally:
        _clear_overrides()


@pytest.mark.anyio
async def test_reroute_accepted_order():
    """Reroute an ACCEPTED order resets status to ASSIGNED."""
    order = _make_order(status=OrderStatus.ACCEPTED)
    phleb = _make_phleb()
    phleb_user = _make_phleb_user()
    pincode = _make_pincode()
    zone_assign = _make_zone_assignment()

    mock_db = AsyncMock()
    call_count = 0

    async def fake_execute(stmt):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            result.scalar_one_or_none.return_value = order
        elif call_count == 2:
            result.scalar_one_or_none.return_value = phleb
        elif call_count == 3:
            result.scalar_one_or_none.return_value = phleb_user
        elif call_count == 4:
            result.scalar_one.return_value = pincode
        elif call_count == 5:
            result.scalar_one_or_none.return_value = zone_assign
        elif call_count == 6:
            result.scalar_one_or_none.return_value = None
        return result

    mock_db.execute = fake_execute
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db
    _override_auth(ADMIN_USER)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                f"/api/v1/orders/{ORDER_ID}/reroute",
                json={
                    "new_phlebotomist_id": str(NEW_PHLEB_ID),
                    "reason": "Schedule conflict",
                },
            )
        assert resp.status_code == 200
        assert order.status == OrderStatus.ASSIGNED
    finally:
        _clear_overrides()


@pytest.mark.anyio
async def test_reroute_wrong_status():
    """Reroute should fail for orders not in ASSIGNED/ACCEPTED."""
    order = _make_order(status=OrderStatus.PENDING)

    mock_db = AsyncMock()

    async def fake_execute(stmt):
        result = MagicMock()
        result.scalar_one_or_none.return_value = order
        return result

    mock_db.execute = fake_execute

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db
    _override_auth(ADMIN_USER)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                f"/api/v1/orders/{ORDER_ID}/reroute",
                json={
                    "new_phlebotomist_id": str(NEW_PHLEB_ID),
                    "reason": "test",
                },
            )
        assert resp.status_code == 400
        assert "must be assigned or accepted" in _get_detail(resp)
    finally:
        _clear_overrides()


@pytest.mark.anyio
async def test_reroute_order_not_found():
    """Reroute should 404 for missing order."""
    mock_db = AsyncMock()

    async def fake_execute(stmt):
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        return result

    mock_db.execute = fake_execute

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db
    _override_auth(ADMIN_USER)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                f"/api/v1/orders/{uuid.uuid4()}/reroute",
                json={
                    "new_phlebotomist_id": str(NEW_PHLEB_ID),
                    "reason": "test",
                },
            )
        assert resp.status_code == 404
    finally:
        _clear_overrides()


@pytest.mark.anyio
async def test_reroute_phleb_on_leave():
    """Reroute should fail if new phlebotomist is on leave."""
    order = _make_order(status=OrderStatus.ASSIGNED)
    phleb = _make_phleb()
    phleb_user = _make_phleb_user()
    pincode = _make_pincode()
    zone_assign = _make_zone_assignment()
    leave = MagicMock(spec=PhlebotomistLeave)

    mock_db = AsyncMock()
    call_count = 0

    async def fake_execute(stmt):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            result.scalar_one_or_none.return_value = order
        elif call_count == 2:
            result.scalar_one_or_none.return_value = phleb
        elif call_count == 3:
            result.scalar_one_or_none.return_value = phleb_user
        elif call_count == 4:
            result.scalar_one.return_value = pincode
        elif call_count == 5:
            result.scalar_one_or_none.return_value = zone_assign
        elif call_count == 6:
            result.scalar_one_or_none.return_value = leave
        return result

    mock_db.execute = fake_execute

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db
    _override_auth(ADMIN_USER)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                f"/api/v1/orders/{ORDER_ID}/reroute",
                json={
                    "new_phlebotomist_id": str(NEW_PHLEB_ID),
                    "reason": "test",
                },
            )
        assert resp.status_code == 400
        assert "on leave" in _get_detail(resp)
    finally:
        _clear_overrides()


# ── Bulk Assign Tests ────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_bulk_assign_success():
    """Bulk assign single order successfully."""
    order = _make_order(status=OrderStatus.PENDING)
    phleb = _make_phleb()
    phleb_user = _make_phleb_user()
    pincode = _make_pincode()
    zone_assign = _make_zone_assignment()

    mock_db = AsyncMock()
    call_count = 0

    async def fake_execute(stmt):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:  # Order
            result.scalar_one_or_none.return_value = order
        elif call_count == 2:  # Phleb
            result.scalar_one_or_none.return_value = phleb
        elif call_count == 3:  # Phleb user
            result.scalar_one_or_none.return_value = phleb_user
        elif call_count == 4:  # Pincode
            result.scalar_one.return_value = pincode
        elif call_count == 5:  # Zone
            result.scalar_one_or_none.return_value = zone_assign
        elif call_count == 6:  # Leave
            result.scalar_one_or_none.return_value = None
        return result

    mock_db.execute = fake_execute
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db
    _override_auth(ADMIN_USER)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/orders/bulk-assign",
                json={
                    "assignments": [
                        {
                            "order_id": str(ORDER_ID),
                            "phlebotomist_id": str(NEW_PHLEB_ID),
                        }
                    ]
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["success"]) == 1
        assert len(data["failed"]) == 0
        assert data["success"][0]["order_id"] == str(ORDER_ID)
    finally:
        _clear_overrides()


@pytest.mark.anyio
async def test_bulk_assign_mixed():
    """Bulk assign with one success and one failure (order not found)."""
    order = _make_order(status=OrderStatus.PENDING, order_id=ORDER_ID)
    phleb = _make_phleb()
    phleb_user = _make_phleb_user()
    pincode = _make_pincode()
    zone_assign = _make_zone_assignment()

    mock_db = AsyncMock()
    call_count = 0

    async def fake_execute(stmt):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        # First assignment: order found + full validation
        if call_count == 1:
            result.scalar_one_or_none.return_value = order
        elif call_count == 2:
            result.scalar_one_or_none.return_value = phleb
        elif call_count == 3:
            result.scalar_one_or_none.return_value = phleb_user
        elif call_count == 4:
            result.scalar_one.return_value = pincode
        elif call_count == 5:
            result.scalar_one_or_none.return_value = zone_assign
        elif call_count == 6:
            result.scalar_one_or_none.return_value = None
        # Second assignment: order not found
        elif call_count == 7:
            result.scalar_one_or_none.return_value = None
        return result

    mock_db.execute = fake_execute
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db
    _override_auth(ADMIN_USER)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/orders/bulk-assign",
                json={
                    "assignments": [
                        {
                            "order_id": str(ORDER_ID),
                            "phlebotomist_id": str(NEW_PHLEB_ID),
                        },
                        {
                            "order_id": str(ORDER_ID_2),
                            "phlebotomist_id": str(NEW_PHLEB_ID),
                        },
                    ]
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["success"]) == 1
        assert len(data["failed"]) == 1
        assert data["failed"][0]["reason"] == "Order not found"
    finally:
        _clear_overrides()


@pytest.mark.anyio
async def test_bulk_assign_wrong_status():
    """Bulk assign fails for non-PENDING order."""
    order = _make_order(status=OrderStatus.ASSIGNED)

    mock_db = AsyncMock()

    async def fake_execute(stmt):
        result = MagicMock()
        result.scalar_one_or_none.return_value = order
        return result

    mock_db.execute = fake_execute
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db
    _override_auth(ADMIN_USER)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/orders/bulk-assign",
                json={
                    "assignments": [
                        {
                            "order_id": str(ORDER_ID),
                            "phlebotomist_id": str(NEW_PHLEB_ID),
                        }
                    ]
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["success"]) == 0
        assert len(data["failed"]) == 1
        assert "must be pending" in data["failed"][0]["reason"]
    finally:
        _clear_overrides()
