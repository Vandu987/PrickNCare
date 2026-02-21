"""Tests for pricing calculation API endpoint — task 7.4."""

from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_active_user, get_current_user
from app.core.database import get_db
from app.main import app
from app.models.users import UserRole

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

URL = "/api/v1/pricing/calculate"


def _fake_user(role=UserRole.CLIENT_USER):
    user = MagicMock()
    user.id = uuid.uuid4()
    user.role = role
    user.is_active = True
    return user


def _make_client(client_id=None, is_active=True):
    obj = MagicMock()
    obj.id = client_id or uuid.uuid4()
    obj.name = "Test Client"
    obj.is_active = is_active
    obj.rate_first_collection = Decimal("150.00")
    obj.rate_second_collection = Decimal("100.00")
    obj.rate_priority = Decimal("50.00")
    return obj


def _make_package(pkg_id=None, is_active=True):
    obj = MagicMock()
    obj.id = pkg_id or uuid.uuid4()
    obj.name = "CBC"
    obj.code = "CBC001"
    obj.is_active = is_active
    return obj


def _override_auth(user):
    async def _fake():
        return user

    app.dependency_overrides[get_current_user] = _fake
    app.dependency_overrides[get_current_active_user] = _fake


def _mock_db(client_obj, packages):
    call_count = 0

    async def _execute(stmt):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count in (1, 3):
            # Client query (endpoint + engine)
            result.scalar_one_or_none.return_value = client_obj
        else:
            # Package query (endpoint + engine)
            scalars_mock = MagicMock()
            scalars_mock.all.return_value = packages
            result.scalars.return_value = scalars_mock
        return result

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=_execute)
    return db


def _override_db(db):
    async def _fake():
        yield db

    app.dependency_overrides[get_db] = _fake


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def http_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def pkg_ids():
    return [uuid.uuid4(), uuid.uuid4()]


@pytest.fixture
def client_id():
    return uuid.uuid4()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_calculate_pricing_success(http_client, client_id, pkg_ids):
    mock_client = _make_client(client_id=client_id)
    pkgs = [_make_package(pid) for pid in pkg_ids]
    _override_auth(_fake_user(UserRole.CLIENT_USER))
    _override_db(_mock_db(mock_client, pkgs))

    resp = await http_client.post(
        URL,
        json={
            "client_id": str(client_id),
            "package_ids": [str(p) for p in pkg_ids],
            "priority": "normal",
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "packages" in data
    assert len(data["packages"]) == 2


@pytest.mark.anyio
async def test_calculate_pricing_high_priority(http_client, client_id, pkg_ids):
    mock_client = _make_client(client_id=client_id)
    pkgs = [_make_package(pid) for pid in pkg_ids]
    _override_auth(_fake_user(UserRole.SUPER_ADMIN))
    _override_db(_mock_db(mock_client, pkgs))

    resp = await http_client.post(
        URL,
        json={
            "client_id": str(client_id),
            "package_ids": [str(p) for p in pkg_ids],
            "priority": "high",
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["priority_fee"] == 50.0


@pytest.mark.anyio
async def test_calculate_pricing_client_not_found(http_client, pkg_ids):
    _override_auth(_fake_user(UserRole.SUPER_ADMIN))
    _override_db(_mock_db(None, []))

    resp = await http_client.post(
        URL,
        json={
            "client_id": str(uuid.uuid4()),
            "package_ids": [str(uuid.uuid4())],
        },
    )

    assert resp.status_code == 404
    assert "not found" in resp.json()["error"]["message"]


@pytest.mark.anyio
async def test_calculate_pricing_inactive_client(http_client, client_id, pkg_ids):
    mock_client = _make_client(client_id=client_id, is_active=False)
    _override_auth(_fake_user(UserRole.SUPER_ADMIN))
    _override_db(_mock_db(mock_client, []))

    resp = await http_client.post(
        URL,
        json={
            "client_id": str(client_id),
            "package_ids": [str(uuid.uuid4())],
        },
    )

    assert resp.status_code == 400
    assert "not active" in resp.json()["error"]["message"]


@pytest.mark.anyio
async def test_calculate_pricing_missing_packages(http_client, client_id):
    mock_client = _make_client(client_id=client_id)
    _override_auth(_fake_user(UserRole.CITY_ADMIN))
    _override_db(_mock_db(mock_client, []))

    resp = await http_client.post(
        URL,
        json={
            "client_id": str(client_id),
            "package_ids": [str(uuid.uuid4())],
        },
    )

    assert resp.status_code == 404
    assert "Packages not found" in resp.json()["error"]["message"]


@pytest.mark.anyio
async def test_calculate_pricing_inactive_package(http_client, client_id, pkg_ids):
    mock_client = _make_client(client_id=client_id)
    pkgs = [_make_package(pkg_ids[0], is_active=False), _make_package(pkg_ids[1])]
    _override_auth(_fake_user(UserRole.SUPER_ADMIN))
    _override_db(_mock_db(mock_client, pkgs))

    resp = await http_client.post(
        URL,
        json={
            "client_id": str(client_id),
            "package_ids": [str(p) for p in pkg_ids],
        },
    )

    assert resp.status_code == 400
    assert "Inactive packages" in resp.json()["error"]["message"]


@pytest.mark.anyio
async def test_calculate_pricing_unauthorized_role(http_client, client_id, pkg_ids):
    _override_auth(_fake_user(UserRole.PHLEBOTOMIST))

    resp = await http_client.post(
        URL,
        json={
            "client_id": str(client_id),
            "package_ids": [str(p) for p in pkg_ids],
        },
    )

    assert resp.status_code == 403


@pytest.mark.anyio
async def test_calculate_pricing_empty_package_ids(http_client, client_id):
    _override_auth(_fake_user(UserRole.CLIENT_USER))

    resp = await http_client.post(
        URL,
        json={
            "client_id": str(client_id),
            "package_ids": [],
        },
    )

    assert resp.status_code == 422
