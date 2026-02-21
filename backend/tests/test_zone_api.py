"""API tests for Zone CRUD endpoints — task 5.2."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_active_user, get_current_user
from app.core.database import get_db
from app.main import app
from app.models.users import User, UserRole
from app.models.zones import City, Zone

# ── Helpers ──────────────────────────────────────────────────────────────

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


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
) -> City:
    city = MagicMock(spec=City)
    city.id = uuid.uuid4()
    city.name = name
    city.state = state
    city.is_serviceable = is_serviceable
    city.created_at = _NOW
    city.updated_at = _NOW
    return city


def _make_zone(
    name: str = "Zone A",
    city: City | None = None,
    is_active: bool = True,
    pincodes: list | None = None,
) -> Zone:
    if city is None:
        city = _make_city()
    zone = MagicMock(spec=Zone)
    zone.id = uuid.uuid4()
    zone.name = name
    zone.city_id = city.id
    zone.city = city
    zone.is_active = is_active
    zone.pincodes = pincodes if pincodes is not None else []
    zone.created_at = _NOW
    zone.updated_at = _NOW
    return zone


class MockDB:
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


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    app.dependency_overrides.clear()


async def _client() -> AsyncClient:
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


# ── POST /api/v1/zones ──────────────────────────────────────────────────


class TestCreateZone:
    @pytest.mark.asyncio
    async def test_create_zone_success(self) -> None:
        city = _make_city()
        zone = _make_zone(city=city)
        mock_db = MockDB()

        # First call: find city
        city_result = MagicMock()
        city_result.scalar_one_or_none.return_value = city

        mock_db.execute = AsyncMock(return_value=city_result)

        _setup_overrides(ADMIN_USER, mock_db)

        import app.api.v1.zones as zones_mod

        original_zone = zones_mod.Zone
        zones_mod.Zone = lambda **kwargs: zone  # type: ignore[assignment]

        try:
            async with await _client() as ac:
                resp = await ac.post(
                    "/api/v1/zones",
                    json={"name": "Zone A", "city_id": str(city.id)},
                )
        finally:
            zones_mod.Zone = original_zone

        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Zone A"
        assert data["city_name"] == "Mumbai"
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_create_zone_city_not_found(self) -> None:
        mock_db = MockDB()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result)

        _setup_overrides(ADMIN_USER, mock_db)

        async with await _client() as ac:
            resp = await ac.post(
                "/api/v1/zones",
                json={"name": "Zone A", "city_id": str(uuid.uuid4())},
            )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_create_zone_city_not_serviceable(self) -> None:
        city = _make_city(is_serviceable=False)
        mock_db = MockDB()
        result = MagicMock()
        result.scalar_one_or_none.return_value = city
        mock_db.execute = AsyncMock(return_value=result)

        _setup_overrides(ADMIN_USER, mock_db)

        async with await _client() as ac:
            resp = await ac.post(
                "/api/v1/zones",
                json={"name": "Zone A", "city_id": str(city.id)},
            )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_create_zone_forbidden_for_city_admin(self) -> None:
        _setup_auth_only(CITY_ADMIN_USER)
        async with await _client() as ac:
            resp = await ac.post(
                "/api/v1/zones",
                json={"name": "Zone A", "city_id": str(uuid.uuid4())},
            )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_create_zone_no_auth(self) -> None:
        async with await _client() as ac:
            resp = await ac.post(
                "/api/v1/zones",
                json={"name": "Zone A", "city_id": str(uuid.uuid4())},
            )
        assert resp.status_code in (401, 403)


# ── GET /api/v1/zones ───────────────────────────────────────────────────


class TestListZones:
    @pytest.mark.asyncio
    async def test_list_zones_as_admin(self) -> None:
        city = _make_city()
        zones = [_make_zone("Zone A", city), _make_zone("Zone B", city)]
        mock_db = MockDB()

        count_result = MagicMock()
        count_result.scalar_one.return_value = 2
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = zones
        data_result = MagicMock()
        data_result.scalars.return_value = scalars_mock
        # Pincode count query
        pc_result = MagicMock()
        pc_result.__iter__ = MagicMock(return_value=iter([]))
        mock_db.execute = AsyncMock(
            side_effect=[count_result, data_result, pc_result]
        )

        _setup_overrides(ADMIN_USER, mock_db)

        async with await _client() as ac:
            resp = await ac.get("/api/v1/zones")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    @pytest.mark.asyncio
    async def test_list_zones_as_city_admin(self) -> None:
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
            resp = await ac.get("/api/v1/zones")

        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_list_zones_with_city_filter(self) -> None:
        city = _make_city()
        zone = _make_zone(city=city)
        mock_db = MockDB()

        count_result = MagicMock()
        count_result.scalar_one.return_value = 1
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [zone]
        data_result = MagicMock()
        data_result.scalars.return_value = scalars_mock
        pc_result = MagicMock()
        pc_result.__iter__ = MagicMock(return_value=iter([]))
        mock_db.execute = AsyncMock(
            side_effect=[count_result, data_result, pc_result]
        )

        _setup_overrides(ADMIN_USER, mock_db)

        async with await _client() as ac:
            resp = await ac.get(f"/api/v1/zones?city_id={city.id}")

        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    @pytest.mark.asyncio
    async def test_list_zones_with_active_filter(self) -> None:
        zone = _make_zone(is_active=True)
        mock_db = MockDB()

        count_result = MagicMock()
        count_result.scalar_one.return_value = 1
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [zone]
        data_result = MagicMock()
        data_result.scalars.return_value = scalars_mock
        pc_result = MagicMock()
        pc_result.__iter__ = MagicMock(return_value=iter([]))
        mock_db.execute = AsyncMock(
            side_effect=[count_result, data_result, pc_result]
        )

        _setup_overrides(ADMIN_USER, mock_db)

        async with await _client() as ac:
            resp = await ac.get("/api/v1/zones?is_active=true")

        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_list_zones_unauthorized(self) -> None:
        _setup_auth_only(CLIENT_USER_OBJ)
        async with await _client() as ac:
            resp = await ac.get("/api/v1/zones")
        assert resp.status_code == 403


# ── GET /api/v1/zones/{zone_id} ─────────────────────────────────────────


class TestGetZone:
    @pytest.mark.asyncio
    async def test_get_zone_found(self) -> None:
        zone = _make_zone()
        mock_db = MockDB()

        zone_result = MagicMock()
        zone_result.scalar_one_or_none.return_value = zone
        pc_result = MagicMock()
        pc_result.scalar_one.return_value = 3
        mock_db.execute = AsyncMock(side_effect=[zone_result, pc_result])

        _setup_overrides(ADMIN_USER, mock_db)

        async with await _client() as ac:
            resp = await ac.get(f"/api/v1/zones/{zone.id}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(zone.id)
        assert data["pincode_count"] == 3

    @pytest.mark.asyncio
    async def test_get_zone_not_found(self) -> None:
        mock_db = MockDB()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result)

        _setup_overrides(ADMIN_USER, mock_db)

        async with await _client() as ac:
            resp = await ac.get(f"/api/v1/zones/{uuid.uuid4()}")

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_zone_as_city_admin(self) -> None:
        zone = _make_zone()
        mock_db = MockDB()

        zone_result = MagicMock()
        zone_result.scalar_one_or_none.return_value = zone
        pc_result = MagicMock()
        pc_result.scalar_one.return_value = 0
        mock_db.execute = AsyncMock(side_effect=[zone_result, pc_result])

        _setup_overrides(CITY_ADMIN_USER, mock_db)

        async with await _client() as ac:
            resp = await ac.get(f"/api/v1/zones/{zone.id}")

        assert resp.status_code == 200


# ── PUT /api/v1/zones/{zone_id} ─────────────────────────────────────────


class TestUpdateZone:
    @pytest.mark.asyncio
    async def test_update_zone_success(self) -> None:
        zone = _make_zone()
        mock_db = MockDB()

        # First: find zone
        find_result = MagicMock()
        find_result.scalar_one_or_none.return_value = zone
        # Second: reload zone with city
        reload_result = MagicMock()
        reload_result.scalar_one.return_value = zone
        # Third: pincode count
        pc_result = MagicMock()
        pc_result.scalar_one.return_value = 0

        mock_db.execute = AsyncMock(
            side_effect=[find_result, reload_result, pc_result]
        )

        _setup_overrides(ADMIN_USER, mock_db)

        async with await _client() as ac:
            resp = await ac.put(
                f"/api/v1/zones/{zone.id}",
                json={"name": "Updated Zone"},
            )

        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_update_zone_not_found(self) -> None:
        mock_db = MockDB()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result)

        _setup_overrides(ADMIN_USER, mock_db)

        async with await _client() as ac:
            resp = await ac.put(
                f"/api/v1/zones/{uuid.uuid4()}",
                json={"name": "Test"},
            )

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_zone_forbidden_for_city_admin(self) -> None:
        _setup_auth_only(CITY_ADMIN_USER)
        async with await _client() as ac:
            resp = await ac.put(
                f"/api/v1/zones/{uuid.uuid4()}",
                json={"name": "Test"},
            )
        assert resp.status_code == 403


# ── PUT /api/v1/zones/{zone_id}/active ──────────────────────────────────


class TestToggleZoneActive:
    @pytest.mark.asyncio
    async def test_toggle_active_success(self) -> None:
        zone = _make_zone(is_active=True)
        mock_db = MockDB()

        find_result = MagicMock()
        find_result.scalar_one_or_none.return_value = zone
        reload_result = MagicMock()
        reload_result.scalar_one.return_value = zone
        pc_result = MagicMock()
        pc_result.scalar_one.return_value = 0

        mock_db.execute = AsyncMock(
            side_effect=[find_result, reload_result, pc_result]
        )

        _setup_overrides(ADMIN_USER, mock_db)

        async with await _client() as ac:
            resp = await ac.put(
                f"/api/v1/zones/{zone.id}/active",
                json={"is_active": False},
            )

        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_toggle_active_not_found(self) -> None:
        mock_db = MockDB()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result)

        _setup_overrides(ADMIN_USER, mock_db)

        async with await _client() as ac:
            resp = await ac.put(
                f"/api/v1/zones/{uuid.uuid4()}/active",
                json={"is_active": False},
            )

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_toggle_active_forbidden_for_city_admin(self) -> None:
        _setup_auth_only(CITY_ADMIN_USER)
        async with await _client() as ac:
            resp = await ac.put(
                f"/api/v1/zones/{uuid.uuid4()}/active",
                json={"is_active": False},
            )
        assert resp.status_code == 403


# ── DELETE /api/v1/zones/{zone_id} ──────────────────────────────────────


class TestDeleteZone:
    @pytest.mark.asyncio
    async def test_delete_zone_no_pincodes(self) -> None:
        zone = _make_zone(pincodes=[])
        mock_db = MockDB()

        result = MagicMock()
        result.scalar_one_or_none.return_value = zone
        mock_db.execute = AsyncMock(return_value=result)

        _setup_overrides(ADMIN_USER, mock_db)

        async with await _client() as ac:
            resp = await ac.delete(f"/api/v1/zones/{zone.id}")

        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_zone_with_pincodes_returns_400(self) -> None:
        pincode_mock = MagicMock()
        zone = _make_zone(pincodes=[pincode_mock])
        mock_db = MockDB()

        result = MagicMock()
        result.scalar_one_or_none.return_value = zone
        mock_db.execute = AsyncMock(return_value=result)

        _setup_overrides(ADMIN_USER, mock_db)

        async with await _client() as ac:
            resp = await ac.delete(f"/api/v1/zones/{zone.id}")

        assert resp.status_code == 400
        body = resp.json()
        msg = body.get("detail", "") or body.get("error", {}).get("message", "")
        assert "pincodes" in msg.lower()

    @pytest.mark.asyncio
    async def test_delete_zone_not_found(self) -> None:
        mock_db = MockDB()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result)

        _setup_overrides(ADMIN_USER, mock_db)

        async with await _client() as ac:
            resp = await ac.delete(f"/api/v1/zones/{uuid.uuid4()}")

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_zone_forbidden_for_city_admin(self) -> None:
        _setup_auth_only(CITY_ADMIN_USER)
        async with await _client() as ac:
            resp = await ac.delete(f"/api/v1/zones/{uuid.uuid4()}")
        assert resp.status_code == 403
