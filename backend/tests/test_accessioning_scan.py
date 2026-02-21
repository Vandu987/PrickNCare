"""Tests for barcode/booking ID lookup — task 8.4."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.users import User, UserRole


def _fake_user(role: UserRole = UserRole.SUPER_ADMIN) -> User:
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = f"{role.value}@test.com"
    user.phone = "+911234567890"
    user.role = role
    user.is_active = True
    return user


ADMIN_USER = _fake_user(UserRole.SUPER_ADMIN)
CITY_ADMIN = _fake_user(UserRole.CITY_ADMIN)
PHLEB_USER = _fake_user(UserRole.PHLEBOTOMIST)


def _override_auth(user: User) -> None:
    from app.api.deps import get_current_active_user, get_current_user

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


@pytest.fixture
async def admin_client():
    _override_auth(ADMIN_USER)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def city_admin_client():
    _override_auth(CITY_ADMIN)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def phleb_client():
    _override_auth(PHLEB_USER)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _make_mock_order(booking_id: str = "BK-ABC12345") -> MagicMock:
    """Build a mock Order with relationships."""
    order = MagicMock()
    order.id = uuid.uuid4()
    order.booking_id = booking_id
    order.patient_name = "John Doe"
    order.patient_age = 30
    order.patient_gender = MagicMock(value="M")
    order.collected_at = None
    order.status = MagicMock(value="collected")

    # Client
    client = MagicMock()
    client.name = "Test Client"
    order.client = client

    # Phlebotomist
    phleb = MagicMock()
    phleb.name = "Jane Phleb"
    order.assigned_phlebotomist = phleb

    # Packages
    pkg = MagicMock()
    pkg.package.name = "CBC"
    pkg.package.code = "CBC001"
    pkg.package.sample_types = ["BLOOD_EDTA"]
    order.packages = [pkg]

    # Samples
    sample = MagicMock()
    sample.id = uuid.uuid4()
    sample.vial_type = "BLOOD_EDTA"
    sample.quantity = 1
    sample.integrity = MagicMock(value="ok")
    sample.status = MagicMock(value="accepted")
    sample.received_at = None
    order.samples = [sample]

    return order


@pytest.mark.asyncio
async def test_scan_barcode_found(admin_client: AsyncClient):
    mock_order = _make_mock_order()

    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [mock_order]
    mock_result.scalars.return_value = mock_scalars

    with patch("app.api.v1.accessioning.get_db") as mock_get_db:
        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result
        mock_get_db.return_value = mock_db

        # Override the get_db dependency directly
        from app.core.database import get_db

        app.dependency_overrides[get_db] = lambda: mock_db

        resp = await admin_client.get("/api/v1/accessioning/scan/BK-ABC")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["booking_id"] == "BK-ABC12345"
    assert data[0]["patient_name"] == "John Doe"
    assert data[0]["client_name"] == "Test Client"
    assert data[0]["phlebotomist_name"] == "Jane Phleb"
    assert len(data[0]["ordered_tests"]) == 1
    assert data[0]["ordered_tests"][0]["package_code"] == "CBC001"


@pytest.mark.asyncio
async def test_scan_barcode_not_found(admin_client: AsyncClient):
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_result.scalars.return_value = mock_scalars

    from app.core.database import get_db

    mock_db = AsyncMock()
    mock_db.execute.return_value = mock_result
    app.dependency_overrides[get_db] = lambda: mock_db

    resp = await admin_client.get("/api/v1/accessioning/scan/NONEXISTENT")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_scan_barcode_city_admin_allowed(city_admin_client: AsyncClient):
    mock_order = _make_mock_order()

    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [mock_order]
    mock_result.scalars.return_value = mock_scalars

    from app.core.database import get_db

    mock_db = AsyncMock()
    mock_db.execute.return_value = mock_result
    app.dependency_overrides[get_db] = lambda: mock_db

    resp = await city_admin_client.get("/api/v1/accessioning/scan/BK-ABC")

    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_scan_barcode_phleb_forbidden(phleb_client: AsyncClient):
    resp = await phleb_client.get("/api/v1/accessioning/scan/BK-ABC")
    assert resp.status_code == 403
