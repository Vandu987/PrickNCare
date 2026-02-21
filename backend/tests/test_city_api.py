"""API tests for City CRUD endpoints — task 5.1."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_active_user, get_current_user
from app.core.database import get_db
from app.main import app
from app.models.users import User, UserRole
from app.models.zones import City

# ── Helpers ──────────────────────────────────────────────────────────────

_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _fake_user(role: UserRole = UserRole.SUPER_ADMIN) -> User:
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.role = role
    user.is_active = True
    return user


ADMIN_USER = _fake_user(UserRole.SUPER_ADMIN)
CITY_ADMIN_USER = _fake_user(UserRole.CITY_ADMIN)
CLIENT_USER_OBJ = _fake_user(UserRole.CLIENT_USER)


def _make_city(
    name: str = "Mumbai",
    state: str = "Maharashtra",
    is_serviceable: bool = True,
    zones: list | None = None,
) -> City:
    city = MagicMock(spec=City)
    city.id = uuid.uuid4()
    city.name = name
    city.state = state
    city.is_serviceable = is_serviceable
    city.created_at = _NOW
    city.updated_at = _NOW
    city.zones = zones if zones is not None else []
    return city


class MockDB:
    """A mock async DB session that can be configured per test."""

    def __init__(self) -> None:
        self.execute = AsyncMock()
        self.add = MagicMock()
        self.commit = AsyncMock()
        self.refresh = AsyncMock()
        self.delete = AsyncMock()


def _setup_overrides(user: User, mock_db: MockDB) -> None:
    async def _fake_active() -> User:
        return user

    async def _fake_current() -> User:
        return user

    async def _fake_db():
        yield mock_db

    app.dependency_overrides[get_current_active_user] = _fake_active
    app.dependency_overrides[get_current_user] = _fake_current
    app.dependency_overrides[get_db] = _fake_db


def _setup_auth_only(user: User) -> None:
    async def _fake_active() -> User:
        return user

    async def _fake_current() -> User:
        return user

    app.dependency_overrides[get_current_active_user] = _fake_active
    app.dependency_overrides[get_current_user] = _fake_current


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    app.dependency_overrides.clear()


async def _client() -> AsyncClient:
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


# ── POST /api/v1/cities ─────────────────────────────────────────────────


class TestCreateCity:
    @pytest.mark.asyncio
    async def test_create_city_success(self) -> None:
        city = _make_city()
        mock_db = MockDB()
        mock_db.refresh = AsyncMock()
        _setup_overrides(ADMIN_USER, mock_db)

        # Patch City constructor to return our mock
        import app.api.v1.zones as zones_mod

        original_city = zones_mod.City
        zones_mod.City = lambda **kwargs: city  # type: ignore[assignment]

        try:
            async with await _client() as ac:
                resp = await ac.post(
                    "/api/v1/cities",
                    json={"name": "Mumbai", "state": "Maharashtra"},
                )
        finally:
            zones_mod.City = original_city

        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Mumbai"
        assert data["state"] == "Maharashtra"
        assert data["is_serviceable"] is True

    @pytest.mark.asyncio
    async def test_create_city_forbidden_for_client_user(self) -> None:
        _setup_auth_only(CLIENT_USER_OBJ)
        async with await _client() as ac:
            resp = await ac.post(
                "/api/v1/cities",
                json={"name": "Mumbai", "state": "Maharashtra"},
            )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_create_city_forbidden_for_city_admin(self) -> None:
        _setup_auth_only(CITY_ADMIN_USER)
        async with await _client() as ac:
            resp = await ac.post(
                "/api/v1/cities",
                json={"name": "Mumbai", "state": "Maharashtra"},
            )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_create_city_no_auth(self) -> None:
        async with await _client() as ac:
            resp = await ac.post(
                "/api/v1/cities",
                json={"name": "Mumbai", "state": "Maharashtra"},
            )
        assert resp.status_code in (401, 403)


# ── GET /api/v1/cities ──────────────────────────────────────────────────


class TestListCities:
    @pytest.mark.asyncio
    async def test_list_cities_as_admin(self) -> None:
        cities = [_make_city("Mumbai"), _make_city("Delhi", "Delhi")]
        mock_db = MockDB()

        count_result = MagicMock()
        count_result.scalar_one.return_value = 2
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = cities
        data_result = MagicMock()
        data_result.scalars.return_value = scalars_mock
        mock_db.execute = AsyncMock(side_effect=[count_result, data_result])

        _setup_overrides(ADMIN_USER, mock_db)

        async with await _client() as ac:
            resp = await ac.get("/api/v1/cities")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    @pytest.mark.asyncio
    async def test_list_cities_as_city_admin(self) -> None:
        mock_db = MockDB()
        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        data_result = MagicMock()
        data_result.scalars.return_value = scalars_mock
        mock_db.execute = AsyncMock(side_effect=[count_result, data_result])

        _setup_overrides(CITY_ADMIN_USER, mock_db)

        async with await _client() as ac:
            resp = await ac.get("/api/v1/cities")

        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_list_cities_with_serviceable_filter(self) -> None:
        city = _make_city(is_serviceable=True)
        mock_db = MockDB()
        count_result = MagicMock()
        count_result.scalar_one.return_value = 1
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [city]
        data_result = MagicMock()
        data_result.scalars.return_value = scalars_mock
        mock_db.execute = AsyncMock(side_effect=[count_result, data_result])

        _setup_overrides(ADMIN_USER, mock_db)

        async with await _client() as ac:
            resp = await ac.get("/api/v1/cities?is_serviceable=true")

        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    @pytest.mark.asyncio
    async def test_list_cities_unauthorized(self) -> None:
        _setup_auth_only(CLIENT_USER_OBJ)
        async with await _client() as ac:
            resp = await ac.get("/api/v1/cities")
        assert resp.status_code == 403


# ── GET /api/v1/cities/{city_id} ────────────────────────────────────────


class TestGetCity:
    @pytest.mark.asyncio
    async def test_get_city_found(self) -> None:
        city = _make_city()
        mock_db = MockDB()
        result = MagicMock()
        result.scalar_one_or_none.return_value = city
        mock_db.execute = AsyncMock(return_value=result)

        _setup_overrides(ADMIN_USER, mock_db)

        async with await _client() as ac:
            resp = await ac.get(f"/api/v1/cities/{city.id}")

        assert resp.status_code == 200
        assert resp.json()["id"] == str(city.id)

    @pytest.mark.asyncio
    async def test_get_city_not_found(self) -> None:
        mock_db = MockDB()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result)

        _setup_overrides(ADMIN_USER, mock_db)

        async with await _client() as ac:
            resp = await ac.get(f"/api/v1/cities/{uuid.uuid4()}")

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_city_as_city_admin(self) -> None:
        city = _make_city()
        mock_db = MockDB()
        result = MagicMock()
        result.scalar_one_or_none.return_value = city
        mock_db.execute = AsyncMock(return_value=result)

        _setup_overrides(CITY_ADMIN_USER, mock_db)

        async with await _client() as ac:
            resp = await ac.get(f"/api/v1/cities/{city.id}")

        assert resp.status_code == 200


# ── PUT /api/v1/cities/{city_id} ────────────────────────────────────────


class TestUpdateCity:
    @pytest.mark.asyncio
    async def test_update_city_success(self) -> None:
        city = _make_city()
        mock_db = MockDB()
        result = MagicMock()
        result.scalar_one_or_none.return_value = city
        mock_db.execute = AsyncMock(return_value=result)

        _setup_overrides(ADMIN_USER, mock_db)

        async with await _client() as ac:
            resp = await ac.put(
                f"/api/v1/cities/{city.id}",
                json={"name": "New Mumbai"},
            )

        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_update_city_not_found(self) -> None:
        mock_db = MockDB()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result)

        _setup_overrides(ADMIN_USER, mock_db)

        async with await _client() as ac:
            resp = await ac.put(
                f"/api/v1/cities/{uuid.uuid4()}",
                json={"name": "Test"},
            )

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_city_forbidden_for_city_admin(self) -> None:
        _setup_auth_only(CITY_ADMIN_USER)
        async with await _client() as ac:
            resp = await ac.put(
                f"/api/v1/cities/{uuid.uuid4()}",
                json={"name": "Test"},
            )
        assert resp.status_code == 403


# ── PUT /api/v1/cities/{city_id}/serviceable ─────────────────────────────


class TestToggleServiceable:
    @pytest.mark.asyncio
    async def test_toggle_serviceable_success(self) -> None:
        city = _make_city(is_serviceable=True)
        mock_db = MockDB()
        result = MagicMock()
        result.scalar_one_or_none.return_value = city
        mock_db.execute = AsyncMock(return_value=result)

        _setup_overrides(ADMIN_USER, mock_db)

        async with await _client() as ac:
            resp = await ac.put(
                f"/api/v1/cities/{city.id}/serviceable",
                json={"is_serviceable": False},
            )

        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_toggle_serviceable_not_found(self) -> None:
        mock_db = MockDB()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result)

        _setup_overrides(ADMIN_USER, mock_db)

        async with await _client() as ac:
            resp = await ac.put(
                f"/api/v1/cities/{uuid.uuid4()}/serviceable",
                json={"is_serviceable": False},
            )

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_toggle_serviceable_forbidden_for_city_admin(self) -> None:
        _setup_auth_only(CITY_ADMIN_USER)
        async with await _client() as ac:
            resp = await ac.put(
                f"/api/v1/cities/{uuid.uuid4()}/serviceable",
                json={"is_serviceable": False},
            )
        assert resp.status_code == 403


# ── DELETE /api/v1/cities/{city_id} ─────────────────────────────────────


class TestDeleteCity:
    @pytest.mark.asyncio
    async def test_delete_city_no_zones(self) -> None:
        city = _make_city(zones=[])
        mock_db = MockDB()

        first_result = MagicMock()
        first_result.scalar_one_or_none.return_value = city
        second_result = MagicMock()
        second_result.scalar_one.return_value = city

        mock_db.execute = AsyncMock(side_effect=[first_result, second_result])

        _setup_overrides(ADMIN_USER, mock_db)

        async with await _client() as ac:
            resp = await ac.delete(f"/api/v1/cities/{city.id}")

        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_city_with_zones_returns_400(self) -> None:
        zone_mock = MagicMock()
        city = _make_city(zones=[zone_mock])
        mock_db = MockDB()

        first_result = MagicMock()
        first_result.scalar_one_or_none.return_value = city
        second_result = MagicMock()
        second_result.scalar_one.return_value = city

        mock_db.execute = AsyncMock(side_effect=[first_result, second_result])

        _setup_overrides(ADMIN_USER, mock_db)

        async with await _client() as ac:
            resp = await ac.delete(f"/api/v1/cities/{city.id}")

        assert resp.status_code == 400
        body = resp.json()
        # Support both {"detail": ...} and {"error": {"message": ...}} formats
        msg = body.get("detail", "") or body.get("error", {}).get("message", "")
        assert "zones" in msg.lower()

    @pytest.mark.asyncio
    async def test_delete_city_not_found(self) -> None:
        mock_db = MockDB()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result)

        _setup_overrides(ADMIN_USER, mock_db)

        async with await _client() as ac:
            resp = await ac.delete(f"/api/v1/cities/{uuid.uuid4()}")

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_city_forbidden_for_city_admin(self) -> None:
        _setup_auth_only(CITY_ADMIN_USER)
        async with await _client() as ac:
            resp = await ac.delete(f"/api/v1/cities/{uuid.uuid4()}")
        assert resp.status_code == 403
