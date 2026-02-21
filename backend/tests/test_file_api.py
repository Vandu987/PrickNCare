"""API tests for file upload, download and delete — task 15.4."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.main import app
from app.models.users import User, UserRole
from app.services.file_upload import FileUploadError, FileUploadService

# ── Helpers ──────────────────────────────────────────────────────────────


def _fake_user(role: UserRole = UserRole.SUPER_ADMIN) -> User:
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = f"{role.value}@test.com"
    user.phone = "+911234567890"
    user.role = role
    user.is_active = True
    return user


ADMIN_USER = _fake_user(UserRole.SUPER_ADMIN)
CLIENT_USER = _fake_user(UserRole.CLIENT_USER)
PHLEB_USER = _fake_user(UserRole.PHLEBOTOMIST)


def _override_auth(user: User) -> None:
    from app.api.deps import get_current_active_user, get_current_user

    app.dependency_overrides[get_current_active_user] = lambda: user
    app.dependency_overrides[get_current_user] = lambda: user


def _mock_file_service(**overrides) -> FileUploadService:
    svc = MagicMock(spec=FileUploadService)
    svc.upload_file = overrides.get(
        "upload_file",
        AsyncMock(return_value="https://cdn.example.com/documents/test_abc123.pdf"),
    )
    svc.get_presigned_url = overrides.get(
        "get_presigned_url", MagicMock(return_value="https://s3.example.com/signed-url")
    )
    svc.delete_file = overrides.get("delete_file", MagicMock())
    return svc


def _override_file_service(svc: FileUploadService) -> None:
    from app.services.file_upload import get_file_upload_service

    app.dependency_overrides[get_file_upload_service] = lambda: svc


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


# ── Upload Tests ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upload_success(client):
    _override_auth(CLIENT_USER)
    svc = _mock_file_service()
    _override_file_service(svc)
    try:
        resp = await client.post(
            "/api/v1/files/upload",
            params={"folder": "documents"},
            files={"file": ("test.pdf", b"fake-pdf-content", "application/pdf")},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "url" in data
        assert "key" in data
    finally:
        _clear_overrides()


@pytest.mark.asyncio
async def test_upload_no_auth(client):
    _clear_overrides()
    resp = await client.post(
        "/api/v1/files/upload",
        params={"folder": "documents"},
        files={"file": ("test.pdf", b"fake-pdf-content", "application/pdf")},
    )
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_upload_validation_error(client):
    _override_auth(CLIENT_USER)
    svc = _mock_file_service()
    svc.upload_file = AsyncMock(side_effect=FileUploadError("Invalid folder"))
    _override_file_service(svc)
    try:
        resp = await client.post(
            "/api/v1/files/upload",
            params={"folder": "bad_folder"},
            files={"file": ("test.pdf", b"content", "application/pdf")},
        )
        assert resp.status_code == 400
        assert "Invalid folder" in resp.json()["error"]["message"]
    finally:
        _clear_overrides()


# ── Download Tests ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_download_success(client):
    _override_auth(CLIENT_USER)
    svc = _mock_file_service()
    _override_file_service(svc)
    try:
        resp = await client.get(
            "/api/v1/files/download",
            params={"key": "documents/test_abc123.pdf"},
        )
        assert resp.status_code == 200
        assert "presigned_url" in resp.json()
    finally:
        _clear_overrides()


@pytest.mark.asyncio
async def test_download_not_found(client):
    _override_auth(CLIENT_USER)
    svc = _mock_file_service()
    svc.get_presigned_url = MagicMock(
        side_effect=FileUploadError("Object not found: missing.pdf")
    )
    _override_file_service(svc)
    try:
        resp = await client.get(
            "/api/v1/files/download",
            params={"key": "missing.pdf"},
        )
        assert resp.status_code == 404
    finally:
        _clear_overrides()


@pytest.mark.asyncio
async def test_download_no_auth(client):
    _clear_overrides()
    resp = await client.get(
        "/api/v1/files/download",
        params={"key": "documents/test.pdf"},
    )
    assert resp.status_code in (401, 403)


# ── Delete Tests ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_super_admin(client):
    _override_auth(ADMIN_USER)
    svc = _mock_file_service()
    _override_file_service(svc)
    try:
        resp = await client.delete("/api/v1/files/documents/test_abc123.pdf")
        assert resp.status_code == 200
        svc.delete_file.assert_called_once_with("documents/test_abc123.pdf")
    finally:
        _clear_overrides()


@pytest.mark.asyncio
async def test_delete_forbidden_for_non_admin(client):
    _override_auth(CLIENT_USER)
    svc = _mock_file_service()
    _override_file_service(svc)
    try:
        resp = await client.delete("/api/v1/files/documents/test.pdf")
        assert resp.status_code == 403
    finally:
        _clear_overrides()


@pytest.mark.asyncio
async def test_delete_no_auth(client):
    _clear_overrides()
    resp = await client.delete("/api/v1/files/documents/test.pdf")
    assert resp.status_code in (401, 403)
