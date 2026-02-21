"""API tests for reconciliation creation — task 9.3."""

from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.phlebotomists import Phlebotomist
from app.models.reconciliation import (
    DiscrepancyCategory,
    Reconciliation,
    ReconciliationDiscrepancy,
    ReconciliationStatus,
)
from app.models.users import User, UserRole

_transport = ASGITransport(app=app)

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
PHLEB_USER = _fake_user(UserRole.PHLEBOTOMIST)
PHLEB_ID = uuid.uuid4()
PHLEB_USER_ID = uuid.uuid4()


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


def _make_phleb() -> MagicMock:
    phleb = MagicMock(spec=Phlebotomist)
    phleb.id = PHLEB_ID
    phleb.user_id = PHLEB_USER_ID
    phleb.name = "Test Phleb"
    return phleb


def _make_reconciliation(
    rec_id: uuid.UUID | None = None,
    expected_cash: float = 1500.0,
    cash_handed_over: float = 1400.0,
    net_discrepancy: float = 0.0,
) -> MagicMock:
    rec = MagicMock(spec=Reconciliation)
    rec.id = rec_id or uuid.uuid4()
    rec.phlebotomist_id = PHLEB_ID
    rec.date = "2026-02-22"
    rec.expected_cash = expected_cash
    rec.cash_handed_over = cash_handed_over
    rec.net_discrepancy = net_discrepancy
    rec.status = ReconciliationStatus.CONFIRMED
    rec.created_by = ADMIN_USER.id
    rec.created_at = "2026-02-22T02:13:00+05:30"
    rec.updated_at = "2026-02-22T02:13:00+05:30"
    rec.discrepancies = []
    return rec


# ── POST /reconciliation tests ──────────────────────────────────────────


@pytest.mark.anyio
async def test_create_reconciliation_success():
    """Super admin can create a reconciliation."""
    _override_auth(ADMIN_USER)
    try:
        phleb = _make_phleb()
        rec_id = uuid.uuid4()

        mock_db = AsyncMock()

        # db.get(Phlebotomist, ...) -> phleb
        mock_db.get = AsyncMock(return_value=phleb)

        call_count = 0

        async def _execute_side_effect(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                # Check duplicate - none found
                result.scalar_one_or_none = MagicMock(return_value=None)
            elif call_count == 2:
                # Sum of cash payments
                result.scalar_one = MagicMock(return_value=Decimal("1500.00"))
            elif call_count == 3:
                # Fetch payments to mark as reconciled
                scalars_mock = MagicMock()
                scalars_mock.all.return_value = []
                result.scalars = MagicMock(return_value=scalars_mock)
            elif call_count == 4:
                # Reload reconciliation with discrepancies
                rec = _make_reconciliation(
                    rec_id=rec_id,
                    expected_cash=1500.0,
                    cash_handed_over=1400.0,
                    net_discrepancy=0.0,
                )
                disc = MagicMock(spec=ReconciliationDiscrepancy)
                disc.id = uuid.uuid4()
                disc.type = DiscrepancyCategory.FUEL_ALLOWANCE
                disc.amount = 100.0
                disc.notes = "Daily fuel"
                rec.discrepancies = [disc]
                result.scalar_one = MagicMock(return_value=rec)
            return result

        mock_db.execute = AsyncMock(side_effect=_execute_side_effect)
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()

        from app.core.database import get_db

        app.dependency_overrides[get_db] = lambda: mock_db

        async with AsyncClient(transport=_transport, base_url="http://test") as ac:
            resp = await ac.post(
                "/api/v1/reconciliation",
                json={
                    "phlebotomist_id": str(PHLEB_ID),
                    "date": "2026-02-22",
                    "cash_handed_over": 1400.0,
                    "discrepancies": [
                        {
                            "type": "fuel_allowance",
                            "amount": 100.0,
                            "notes": "Daily fuel",
                        }
                    ],
                },
            )

        assert resp.status_code == 201
        data = resp.json()
        assert data["expected_cash"] == 1500.0
        assert data["cash_handed_over"] == 1400.0
        assert len(data["discrepancies"]) == 1
        assert data["discrepancies"][0]["type"] == "fuel_allowance"
    finally:
        _clear_overrides()


@pytest.mark.anyio
async def test_create_reconciliation_phlebotomist_not_found():
    """Returns 404 if phlebotomist doesn't exist."""
    _override_auth(ADMIN_USER)
    try:
        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=None)

        from app.core.database import get_db

        app.dependency_overrides[get_db] = lambda: mock_db

        async with AsyncClient(transport=_transport, base_url="http://test") as ac:
            resp = await ac.post(
                "/api/v1/reconciliation",
                json={
                    "phlebotomist_id": str(uuid.uuid4()),
                    "date": "2026-02-22",
                    "cash_handed_over": 1400.0,
                },
            )

        assert resp.status_code == 404
    finally:
        _clear_overrides()


@pytest.mark.anyio
async def test_create_reconciliation_duplicate():
    """Returns 409 if reconciliation already exists for phlebotomist+date."""
    _override_auth(ADMIN_USER)
    try:
        phleb = _make_phleb()
        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=phleb)

        existing = _make_reconciliation()

        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=existing)
        mock_db.execute = AsyncMock(return_value=result)

        from app.core.database import get_db

        app.dependency_overrides[get_db] = lambda: mock_db

        async with AsyncClient(transport=_transport, base_url="http://test") as ac:
            resp = await ac.post(
                "/api/v1/reconciliation",
                json={
                    "phlebotomist_id": str(PHLEB_ID),
                    "date": "2026-02-22",
                    "cash_handed_over": 1400.0,
                },
            )

        assert resp.status_code == 409
    finally:
        _clear_overrides()


@pytest.mark.anyio
async def test_create_reconciliation_forbidden_for_phlebotomist():
    """Phlebotomist role should be denied."""
    _override_auth(PHLEB_USER)
    try:
        async with AsyncClient(transport=_transport, base_url="http://test") as ac:
            resp = await ac.post(
                "/api/v1/reconciliation",
                json={
                    "phlebotomist_id": str(PHLEB_ID),
                    "date": "2026-02-22",
                    "cash_handed_over": 1400.0,
                },
            )

        assert resp.status_code == 403
    finally:
        _clear_overrides()


# ── GET /reconciliation/{id} tests ──────────────────────────────────────


@pytest.mark.anyio
async def test_get_reconciliation_success():
    """Super admin can fetch a reconciliation by ID."""
    _override_auth(ADMIN_USER)
    try:
        rec_id = uuid.uuid4()
        rec = _make_reconciliation(rec_id=rec_id)

        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=rec)
        mock_db.execute = AsyncMock(return_value=result)

        from app.core.database import get_db

        app.dependency_overrides[get_db] = lambda: mock_db

        async with AsyncClient(transport=_transport, base_url="http://test") as ac:
            resp = await ac.get(f"/api/v1/reconciliation/{rec_id}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(rec_id)
    finally:
        _clear_overrides()


@pytest.mark.anyio
async def test_get_reconciliation_not_found():
    """Returns 404 for non-existent reconciliation."""
    _override_auth(ADMIN_USER)
    try:
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=result)

        from app.core.database import get_db

        app.dependency_overrides[get_db] = lambda: mock_db

        async with AsyncClient(transport=_transport, base_url="http://test") as ac:
            resp = await ac.get(f"/api/v1/reconciliation/{uuid.uuid4()}")

        assert resp.status_code == 404
    finally:
        _clear_overrides()


# ── PUT /reconciliation/{id} tests ──────────────────────────────────────


@pytest.mark.anyio
async def test_update_reconciliation_status():
    """Super admin can update reconciliation status."""
    _override_auth(ADMIN_USER)
    try:
        rec_id = uuid.uuid4()
        rec = _make_reconciliation(rec_id=rec_id)
        # Make status mutable
        rec.status = ReconciliationStatus.CONFIRMED

        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=rec)
        mock_db.execute = AsyncMock(return_value=result)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        from app.core.database import get_db

        app.dependency_overrides[get_db] = lambda: mock_db

        async with AsyncClient(transport=_transport, base_url="http://test") as ac:
            resp = await ac.put(
                f"/api/v1/reconciliation/{rec_id}",
                json={"status": "disputed"},
            )

        assert resp.status_code == 200
    finally:
        _clear_overrides()


@pytest.mark.anyio
async def test_update_reconciliation_not_found():
    """Returns 404 for non-existent reconciliation."""
    _override_auth(ADMIN_USER)
    try:
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=result)

        from app.core.database import get_db

        app.dependency_overrides[get_db] = lambda: mock_db

        async with AsyncClient(transport=_transport, base_url="http://test") as ac:
            resp = await ac.put(
                f"/api/v1/reconciliation/{uuid.uuid4()}",
                json={"status": "disputed"},
            )

        assert resp.status_code == 404
    finally:
        _clear_overrides()
