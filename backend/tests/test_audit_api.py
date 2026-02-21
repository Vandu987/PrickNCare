"""Tests for audit log API — task 16.6."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.audit import AuditLog
from app.models.users import User, UserRole

# ── Helpers ──────────────────────────────────────────────────────────────


def _fake_user(role: UserRole = UserRole.SUPER_ADMIN) -> User:
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = f"{role.value}@test.com"
    user.phone = "+911234567890"
    user.role = role
    user.is_active = True
    return user


ADMIN = _fake_user(UserRole.SUPER_ADMIN)
CLIENT = _fake_user(UserRole.CLIENT_USER)


def _override_auth(user: User) -> None:
    from app.api.deps import get_current_active_user, get_current_user

    app.dependency_overrides[get_current_active_user] = lambda: user
    app.dependency_overrides[get_current_user] = lambda: user


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def _fake_audit_log(**kwargs) -> AuditLog:
    defaults = dict(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        action="create",
        entity_type="Order",
        entity_id=uuid.uuid4(),
        old_value=None,
        new_value={"status": "pending"},
        ip_address="127.0.0.1",
        user_agent="test",
        request_method="POST",
        request_path="/api/v1/orders",
        response_status=201,
        created_at=datetime.now(UTC),
    )
    defaults.update(kwargs)
    log = MagicMock(spec=AuditLog)
    for k, v in defaults.items():
        setattr(log, k, v)
    return log


# ── Tests ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_audit_logs_forbidden_for_non_admin():
    _override_auth(CLIENT)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get("/api/v1/audit/logs")
        assert resp.status_code == 403
    finally:
        _clear_overrides()


@pytest.mark.asyncio
async def test_list_audit_logs_success():
    _override_auth(ADMIN)
    logs = [_fake_audit_log() for _ in range(3)]

    mock_db = AsyncMock()
    # count query
    count_result = MagicMock()
    count_result.scalar.return_value = 3
    # rows query
    rows_result = MagicMock()
    rows_result.scalars.return_value.all.return_value = logs

    mock_db.execute = AsyncMock(side_effect=[count_result, rows_result])

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get("/api/v1/audit/logs?page=1&page_size=50")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3
        assert data["page"] == 1
    finally:
        _clear_overrides()


@pytest.mark.asyncio
async def test_get_audit_log_not_found():
    _override_auth(ADMIN)
    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=None)

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get(f"/api/v1/audit/logs/{uuid.uuid4()}")
        assert resp.status_code == 404
    finally:
        _clear_overrides()


@pytest.mark.asyncio
async def test_get_audit_log_success():
    _override_auth(ADMIN)
    log = _fake_audit_log()
    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=log)

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get(f"/api/v1/audit/logs/{log.id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == str(log.id)
    finally:
        _clear_overrides()


@pytest.mark.asyncio
async def test_cleanup_forbidden_for_non_admin():
    _override_auth(CLIENT)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.delete("/api/v1/audit/logs/cleanup")
        assert resp.status_code == 403
    finally:
        _clear_overrides()


@pytest.mark.asyncio
async def test_cleanup_success():
    _override_auth(ADMIN)
    mock_db = AsyncMock()
    exec_result = MagicMock()
    exec_result.rowcount = 42
    mock_db.execute = AsyncMock(return_value=exec_result)
    mock_db.commit = AsyncMock()

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.delete("/api/v1/audit/logs/cleanup?retention_days=30")
        assert resp.status_code == 200
        data = resp.json()
        assert data["deleted_count"] == 42
        assert data["retention_days"] == 30
    finally:
        _clear_overrides()


@pytest.mark.asyncio
async def test_cleanup_uses_default_retention():
    _override_auth(ADMIN)
    mock_db = AsyncMock()
    exec_result = MagicMock()
    exec_result.rowcount = 0
    mock_db.execute = AsyncMock(return_value=exec_result)
    mock_db.commit = AsyncMock()

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.delete("/api/v1/audit/logs/cleanup")
        assert resp.status_code == 200
        assert resp.json()["retention_days"] == 90
    finally:
        _clear_overrides()
