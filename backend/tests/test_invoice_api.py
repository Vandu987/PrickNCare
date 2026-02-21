"""API tests for invoice endpoints — task 9.5."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.users import User, UserRole

# ── Helpers ──────────────────────────────────────────────────────────────


def _fake_user(
    role: UserRole = UserRole.SUPER_ADMIN,
    user_id: uuid.UUID | None = None,
    client_id: uuid.UUID | None = None,
) -> User:
    user = MagicMock(spec=User)
    user.id = user_id or uuid.uuid4()
    user.email = f"{role.value}@test.com"
    user.phone = "+911234567890"
    user.role = role
    user.is_active = True
    if client_id:
        user.client_id = client_id
    return user


ADMIN_USER = _fake_user(UserRole.SUPER_ADMIN)
CITY_ADMIN = _fake_user(UserRole.CITY_ADMIN)
CLIENT_USER = _fake_user(UserRole.CLIENT_USER, client_id=uuid.uuid4())
PHLEB_USER = _fake_user(UserRole.PHLEBOTOMIST)


def _override_auth(user: User) -> None:
    from app.api.deps import get_current_active_user, get_current_user

    async def _fake_active_user() -> User:
        return user

    async def _fake_current_user() -> User:
        return user

    app.dependency_overrides[get_current_active_user] = _fake_active_user
    app.dependency_overrides[get_current_user] = _fake_current_user


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    _clear_overrides()


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


# ── Tests: POST /invoices/generate ───────────────────────────────────────


@pytest.mark.anyio
async def test_generate_invoice_forbidden_for_phlebotomist(phleb_client):
    resp = await phleb_client.post(
        "/api/v1/invoices/generate",
        json={
            "client_id": str(uuid.uuid4()),
            "date_from": "2026-01-01",
            "date_to": "2026-01-31",
        },
    )
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_generate_invoice_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/invoices/generate",
            json={
                "client_id": str(uuid.uuid4()),
                "date_from": "2026-01-01",
                "date_to": "2026-01-31",
            },
        )
    assert resp.status_code in (401, 403)


# ── Tests: GET /invoices ─────────────────────────────────────────────────


@pytest.mark.anyio
async def test_list_invoices_forbidden_for_phlebotomist(phleb_client):
    resp = await phleb_client.get("/api/v1/invoices")
    assert resp.status_code == 403


# ── Tests: GET /invoices/{id} ────────────────────────────────────────────


@pytest.mark.anyio
async def test_get_invoice_not_found(admin_client):
    resp = await admin_client.get(f"/api/v1/invoices/{uuid.uuid4()}")
    assert resp.status_code == 404


# ── Tests: PUT /invoices/{id}/mark-paid ──────────────────────────────────


@pytest.mark.anyio
async def test_mark_paid_not_found(admin_client):
    resp = await admin_client.put(
        f"/api/v1/invoices/{uuid.uuid4()}/mark-paid",
        json={"payment_ref": "PAY-001"},
    )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_mark_paid_forbidden_for_phlebotomist(phleb_client):
    resp = await phleb_client.put(
        f"/api/v1/invoices/{uuid.uuid4()}/mark-paid",
        json={"payment_ref": "PAY-001"},
    )
    assert resp.status_code == 403


# ── Tests: GET /invoices/{id}/pdf ────────────────────────────────────────


@pytest.mark.anyio
async def test_pdf_not_found(admin_client):
    resp = await admin_client.get(f"/api/v1/invoices/{uuid.uuid4()}/pdf")
    assert resp.status_code == 404


# ── Tests: Route registration ────────────────────────────────────────────


@pytest.mark.anyio
async def test_invoice_routes_registered(admin_client):
    """Verify that invoice endpoints are reachable (not 404 method-not-allowed)."""
    # List endpoint should return 200 or DB error, not 404
    resp = await admin_client.get("/api/v1/invoices")
    assert resp.status_code != 404
