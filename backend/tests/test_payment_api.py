"""API tests for payment recording — task 9.1."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.main import app
from app.models.orders import Order, OrderStatus
from app.models.payments import OrderPaymentMode, OrderPaymentStatus, Payment
from app.models.users import User, UserRole

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
PHLEB_USER = _fake_user(UserRole.PHLEBOTOMIST, user_id=uuid.uuid4())
CLIENT_USER = _fake_user(UserRole.CLIENT_USER)

FAKE_ORDER_ID = uuid.uuid4()
FAKE_PAYMENT_ID = uuid.uuid4()


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


def _fake_order(
    order_id: uuid.UUID | None = None,
    status: OrderStatus = OrderStatus.COLLECTED,
) -> MagicMock:
    order = MagicMock(spec=Order)
    order.id = order_id or FAKE_ORDER_ID
    order.status = status
    order.client_id = uuid.uuid4()
    return order


def _fake_payment(
    order_id: uuid.UUID | None = None,
    collected_by: uuid.UUID | None = None,
) -> MagicMock:
    p = MagicMock(spec=Payment)
    p.id = FAKE_PAYMENT_ID
    p.order_id = order_id or FAKE_ORDER_ID
    p.amount = 500.00
    p.mode = OrderPaymentMode.CASH
    p.status = OrderPaymentStatus.COLLECTED
    p.transaction_ref = None
    p.collected_by = collected_by or PHLEB_USER.id
    p.collected_at = datetime.now(UTC)
    p.created_at = datetime.now(UTC)
    p.updated_at = datetime.now(UTC)
    p.notes = None
    return p


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    _clear_overrides()


# ── POST /orders/{order_id}/payment ─────────────────────────────────────


@pytest.mark.anyio
async def test_record_payment_success(client: AsyncClient):
    """Phlebotomist can record payment for a collected order."""
    _override_auth(PHLEB_USER)
    order = _fake_order(status=OrderStatus.COLLECTED)
    payment = _fake_payment(collected_by=PHLEB_USER.id)

    mock_db = AsyncMock()
    # First execute: order lookup
    mock_order_result = MagicMock()
    mock_order_result.scalar_one_or_none.return_value = order
    # Second execute (refresh is separate)
    mock_db.execute.return_value = mock_order_result
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock(side_effect=lambda p: None)
    mock_db.add = MagicMock()

    with patch("app.api.v1.payments.get_db", return_value=mock_db):
        # We need to patch at the dependency level
        pass

    # Use dependency override for db
    from app.core.database import get_db

    async def _fake_db():
        yield mock_db

    app.dependency_overrides[get_db] = _fake_db

    # Patch Payment constructor to return our fake
    with patch("app.api.v1.payments.Payment", return_value=payment):
        resp = await client.post(
            f"/api/v1/orders/{FAKE_ORDER_ID}/payment",
            json={"amount": 500.0, "mode": "cash"},
            headers={"Authorization": "Bearer fake"},
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["amount"] == 500.0
    assert data["mode"] == "cash"


@pytest.mark.anyio
async def test_record_payment_order_not_found(client: AsyncClient):
    """404 when order doesn't exist."""
    _override_auth(PHLEB_USER)

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    from app.core.database import get_db

    async def _fake_db():
        yield mock_db

    app.dependency_overrides[get_db] = _fake_db

    resp = await client.post(
        f"/api/v1/orders/{uuid.uuid4()}/payment",
        json={"amount": 500.0, "mode": "cash"},
        headers={"Authorization": "Bearer fake"},
    )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_record_payment_wrong_status(client: AsyncClient):
    """400 when order is in non-payable status."""
    _override_auth(PHLEB_USER)
    order = _fake_order(status=OrderStatus.CANCELLED)

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = order
    mock_db.execute.return_value = mock_result

    from app.core.database import get_db

    async def _fake_db():
        yield mock_db

    app.dependency_overrides[get_db] = _fake_db

    resp = await client.post(
        f"/api/v1/orders/{FAKE_ORDER_ID}/payment",
        json={"amount": 500.0, "mode": "cash"},
        headers={"Authorization": "Bearer fake"},
    )
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_record_payment_forbidden_for_client_user(client: AsyncClient):
    """Client users cannot record payments."""
    _override_auth(CLIENT_USER)

    resp = await client.post(
        f"/api/v1/orders/{FAKE_ORDER_ID}/payment",
        json={"amount": 500.0, "mode": "cash"},
        headers={"Authorization": "Bearer fake"},
    )
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_record_payment_invalid_mode(client: AsyncClient):
    """422 for invalid payment mode."""
    _override_auth(PHLEB_USER)
    order = _fake_order(status=OrderStatus.COLLECTED)

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = order
    mock_db.execute.return_value = mock_result

    from app.core.database import get_db

    async def _fake_db():
        yield mock_db

    app.dependency_overrides[get_db] = _fake_db

    resp = await client.post(
        f"/api/v1/orders/{FAKE_ORDER_ID}/payment",
        json={"amount": 500.0, "mode": "bitcoin"},
        headers={"Authorization": "Bearer fake"},
    )
    assert resp.status_code == 422


# ── GET /payments ────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_list_payments_admin(client: AsyncClient):
    """Admin can list all payments."""
    _override_auth(ADMIN_USER)

    mock_db = AsyncMock()
    # count query
    mock_count = MagicMock()
    mock_count.scalar.return_value = 0
    # select query
    mock_select = MagicMock()
    mock_select.scalars.return_value.all.return_value = []

    mock_db.execute = AsyncMock(side_effect=[mock_count, mock_select])

    from app.core.database import get_db

    async def _fake_db():
        yield mock_db

    app.dependency_overrides[get_db] = _fake_db

    resp = await client.get(
        "/api/v1/payments",
        headers={"Authorization": "Bearer fake"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.anyio
async def test_list_payments_forbidden_for_client(client: AsyncClient):
    """Client users cannot list payments."""
    _override_auth(CLIENT_USER)

    resp = await client.get(
        "/api/v1/payments",
        headers={"Authorization": "Bearer fake"},
    )
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_list_payments_phlebotomist_sees_own(client: AsyncClient):
    """Phlebotomist can list payments (filtered to own)."""
    _override_auth(PHLEB_USER)

    mock_db = AsyncMock()
    mock_count = MagicMock()
    mock_count.scalar.return_value = 0
    mock_select = MagicMock()
    mock_select.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(side_effect=[mock_count, mock_select])

    from app.core.database import get_db

    async def _fake_db():
        yield mock_db

    app.dependency_overrides[get_db] = _fake_db

    resp = await client.get(
        "/api/v1/payments",
        headers={"Authorization": "Bearer fake"},
    )
    assert resp.status_code == 200
