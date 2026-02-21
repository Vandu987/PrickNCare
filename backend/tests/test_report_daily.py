"""API tests for daily collection report — task 14.1."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.orders import Order, OrderStatus
from app.models.users import User, UserRole

# ── Helpers ──────────────────────────────────────────────────────────────

FAKE_PHLEB_ID = uuid.uuid4()
FAKE_PINCODE_ID = uuid.uuid4()
REPORT_DATE = date(2026, 2, 22)


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


def _mock_order(
    status: OrderStatus = OrderStatus.PENDING,
    booking_id: str = "BK-TEST0001",
    patient_name: str = "Test Patient",
    phleb_name: str | None = "Dr Phleb",
) -> MagicMock:
    order = MagicMock(spec=Order)
    order.id = uuid.uuid4()
    order.booking_id = booking_id
    order.patient_name = patient_name
    order.status = status
    order.appointment_date = REPORT_DATE
    order.created_at = datetime(2026, 2, 22, 9, 0, 0, tzinfo=UTC)
    order.pincode_id = FAKE_PINCODE_ID

    if phleb_name:
        phleb = MagicMock()
        phleb.name = phleb_name
        order.assigned_phlebotomist = phleb
    else:
        order.assigned_phlebotomist = None

    return order


def _mock_db_with_orders(orders: list) -> AsyncMock:
    db = AsyncMock()
    result = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = orders
    result.scalars.return_value = scalars
    db.execute.return_value = result
    return db


# ── Tests ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestDailyCollectionReport:
    """Tests for GET /api/v1/reports/daily-collection."""

    async def setup_method(self, method: object) -> None:
        _clear_overrides()

    async def teardown_method(self, method: object) -> None:
        _clear_overrides()

    async def test_success_with_orders(self) -> None:
        _override_auth(ADMIN_USER)
        orders = [
            _mock_order(OrderStatus.COMPLETED, "BK-001", "Alice"),
            _mock_order(OrderStatus.PENDING, "BK-002", "Bob"),
            _mock_order(OrderStatus.CANCELLED, "BK-003", "Charlie"),
            _mock_order(OrderStatus.UNCOLLECTED, "BK-004", "Dave", phleb_name=None),
        ]
        mock_db = _mock_db_with_orders(orders)

        from app.core.database import get_db

        app.dependency_overrides[get_db] = lambda: mock_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get(
                "/api/v1/reports/daily-collection",
                params={"date": str(REPORT_DATE)},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_orders"] == 4
        assert data["completed"] == 1
        assert data["pending"] == 1
        assert data["cancelled"] == 1
        assert data["uncollected"] == 1
        assert len(data["orders"]) == 4

    async def test_empty_report(self) -> None:
        _override_auth(ADMIN_USER)
        mock_db = _mock_db_with_orders([])

        from app.core.database import get_db

        app.dependency_overrides[get_db] = lambda: mock_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get(
                "/api/v1/reports/daily-collection",
                params={"date": str(REPORT_DATE)},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_orders"] == 0
        assert data["orders"] == []

    async def test_city_admin_allowed(self) -> None:
        _override_auth(CITY_ADMIN_USER)
        mock_db = _mock_db_with_orders([])

        from app.core.database import get_db

        app.dependency_overrides[get_db] = lambda: mock_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get(
                "/api/v1/reports/daily-collection",
                params={"date": str(REPORT_DATE)},
            )

        assert resp.status_code == 200

    async def test_client_user_forbidden(self) -> None:
        _override_auth(CLIENT_USER)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get(
                "/api/v1/reports/daily-collection",
                params={"date": str(REPORT_DATE)},
            )

        assert resp.status_code == 403

    async def test_phlebotomist_forbidden(self) -> None:
        _override_auth(PHLEB_USER)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get(
                "/api/v1/reports/daily-collection",
                params={"date": str(REPORT_DATE)},
            )

        assert resp.status_code == 403

    async def test_missing_date_param(self) -> None:
        _override_auth(ADMIN_USER)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get("/api/v1/reports/daily-collection")

        assert resp.status_code == 422

    async def test_with_city_id_filter(self) -> None:
        _override_auth(ADMIN_USER)
        mock_db = _mock_db_with_orders([])

        from app.core.database import get_db

        app.dependency_overrides[get_db] = lambda: mock_db

        city_id = uuid.uuid4()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get(
                "/api/v1/reports/daily-collection",
                params={"date": str(REPORT_DATE), "city_id": str(city_id)},
            )

        assert resp.status_code == 200

    async def test_with_zone_id_filter(self) -> None:
        _override_auth(ADMIN_USER)
        mock_db = _mock_db_with_orders([])

        from app.core.database import get_db

        app.dependency_overrides[get_db] = lambda: mock_db

        zone_id = uuid.uuid4()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get(
                "/api/v1/reports/daily-collection",
                params={"date": str(REPORT_DATE), "zone_id": str(zone_id)},
            )

        assert resp.status_code == 200
