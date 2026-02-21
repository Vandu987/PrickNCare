"""API tests for client endpoints — tasks 4.1, 4.2, 4.3."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.users import User, UserRole


# ── Helpers ──────────────────────────────────────────────────────────────


def _fake_user(
    role: UserRole = UserRole.SUPER_ADMIN,
    user_id: uuid.UUID | None = None,
) -> User:
    user = MagicMock(spec=User)
    user.id = user_id or uuid.uuid4()
    user.email = f"{role.value}@test.com"
    user.phone = "+911234567890"
    user.role = role
    user.is_active = True
    return user


ADMIN_USER = _fake_user(UserRole.SUPER_ADMIN)
CITY_ADMIN = _fake_user(UserRole.CITY_ADMIN)
CLIENT_USER = _fake_user(UserRole.CLIENT_USER)
PHLEB_USER = _fake_user(UserRole.PHLEBOTOMIST)


def _override_auth(user: User) -> None:
    """Override auth deps to return a specific fake user."""
    from app.api.deps import get_current_active_user, get_current_user

    async def _fake_active_user() -> User:
        return user

    async def _fake_current_user() -> User:
        return user

    app.dependency_overrides[get_current_active_user] = _fake_active_user
    app.dependency_overrides[get_current_user] = _fake_current_user


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


# ── Fixtures ─────────────────────────────────────────────────────────────


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
async def phleb_client():
    """Client authenticated as phlebotomist — should be rejected by admin endpoints."""
    _override_auth(PHLEB_USER)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def client_user_client():
    _override_auth(CLIENT_USER)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ── 4.1 Client CRUD ─────────────────────────────────────────────────────


class TestClientCreate:
    @pytest.mark.asyncio
    async def test_create_client_valid(self, admin_client: AsyncClient) -> None:
        resp = await admin_client.post(
            "/api/v1/clients",
            json={"name": "Test Lab Pvt Ltd", "city": "Mumbai"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Test Lab Pvt Ltd"
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_create_client_missing_name(self, admin_client: AsyncClient) -> None:
        resp = await admin_client.post("/api/v1/clients", json={})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_client_unauthorized(
        self, phleb_client: AsyncClient
    ) -> None:
        resp = await phleb_client.post(
            "/api/v1/clients",
            json={"name": "Unauthorized Lab"},
        )
        assert resp.status_code == 403


class TestClientList:
    @pytest.mark.asyncio
    async def test_list_clients(self, admin_client: AsyncClient) -> None:
        resp = await admin_client.get("/api/v1/clients")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data

    @pytest.mark.asyncio
    async def test_list_clients_pagination(self, admin_client: AsyncClient) -> None:
        resp = await admin_client.get("/api/v1/clients?skip=0&limit=5")
        assert resp.status_code == 200
        assert resp.json()["page_size"] == 5

    @pytest.mark.asyncio
    async def test_list_clients_search(self, admin_client: AsyncClient) -> None:
        resp = await admin_client.get("/api/v1/clients?search=test")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_list_clients_city_filter(self, admin_client: AsyncClient) -> None:
        resp = await admin_client.get("/api/v1/clients?city=Mumbai")
        assert resp.status_code == 200


class TestClientGetById:
    @pytest.mark.asyncio
    async def test_get_client_not_found(self, admin_client: AsyncClient) -> None:
        fake_id = uuid.uuid4()
        resp = await admin_client.get(f"/api/v1/clients/{fake_id}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_client_existing(self, admin_client: AsyncClient) -> None:
        # Create first
        create_resp = await admin_client.post(
            "/api/v1/clients",
            json={"name": "Fetch Me Lab"},
        )
        if create_resp.status_code != 201:
            pytest.skip("Cannot create client (DB not configured)")
        client_id = create_resp.json()["id"]
        resp = await admin_client.get(f"/api/v1/clients/{client_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Fetch Me Lab"


class TestClientUpdate:
    @pytest.mark.asyncio
    async def test_update_client(self, admin_client: AsyncClient) -> None:
        create_resp = await admin_client.post(
            "/api/v1/clients",
            json={"name": "Old Name"},
        )
        if create_resp.status_code != 201:
            pytest.skip("Cannot create client (DB not configured)")
        client_id = create_resp.json()["id"]
        resp = await admin_client.put(
            f"/api/v1/clients/{client_id}",
            json={"name": "New Name"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "New Name"

    @pytest.mark.asyncio
    async def test_update_client_unauthorized(
        self, phleb_client: AsyncClient
    ) -> None:
        fake_id = uuid.uuid4()
        resp = await phleb_client.put(
            f"/api/v1/clients/{fake_id}",
            json={"name": "Nope"},
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_update_client_not_found(self, admin_client: AsyncClient) -> None:
        fake_id = uuid.uuid4()
        resp = await admin_client.put(
            f"/api/v1/clients/{fake_id}",
            json={"name": "Ghost"},
        )
        assert resp.status_code == 404


class TestClientDelete:
    @pytest.mark.asyncio
    async def test_delete_client_soft(self, admin_client: AsyncClient) -> None:
        create_resp = await admin_client.post(
            "/api/v1/clients",
            json={"name": "Delete Me Lab"},
        )
        if create_resp.status_code != 201:
            pytest.skip("Cannot create client (DB not configured)")
        client_id = create_resp.json()["id"]
        resp = await admin_client.delete(f"/api/v1/clients/{client_id}")
        assert resp.status_code == 204

        # Verify soft delete
        get_resp = await admin_client.get(f"/api/v1/clients/{client_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["is_active"] is False

    @pytest.mark.asyncio
    async def test_delete_client_not_found(self, admin_client: AsyncClient) -> None:
        fake_id = uuid.uuid4()
        resp = await admin_client.delete(f"/api/v1/clients/{fake_id}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_client_unauthorized(
        self, phleb_client: AsyncClient
    ) -> None:
        fake_id = uuid.uuid4()
        resp = await phleb_client.delete(f"/api/v1/clients/{fake_id}")
        assert resp.status_code == 403


# ── 4.2 Rate Configuration ──────────────────────────────────────────────


class TestClientRates:
    @pytest.mark.asyncio
    async def test_update_rates(self, admin_client: AsyncClient) -> None:
        create_resp = await admin_client.post(
            "/api/v1/clients",
            json={"name": "Rate Lab"},
        )
        if create_resp.status_code != 201:
            pytest.skip("Cannot create client (DB not configured)")
        client_id = create_resp.json()["id"]
        resp = await admin_client.put(
            f"/api/v1/clients/{client_id}/rates",
            json={"rate_first_collection": 150.50, "rate_priority": 200},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_update_rates_not_found(self, admin_client: AsyncClient) -> None:
        fake_id = uuid.uuid4()
        resp = await admin_client.put(
            f"/api/v1/clients/{fake_id}/rates",
            json={"rate_first_collection": 100},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_rates_empty_body(self, admin_client: AsyncClient) -> None:
        create_resp = await admin_client.post(
            "/api/v1/clients",
            json={"name": "Empty Rate Lab"},
        )
        if create_resp.status_code != 201:
            pytest.skip("Cannot create client (DB not configured)")
        client_id = create_resp.json()["id"]
        resp = await admin_client.put(
            f"/api/v1/clients/{client_id}/rates",
            json={},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_update_rates_negative_value(
        self, admin_client: AsyncClient
    ) -> None:
        resp = await admin_client.put(
            f"/api/v1/clients/{uuid.uuid4()}/rates",
            json={"rate_first_collection": -10},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_get_rates(self, admin_client: AsyncClient) -> None:
        create_resp = await admin_client.post(
            "/api/v1/clients",
            json={"name": "Get Rate Lab"},
        )
        if create_resp.status_code != 201:
            pytest.skip("Cannot create client (DB not configured)")
        client_id = create_resp.json()["id"]
        resp = await admin_client.get(f"/api/v1/clients/{client_id}/rates")
        assert resp.status_code == 200
        data = resp.json()
        assert "rate_first_collection" in data
        assert "credit_limit" in data

    @pytest.mark.asyncio
    async def test_get_rates_not_found(self, admin_client: AsyncClient) -> None:
        resp = await admin_client.get(f"/api/v1/clients/{uuid.uuid4()}/rates")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_rate_history(self, admin_client: AsyncClient) -> None:
        create_resp = await admin_client.post(
            "/api/v1/clients",
            json={"name": "History Lab"},
        )
        if create_resp.status_code != 201:
            pytest.skip("Cannot create client (DB not configured)")
        client_id = create_resp.json()["id"]

        # Update rates to create history
        await admin_client.put(
            f"/api/v1/clients/{client_id}/rates",
            json={"rate_first_collection": 100},
        )

        resp = await admin_client.get(
            f"/api/v1/clients/{client_id}/rates/history"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_get_rate_history_not_found(
        self, admin_client: AsyncClient
    ) -> None:
        resp = await admin_client.get(
            f"/api/v1/clients/{uuid.uuid4()}/rates/history"
        )
        assert resp.status_code == 404


# ── 4.3 Client Users ────────────────────────────────────────────────────


class TestClientUsers:
    @pytest.mark.asyncio
    async def test_create_client_user(self, admin_client: AsyncClient) -> None:
        create_resp = await admin_client.post(
            "/api/v1/clients",
            json={"name": "User Lab"},
        )
        if create_resp.status_code != 201:
            pytest.skip("Cannot create client (DB not configured)")
        client_id = create_resp.json()["id"]
        resp = await admin_client.post(
            f"/api/v1/clients/{client_id}/users",
            json={
                "email": f"user_{uuid.uuid4().hex[:8]}@test.com",
                "phone": "+911234500001",
                "is_primary": True,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["is_primary"] is True
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_create_client_user_client_not_found(
        self, admin_client: AsyncClient
    ) -> None:
        resp = await admin_client.post(
            f"/api/v1/clients/{uuid.uuid4()}/users",
            json={
                "email": "ghost@test.com",
                "phone": "+911234500002",
            },
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_create_client_user_duplicate_email(
        self, admin_client: AsyncClient
    ) -> None:
        create_resp = await admin_client.post(
            "/api/v1/clients",
            json={"name": "Dup Email Lab"},
        )
        if create_resp.status_code != 201:
            pytest.skip("Cannot create client (DB not configured)")
        client_id = create_resp.json()["id"]
        email = f"dup_{uuid.uuid4().hex[:8]}@test.com"

        first = await admin_client.post(
            f"/api/v1/clients/{client_id}/users",
            json={"email": email, "phone": "+911234500003"},
        )
        if first.status_code != 201:
            pytest.skip("Cannot create user (DB issue)")

        second = await admin_client.post(
            f"/api/v1/clients/{client_id}/users",
            json={"email": email, "phone": "+911234500004"},
        )
        assert second.status_code == 400
        assert "Email already registered" in second.json()["detail"]

    @pytest.mark.asyncio
    async def test_list_client_users(self, admin_client: AsyncClient) -> None:
        create_resp = await admin_client.post(
            "/api/v1/clients",
            json={"name": "List Users Lab"},
        )
        if create_resp.status_code != 201:
            pytest.skip("Cannot create client (DB not configured)")
        client_id = create_resp.json()["id"]
        resp = await admin_client.get(f"/api/v1/clients/{client_id}/users")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_list_client_users_not_found(
        self, admin_client: AsyncClient
    ) -> None:
        resp = await admin_client.get(f"/api/v1/clients/{uuid.uuid4()}/users")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_client_user(self, admin_client: AsyncClient) -> None:
        create_resp = await admin_client.post(
            "/api/v1/clients",
            json={"name": "Delete User Lab"},
        )
        if create_resp.status_code != 201:
            pytest.skip("Cannot create client (DB not configured)")
        client_id = create_resp.json()["id"]

        user_resp = await admin_client.post(
            f"/api/v1/clients/{client_id}/users",
            json={
                "email": f"delme_{uuid.uuid4().hex[:8]}@test.com",
                "phone": "+911234500005",
            },
        )
        if user_resp.status_code != 201:
            pytest.skip("Cannot create user (DB issue)")
        user_id = user_resp.json()["user_id"]

        resp = await admin_client.delete(
            f"/api/v1/clients/{client_id}/users/{user_id}"
        )
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_client_user_not_found(
        self, admin_client: AsyncClient
    ) -> None:
        resp = await admin_client.delete(
            f"/api/v1/clients/{uuid.uuid4()}/users/{uuid.uuid4()}"
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_create_client_user_unauthorized(
        self, phleb_client: AsyncClient
    ) -> None:
        resp = await phleb_client.post(
            f"/api/v1/clients/{uuid.uuid4()}/users",
            json={"email": "x@test.com", "phone": "+911234500006"},
        )
        assert resp.status_code == 403
