"""API tests for revenue report and TAT analysis — task 14.4."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.orders import Order, OrderPriority, OrderStatus
from app.models.users import User, UserRole

# ── Helpers ──────────────────────────────────────────────────────────────

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
CLIENT_USER = _fake_user(UserRole.CLIENT_USER)
PHLEB_USER = _fake_user(UserRole.PHLEBOTOMIST)


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


# ── Revenue Report Tests ────────────────────────────────────────────────


@pytest.mark.asyncio
class TestRevenueReport:
    """Tests for GET /api/v1/reports/revenue."""

    async def setup_method(self, method: object) -> None:
        _clear_overrides()

    async def teardown_method(self, method: object) -> None:
        _clear_overrides()

    async def test_success_daily_grouping(self) -> None:
        _override_auth(ADMIN_USER)

        db = AsyncMock()
        # Simulate aggregated rows: (period, total_revenue, order_count)
        row1 = (date(2026, 2, 20), 5000.0, 10)
        row2 = (date(2026, 2, 21), 3000.0, 6)
        result = MagicMock()
        result.all.return_value = [row1, row2]
        db.execute.return_value = result

        from app.core.database import get_db

        app.dependency_overrides[get_db] = lambda: db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get(
                "/api/v1/reports/revenue",
                params={
                    "date_from": "2026-02-20",
                    "date_to": "2026-02-21",
                    "group_by": "day",
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["group_by"] == "day"
        assert len(data["data"]) == 2
        assert data["data"][0]["total_revenue"] == 5000.0
        assert data["data"][0]["order_count"] == 10
        assert data["data"][0]["avg_order_value"] == 500.0

    async def test_empty_revenue(self) -> None:
        _override_auth(ADMIN_USER)

        db = AsyncMock()
        result = MagicMock()
        result.all.return_value = []
        db.execute.return_value = result

        from app.core.database import get_db

        app.dependency_overrides[get_db] = lambda: db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get(
                "/api/v1/reports/revenue",
                params={"date_from": "2026-02-20", "date_to": "2026-02-21"},
            )

        assert resp.status_code == 200
        assert resp.json()["data"] == []

    async def test_city_admin_allowed(self) -> None:
        _override_auth(CITY_ADMIN_USER)

        db = AsyncMock()
        result = MagicMock()
        result.all.return_value = []
        db.execute.return_value = result

        from app.core.database import get_db

        app.dependency_overrides[get_db] = lambda: db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get(
                "/api/v1/reports/revenue",
                params={"date_from": "2026-02-20", "date_to": "2026-02-21"},
            )

        assert resp.status_code == 200

    async def test_client_user_forbidden(self) -> None:
        _override_auth(CLIENT_USER)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get(
                "/api/v1/reports/revenue",
                params={"date_from": "2026-02-20", "date_to": "2026-02-21"},
            )

        assert resp.status_code == 403

    async def test_phlebotomist_forbidden(self) -> None:
        _override_auth(PHLEB_USER)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get(
                "/api/v1/reports/revenue",
                params={"date_from": "2026-02-20", "date_to": "2026-02-21"},
            )

        assert resp.status_code == 403

    async def test_missing_params(self) -> None:
        _override_auth(ADMIN_USER)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get("/api/v1/reports/revenue")

        assert resp.status_code == 422

    async def test_weekly_grouping(self) -> None:
        _override_auth(ADMIN_USER)

        db = AsyncMock()
        row = (date(2026, 2, 16), 10000.0, 20)
        result = MagicMock()
        result.all.return_value = [row]
        db.execute.return_value = result

        from app.core.database import get_db

        app.dependency_overrides[get_db] = lambda: db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get(
                "/api/v1/reports/revenue",
                params={
                    "date_from": "2026-02-16",
                    "date_to": "2026-02-22",
                    "group_by": "week",
                },
            )

        assert resp.status_code == 200
        assert resp.json()["group_by"] == "week"
        assert len(resp.json()["data"]) == 1


# ── TAT Analysis Tests ──────────────────────────────────────────────────


def _mock_order_for_tat(
    priority: OrderPriority = OrderPriority.NORMAL,
    assigned_at: datetime | None = None,
    collected_at: datetime | None = None,
    order_id: uuid.UUID | None = None,
) -> MagicMock:
    o = MagicMock(spec=Order)
    o.id = order_id or uuid.uuid4()
    o.priority = priority
    o.assigned_at = assigned_at or datetime(2026, 2, 22, 8, 0, 0, tzinfo=UTC)
    o.collected_at = collected_at or datetime(2026, 2, 22, 9, 0, 0, tzinfo=UTC)
    o.appointment_date = date(2026, 2, 22)
    o.pincode_id = FAKE_PINCODE_ID
    o.status = OrderStatus.COMPLETED
    return o


@pytest.mark.asyncio
class TestTATAnalysis:
    """Tests for GET /api/v1/reports/tat-analysis."""

    async def setup_method(self, method: object) -> None:
        _clear_overrides()

    async def teardown_method(self, method: object) -> None:
        _clear_overrides()

    async def test_success_with_orders(self) -> None:
        _override_auth(ADMIN_USER)

        oid1 = uuid.uuid4()
        oid2 = uuid.uuid4()
        orders = [
            _mock_order_for_tat(
                OrderPriority.NORMAL,
                datetime(2026, 2, 22, 8, 0, 0, tzinfo=UTC),
                datetime(2026, 2, 22, 9, 0, 0, tzinfo=UTC),
                oid1,
            ),
            _mock_order_for_tat(
                OrderPriority.HIGH,
                datetime(2026, 2, 22, 8, 0, 0, tzinfo=UTC),
                datetime(2026, 2, 22, 8, 30, 0, tzinfo=UTC),
                oid2,
            ),
        ]

        db = AsyncMock()
        call_count = 0

        async def _mock_execute(stmt, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                # Orders query
                scalars = MagicMock()
                scalars.all.return_value = orders
                result.scalars.return_value = scalars
            else:
                # Accessioning query — return accessioning times
                acc_row1 = (oid1, datetime(2026, 2, 22, 10, 0, 0, tzinfo=UTC))
                acc_row2 = (oid2, datetime(2026, 2, 22, 9, 30, 0, tzinfo=UTC))
                result.all.return_value = [acc_row1, acc_row2]
            return result

        db.execute = _mock_execute

        from app.core.database import get_db

        app.dependency_overrides[get_db] = lambda: db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get(
                "/api/v1/reports/tat-analysis",
                params={"date_from": "2026-02-22", "date_to": "2026-02-22"},
            )

        assert resp.status_code == 200
        data = resp.json()
        # avg a2c: (60 + 30) / 2 = 45
        assert data["avg_assignment_to_collection_minutes"] == 45.0
        assert data["avg_collection_to_accessioning_minutes"] is not None
        assert data["percentile_95_assignment_to_collection_minutes"] is not None
        assert len(data["by_priority"]) == 2

    async def test_empty_tat(self) -> None:
        _override_auth(ADMIN_USER)

        db = AsyncMock()
        result = MagicMock()
        scalars = MagicMock()
        scalars.all.return_value = []
        result.scalars.return_value = scalars
        db.execute.return_value = result

        from app.core.database import get_db

        app.dependency_overrides[get_db] = lambda: db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get(
                "/api/v1/reports/tat-analysis",
                params={"date_from": "2026-02-22", "date_to": "2026-02-22"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["by_priority"] == []
        assert data["avg_assignment_to_collection_minutes"] is None

    async def test_client_user_forbidden(self) -> None:
        _override_auth(CLIENT_USER)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get(
                "/api/v1/reports/tat-analysis",
                params={"date_from": "2026-02-22", "date_to": "2026-02-22"},
            )

        assert resp.status_code == 403

    async def test_phlebotomist_forbidden(self) -> None:
        _override_auth(PHLEB_USER)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get(
                "/api/v1/reports/tat-analysis",
                params={"date_from": "2026-02-22", "date_to": "2026-02-22"},
            )

        assert resp.status_code == 403

    async def test_missing_params(self) -> None:
        _override_auth(ADMIN_USER)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get("/api/v1/reports/tat-analysis")

        assert resp.status_code == 422

    async def test_city_admin_allowed(self) -> None:
        _override_auth(CITY_ADMIN_USER)

        db = AsyncMock()
        result = MagicMock()
        scalars = MagicMock()
        scalars.all.return_value = []
        result.scalars.return_value = scalars
        db.execute.return_value = result

        from app.core.database import get_db

        app.dependency_overrides[get_db] = lambda: db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get(
                "/api/v1/reports/tat-analysis",
                params={"date_from": "2026-02-22", "date_to": "2026-02-22"},
            )

        assert resp.status_code == 200
