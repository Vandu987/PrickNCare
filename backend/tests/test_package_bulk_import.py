"""Tests for package bulk import endpoint — task 7.2."""

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


def _make_xlsx(rows: list[list]) -> bytes:
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _mock_db(existing_codes: list[str] | None = None):
    """Return a mock async db session with no existing packages by default."""
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.all.return_value = [(c,) for c in (existing_codes or [])]
    db.execute.return_value = mock_result
    db.commit = AsyncMock()
    db.add = MagicMock()
    return db


def _setup(user: User, existing_codes: list[str] | None = None):
    """Override auth and db dependencies, return the mock db."""
    _override_auth(user)
    db = _mock_db(existing_codes)

    async def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    return db


HEADER = [
    "name",
    "code",
    "sample_types",
    "base_price",
    "description",
    "preparation_instructions",
    "tat_hours",
]


@pytest.mark.asyncio
async def test_bulk_import_csv_success():
    _setup(ADMIN_USER)
    csv_data = _make_csv(
        [
            HEADER,
            [
                "CBC",
                "CBC001",
                "BLOOD_EDTA",
                "500",
                "Complete blood count",
                "Fasting",
                "24",
            ],
            ["Urine Test", "UR001", "URINE", "200", "Routine urine", "", "12"],
        ]
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.post(
            "/api/v1/packages/bulk-import",
            files={"file": ("packages.csv", csv_data, "text/csv")},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["total_rows"] == 2
    assert data["successful"] == 2
    assert data["failed"] == 0
    assert data["errors"] == []


@pytest.mark.asyncio
async def test_bulk_import_xlsx_success():
    _setup(ADMIN_USER)
    xlsx_data = _make_xlsx(
        [
            HEADER,
            ["CBC", "CBC002", "BLOOD_EDTA", 500, "Complete blood count", "Fasting", 24],
        ]
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.post(
            "/api/v1/packages/bulk-import",
            files={
                "file": (
                    "packages.xlsx",
                    xlsx_data,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["total_rows"] == 1
    assert data["successful"] == 1


@pytest.mark.asyncio
async def test_bulk_import_validation_errors():
    _setup(ADMIN_USER)
    csv_data = _make_csv(
        [
            HEADER,
            ["", "PKG001", "BLOOD_EDTA", "500", "", "", "24"],  # missing name
            ["Test", "", "BLOOD_EDTA", "abc", "", "", "24"],  # missing code, bad price
            ["Test2", "PKG002", "INVALID_TYPE", "100", "", "", "24"],  # bad sample type
        ]
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.post(
            "/api/v1/packages/bulk-import",
            files={"file": ("packages.csv", csv_data, "text/csv")},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["total_rows"] == 3
    assert data["failed"] == 3
    assert data["successful"] == 0
    assert len(data["errors"]) >= 3


@pytest.mark.asyncio
async def test_bulk_import_partial_success():
    _setup(ADMIN_USER)
    csv_data = _make_csv(
        [
            HEADER,
            ["Good Package", "GOOD01", "BLOOD_EDTA", "100", "", "", "24"],
            ["", "", "", "", "", "", ""],  # all empty — fails
        ]
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.post(
            "/api/v1/packages/bulk-import",
            files={"file": ("packages.csv", csv_data, "text/csv")},
        )

    data = resp.json()
    assert data["successful"] == 1
    assert data["failed"] == 1


@pytest.mark.asyncio
async def test_bulk_import_duplicate_code_in_file():
    _setup(ADMIN_USER)
    csv_data = _make_csv(
        [
            HEADER,
            ["Pkg A", "DUP01", "BLOOD_EDTA", "100", "", "", "24"],
            ["Pkg B", "DUP01", "URINE", "200", "", "", "12"],
        ]
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.post(
            "/api/v1/packages/bulk-import",
            files={"file": ("packages.csv", csv_data, "text/csv")},
        )

    data = resp.json()
    assert data["successful"] == 1
    assert data["failed"] == 1
    assert any("Duplicate" in e["message"] for e in data["errors"])


@pytest.mark.asyncio
async def test_bulk_import_unsupported_file():
    _override_auth(ADMIN_USER)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.post(
            "/api/v1/packages/bulk-import",
            files={"file": ("packages.json", b"{}", "application/json")},
        )

    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_bulk_import_forbidden_for_non_admin():
    _override_auth(PHLEB_USER)

    csv_data = _make_csv([HEADER, ["X", "X01", "BLOOD_EDTA", "100", "", "", "24"]])

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.post(
            "/api/v1/packages/bulk-import",
            files={"file": ("packages.csv", csv_data, "text/csv")},
        )

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_bulk_import_existing_code_in_db():
    _setup(ADMIN_USER, existing_codes=["EXIST01"])
    csv_data = _make_csv(
        [
            HEADER,
            ["Existing Pkg", "EXIST01", "BLOOD_EDTA", "100", "", "", "24"],
        ]
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.post(
            "/api/v1/packages/bulk-import",
            files={"file": ("packages.csv", csv_data, "text/csv")},
        )

    data = resp.json()
    assert data["failed"] == 1
    assert any("already exists" in e["message"] for e in data["errors"])
