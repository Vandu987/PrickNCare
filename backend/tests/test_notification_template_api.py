"""API tests for notification template management — task 10.5."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.notifications import NotificationTemplate
from app.models.users import User, UserRole

_transport = ASGITransport(app=app)


# ── Helpers ──────────────────────────────────────────────────────────────


def _fake_user(role: UserRole = UserRole.SUPER_ADMIN) -> User:
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = f"{role.value}@test.com"
    user.phone = "+911234567890"
    user.role = role
    user.is_active = True
    return user


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


ADMIN = _fake_user(UserRole.SUPER_ADMIN)
TEMPLATE_ID = uuid.uuid4()


def _fake_template(**overrides):
    defaults = dict(
        id=TEMPLATE_ID,
        notification_type="otp",
        channel="sms",
        name="OTP SMS",
        subject=None,
        body_template="Your OTP is {otp}",
        is_active=True,
        is_deleted=False,
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
    )
    defaults.update(overrides)
    t = MagicMock(spec=NotificationTemplate)
    for k, v in defaults.items():
        setattr(t, k, v)
    return t


# ── Tests ────────────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_create_template():
    _override_auth(ADMIN)

    mock_db = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.add = MagicMock()

    from datetime import UTC, datetime

    async def _fake_refresh(obj):
        obj.id = TEMPLATE_ID
        obj.created_at = datetime.now(UTC)
        obj.updated_at = datetime.now(UTC)

    mock_db.refresh = AsyncMock(side_effect=_fake_refresh)

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db

    async with AsyncClient(transport=_transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/notifications/templates",
            json={
                "notification_type": "otp",
                "channel": "sms",
                "name": "OTP SMS",
                "body_template": "Your OTP is {otp}",
            },
        )

    assert resp.status_code == 201
    assert resp.json()["name"] == "OTP SMS"
    mock_db.add.assert_called_once()
    mock_db.commit.assert_awaited_once()
    _clear_overrides()


@pytest.mark.anyio
async def test_list_templates():
    _override_auth(ADMIN)
    tpl = _fake_template()

    mock_db = AsyncMock()
    # Mock execute to return scalars
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [tpl]
    mock_result.scalars.return_value = mock_scalars

    mock_count_result = MagicMock()
    mock_count_result.scalar.return_value = 1

    mock_db.execute = AsyncMock(side_effect=[mock_count_result, mock_result])

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db

    async with AsyncClient(transport=_transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/notifications/templates")

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    _clear_overrides()


@pytest.mark.anyio
async def test_get_template():
    _override_auth(ADMIN)
    tpl = _fake_template()

    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=tpl)

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db

    async with AsyncClient(transport=_transport, base_url="http://test") as ac:
        resp = await ac.get(f"/api/v1/notifications/templates/{TEMPLATE_ID}")

    assert resp.status_code == 200
    assert resp.json()["name"] == "OTP SMS"
    _clear_overrides()


@pytest.mark.anyio
async def test_get_template_not_found():
    _override_auth(ADMIN)

    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=None)

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db

    async with AsyncClient(transport=_transport, base_url="http://test") as ac:
        resp = await ac.get(f"/api/v1/notifications/templates/{uuid.uuid4()}")

    assert resp.status_code == 404
    _clear_overrides()


@pytest.mark.anyio
async def test_update_template():
    _override_auth(ADMIN)
    tpl = _fake_template()

    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=tpl)
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db

    async with AsyncClient(transport=_transport, base_url="http://test") as ac:
        resp = await ac.put(
            f"/api/v1/notifications/templates/{TEMPLATE_ID}",
            json={"name": "Updated OTP SMS"},
        )

    assert resp.status_code == 200
    _clear_overrides()


@pytest.mark.anyio
async def test_delete_template():
    _override_auth(ADMIN)
    tpl = _fake_template()

    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=tpl)
    mock_db.commit = AsyncMock()

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db

    async with AsyncClient(transport=_transport, base_url="http://test") as ac:
        resp = await ac.delete(f"/api/v1/notifications/templates/{TEMPLATE_ID}")

    assert resp.status_code == 204
    assert tpl.is_deleted is True
    _clear_overrides()


@pytest.mark.anyio
async def test_manual_send():
    _override_auth(ADMIN)

    mock_db = AsyncMock()

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db

    with patch("app.api.v1.notifications.NotificationService") as MockSvc:
        instance = MockSvc.return_value
        instance.send = AsyncMock(return_value=[{"channel": "sms", "success": True}])

        async with AsyncClient(transport=_transport, base_url="http://test") as ac:
            resp = await ac.post(
                "/api/v1/notifications/send",
                json={
                    "notification_type": "otp",
                    "phone": "+919999999999",
                    "data": {"otp": "1234"},
                },
            )

    assert resp.status_code == 200
    assert resp.json()["results"][0]["success"] is True
    _clear_overrides()


@pytest.mark.anyio
async def test_manual_send_missing_recipient():
    _override_auth(ADMIN)

    mock_db = AsyncMock()

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db

    async with AsyncClient(transport=_transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/notifications/send",
            json={"notification_type": "otp"},
        )

    assert resp.status_code == 400
    _clear_overrides()
