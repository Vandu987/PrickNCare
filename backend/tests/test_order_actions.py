"""API tests for phlebotomist order action endpoints — task 6.7."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.orders import Order, OrderStatus
from app.models.users import User, UserRole

# ── Helpers ──────────────────────────────────────────────────────────────

PHLEB_USER_ID = uuid.uuid4()
PHLEB_ID = uuid.uuid4()
ORDER_ID = uuid.uuid4()


def _fake_user(
    role: UserRole = UserRole.PHLEBOTOMIST,
    user_id: uuid.UUID | None = None,
) -> User:
    user = MagicMock(spec=User)
    user.id = user_id or uuid.uuid4()
    user.email = f"{role.value}@test.com"
    user.phone = "+911234567890"
    user.role = role
    user.is_active = True
    return user


PHLEB_USER = _fake_user(UserRole.PHLEBOTOMIST, PHLEB_USER_ID)


def _override_auth(user: User) -> None:
    from app.api.deps import get_current_active_user, get_current_user

    app.dependency_overrides[get_current_active_user] = lambda: user
    app.dependency_overrides[get_current_user] = lambda: user


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def _make_order(
    status: OrderStatus = OrderStatus.ASSIGNED,
    phleb_id: uuid.UUID | None = PHLEB_ID,
) -> MagicMock:
    order = MagicMock(spec=Order)
    order.id = ORDER_ID
    order.status = status
    order.assigned_phlebotomist_id = phleb_id
    order.assigned_at = None
    order.accepted_at = None
    order.collected_at = None
    order.amount = 0
    order.payment_mode = "cash"
    order.collection_proof_url = None
    order.patient_signature_url = None
    return order


def _mock_db(order: MagicMock | None, phleb_id: uuid.UUID | None = PHLEB_ID):
    """Create a mock db that returns phleb_id then order on successive execute calls."""
    mock_db = AsyncMock()
    call_count = 0

    async def fake_execute(stmt):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            # Phlebotomist lookup
            result.scalar_one_or_none.return_value = phleb_id
        else:
            # Order lookup
            result.scalar_one_or_none.return_value = order
        return result

    mock_db.execute = fake_execute
    mock_db.commit = AsyncMock()
    mock_db.add = MagicMock()

    async def fake_refresh(obj):
        if not hasattr(obj, "id") or obj.id is None:
            obj.id = uuid.uuid4()
        if not hasattr(obj, "created_at") or obj.created_at is None:
            obj.created_at = "2026-01-01T00:00:00+00:00"

    mock_db.refresh = fake_refresh
    return mock_db


@pytest.fixture(autouse=True)
def _cleanup():
    _override_auth(PHLEB_USER)
    yield
    _clear_overrides()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _set_db(mock_db):
    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db


# ── Accept ───────────────────────────────────────────────────────────────


class TestAcceptOrder:
    @pytest.mark.anyio
    async def test_accept_success(self, client: AsyncClient):
        order = _make_order(OrderStatus.ASSIGNED)
        db = _mock_db(order)
        _set_db(db)

        resp = await client.post(
            f"/api/v1/orders/{ORDER_ID}/accept",
            headers={"Authorization": "Bearer fake"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "accepted"
        assert order.status == OrderStatus.ACCEPTED

    @pytest.mark.anyio
    async def test_accept_wrong_status(self, client: AsyncClient):
        order = _make_order(OrderStatus.PENDING)
        db = _mock_db(order)
        _set_db(db)

        resp = await client.post(
            f"/api/v1/orders/{ORDER_ID}/accept",
            headers={"Authorization": "Bearer fake"},
        )
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_accept_not_assigned_to_user(self, client: AsyncClient):
        order = _make_order(OrderStatus.ASSIGNED, phleb_id=uuid.uuid4())
        db = _mock_db(order)
        _set_db(db)

        resp = await client.post(
            f"/api/v1/orders/{ORDER_ID}/accept",
            headers={"Authorization": "Bearer fake"},
        )
        assert resp.status_code == 403

    @pytest.mark.anyio
    async def test_accept_order_not_found(self, client: AsyncClient):
        db = _mock_db(None)
        _set_db(db)

        resp = await client.post(
            f"/api/v1/orders/{ORDER_ID}/accept",
            headers={"Authorization": "Bearer fake"},
        )
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_accept_non_phleb_forbidden(self, client: AsyncClient):
        _override_auth(_fake_user(UserRole.CLIENT_USER))
        order = _make_order(OrderStatus.ASSIGNED)
        db = _mock_db(order)
        _set_db(db)

        resp = await client.post(
            f"/api/v1/orders/{ORDER_ID}/accept",
            headers={"Authorization": "Bearer fake"},
        )
        assert resp.status_code == 403


# ── Reject ───────────────────────────────────────────────────────────────


class TestRejectOrder:
    @pytest.mark.anyio
    async def test_reject_success(self, client: AsyncClient):
        order = _make_order(OrderStatus.ASSIGNED)
        db = _mock_db(order)
        _set_db(db)

        resp = await client.post(
            f"/api/v1/orders/{ORDER_ID}/reject",
            json={"reason": "Too far away"},
            headers={"Authorization": "Bearer fake"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "pending"
        assert order.status == OrderStatus.PENDING
        assert order.assigned_phlebotomist_id is None

    @pytest.mark.anyio
    async def test_reject_wrong_status(self, client: AsyncClient):
        order = _make_order(OrderStatus.ACCEPTED)
        db = _mock_db(order)
        _set_db(db)

        resp = await client.post(
            f"/api/v1/orders/{ORDER_ID}/reject",
            json={"reason": "reason"},
            headers={"Authorization": "Bearer fake"},
        )
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_reject_missing_reason(self, client: AsyncClient):
        order = _make_order(OrderStatus.ASSIGNED)
        db = _mock_db(order)
        _set_db(db)

        resp = await client.post(
            f"/api/v1/orders/{ORDER_ID}/reject",
            json={},
            headers={"Authorization": "Bearer fake"},
        )
        assert resp.status_code == 422


# ── Start Transit ────────────────────────────────────────────────────────


class TestStartTransit:
    @pytest.mark.anyio
    async def test_start_transit_success(self, client: AsyncClient):
        order = _make_order(OrderStatus.ACCEPTED)
        db = _mock_db(order)
        _set_db(db)

        resp = await client.post(
            f"/api/v1/orders/{ORDER_ID}/start-transit",
            headers={"Authorization": "Bearer fake"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "in_transit"
        assert order.status == OrderStatus.IN_TRANSIT

    @pytest.mark.anyio
    async def test_start_transit_wrong_status(self, client: AsyncClient):
        order = _make_order(OrderStatus.ASSIGNED)
        db = _mock_db(order)
        _set_db(db)

        resp = await client.post(
            f"/api/v1/orders/{ORDER_ID}/start-transit",
            headers={"Authorization": "Bearer fake"},
        )
        assert resp.status_code == 400


# ── Collect ──────────────────────────────────────────────────────────────


class TestCollectOrder:
    @pytest.mark.anyio
    async def test_collect_success(self, client: AsyncClient):
        order = _make_order(OrderStatus.IN_TRANSIT)
        db = _mock_db(order)
        _set_db(db)

        resp = await client.post(
            f"/api/v1/orders/{ORDER_ID}/collect",
            json={
                "payment_amount": 500.0,
                "payment_mode": "cash",
                "photo_url": "https://example.com/photo.jpg",
                "signature_url": "https://example.com/sig.png",
            },
            headers={"Authorization": "Bearer fake"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "collected"
        assert order.status == OrderStatus.COLLECTED
        assert order.amount == 500.0
        assert order.collection_proof_url == "https://example.com/photo.jpg"
        assert order.patient_signature_url == "https://example.com/sig.png"

    @pytest.mark.anyio
    async def test_collect_wrong_status(self, client: AsyncClient):
        order = _make_order(OrderStatus.ACCEPTED)
        db = _mock_db(order)
        _set_db(db)

        resp = await client.post(
            f"/api/v1/orders/{ORDER_ID}/collect",
            json={"payment_amount": 100, "payment_mode": "cash"},
            headers={"Authorization": "Bearer fake"},
        )
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_collect_invalid_payment_mode(self, client: AsyncClient):
        order = _make_order(OrderStatus.IN_TRANSIT)
        db = _mock_db(order)
        _set_db(db)

        resp = await client.post(
            f"/api/v1/orders/{ORDER_ID}/collect",
            json={"payment_amount": 100, "payment_mode": "bitcoin"},
            headers={"Authorization": "Bearer fake"},
        )
        assert resp.status_code == 422
