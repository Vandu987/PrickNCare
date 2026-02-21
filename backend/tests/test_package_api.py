"""API tests for package endpoints — task 7.1."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.users import User, UserRole


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
PHLEB_USER = _fake_user(UserRole.PHLEBOTOMIST)
CITY_ADMIN = _fake_user(UserRole.CITY_ADMIN)


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
async def phleb_client():
    _override_auth(PHLEB_USER)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def city_admin_client():
    _override_auth(CITY_ADMIN)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestPackageCreate:
    @pytest.mark.asyncio
    async def test_create_package_valid(self, admin_client: AsyncClient) -> None:
        resp = await admin_client.post(
            "/api/v1/packages",
            json={
                "name": "Complete Blood Count",
                "code": "CBC-001",
                "description": "Full CBC panel",
                "preparation_instructions": "Fasting for 8 hours",
                "tat_hours": 6,
                "sample_types": ["BLOOD_EDTA"],
                "base_price": 350.00,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Complete Blood Count"
        assert data["code"] == "CBC-001"
        assert data["description"] == "Full CBC panel"
        assert data["tat_hours"] == 6
        assert data["sample_types"] == ["BLOOD_EDTA"]
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_create_package_missing_name(self, admin_client: AsyncClient) -> None:
        resp = await admin_client.post(
            "/api/v1/packages",
            json={"code": "X-001"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_package_missing_code(self, admin_client: AsyncClient) -> None:
        resp = await admin_client.post(
            "/api/v1/packages",
            json={"name": "Test"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_package_invalid_sample_type(
        self, admin_client: AsyncClient
    ) -> None:
        resp = await admin_client.post(
            "/api/v1/packages",
            json={
                "name": "Test",
                "code": "T-001",
                "sample_types": ["INVALID_TYPE"],
            },
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_package_unauthorized(self, phleb_client: AsyncClient) -> None:
        resp = await phleb_client.post(
            "/api/v1/packages",
            json={"name": "Test", "code": "T-002"},
        )
        assert resp.status_code == 403


class TestPackageList:
    @pytest.mark.asyncio
    async def test_list_packages(self, admin_client: AsyncClient) -> None:
        resp = await admin_client.get("/api/v1/packages")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data

    @pytest.mark.asyncio
    async def test_list_packages_pagination(self, admin_client: AsyncClient) -> None:
        resp = await admin_client.get("/api/v1/packages?skip=0&limit=5")
        assert resp.status_code == 200
        assert resp.json()["page_size"] == 5

    @pytest.mark.asyncio
    async def test_list_packages_search(self, admin_client: AsyncClient) -> None:
        resp = await admin_client.get("/api/v1/packages?search=blood")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_list_packages_is_active_filter(
        self, admin_client: AsyncClient
    ) -> None:
        resp = await admin_client.get("/api/v1/packages?is_active=true")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_list_packages_sample_type_filter(
        self, admin_client: AsyncClient
    ) -> None:
        resp = await admin_client.get("/api/v1/packages?sample_type=BLOOD_EDTA")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_list_packages_unauthorized(self, phleb_client: AsyncClient) -> None:
        resp = await phleb_client.get("/api/v1/packages")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_list_packages_city_admin(
        self, city_admin_client: AsyncClient
    ) -> None:
        resp = await city_admin_client.get("/api/v1/packages")
        assert resp.status_code == 200


class TestPackageGetById:
    @pytest.mark.asyncio
    async def test_get_package_not_found(self, admin_client: AsyncClient) -> None:
        fake_id = uuid.uuid4()
        resp = await admin_client.get(f"/api/v1/packages/{fake_id}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_package_existing(self, admin_client: AsyncClient) -> None:
        create_resp = await admin_client.post(
            "/api/v1/packages",
            json={"name": "Fetch Me", "code": f"FM-{uuid.uuid4().hex[:6]}"},
        )
        if create_resp.status_code != 201:
            pytest.skip("Cannot create package (DB not configured)")
        pkg_id = create_resp.json()["id"]
        resp = await admin_client.get(f"/api/v1/packages/{pkg_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Fetch Me"


class TestPackageUpdate:
    @pytest.mark.asyncio
    async def test_update_package(self, admin_client: AsyncClient) -> None:
        create_resp = await admin_client.post(
            "/api/v1/packages",
            json={"name": "Old Name", "code": f"ON-{uuid.uuid4().hex[:6]}"},
        )
        if create_resp.status_code != 201:
            pytest.skip("Cannot create package (DB not configured)")
        pkg_id = create_resp.json()["id"]
        resp = await admin_client.put(
            f"/api/v1/packages/{pkg_id}",
            json={"name": "New Name", "tat_hours": 12},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "New Name"
        assert resp.json()["tat_hours"] == 12

    @pytest.mark.asyncio
    async def test_update_package_not_found(self, admin_client: AsyncClient) -> None:
        fake_id = uuid.uuid4()
        resp = await admin_client.put(
            f"/api/v1/packages/{fake_id}",
            json={"name": "Nope"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_package_unauthorized(self, phleb_client: AsyncClient) -> None:
        fake_id = uuid.uuid4()
        resp = await phleb_client.put(
            f"/api/v1/packages/{fake_id}",
            json={"name": "Nope"},
        )
        assert resp.status_code == 403


class TestPackageDelete:
    @pytest.mark.asyncio
    async def test_delete_package_soft(self, admin_client: AsyncClient) -> None:
        create_resp = await admin_client.post(
            "/api/v1/packages",
            json={"name": "Delete Me", "code": f"DM-{uuid.uuid4().hex[:6]}"},
        )
        if create_resp.status_code != 201:
            pytest.skip("Cannot create package (DB not configured)")
        pkg_id = create_resp.json()["id"]
        resp = await admin_client.delete(f"/api/v1/packages/{pkg_id}")
        assert resp.status_code == 204

        # Verify soft-deleted
        get_resp = await admin_client.get(f"/api/v1/packages/{pkg_id}")
        if get_resp.status_code == 200:
            assert get_resp.json()["is_active"] is False

    @pytest.mark.asyncio
    async def test_delete_package_not_found(self, admin_client: AsyncClient) -> None:
        fake_id = uuid.uuid4()
        resp = await admin_client.delete(f"/api/v1/packages/{fake_id}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_package_unauthorized(self, phleb_client: AsyncClient) -> None:
        fake_id = uuid.uuid4()
        resp = await phleb_client.delete(f"/api/v1/packages/{fake_id}")
        assert resp.status_code == 403
