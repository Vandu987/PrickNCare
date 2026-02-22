"""Tests for order bulk upload endpoint — task 6.9."""

from __future__ import annotations

import io
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
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


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    _clear_overrides()


def _make_csv(rows: list[list[str]]) -> bytes:
    buf = io.StringIO()
    for row in rows:
        buf.write(",".join(row) + "\n")
    return buf.getvalue().encode()


HEADER = [
    "patient_name",
    "patient_age",
    "patient_gender",
    "patient_phone",
    "appointment_date",
    "appointment_time",
    "pincode",
    "address",
    "package_code",
    "priority",
    "special_instructions",
]

VALID_ROW = [
    "John Doe",
    "30",
    "M",
    "9876543210",
    "2026-03-15",
    "09:00",
    "110001",
    "123 Main St",
    "CBC01",
    "normal",
    "None",
]


def _mock_db():
    """Return a mock async session with lookup data."""
    db = AsyncMock()

    # Pincode mock
    pincode = MagicMock()
    pincode.id = uuid.uuid4()
    pincode.pincode = "110001"

    # Package mock
    pkg = MagicMock()
    pkg.id = uuid.uuid4()
    pkg.code = "CBC01"
    pkg.base_price = 500.0
    pkg.is_active = True

    # Mock execute for different queries
    call_count = {"n": 0}

    async def mock_execute(stmt):
        call_count["n"] += 1
        result = MagicMock()
        n = call_count["n"]
        if n == 1:  # Pincode query
            result.scalars.return_value = [pincode]
        elif n == 2:  # NSA query
            result.all.return_value = []
        elif n == 3:  # Package query
            result.scalars.return_value = [pkg]
        else:  # booking ID count
            result.scalar_one.return_value = 0
        return result

    db.execute = mock_execute
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.mark.anyio
async def test_bulk_upload_csv_success():
    """Valid CSV with one row should create one order."""
    _override_auth(ADMIN_USER)
    mock_db = _mock_db()
    app.dependency_overrides[get_db] = lambda: mock_db

    csv_data = _make_csv([HEADER, VALID_ROW])

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/orders/bulk-upload",
            files={"file": ("orders.csv", csv_data, "text/csv")},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["total_rows"] == 1
    assert body["successful"] == 1
    assert body["failed"] == 0
    assert len(body["created_order_ids"]) == 1


@pytest.mark.anyio
async def test_bulk_upload_validation_errors():
    """Row with invalid data should be reported as error."""
    _override_auth(ADMIN_USER)
    mock_db = _mock_db()
    app.dependency_overrides[get_db] = lambda: mock_db

    bad_row = [
        "Jane",
        "-1",
        "X",
        "abc",
        "not-a-date",
        "25:99",
        "12345",
        "addr",
        "NONEXIST",
        "urgent",
        "",
    ]
    csv_data = _make_csv([HEADER, bad_row])

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/orders/bulk-upload",
            files={"file": ("orders.csv", csv_data, "text/csv")},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["total_rows"] == 1
    assert body["successful"] == 0
    assert body["failed"] == 1
    assert len(body["errors"]) == 1
    assert body["errors"][0]["row"] == 2


@pytest.mark.anyio
async def test_bulk_upload_rbac_phlebotomist_denied():
    """Phlebotomist should be denied access."""
    _override_auth(PHLEB_USER)

    csv_data = _make_csv([HEADER, VALID_ROW])

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/orders/bulk-upload",
            files={"file": ("orders.csv", csv_data, "text/csv")},
        )

    assert resp.status_code == 403


@pytest.mark.anyio
async def test_bulk_upload_unsupported_file_type():
    """Non-csv/xlsx file should be rejected."""
    _override_auth(ADMIN_USER)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/orders/bulk-upload",
            files={"file": ("orders.txt", b"data", "text/plain")},
        )

    assert resp.status_code == 400
    assert "Unsupported" in resp.json()["detail"]


@pytest.mark.anyio
async def test_bulk_upload_empty_file():
    """CSV with only headers should return error."""
    _override_auth(ADMIN_USER)
    mock_db = _mock_db()
    app.dependency_overrides[get_db] = lambda: mock_db

    csv_data = _make_csv([HEADER])

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/orders/bulk-upload",
            files={"file": ("orders.csv", csv_data, "text/csv")},
        )

    assert resp.status_code == 400
    assert "no data" in resp.json()["detail"].lower()


@pytest.mark.anyio
async def test_bulk_upload_city_admin_allowed():
    """City admin should have access."""
    _override_auth(CITY_ADMIN)
    mock_db = _mock_db()
    app.dependency_overrides[get_db] = lambda: mock_db

    csv_data = _make_csv([HEADER, VALID_ROW])

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/orders/bulk-upload",
            files={"file": ("orders.csv", csv_data, "text/csv")},
        )

    assert resp.status_code == 200
    assert resp.json()["successful"] == 1


@pytest.mark.anyio
async def test_bulk_upload_mixed_rows():
    """Mix of valid and invalid rows."""
    _override_auth(ADMIN_USER)
    mock_db = _mock_db()
    app.dependency_overrides[get_db] = lambda: mock_db

    bad_row = ["", "", "", "", "", "", "", "", "", "", ""]
    csv_data = _make_csv([HEADER, VALID_ROW, bad_row])

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/orders/bulk-upload",
            files={"file": ("orders.csv", csv_data, "text/csv")},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["total_rows"] == 2
    assert body["successful"] == 1
    assert body["failed"] == 1
