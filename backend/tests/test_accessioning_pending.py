"""API tests for pending samples listing — task 8.1."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.orders import Order, OrderStatus, PatientGender
from app.models.users import User, UserRole

# ── Helpers ──────────────────────────────────────────────────────────────

FAKE_CLIENT_ID = uuid.uuid4()
FAKE_PHLEB_ID = uuid.uuid4()


def _fake_user(role: UserRole = UserRole.SUPER_ADMIN) -> User:
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = f"{role.value}@test.com"
    user.phone = "+911234567890"
    user.role = role
    user.is_active = True
    return user


ADMIN_USER = _fake_user(UserRole.SUPER_ADMIN)
CITY_ADMIN_USER = _fake_user(UserRole.CITY_ADMIN)
CLIENT_USER = _fake_user(UserRole.CLIENT_USER)
PHLEB_USER = _fake_user(UserRole.PHLEBOTOMIST)


def _override_auth(user: User) -> None:
    from app.api.deps import get_current_active_user, get_current_user

    app.dependency_overrides[get_current_active_user] = lambda: user
    app.dependency_overrides[get_current_user] = lambda: user


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def _mock_client_obj() -> MagicMock:
    c = MagicMock()
    c.id = FAKE_CLIENT_ID
    c.name = "Test Client"
    return c


def _mock_phlebotomist() -> MagicMock:
    p = MagicMock()
    p.id = FAKE_PHLEB_ID
    p.name = "Test Phleb"
    p.phone = "+919876543210"
    return p


def _mock_order_package(sample_types: list[str] | None = None) -> MagicMock:
    pkg = MagicMock()
    pkg.name = "CBC"
    pkg.code = "CBC-001"
    pkg.sample_types = sample_types or ["BLOOD_EDTA"]
    op = MagicMock()
    op.package = pkg
    return op


def _mock_order(
    booking_id: str = "PNC-TEST-0001",
    sample_types: list[str] | None = None,
) -> MagicMock:
    order = MagicMock(spec=Order)
    order.id = uuid.uuid4()
    order.booking_id = booking_id
    order.patient_name = "Test Patient"
    order.patient_age = 30
    order.patient_gender = PatientGender.MALE
    order.patient_phone = "+911234567890"
    order.status = OrderStatus.COLLECTED
    order.collected_at = datetime(2026, 2, 22, 10, 0, tzinfo=UTC)
    order.client = _mock_client_obj()
    order.assigned_phlebotomist = _mock_phlebotomist()
    order.assigned_phlebotomist_id = FAKE_PHLEB_ID
    order.packages = [_mock_order_package(sample_types)]
    order.samples = []
    return order


def _setup_db(orders: list[MagicMock], total: int | None = None) -> AsyncMock:
    """Mock DB returning count then rows for the pending endpoint."""
    db = AsyncMock()

    if total is None:
        total = len(orders)

    count_result = MagicMock()
    count_result.scalar_one.return_value = total

    rows_result = MagicMock()
    rows_result.scalars.return_value.unique.return_value.all.return_value = orders

    db.execute = AsyncMock(side_effect=[count_result, rows_result])

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: db
    return db


def _make_client(user: User) -> AsyncClient:
    _override_auth(user)
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    _clear_overrides()


# ── Tests: RBAC ──────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_pending_forbidden_for_client_user():
    """CLIENT_USER should get 403."""
    async with _make_client(CLIENT_USER) as ac:
        resp = await ac.get(
            "/api/v1/accessioning/pending",
            headers={"Authorization": "Bearer fake"},
        )
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_pending_forbidden_for_phlebotomist():
    """PHLEBOTOMIST should get 403."""
    async with _make_client(PHLEB_USER) as ac:
        resp = await ac.get(
            "/api/v1/accessioning/pending",
            headers={"Authorization": "Bearer fake"},
        )
    assert resp.status_code == 403


# ── Tests: Successful listing ────────────────────────────────────────────


@pytest.mark.anyio
async def test_pending_empty_for_super_admin():
    """SUPER_ADMIN gets empty list when no pending samples."""
    _setup_db([], total=0)
    async with _make_client(ADMIN_USER) as ac:
        resp = await ac.get(
            "/api/v1/accessioning/pending",
            headers={"Authorization": "Bearer fake"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.anyio
async def test_pending_returns_items_for_city_admin():
    """CITY_ADMIN sees pending items with correct fields."""
    order = _mock_order()
    _setup_db([order], total=1)

    async with _make_client(CITY_ADMIN_USER) as ac:
        resp = await ac.get(
            "/api/v1/accessioning/pending",
            headers={"Authorization": "Bearer fake"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1

    item = data["items"][0]
    assert item["booking_id"] == "PNC-TEST-0001"
    assert item["patient_name"] == "Test Patient"
    assert item["patient_age"] == 30
    assert item["patient_gender"] == "M"
    assert item["expected_sample_types"] == ["BLOOD_EDTA"]
    assert item["phlebotomist"]["name"] == "Test Phleb"
    assert item["client"]["name"] == "Test Client"
    assert item["collection_timestamp"] is not None


# ── Tests: Filters ───────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_pending_accepts_filters():
    """Verify filter query params are accepted."""
    _setup_db([], total=0)

    async with _make_client(ADMIN_USER) as ac:
        resp = await ac.get(
            "/api/v1/accessioning/pending",
            params={
                "collection_date": "2026-02-22",
                "phlebotomist_id": str(FAKE_PHLEB_ID),
                "skip": 0,
                "limit": 10,
            },
            headers={"Authorization": "Bearer fake"},
        )
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_pending_pagination():
    """Verify skip/limit pagination works."""
    orders = [_mock_order(booking_id=f"PNC-TEST-{i:04d}") for i in range(5)]
    _setup_db(orders[:2], total=5)

    async with _make_client(ADMIN_USER) as ac:
        resp = await ac.get(
            "/api/v1/accessioning/pending",
            params={"skip": 0, "limit": 2},
            headers={"Authorization": "Bearer fake"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2
