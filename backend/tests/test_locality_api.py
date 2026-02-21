"""API tests for Locality CRUD endpoints — task 5.4."""

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
from app.models.zones import City, Locality, Pincode, Zone

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


def _make_city() -> City:
    city = MagicMock(spec=City)
    city.id = uuid.uuid4()
    city.name = "Mumbai"
    city.state = "Maharashtra"
    city.is_serviceable = True
    city.created_at = _NOW
    city.updated_at = _NOW
    return city


def _make_zone(city: City | None = None) -> Zone:
    if city is None:
        city = _make_city()
    zone = MagicMock(spec=Zone)
    zone.id = uuid.uuid4()
    zone.name = "Zone A"
    zone.city_id = city.id
    zone.city = city
    zone.is_active = True
    zone.created_at = _NOW
    zone.updated_at = _NOW
    return zone


def _make_pincode(pincode: str = "400001", zone: Zone | None = None) -> Pincode:
    if zone is None:
        zone = _make_zone()
    p = MagicMock(spec=Pincode)
    p.id = uuid.uuid4()
    p.pincode = pincode
    p.zone_id = zone.id
    p.zone = zone
    p.created_at = _NOW
    return p


def _make_locality(
    name: str = "Andheri East", pincode: Pincode | None = None
) -> Locality:
    if pincode is None:
        pincode = _make_pincode()
    loc = MagicMock(spec=Locality)
    loc.id = uuid.uuid4()
    loc.name = name
    loc.pincode_id = pincode.id
    loc.pincode = pincode
    return loc


class MockDB:
    def __init__(self) -> None:
        self.execute = AsyncMock()
        self.add = MagicMock()
        self.commit = AsyncMock()
        self.refresh = AsyncMock()
        self.delete = AsyncMock()
        self.flush = AsyncMock()


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


def _setup_no_auth(mock_db: MockDB) -> None:
    async def _fake_db():
        yield mock_db

    app.dependency_overrides[get_db] = _fake_db


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    app.dependency_overrides.clear()


async def _client() -> AsyncClient:
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


# ── POST /api/v1/localities ─────────────────────────────────────────────


class TestCreateLocality:
    @pytest.mark.asyncio
    async def test_create_locality_success(self) -> None:
        pincode = _make_pincode()
        mock_db = MockDB()

        # First execute: pincode lookup
        pincode_result = MagicMock()
        pincode_result.scalar_one_or_none.return_value = pincode

        # Second execute: uniqueness check
        unique_result = MagicMock()
        unique_result.scalar_one_or_none.return_value = None

        mock_db.execute.side_effect = [pincode_result, unique_result]

        _setup_overrides(ADMIN_USER, mock_db)
        client = await _client()

        resp = await client.post(
            "/api/v1/localities",
            json={"name": "Andheri East", "pincode_id": str(pincode.id)},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Andheri East"
        assert data["pincode"] == pincode.pincode
        assert data["zone_name"] == pincode.zone.name
        await client.aclose()

    @pytest.mark.asyncio
    async def test_create_locality_pincode_not_found(self) -> None:
        mock_db = MockDB()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result

        _setup_overrides(ADMIN_USER, mock_db)
        client = await _client()

        resp = await client.post(
            "/api/v1/localities",
            json={"name": "Test", "pincode_id": str(uuid.uuid4())},
        )
        assert resp.status_code == 404
        assert "Pincode not found" in resp.json()["error"]["message"]
        await client.aclose()

    @pytest.mark.asyncio
    async def test_create_locality_duplicate(self) -> None:
        pincode = _make_pincode()
        existing = _make_locality("Andheri East", pincode)
        mock_db = MockDB()

        pincode_result = MagicMock()
        pincode_result.scalar_one_or_none.return_value = pincode

        dup_result = MagicMock()
        dup_result.scalar_one_or_none.return_value = existing

        mock_db.execute.side_effect = [pincode_result, dup_result]

        _setup_overrides(ADMIN_USER, mock_db)
        client = await _client()

        resp = await client.post(
            "/api/v1/localities",
            json={"name": "Andheri East", "pincode_id": str(pincode.id)},
        )
        assert resp.status_code == 409
        await client.aclose()

    @pytest.mark.asyncio
    async def test_create_locality_unauthorized(self) -> None:
        mock_db = MockDB()
        _setup_overrides(CLIENT_USER_OBJ, mock_db)
        client = await _client()

        resp = await client.post(
            "/api/v1/localities",
            json={"name": "Test", "pincode_id": str(uuid.uuid4())},
        )
        assert resp.status_code == 403
        await client.aclose()


# ── POST /api/v1/localities/bulk ─────────────────────────────────────────


class TestBulkCreateLocalities:
    @pytest.mark.asyncio
    async def test_bulk_create_success(self) -> None:
        pincode = _make_pincode()
        mock_db = MockDB()

        pc_result = MagicMock()
        pc_result.scalar_one_or_none.return_value = pincode

        no_dup = MagicMock()
        no_dup.scalar_one_or_none.return_value = None

        # Two localities: each needs pincode check + dup check
        mock_db.execute.side_effect = [pc_result, no_dup, pc_result, no_dup]

        _setup_overrides(ADMIN_USER, mock_db)
        client = await _client()

        resp = await client.post(
            "/api/v1/localities/bulk",
            json={
                "localities": [
                    {"name": "Loc A", "pincode_id": str(pincode.id)},
                    {"name": "Loc B", "pincode_id": str(pincode.id)},
                ]
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_rows"] == 2
        assert data["created"] == 2
        assert data["errors"] == 0
        await client.aclose()

    @pytest.mark.asyncio
    async def test_bulk_create_skips_duplicates(self) -> None:
        pincode = _make_pincode()
        existing = _make_locality("Existing", pincode)
        mock_db = MockDB()

        pc_result = MagicMock()
        pc_result.scalar_one_or_none.return_value = pincode

        dup_result = MagicMock()
        dup_result.scalar_one_or_none.return_value = existing

        mock_db.execute.side_effect = [pc_result, dup_result]

        _setup_overrides(ADMIN_USER, mock_db)
        client = await _client()

        resp = await client.post(
            "/api/v1/localities/bulk",
            json={
                "localities": [
                    {"name": "Existing", "pincode_id": str(pincode.id)},
                ]
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["created"] == 0
        assert data["errors"] == 1
        await client.aclose()


# ── GET /api/v1/localities ───────────────────────────────────────────────


class TestListLocalities:
    @pytest.mark.asyncio
    async def test_list_localities(self) -> None:
        pincode = _make_pincode()
        loc = _make_locality("Andheri East", pincode)
        mock_db = MockDB()

        count_result = MagicMock()
        count_result.scalar_one.return_value = 1

        list_result = MagicMock()
        list_result.scalars.return_value.all.return_value = [loc]

        mock_db.execute.side_effect = [count_result, list_result]

        _setup_overrides(ADMIN_USER, mock_db)
        client = await _client()

        resp = await client.get("/api/v1/localities")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "Andheri East"
        await client.aclose()

    @pytest.mark.asyncio
    async def test_list_localities_city_admin(self) -> None:
        mock_db = MockDB()

        count_result = MagicMock()
        count_result.scalar_one.return_value = 0

        list_result = MagicMock()
        list_result.scalars.return_value.all.return_value = []

        mock_db.execute.side_effect = [count_result, list_result]

        _setup_overrides(CITY_ADMIN_USER, mock_db)
        client = await _client()

        resp = await client.get("/api/v1/localities")
        assert resp.status_code == 200
        await client.aclose()

    @pytest.mark.asyncio
    async def test_list_localities_unauthorized(self) -> None:
        mock_db = MockDB()
        _setup_overrides(CLIENT_USER_OBJ, mock_db)
        client = await _client()

        resp = await client.get("/api/v1/localities")
        assert resp.status_code == 403
        await client.aclose()


# ── GET /api/v1/localities/by-pincode/{pincode} ─────────────────────────


class TestGetLocalitiesByPincode:
    @pytest.mark.asyncio
    async def test_by_pincode_success(self) -> None:
        pincode = _make_pincode("400001")
        loc1 = _make_locality("Andheri East", pincode)
        loc2 = _make_locality("Andheri West", pincode)
        mock_db = MockDB()

        result = MagicMock()
        result.scalars.return_value.all.return_value = [loc1, loc2]
        mock_db.execute.return_value = result

        _setup_no_auth(mock_db)
        client = await _client()

        resp = await client.get("/api/v1/localities/by-pincode/400001")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["pincode"] == "400001"
        await client.aclose()

    @pytest.mark.asyncio
    async def test_by_pincode_empty(self) -> None:
        mock_db = MockDB()

        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = result

        _setup_no_auth(mock_db)
        client = await _client()

        resp = await client.get("/api/v1/localities/by-pincode/999999")
        assert resp.status_code == 200
        assert resp.json() == []
        await client.aclose()

    @pytest.mark.asyncio
    async def test_by_pincode_no_auth_required(self) -> None:
        """Ensure no auth is needed for by-pincode endpoint."""
        mock_db = MockDB()

        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = result

        # Only DB override, no auth override
        _setup_no_auth(mock_db)
        client = await _client()

        resp = await client.get("/api/v1/localities/by-pincode/400001")
        assert resp.status_code == 200
        await client.aclose()
