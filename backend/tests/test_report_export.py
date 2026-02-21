"""API tests for report export and dashboard analytics — task 14.5."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.orders import Order, OrderStatus, PaymentStatus
from app.models.users import User, UserRole

# ── Helpers ──────────────────────────────────────────────────────────────

FAKE_PHLEB_ID = uuid.uuid4()
FAKE_CLIENT_ID = uuid.uuid4()


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


def _fake_order(**kwargs) -> MagicMock:
    o = MagicMock(spec=Order)
    o.id = kwargs.get("id", uuid.uuid4())
    o.booking_id = kwargs.get("booking_id", "BK-001")
    o.patient_name = kwargs.get("patient_name", "Test Patient")
    o.status = kwargs.get("status", OrderStatus.PENDING)
    o.appointment_date = kwargs.get("appointment_date", date(2026, 2, 22))
    o.amount = kwargs.get("amount", Decimal("500.00"))
    o.created_at = kwargs.get("created_at", datetime(2026, 2, 22, 10, 0, tzinfo=UTC))
    o.client_id = kwargs.get("client_id", FAKE_CLIENT_ID)
    o.payment_status = kwargs.get("payment_status", PaymentStatus.PENDING)
    o.assigned_phlebotomist_id = kwargs.get("assigned_phlebotomist_id", None)
    o.pincode_id = kwargs.get("pincode_id", uuid.uuid4())
    o.assigned_at = kwargs.get("assigned_at", None)
    o.collected_at = kwargs.get("collected_at", None)
    o.client = kwargs.get("client", None)
    return o


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ── Export endpoint tests ────────────────────────────────────────────────


@pytest.mark.anyio
async def test_export_csv_requires_auth(client: AsyncClient):
    """Export endpoint should reject unauthenticated requests."""
    resp = await client.get(
        "/api/v1/reports/export",
        params={
            "report_type": "daily-collection",
            "date_from": "2026-02-01",
            "date_to": "2026-02-28",
            "format": "csv",
        },
    )
    assert resp.status_code in (401, 403)


@pytest.mark.anyio
async def test_export_csv_forbidden_for_phleb(client: AsyncClient):
    """Phlebotomist role should be rejected."""
    with patch("app.api.deps.get_current_user", return_value=PHLEB_USER):
        resp = await client.get(
            "/api/v1/reports/export",
            params={
                "report_type": "daily-collection",
                "date_from": "2026-02-01",
                "date_to": "2026-02-28",
                "format": "csv",
            },
        )
    assert resp.status_code in (401, 403)


@pytest.mark.anyio
async def test_export_csv_daily_collection(client: AsyncClient):
    """Super admin can export daily-collection as CSV."""
    orders = [
        _fake_order(booking_id="BK-001", status=OrderStatus.COMPLETED),
        _fake_order(booking_id="BK-002", status=OrderStatus.PENDING),
    ]

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = orders

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    with (
        patch("app.api.deps.get_current_user", return_value=ADMIN_USER),
        patch("app.core.database.get_db", return_value=mock_db),
        patch(
            "app.api.v1.reports.get_db",
            return_value=mock_db,
        ),
    ):
        resp = await client.get(
            "/api/v1/reports/export",
            params={
                "report_type": "daily-collection",
                "date_from": "2026-02-01",
                "date_to": "2026-02-28",
                "format": "csv",
            },
        )

    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")
    assert "attachment" in resp.headers.get("content-disposition", "")
    # Check CSV content has header + rows
    lines = resp.text.strip().split("\n")
    assert len(lines) >= 1  # at least header


@pytest.mark.anyio
async def test_export_invalid_report_type(client: AsyncClient):
    """Invalid report type should return 422."""
    with patch("app.api.deps.get_current_user", return_value=ADMIN_USER):
        resp = await client.get(
            "/api/v1/reports/export",
            params={
                "report_type": "nonexistent",
                "date_from": "2026-02-01",
                "date_to": "2026-02-28",
                "format": "csv",
            },
        )
    assert resp.status_code == 422


# ── Dashboard endpoint tests ────────────────────────────────────────────


@pytest.mark.anyio
async def test_dashboard_requires_auth(client: AsyncClient):
    """Dashboard endpoint should reject unauthenticated requests."""
    resp = await client.get("/api/v1/reports/dashboard")
    assert resp.status_code in (401, 403)


@pytest.mark.anyio
async def test_dashboard_forbidden_for_client_user(client: AsyncClient):
    """Client user role should be rejected."""
    with patch("app.api.deps.get_current_user", return_value=CLIENT_USER):
        resp = await client.get("/api/v1/reports/dashboard")
    assert resp.status_code in (401, 403)


@pytest.mark.anyio
async def test_dashboard_success(client: AsyncClient):
    """Super admin can access the dashboard analytics."""
    # Mock all DB calls - dashboard makes 7 execute calls
    recent_orders = [
        _fake_order(booking_id="BK-100", status=OrderStatus.COMPLETED),
    ]

    call_count = 0

    async def mock_execute(stmt):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        # The first 6 calls are scalar queries (counts/sums)
        if call_count <= 6:
            if call_count == 1:
                result.scalar.return_value = 10  # today total
            elif call_count == 2:
                result.scalar.return_value = 5  # today completed
            elif call_count == 3:
                result.scalar.return_value = 3  # today pending
            elif call_count == 4:
                result.scalar.return_value = Decimal("25000.00")  # week revenue
            elif call_count == 5:
                result.scalar.return_value = 8  # active phlebotomists
            elif call_count == 6:
                result.scalar.return_value = 2  # pending reconciliations
        else:
            # 7th call: recent orders
            result.scalars.return_value.all.return_value = recent_orders
        return result

    mock_db = AsyncMock()
    mock_db.execute = mock_execute

    with (
        patch("app.api.deps.get_current_user", return_value=ADMIN_USER),
        patch("app.api.v1.reports.get_db", return_value=mock_db),
    ):
        resp = await client.get("/api/v1/reports/dashboard")

    assert resp.status_code == 200
    data = resp.json()
    assert data["today_total_orders"] == 10
    assert data["today_completed_orders"] == 5
    assert data["today_pending_orders"] == 3
    assert data["this_week_revenue"] == 25000.0
    assert data["active_phlebotomists"] == 8
    assert data["pending_reconciliations"] == 2
    assert len(data["recent_orders"]) == 1
    assert data["recent_orders"][0]["booking_id"] == "BK-100"


@pytest.mark.anyio
async def test_dashboard_city_admin_access(client: AsyncClient):
    """City admin can also access the dashboard."""

    async def mock_execute(stmt):
        result = MagicMock()
        result.scalar.return_value = 0
        result.scalars.return_value.all.return_value = []
        return result

    mock_db = AsyncMock()
    mock_db.execute = mock_execute

    with (
        patch("app.api.deps.get_current_user", return_value=CITY_ADMIN_USER),
        patch("app.api.v1.reports.get_db", return_value=mock_db),
    ):
        resp = await client.get("/api/v1/reports/dashboard")

    assert resp.status_code == 200
    data = resp.json()
    assert data["today_total_orders"] == 0
