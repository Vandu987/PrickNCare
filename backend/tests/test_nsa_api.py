"""API tests for NSA management endpoints — task 5.5."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_active_user, get_current_user
from app.core.database import get_db
from app.main import app
from app.models.nsa import NSARecord
from app.models.phlebotomists import Phlebotomist, PhlebotomistZoneAssignment
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
PHLEB_USER = _fake_user(UserRole.PHLEBOTOMIST)

_CITY_ID = uuid.uuid4()
_ZONE_ID = uuid.uuid4()
_PINCODE_ID = uuid.uuid4()
_NSA_ID = uuid.uuid4()


def _make_city() -> MagicMock:
    city = MagicMock(spec=City)
    city.id = _CITY_ID
    city.name = "Mumbai"
    city.is_serviceable = True
    return city


def _make_zone(city: MagicMock | None = None) -> MagicMock:
    zone = MagicMock(spec=Zone)
    zone.id = _ZONE_ID
    zone.name = "Zone A"
    zone.city_id = _CITY_ID
    zone.is_active = True
    zone.city = city or _make_city()
    return zone


def _make_pincode(zone: MagicMock | None = None) -> MagicMock:
    pc = MagicMock(spec=Pincode)
    pc.id = _PINCODE_ID
    pc.pincode = "400001"
    pc.zone_id = _ZONE_ID
    pc.zone = zone or _make_zone()
    return pc


def _make_nsa(
    pincode: str = "400001", is_active: bool = True, reason: str | None = None
) -> MagicMock:
    nsa = MagicMock(spec=NSARecord)
    nsa.id = _NSA_ID
    nsa.pincode = pincode
    nsa.reason = reason
    nsa.marked_at = _NOW
    nsa.marked_by = ADMIN_USER.id
    nsa.is_active = is_active
    return nsa


class MockResult:
    """Mock for db.execute() result."""

    def __init__(self, value: object = None) -> None:
        self._value = value

    def scalar_one_or_none(self) -> object:
        return self._value

    def scalar_one(self) -> object:
        return self._value if self._value is not None else 0

    def scalars(self) -> "MockResult":
        return self

    def all(self) -> list:
        if isinstance(self._value, list):
            return self._value
        return [self._value] if self._value is not None else []


class MockDB:
    def __init__(self) -> None:
        self.execute = AsyncMock()
        self.add = MagicMock()
        self.commit = AsyncMock()
        self.refresh = AsyncMock()
        self.delete = AsyncMock()

    def set_sequence(self, *results: object) -> None:
        self.execute.side_effect = list(results)


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture
def mock_db():
    return MockDB()


@pytest.fixture
def admin_client(mock_db: MockDB):
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: ADMIN_USER
    app.dependency_overrides[get_current_active_user] = lambda: ADMIN_USER
    yield mock_db
    app.dependency_overrides.clear()


@pytest.fixture
def city_admin_client(mock_db: MockDB):
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: CITY_ADMIN_USER
    app.dependency_overrides[get_current_active_user] = lambda: CITY_ADMIN_USER
    yield mock_db
    app.dependency_overrides.clear()


@pytest.fixture
def phleb_client(mock_db: MockDB):
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: PHLEB_USER
    app.dependency_overrides[get_current_active_user] = lambda: PHLEB_USER
    yield mock_db
    app.dependency_overrides.clear()


@pytest.fixture
def noauth_client(mock_db: MockDB):
    app.dependency_overrides[get_db] = lambda: mock_db
    yield mock_db
    app.dependency_overrides.clear()


# Disable Redis for all tests
@pytest.fixture(autouse=True)
def _no_redis():
    with patch("app.api.v1.zones._get_redis", new_callable=AsyncMock, return_value=None):
        yield


# ── Tests: GET /nsa/check ───────────────────────────────────────────────


@pytest.mark.anyio
async def test_check_serviceable_pincode(noauth_client: MockDB) -> None:
    db = noauth_client
    pc = _make_pincode()

    # 1st call: NSA check → None, 2nd: pincode lookup → found, 3rd: phleb count → 3
    db.set_sequence(
        MockResult(None),   # NSA check
        MockResult(pc),     # pincode lookup
        MockResult(3),      # phleb count
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/nsa/check", params={"pincode": "400001"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["is_serviceable"] is True
    assert data["zone_name"] == "Zone A"
    assert data["city_name"] == "Mumbai"
    assert data["available_phlebotomists"] == 3
    assert data["nsa_reason"] is None


@pytest.mark.anyio
async def test_check_nsa_pincode(noauth_client: MockDB) -> None:
    db = noauth_client
    nsa = _make_nsa(reason="Flood area")

    db.set_sequence(MockResult(nsa))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/nsa/check", params={"pincode": "400001"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["is_serviceable"] is False
    assert data["nsa_reason"] == "Flood area"


@pytest.mark.anyio
async def test_check_unknown_pincode(noauth_client: MockDB) -> None:
    db = noauth_client

    db.set_sequence(
        MockResult(None),  # NSA check
        MockResult(None),  # pincode lookup
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/nsa/check", params={"pincode": "999999"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["is_serviceable"] is False


# ── Tests: POST /nsa/mark ───────────────────────────────────────────────


@pytest.mark.anyio
async def test_mark_nsa_success(admin_client: MockDB) -> None:
    db = admin_client

    nsa_record = _make_nsa(pincode="400002", reason="Remote area")
    db.set_sequence(MockResult(None))  # existing check → not found
    db.refresh.side_effect = lambda obj: None  # refresh is no-op

    # We need to mock what refresh does — set attributes on the added object
    original_add = db.add

    def capture_add(obj: object) -> None:
        # Simulate DB assigning fields after commit+refresh
        obj.id = _NSA_ID  # type: ignore[attr-defined]
        obj.pincode = "400002"  # type: ignore[attr-defined]
        obj.reason = "Remote area"  # type: ignore[attr-defined]
        obj.marked_at = _NOW  # type: ignore[attr-defined]
        obj.marked_by = ADMIN_USER.id  # type: ignore[attr-defined]
        obj.is_active = True  # type: ignore[attr-defined]

    db.add = MagicMock(side_effect=capture_add)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/nsa/mark",
            json={"pincode": "400002", "reason": "Remote area"},
            headers={"Authorization": "Bearer fake"},
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["pincode"] == "400002"
    assert data["reason"] == "Remote area"
    assert data["is_active"] is True


@pytest.mark.anyio
async def test_mark_nsa_duplicate(admin_client: MockDB) -> None:
    db = admin_client
    db.set_sequence(MockResult(_make_nsa()))  # already exists

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/nsa/mark",
            json={"pincode": "400001"},
            headers={"Authorization": "Bearer fake"},
        )

    assert resp.status_code == 409


# ── Tests: DELETE /nsa/unmark ────────────────────────────────────────────


@pytest.mark.anyio
async def test_unmark_nsa_success(admin_client: MockDB) -> None:
    db = admin_client
    nsa = _make_nsa()
    db.set_sequence(MockResult(nsa))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.delete(
            "/api/v1/nsa/unmark",
            params={"pincode": "400001"},
            headers={"Authorization": "Bearer fake"},
        )

    assert resp.status_code == 200
    assert nsa.is_active is False


@pytest.mark.anyio
async def test_unmark_nsa_not_found(admin_client: MockDB) -> None:
    db = admin_client
    db.set_sequence(MockResult(None))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.delete(
            "/api/v1/nsa/unmark",
            params={"pincode": "999999"},
            headers={"Authorization": "Bearer fake"},
        )

    assert resp.status_code == 404


# ── Tests: GET /nsa/list ─────────────────────────────────────────────────


@pytest.mark.anyio
async def test_list_nsa_as_admin(admin_client: MockDB) -> None:
    db = admin_client
    nsa1 = _make_nsa(pincode="400001")
    nsa2 = _make_nsa(pincode="400002")

    db.set_sequence(
        MockResult(2),              # count
        MockResult([nsa1, nsa2]),   # items
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/nsa/list",
            headers={"Authorization": "Bearer fake"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


@pytest.mark.anyio
async def test_list_nsa_as_city_admin(city_admin_client: MockDB) -> None:
    db = city_admin_client
    db.set_sequence(MockResult(0), MockResult([]))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/nsa/list",
            headers={"Authorization": "Bearer fake"},
        )

    assert resp.status_code == 200


# ── Tests: Unauthorized access ───────────────────────────────────────────


@pytest.mark.anyio
async def test_mark_nsa_unauthorized(phleb_client: MockDB) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/nsa/mark",
            json={"pincode": "400001"},
            headers={"Authorization": "Bearer fake"},
        )

    assert resp.status_code == 403


@pytest.mark.anyio
async def test_unmark_nsa_unauthorized(phleb_client: MockDB) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.delete(
            "/api/v1/nsa/unmark",
            params={"pincode": "400001"},
            headers={"Authorization": "Bearer fake"},
        )

    assert resp.status_code == 403


@pytest.mark.anyio
async def test_list_nsa_unauthorized(phleb_client: MockDB) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/nsa/list",
            headers={"Authorization": "Bearer fake"},
        )

    assert resp.status_code == 403
