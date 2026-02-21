"""API tests for pending reconciliation — task 9.2."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.phlebotomists import Phlebotomist
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
CITY_ADMIN = _fake_user(UserRole.CITY_ADMIN)
PHLEB_USER = _fake_user(UserRole.PHLEBOTOMIST)
CLIENT_USER = _fake_user(UserRole.CLIENT_USER)

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


# Build mock DB result rows for the aggregation query
def _make_agg_row(
    collected_by: uuid.UUID,
    total_appointments: int = 3,
    cash_collected: float = 1500.0,
    online_collected: float = 500.0,
    total_collected: float = 2000.0,
) -> MagicMock:
    row = MagicMock()
    row.collected_by = collected_by
    row.total_appointments = total_appointments
    row.cash_collected = cash_collected
    row.online_collected = online_collected
    row.total_collected = total_collected
    return row


def _make_phleb(phleb_id: uuid.UUID, user_id: uuid.UUID, name: str) -> MagicMock:
    phleb = MagicMock(spec=Phlebotomist)
    phleb.id = phleb_id
    phleb.user_id = user_id
    phleb.name = name
    return phleb


# ── Tests ────────────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_pending_reconciliation_success():
    """Super admin can fetch pending reconciliation summary."""
    _override_auth(ADMIN_USER)
    try:
        agg_row = _make_agg_row(PHLEB_USER_ID)
        phleb = _make_phleb(PHLEB_ID, PHLEB_USER_ID, "Test Phleb")
        user_mock = _fake_user(UserRole.PHLEBOTOMIST, PHLEB_USER_ID)

        # Mock db.execute to return agg rows then phleb rows
        mock_db = AsyncMock()
        call_count = 0

        async def _execute_side_effect(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.all.return_value = [agg_row]
            else:
                result.all.return_value = [(phleb, user_mock)]
            return result

        mock_db.execute = AsyncMock(side_effect=_execute_side_effect)

        with patch("app.api.v1.reconciliation.get_db", return_value=mock_db):
            app.dependency_overrides[
                __import__("app.core.database", fromlist=["get_db"]).get_db
            ] = lambda: mock_db

            async with AsyncClient(transport=_transport, base_url="http://test") as ac:
                resp = await ac.get(
                    "/api/v1/reconciliation/pending",
                    params={"date": "2026-02-22"},
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["date"] == "2026-02-22"
        assert len(data["items"]) == 1
        item = data["items"][0]
        assert item["name"] == "Test Phleb"
        assert item["cash_collected"] == 1500.0
        assert item["online_collected"] == 500.0
        assert item["total_collected"] == 2000.0
        assert item["total_appointments"] == 3
    finally:
        _clear_overrides()


@pytest.mark.anyio
async def test_pending_reconciliation_empty():
    """Returns empty items when no payments found."""
    _override_auth(ADMIN_USER)
    try:
        mock_db = AsyncMock()
        result = MagicMock()
        result.all.return_value = []
        mock_db.execute = AsyncMock(return_value=result)

        from app.core.database import get_db

        app.dependency_overrides[get_db] = lambda: mock_db

        async with AsyncClient(transport=_transport, base_url="http://test") as ac:
            resp = await ac.get("/api/v1/reconciliation/pending")

        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
    finally:
        _clear_overrides()


@pytest.mark.anyio
async def test_pending_reconciliation_city_admin_allowed():
    """City admin role is also allowed."""
    _override_auth(CITY_ADMIN)
    try:
        mock_db = AsyncMock()
        result = MagicMock()
        result.all.return_value = []
        mock_db.execute = AsyncMock(return_value=result)

        from app.core.database import get_db

        app.dependency_overrides[get_db] = lambda: mock_db

        async with AsyncClient(transport=_transport, base_url="http://test") as ac:
            resp = await ac.get("/api/v1/reconciliation/pending")

        assert resp.status_code == 200
    finally:
        _clear_overrides()


@pytest.mark.anyio
async def test_pending_reconciliation_phlebotomist_forbidden():
    """Phlebotomist role should be denied."""
    _override_auth(PHLEB_USER)
    try:
        async with AsyncClient(transport=_transport, base_url="http://test") as ac:
            resp = await ac.get("/api/v1/reconciliation/pending")

        assert resp.status_code == 403
    finally:
        _clear_overrides()


@pytest.mark.anyio
async def test_pending_reconciliation_client_forbidden():
    """Client user role should be denied."""
    _override_auth(CLIENT_USER)
    try:
        async with AsyncClient(transport=_transport, base_url="http://test") as ac:
            resp = await ac.get("/api/v1/reconciliation/pending")

        assert resp.status_code == 403
    finally:
        _clear_overrides()
