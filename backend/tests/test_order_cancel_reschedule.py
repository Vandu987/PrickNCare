"""Tests for order cancellation and rescheduling APIs — task 6.8."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.main import app
from app.models.nsa import NSARecord
from app.models.orders import Order, OrderStatus
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
CLIENT_USER_ID = uuid.uuid4()
CLIENT_USER = _fake_user(UserRole.CLIENT_USER, user_id=CLIENT_USER_ID)
FAKE_ORDER_ID = uuid.uuid4()
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


def _make_order(
    status: OrderStatus = OrderStatus.PENDING,
    client_id: uuid.UUID | None = None,
    phlebotomist_id: uuid.UUID | None = None,
) -> MagicMock:
    order = MagicMock(spec=Order)
    order.id = FAKE_ORDER_ID
    order.booking_id = "PNC-20260222-0001"
    order.client_id = client_id or FAKE_CLIENT_ID
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
    order.status = status
    order.priority = "normal"
    order.special_instructions = None
    order.amount = 0.0
    order.payment_mode = "cash"
    order.payment_status = "pending"
    order.assigned_phlebotomist_id = phlebotomist_id
    order.created_at = datetime.now(UTC)
    return order


def _mock_db_for_cancel(order, client_id_for_rbac=None):
    """Create a mock DB that returns order on first call, optionally client_id on second."""
    db = AsyncMock()
    call_count = 0

    async def _execute(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            result.scalar_one_or_none.return_value = order
        elif call_count == 2:
            result.scalar_one_or_none.return_value = client_id_for_rbac
        return result

    db.execute = AsyncMock(side_effect=_execute)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    return db


def _mock_db_for_reschedule(
    order, pincode_row=None, nsa_record=None, client_id_for_rbac=None
):
    """Create a mock DB for reschedule endpoint."""
    db = AsyncMock()
    call_count = 0

    async def _execute(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            result.scalar_one_or_none.return_value = order
        elif client_id_for_rbac is not None and call_count == 2:
            # RBAC check for client_user
            result.scalar_one_or_none.return_value = client_id_for_rbac
        else:
            # pincode or nsa lookups
            if pincode_row is not None and nsa_record is None:
                # Could be pincode or nsa call
                if call_count <= 3:
                    result.scalar_one_or_none.return_value = pincode_row
                else:
                    result.scalar_one_or_none.return_value = None
            elif pincode_row is not None and nsa_record is not None:
                if call_count <= 3:
                    result.scalar_one_or_none.return_value = pincode_row
                else:
                    result.scalar_one_or_none.return_value = nsa_record
            else:
                result.scalar_one_or_none.return_value = None
        return result

    db.execute = AsyncMock(side_effect=_execute)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    return db


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    _clear_overrides()


# ── Cancel Tests ─────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_cancel_order_success():
    """Admin can cancel a PENDING order."""
    _override_auth(ADMIN_USER)
    order = _make_order(OrderStatus.PENDING, phlebotomist_id=uuid.uuid4())
    db = _mock_db_for_cancel(order)
    app.dependency_overrides[get_db] = lambda: db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            f"/api/v1/orders/{FAKE_ORDER_ID}/cancel",
            json={"reason": "Patient request"},
        )

    assert resp.status_code == 200
    assert order.status == OrderStatus.CANCELLED


@pytest.mark.anyio
async def test_cancel_order_not_cancellable():
    """Cannot cancel an IN_TRANSIT order."""
    _override_auth(ADMIN_USER)
    order = _make_order(OrderStatus.IN_TRANSIT)
    db = _mock_db_for_cancel(order)
    app.dependency_overrides[get_db] = lambda: db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            f"/api/v1/orders/{FAKE_ORDER_ID}/cancel",
            json={"reason": "Too late"},
        )

    assert resp.status_code == 400
    assert "Cannot cancel" in resp.json()["error"]["message"]


@pytest.mark.anyio
async def test_cancel_order_not_found():
    """Cancel returns 404 for missing order."""
    _override_auth(ADMIN_USER)
    db = _mock_db_for_cancel(None)
    app.dependency_overrides[get_db] = lambda: db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            f"/api/v1/orders/{uuid.uuid4()}/cancel",
            json={"reason": "Test"},
        )

    assert resp.status_code == 404


@pytest.mark.anyio
async def test_cancel_order_missing_reason(client):
    """Cancel requires a reason."""
    _override_auth(ADMIN_USER)

    resp = await client.post(
        f"/api/v1/orders/{FAKE_ORDER_ID}/cancel",
        json={},
    )

    assert resp.status_code == 422


@pytest.mark.anyio
async def test_cancel_assigned_clears_phlebotomist():
    """Cancelling an ASSIGNED order clears phlebotomist_id."""
    _override_auth(ADMIN_USER)
    phleb_id = uuid.uuid4()
    order = _make_order(OrderStatus.ASSIGNED, phlebotomist_id=phleb_id)
    db = _mock_db_for_cancel(order)
    app.dependency_overrides[get_db] = lambda: db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            f"/api/v1/orders/{FAKE_ORDER_ID}/cancel",
            json={"reason": "Reassigning"},
        )

    assert resp.status_code == 200
    assert order.assigned_phlebotomist_id is None


@pytest.mark.anyio
async def test_cancel_client_user_own_order():
    """Client user can cancel their own order."""
    _override_auth(CLIENT_USER)
    order = _make_order(OrderStatus.PENDING, client_id=FAKE_CLIENT_ID)
    db = _mock_db_for_cancel(order, client_id_for_rbac=FAKE_CLIENT_ID)
    app.dependency_overrides[get_db] = lambda: db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            f"/api/v1/orders/{FAKE_ORDER_ID}/cancel",
            json={"reason": "Changed mind"},
        )

    assert resp.status_code == 200


@pytest.mark.anyio
async def test_cancel_client_user_other_order():
    """Client user cannot cancel another client's order."""
    _override_auth(CLIENT_USER)
    other_client_id = uuid.uuid4()
    order = _make_order(OrderStatus.PENDING, client_id=other_client_id)
    db = _mock_db_for_cancel(order, client_id_for_rbac=FAKE_CLIENT_ID)
    app.dependency_overrides[get_db] = lambda: db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            f"/api/v1/orders/{FAKE_ORDER_ID}/cancel",
            json={"reason": "Sneaky"},
        )

    assert resp.status_code == 403


# ── Reschedule Tests ─────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_reschedule_order_success():
    """Admin can reschedule a PENDING order."""
    _override_auth(ADMIN_USER)
    order = _make_order(OrderStatus.PENDING)
    pincode_row = MagicMock(spec=Pincode)
    pincode_row.pincode = "400001"

    db = AsyncMock()
    call_count = 0

    async def _execute(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            result.scalar_one_or_none.return_value = order
        elif call_count == 2:
            result.scalar_one_or_none.return_value = pincode_row
        elif call_count == 3:
            result.scalar_one_or_none.return_value = None  # no NSA
        return result

    db.execute = AsyncMock(side_effect=_execute)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    app.dependency_overrides[get_db] = lambda: db

    new_date = (date.today() + timedelta(days=3)).isoformat()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            f"/api/v1/orders/{FAKE_ORDER_ID}/reschedule",
            json={"new_date": new_date, "new_time_slot": "14:00-16:00"},
        )

    assert resp.status_code == 200
    assert order.appointment_time_slot == "14:00-16:00"


@pytest.mark.anyio
async def test_reschedule_resets_assigned_to_pending():
    """Rescheduling an ASSIGNED order resets to PENDING."""
    _override_auth(ADMIN_USER)
    phleb_id = uuid.uuid4()
    order = _make_order(OrderStatus.ASSIGNED, phlebotomist_id=phleb_id)
    pincode_row = MagicMock(spec=Pincode)
    pincode_row.pincode = "400001"

    db = AsyncMock()
    call_count = 0

    async def _execute(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            result.scalar_one_or_none.return_value = order
        elif call_count == 2:
            result.scalar_one_or_none.return_value = pincode_row
        elif call_count == 3:
            result.scalar_one_or_none.return_value = None
        return result

    db.execute = AsyncMock(side_effect=_execute)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    app.dependency_overrides[get_db] = lambda: db

    new_date = (date.today() + timedelta(days=3)).isoformat()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            f"/api/v1/orders/{FAKE_ORDER_ID}/reschedule",
            json={"new_date": new_date, "new_time_slot": "14:00-16:00"},
        )

    assert resp.status_code == 200
    assert order.status == OrderStatus.PENDING
    assert order.assigned_phlebotomist_id is None


@pytest.mark.anyio
async def test_reschedule_nsa_blocked():
    """Reschedule fails if pincode is now NSA."""
    _override_auth(ADMIN_USER)
    order = _make_order(OrderStatus.PENDING)
    pincode_row = MagicMock(spec=Pincode)
    pincode_row.pincode = "400001"
    nsa = MagicMock(spec=NSARecord)

    db = AsyncMock()
    call_count = 0

    async def _execute(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            result.scalar_one_or_none.return_value = order
        elif call_count == 2:
            result.scalar_one_or_none.return_value = pincode_row
        elif call_count == 3:
            result.scalar_one_or_none.return_value = nsa
        return result

    db.execute = AsyncMock(side_effect=_execute)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    app.dependency_overrides[get_db] = lambda: db

    new_date = (date.today() + timedelta(days=3)).isoformat()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            f"/api/v1/orders/{FAKE_ORDER_ID}/reschedule",
            json={"new_date": new_date, "new_time_slot": "14:00-16:00"},
        )

    assert resp.status_code == 400
    assert "serviceable" in resp.json()["error"]["message"]


@pytest.mark.anyio
async def test_reschedule_not_reschedulable():
    """Cannot reschedule a COMPLETED order."""
    _override_auth(ADMIN_USER)
    order = _make_order(OrderStatus.COMPLETED)
    db = _mock_db_for_cancel(order)  # reuse — only needs first call
    app.dependency_overrides[get_db] = lambda: db

    new_date = (date.today() + timedelta(days=3)).isoformat()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            f"/api/v1/orders/{FAKE_ORDER_ID}/reschedule",
            json={"new_date": new_date, "new_time_slot": "14:00-16:00"},
        )

    assert resp.status_code == 400


@pytest.mark.anyio
async def test_reschedule_past_date_rejected(client):
    """Reschedule with past date is rejected by schema validation."""
    _override_auth(ADMIN_USER)

    past_date = (date.today() - timedelta(days=1)).isoformat()
    resp = await client.post(
        f"/api/v1/orders/{FAKE_ORDER_ID}/reschedule",
        json={"new_date": past_date, "new_time_slot": "09:00-11:00"},
    )

    assert resp.status_code == 422
