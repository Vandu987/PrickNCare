"""API tests for Pincode CRUD endpoints — task 5.3."""

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
from app.models.zones import City, Pincode, Zone

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


def _make_city(name: str = "Mumbai", state: str = "Maharashtra") -> City:
    city = MagicMock(spec=City)
    city.id = uuid.uuid4()
    city.name = name
    city.state = state
    city.is_serviceable = True
    city.created_at = _NOW
    city.updated_at = _NOW
    return city


def _make_zone(name: str = "Zone A", city: City | None = None) -> Zone:
    if city is None:
        city = _make_city()
    zone = MagicMock(spec=Zone)
    zone.id = uuid.uuid4()
    zone.name = name
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
    """Setup DB override without auth for public endpoints."""

    async def _fake_db():
        yield mock_db

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


# ── POST /api/v1/pincodes ───────────────────────────────────────────────


class TestCreatePincode:
    @pytest.mark.asyncio
    async def test_create_pincode_success(self) -> None:
        zone = _make_zone()
        mock_db = MockDB()

        # 1st call: find zone
        zone_result = MagicMock()
        zone_result.scalar_one_or_none.return_value = zone
        # 2nd call: check uniqueness
        dup_result = MagicMock()
        dup_result.scalar_one_or_none.return_value = None

        mock_db.execute = AsyncMock(side_effect=[zone_result, dup_result])

        # refresh should set created_at (normally done by DB server_default)
        async def _fake_refresh(obj):
            if hasattr(obj, "created_at") and obj.created_at is None:
                obj.created_at = _NOW

        mock_db.refresh = AsyncMock(side_effect=_fake_refresh)

        _setup_overrides(ADMIN_USER, mock_db)

        async with await _client() as ac:
            resp = await ac.post(
                "/api/v1/pincodes",
                json={"pincode": "400001", "zone_id": str(zone.id)},
            )

        assert resp.status_code == 201
        data = resp.json()
        assert data["pincode"] == "400001"
        assert data["zone_name"] == "Zone A"

    @pytest.mark.asyncio
    async def test_create_pincode_invalid_format(self) -> None:
        _setup_auth_only(ADMIN_USER)
        async with await _client() as ac:
            resp = await ac.post(
                "/api/v1/pincodes",
                json={"pincode": "12345", "zone_id": str(uuid.uuid4())},
            )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_pincode_invalid_non_numeric(self) -> None:
        _setup_auth_only(ADMIN_USER)
        async with await _client() as ac:
            resp = await ac.post(
                "/api/v1/pincodes",
                json={"pincode": "abcdef", "zone_id": str(uuid.uuid4())},
            )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_pincode_duplicate(self) -> None:
        zone = _make_zone()
        existing = _make_pincode(zone=zone)
        mock_db = MockDB()

        zone_result = MagicMock()
        zone_result.scalar_one_or_none.return_value = zone
        dup_result = MagicMock()
        dup_result.scalar_one_or_none.return_value = existing

        mock_db.execute = AsyncMock(side_effect=[zone_result, dup_result])

        _setup_overrides(ADMIN_USER, mock_db)

        async with await _client() as ac:
            resp = await ac.post(
                "/api/v1/pincodes",
                json={"pincode": "400001", "zone_id": str(zone.id)},
            )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_create_pincode_zone_not_found(self) -> None:
        mock_db = MockDB()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result)

        _setup_overrides(ADMIN_USER, mock_db)

        async with await _client() as ac:
            resp = await ac.post(
                "/api/v1/pincodes",
                json={"pincode": "400001", "zone_id": str(uuid.uuid4())},
            )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_create_pincode_forbidden(self) -> None:
        _setup_auth_only(CITY_ADMIN_USER)
        async with await _client() as ac:
            resp = await ac.post(
                "/api/v1/pincodes",
                json={"pincode": "400001", "zone_id": str(uuid.uuid4())},
            )
        assert resp.status_code == 403


# ── POST /api/v1/pincodes/bulk ──────────────────────────────────────────


class TestBulkCreatePincodes:
    @pytest.mark.asyncio
    async def test_bulk_create_success(self) -> None:
        zone = _make_zone()
        mock_db = MockDB()

        zone_result = MagicMock()
        zone_result.scalar_one_or_none.return_value = zone
        no_dup = MagicMock()
        no_dup.scalar_one_or_none.return_value = None

        # For 2 pincodes: zone check + dup check each
        mock_db.execute = AsyncMock(
            side_effect=[zone_result, no_dup, zone_result, no_dup]
        )

        _setup_overrides(ADMIN_USER, mock_db)

        async with await _client() as ac:
            resp = await ac.post(
                "/api/v1/pincodes/bulk",
                json={
                    "pincodes": [
                        {"pincode": "400001", "zone_id": str(zone.id)},
                        {"pincode": "400002", "zone_id": str(zone.id)},
                    ]
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_rows"] == 2
        assert data["created"] == 2
        assert data["errors"] == 0

    @pytest.mark.asyncio
    async def test_bulk_create_with_duplicates(self) -> None:
        zone = _make_zone()
        existing = _make_pincode(zone=zone)
        mock_db = MockDB()

        zone_result = MagicMock()
        zone_result.scalar_one_or_none.return_value = zone
        dup_result = MagicMock()
        dup_result.scalar_one_or_none.return_value = existing
        no_dup = MagicMock()
        no_dup.scalar_one_or_none.return_value = None

        mock_db.execute = AsyncMock(
            side_effect=[zone_result, dup_result, zone_result, no_dup]
        )

        _setup_overrides(ADMIN_USER, mock_db)

        async with await _client() as ac:
            resp = await ac.post(
                "/api/v1/pincodes/bulk",
                json={
                    "pincodes": [
                        {"pincode": "400001", "zone_id": str(zone.id)},
                        {"pincode": "400002", "zone_id": str(zone.id)},
                    ]
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["created"] == 1
        assert data["errors"] == 1


# ── GET /api/v1/pincodes ────────────────────────────────────────────────


class TestListPincodes:
    @pytest.mark.asyncio
    async def test_list_pincodes(self) -> None:
        zone = _make_zone()
        pincodes = [_make_pincode("400001", zone), _make_pincode("400002", zone)]
        mock_db = MockDB()

        count_result = MagicMock()
        count_result.scalar_one.return_value = 2
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = pincodes
        data_result = MagicMock()
        data_result.scalars.return_value = scalars_mock

        mock_db.execute = AsyncMock(side_effect=[count_result, data_result])

        _setup_overrides(ADMIN_USER, mock_db)

        async with await _client() as ac:
            resp = await ac.get("/api/v1/pincodes")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    @pytest.mark.asyncio
    async def test_list_pincodes_with_zone_filter(self) -> None:
        zone = _make_zone()
        pincodes = [_make_pincode("400001", zone)]
        mock_db = MockDB()

        count_result = MagicMock()
        count_result.scalar_one.return_value = 1
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = pincodes
        data_result = MagicMock()
        data_result.scalars.return_value = scalars_mock

        mock_db.execute = AsyncMock(side_effect=[count_result, data_result])

        _setup_overrides(ADMIN_USER, mock_db)

        async with await _client() as ac:
            resp = await ac.get(f"/api/v1/pincodes?zone_id={zone.id}")

        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    @pytest.mark.asyncio
    async def test_list_pincodes_with_search(self) -> None:
        zone = _make_zone()
        pincodes = [_make_pincode("400001", zone)]
        mock_db = MockDB()

        count_result = MagicMock()
        count_result.scalar_one.return_value = 1
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = pincodes
        data_result = MagicMock()
        data_result.scalars.return_value = scalars_mock

        mock_db.execute = AsyncMock(side_effect=[count_result, data_result])

        _setup_overrides(ADMIN_USER, mock_db)

        async with await _client() as ac:
            resp = await ac.get("/api/v1/pincodes?search=400")

        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    @pytest.mark.asyncio
    async def test_list_pincodes_as_city_admin(self) -> None:
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
            resp = await ac.get("/api/v1/pincodes")

        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_list_pincodes_unauthorized(self) -> None:
        _setup_auth_only(CLIENT_USER_OBJ)
        async with await _client() as ac:
            resp = await ac.get("/api/v1/pincodes")
        assert resp.status_code == 403


# ── GET /api/v1/pincodes/suggest ─────────────────────────────────────────


class TestSuggestPincodes:
    @pytest.mark.asyncio
    async def test_suggest_pincodes(self) -> None:
        city = _make_city()
        zone = _make_zone(city=city)
        pincodes = [_make_pincode("400001", zone), _make_pincode("400002", zone)]
        mock_db = MockDB()

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = pincodes
        data_result = MagicMock()
        data_result.scalars.return_value = scalars_mock

        mock_db.execute = AsyncMock(return_value=data_result)

        _setup_no_auth(mock_db)

        async with await _client() as ac:
            resp = await ac.get("/api/v1/pincodes/suggest?q=400")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["city_name"] == "Mumbai"

    @pytest.mark.asyncio
    async def test_suggest_no_query(self) -> None:
        async with await _client() as ac:
            resp = await ac.get("/api/v1/pincodes/suggest")
        assert resp.status_code == 422


# ── PUT /api/v1/pincodes/{id}/zone ──────────────────────────────────────


class TestReassignPincodeZone:
    @pytest.mark.asyncio
    async def test_reassign_success(self) -> None:
        zone_a = _make_zone("Zone A")
        zone_b = _make_zone("Zone B")
        pincode = _make_pincode("400001", zone_a)
        mock_db = MockDB()

        pincode_result = MagicMock()
        pincode_result.scalar_one_or_none.return_value = pincode
        zone_result = MagicMock()
        zone_result.scalar_one_or_none.return_value = zone_b

        mock_db.execute = AsyncMock(side_effect=[pincode_result, zone_result])

        _setup_overrides(ADMIN_USER, mock_db)

        async with await _client() as ac:
            resp = await ac.put(
                f"/api/v1/pincodes/{pincode.id}/zone",
                json={"zone_id": str(zone_b.id)},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["zone_name"] == "Zone B"

    @pytest.mark.asyncio
    async def test_reassign_pincode_not_found(self) -> None:
        mock_db = MockDB()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result)

        _setup_overrides(ADMIN_USER, mock_db)

        async with await _client() as ac:
            resp = await ac.put(
                f"/api/v1/pincodes/{uuid.uuid4()}/zone",
                json={"zone_id": str(uuid.uuid4())},
            )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_reassign_zone_not_found(self) -> None:
        pincode = _make_pincode()
        mock_db = MockDB()

        pincode_result = MagicMock()
        pincode_result.scalar_one_or_none.return_value = pincode
        zone_result = MagicMock()
        zone_result.scalar_one_or_none.return_value = None

        mock_db.execute = AsyncMock(side_effect=[pincode_result, zone_result])

        _setup_overrides(ADMIN_USER, mock_db)

        async with await _client() as ac:
            resp = await ac.put(
                f"/api/v1/pincodes/{pincode.id}/zone",
                json={"zone_id": str(uuid.uuid4())},
            )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_reassign_forbidden(self) -> None:
        _setup_auth_only(CITY_ADMIN_USER)
        async with await _client() as ac:
            resp = await ac.put(
                f"/api/v1/pincodes/{uuid.uuid4()}/zone",
                json={"zone_id": str(uuid.uuid4())},
            )
        assert resp.status_code == 403


# ── POST /api/v1/zones/import ────────────────────────────────────────────


class TestCSVImport:
    @pytest.mark.asyncio
    async def test_import_valid_csv(self) -> None:
        mock_db = MockDB()

        # city lookup returns None (auto-create)
        city_result = MagicMock()
        city_result.scalar_one_or_none.return_value = None
        # zone lookup returns None (auto-create)
        zone_result = MagicMock()
        zone_result.scalar_one_or_none.return_value = None
        # pincode lookup returns None (create)
        pincode_result = MagicMock()
        pincode_result.scalar_one_or_none.return_value = None
        # locality lookup returns None (create)
        locality_result = MagicMock()
        locality_result.scalar_one_or_none.return_value = None

        mock_db.execute = AsyncMock(
            side_effect=[
                city_result,
                zone_result,
                pincode_result,
                locality_result,
                city_result,
                zone_result,
                pincode_result,
                locality_result,
            ]
        )

        _setup_overrides(ADMIN_USER, mock_db)

        csv_content = (
            "city,zone,pincode,locality\n"
            "Mumbai,Zone A,400001,Colaba\n"
            "Mumbai,Zone A,400002,Andheri\n"
        )

        async with await _client() as ac:
            resp = await ac.post(
                "/api/v1/zones/import",
                files={"file": ("test.csv", csv_content.encode(), "text/csv")},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_rows"] == 2
        assert data["created"] == 2
        assert data["errors"] == 0

    @pytest.mark.asyncio
    async def test_import_invalid_pincode_format(self) -> None:
        mock_db = MockDB()
        mock_db.execute = AsyncMock()

        _setup_overrides(ADMIN_USER, mock_db)

        csv_content = "city,zone,pincode,locality\nMumbai,Zone A,12345,Colaba\n"

        async with await _client() as ac:
            resp = await ac.post(
                "/api/v1/zones/import",
                files={"file": ("test.csv", csv_content.encode(), "text/csv")},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["errors"] == 1
        assert data["created"] == 0

    @pytest.mark.asyncio
    async def test_import_missing_columns(self) -> None:
        mock_db = MockDB()
        _setup_overrides(ADMIN_USER, mock_db)

        csv_content = "name,value\nfoo,bar\n"

        async with await _client() as ac:
            resp = await ac.post(
                "/api/v1/zones/import",
                files={"file": ("test.csv", csv_content.encode(), "text/csv")},
            )

        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_import_forbidden(self) -> None:
        _setup_auth_only(CITY_ADMIN_USER)
        async with await _client() as ac:
            resp = await ac.post(
                "/api/v1/zones/import",
                files={"file": ("test.csv", b"city,zone,pincode\n", "text/csv")},
            )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_import_missing_row_data(self) -> None:
        mock_db = MockDB()
        _setup_overrides(ADMIN_USER, mock_db)

        csv_content = "city,zone,pincode,locality\n,Zone A,400001,Colaba\n"

        async with await _client() as ac:
            resp = await ac.post(
                "/api/v1/zones/import",
                files={"file": ("test.csv", csv_content.encode(), "text/csv")},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["errors"] == 1
        assert "missing" in data["error_details"][0].lower()
