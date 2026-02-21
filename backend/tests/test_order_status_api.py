"""API tests for order status management — task 6.3."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.orders import Order, OrderStatus, OrderStatusHistory
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
ADMIN_USER_ID = ADMIN_USER.id
ORDER_ID = uuid.uuid4()


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


def _make_order(status: OrderStatus = OrderStatus.PENDING) -> MagicMock:
    order = MagicMock(spec=Order)
    order.id = ORDER_ID
    order.status = status
    return order


def _make_history(
    order_id: uuid.UUID,
    status: OrderStatus,
    changed_by: uuid.UUID,
    notes: str | None = None,
) -> MagicMock:
    h = MagicMock(spec=OrderStatusHistory)
    h.id = uuid.uuid4()
    h.order_id = order_id
    h.status = status
    h.changed_by = changed_by
    h.notes = notes
    h.created_at = "2026-01-01T00:00:00+00:00"
    return h


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _cleanup():
    _override_auth(ADMIN_USER)
    yield
    _clear_overrides()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ── State machine unit tests ────────────────────────────────────────────

from app.api.v1.orders import validate_transition


class TestValidateTransition:
    """Test the state machine validation function."""

    @pytest.mark.parametrize(
        "current,target",
        [
            (OrderStatus.PENDING, OrderStatus.ASSIGNED),
            (OrderStatus.PENDING, OrderStatus.CANCELLED),
            (OrderStatus.ASSIGNED, OrderStatus.ACCEPTED),
            (OrderStatus.ASSIGNED, OrderStatus.PENDING),
            (OrderStatus.ASSIGNED, OrderStatus.CANCELLED),
            (OrderStatus.ACCEPTED, OrderStatus.IN_TRANSIT),
            (OrderStatus.ACCEPTED, OrderStatus.PENDING),
            (OrderStatus.IN_TRANSIT, OrderStatus.COLLECTED),
            (OrderStatus.IN_TRANSIT, OrderStatus.UNCOLLECTED),
            (OrderStatus.IN_TRANSIT, OrderStatus.NSA),
            (OrderStatus.UNCOLLECTED, OrderStatus.PENDING),
            (OrderStatus.NSA, OrderStatus.PENDING),
        ],
    )
    def test_valid_transitions(self, current: OrderStatus, target: OrderStatus):
        assert validate_transition(current, target) is True

    @pytest.mark.parametrize(
        "current,target",
        [
            (OrderStatus.PENDING, OrderStatus.COLLECTED),
            (OrderStatus.PENDING, OrderStatus.IN_TRANSIT),
            (OrderStatus.COLLECTED, OrderStatus.PENDING),
            (OrderStatus.COLLECTED, OrderStatus.CANCELLED),
            (OrderStatus.CANCELLED, OrderStatus.PENDING),
            (OrderStatus.CANCELLED, OrderStatus.ASSIGNED),
            (OrderStatus.IN_TRANSIT, OrderStatus.ASSIGNED),
            (OrderStatus.NSA, OrderStatus.CANCELLED),
        ],
    )
    def test_invalid_transitions(self, current: OrderStatus, target: OrderStatus):
        assert validate_transition(current, target) is False

    def test_terminal_collected_no_transitions(self):
        for s in OrderStatus:
            assert validate_transition(OrderStatus.COLLECTED, s) is False

    def test_terminal_cancelled_no_transitions(self):
        for s in OrderStatus:
            assert validate_transition(OrderStatus.CANCELLED, s) is False


# ── PUT /orders/{id}/status tests ───────────────────────────────────────


class TestUpdateOrderStatus:
    """Test the PUT /orders/{order_id}/status endpoint."""

    @pytest.mark.anyio
    async def test_valid_transition_pending_to_assigned(self, client: AsyncClient):
        order = _make_order(OrderStatus.PENDING)

        mock_db = AsyncMock()
        mock_result_order = MagicMock()
        mock_result_order.scalar_one_or_none.return_value = order
        mock_db.execute.return_value = mock_result_order
        mock_db.commit = AsyncMock()

        from datetime import UTC, datetime

        async def fake_refresh(obj):
            if not hasattr(obj, 'created_at') or obj.created_at is None:
                obj.created_at = datetime.now(UTC)

        mock_db.refresh = fake_refresh
        mock_db.add = MagicMock()

        from app.core.database import get_db

        app.dependency_overrides[get_db] = lambda: mock_db
        resp = await client.put(
            f"/api/v1/orders/{ORDER_ID}/status",
            json={"status": "assigned", "reason": "Assigning"},
            headers={"Authorization": "Bearer fake"},
        )
        app.dependency_overrides.pop(get_db, None)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "assigned"

    @pytest.mark.anyio
    async def test_invalid_transition_returns_400(self, client: AsyncClient):
        order = _make_order(OrderStatus.PENDING)

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = order
        mock_db.execute.return_value = mock_result

        from app.core.database import get_db

        app.dependency_overrides[get_db] = lambda: mock_db
        resp = await client.put(
            f"/api/v1/orders/{ORDER_ID}/status",
            json={"status": "collected"},
            headers={"Authorization": "Bearer fake"},
        )
        app.dependency_overrides.pop(get_db, None)

        assert resp.status_code == 400
        body = resp.json()
        msg = body.get("detail", "") or body.get("error", {}).get("message", "")
        assert "Cannot transition" in msg

    @pytest.mark.anyio
    async def test_terminal_collected_cannot_transition(self, client: AsyncClient):
        order = _make_order(OrderStatus.COLLECTED)

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = order
        mock_db.execute.return_value = mock_result

        from app.core.database import get_db

        app.dependency_overrides[get_db] = lambda: mock_db
        resp = await client.put(
            f"/api/v1/orders/{ORDER_ID}/status",
            json={"status": "pending"},
            headers={"Authorization": "Bearer fake"},
        )
        app.dependency_overrides.pop(get_db, None)

        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_terminal_cancelled_cannot_transition(self, client: AsyncClient):
        order = _make_order(OrderStatus.CANCELLED)

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = order
        mock_db.execute.return_value = mock_result

        from app.core.database import get_db

        app.dependency_overrides[get_db] = lambda: mock_db
        resp = await client.put(
            f"/api/v1/orders/{ORDER_ID}/status",
            json={"status": "pending"},
            headers={"Authorization": "Bearer fake"},
        )
        app.dependency_overrides.pop(get_db, None)

        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_order_not_found_returns_404(self, client: AsyncClient):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        from app.core.database import get_db

        app.dependency_overrides[get_db] = lambda: mock_db
        resp = await client.put(
            f"/api/v1/orders/{uuid.uuid4()}/status",
            json={"status": "assigned"},
            headers={"Authorization": "Bearer fake"},
        )
        app.dependency_overrides.pop(get_db, None)

        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_reason_stored_in_history(self, client: AsyncClient):
        """Verify the reason is passed as notes to OrderStatusHistory."""
        order = _make_order(OrderStatus.PENDING)
        added_objects: list = []

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = order
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()

        original_add = mock_db.add

        def capture_add(obj):
            added_objects.append(obj)
            return original_add(obj)

        mock_db.add = capture_add

        # Make refresh populate the history mock
        async def fake_refresh(obj):
            obj.id = uuid.uuid4()
            obj.created_at = "2026-01-01T00:00:00+00:00"

        mock_db.refresh = fake_refresh

        from app.core.database import get_db

        app.dependency_overrides[get_db] = lambda: mock_db
        resp = await client.put(
            f"/api/v1/orders/{ORDER_ID}/status",
            json={"status": "assigned", "reason": "Test reason"},
            headers={"Authorization": "Bearer fake"},
        )
        app.dependency_overrides.pop(get_db, None)

        assert resp.status_code == 200
        # Check the OrderStatusHistory object was created with correct notes
        history_objs = [o for o in added_objects if isinstance(o, OrderStatusHistory)]
        assert len(history_objs) == 1
        assert history_objs[0].notes == "Test reason"
        assert history_objs[0].changed_by == ADMIN_USER_ID

    @pytest.mark.anyio
    async def test_changed_by_captured(self, client: AsyncClient):
        """Verify changed_by is set to the current user's ID."""
        order = _make_order(OrderStatus.ASSIGNED)
        added_objects: list = []

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = order
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()

        def capture_add(obj):
            added_objects.append(obj)

        mock_db.add = capture_add

        async def fake_refresh(obj):
            obj.id = uuid.uuid4()
            obj.created_at = "2026-01-01T00:00:00+00:00"

        mock_db.refresh = fake_refresh

        from app.core.database import get_db

        app.dependency_overrides[get_db] = lambda: mock_db
        resp = await client.put(
            f"/api/v1/orders/{ORDER_ID}/status",
            json={"status": "accepted"},
            headers={"Authorization": "Bearer fake"},
        )
        app.dependency_overrides.pop(get_db, None)

        assert resp.status_code == 200
        history_objs = [o for o in added_objects if isinstance(o, OrderStatusHistory)]
        assert len(history_objs) == 1
        assert history_objs[0].changed_by == ADMIN_USER_ID


# ── GET /orders/{id}/history tests ──────────────────────────────────────


class TestGetOrderHistory:
    """Test the GET /orders/{order_id}/history endpoint."""

    @pytest.mark.anyio
    async def test_returns_history_in_order(self, client: AsyncClient):
        h1 = _make_history(ORDER_ID, OrderStatus.PENDING, ADMIN_USER_ID, "Created")
        h2 = _make_history(ORDER_ID, OrderStatus.ASSIGNED, ADMIN_USER_ID, "Assigned")

        mock_db = AsyncMock()
        call_count = 0

        async def fake_execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                # Order exists check
                result.scalar_one_or_none.return_value = ORDER_ID
            else:
                # History query
                result.scalars.return_value.all.return_value = [h1, h2]
            return result

        mock_db.execute = fake_execute

        from app.core.database import get_db

        app.dependency_overrides[get_db] = lambda: mock_db
        resp = await client.get(
            f"/api/v1/orders/{ORDER_ID}/history",
            headers={"Authorization": "Bearer fake"},
        )
        app.dependency_overrides.pop(get_db, None)

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["status"] == "pending"
        assert data[1]["status"] == "assigned"

    @pytest.mark.anyio
    async def test_order_not_found_returns_404(self, client: AsyncClient):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        from app.core.database import get_db

        app.dependency_overrides[get_db] = lambda: mock_db
        resp = await client.get(
            f"/api/v1/orders/{uuid.uuid4()}/history",
            headers={"Authorization": "Bearer fake"},
        )
        app.dependency_overrides.pop(get_db, None)

        assert resp.status_code == 404
