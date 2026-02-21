"""Tests for payment and reconciliation report endpoints — task 9.6."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from app.main import app
from app.models.users import User, UserRole

# ── Helpers ──────────────────────────────────────────────────────────


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
PHLEB_USER = _fake_user(UserRole.PHLEBOTOMIST)


def _override_auth(user: User) -> None:
    from app.api.deps import get_current_active_user, get_current_user

    async def _fake_active() -> User:
        return user

    async def _fake_current() -> User:
        return user

    app.dependency_overrides[get_current_active_user] = _fake_active
    app.dependency_overrides[get_current_user] = _fake_current


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    app.dependency_overrides.clear()


# ── Payment report tests ────────────────────────────────────────────


@pytest.mark.anyio
async def test_payment_report_success(client: AsyncClient):
    """Admin can fetch payment report."""
    _override_auth(ADMIN_USER)

    # Mock db to return aggregated data
    mock_db = AsyncMock()

    # aggregate row
    agg_row = MagicMock()
    agg_row.total_amount = 5000.0
    agg_row.count = 10

    # mode rows
    mode_row = MagicMock()
    mode_row.mode = MagicMock()
    mode_row.mode.value = "cash"
    mode_row.total = 3000.0

    # status rows
    status_row = MagicMock()
    status_row.status = MagicMock()
    status_row.status.value = "collected"
    status_row.total = 5000.0

    exec_results = [
        MagicMock(one=MagicMock(return_value=agg_row)),
        MagicMock(all=MagicMock(return_value=[mode_row])),
        MagicMock(all=MagicMock(return_value=[status_row])),
    ]
    mock_db.execute = AsyncMock(side_effect=exec_results)

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db

    resp = await client.get(
        "/api/v1/payments/report",
        params={
            "date_from": "2026-01-01T00:00:00Z",
            "date_to": "2026-01-31T23:59:59Z",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_amount"] == 5000.0
    assert data["count"] == 10
    assert data["breakdown_by_mode"]["cash"] == 3000.0
    assert data["breakdown_by_status"]["collected"] == 5000.0


@pytest.mark.anyio
async def test_payment_report_forbidden_for_phlebotomist(client: AsyncClient):
    """Phlebotomist cannot access payment report."""
    _override_auth(PHLEB_USER)

    resp = await client.get(
        "/api/v1/payments/report",
        params={
            "date_from": "2026-01-01T00:00:00Z",
            "date_to": "2026-01-31T23:59:59Z",
        },
    )
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_payment_report_missing_params(client: AsyncClient):
    """Missing required params returns 422."""
    _override_auth(ADMIN_USER)
    resp = await client.get("/api/v1/payments/report")
    assert resp.status_code == 422


# ── Reconciliation report tests ─────────────────────────────────────


@pytest.mark.anyio
async def test_reconciliation_report_success(client: AsyncClient):
    """Admin can fetch reconciliation report."""
    _override_auth(ADMIN_USER)

    mock_db = AsyncMock()

    # rec aggregate
    rec_row = MagicMock()
    rec_row.total_cash_collected = 10000.0
    rec_row.total_handed_over = 9500.0
    rec_row.total_count = 5
    rec_row.pending_count = 1

    # discrepancy rows
    disc_row = MagicMock()
    disc_row.type = MagicMock()
    disc_row.type.value = "cash_shortage"
    disc_row.total = 500.0

    # online total
    online_scalar = MagicMock(scalar_one=MagicMock(return_value=2000.0))

    # outstanding
    outstanding_scalar = MagicMock(scalar_one=MagicMock(return_value=300.0))

    exec_results = [
        MagicMock(one=MagicMock(return_value=rec_row)),
        MagicMock(all=MagicMock(return_value=[disc_row])),
        online_scalar,
        outstanding_scalar,
    ]
    mock_db.execute = AsyncMock(side_effect=exec_results)

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db

    resp = await client.get(
        "/api/v1/reconciliation/report",
        params={"date_from": "2026-01-01", "date_to": "2026-01-31"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_cash_collected"] == 10000.0
    assert data["total_handed_over"] == 9500.0
    assert data["discrepancies_by_type"]["cash_shortage"] == 500.0
    assert data["outstanding_dues"] == 300.0
    assert data["total_online_collected"] == 2000.0
    assert data["reconciliation_count"] == 5
    assert data["pending_count"] == 1


@pytest.mark.anyio
async def test_reconciliation_report_forbidden_for_phlebotomist(client: AsyncClient):
    """Phlebotomist cannot access reconciliation report."""
    _override_auth(PHLEB_USER)

    resp = await client.get(
        "/api/v1/reconciliation/report",
        params={"date_from": "2026-01-01", "date_to": "2026-01-31"},
    )
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_reconciliation_report_missing_params(client: AsyncClient):
    """Missing required params returns 422."""
    _override_auth(ADMIN_USER)
    resp = await client.get("/api/v1/reconciliation/report")
    assert resp.status_code == 422
