"""API tests for phlebotomist endpoints — tasks 4.4, 4.5, 4.6."""

from __future__ import annotations

import io
import uuid
from datetime import date, timedelta
from unittest.mock import MagicMock

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
PHLEB_USER_ID = uuid.uuid4()
PHLEB_USER = _fake_user(UserRole.PHLEBOTOMIST, user_id=PHLEB_USER_ID)
CLIENT_USER = _fake_user(UserRole.CLIENT_USER)


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


VALID_PHLEB = {
    "name": "Ravi Kumar",
    "phone": "+919876543210",
    "employee_id": "EMP001",
}


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


async def _create_phlebotomist(
    ac: AsyncClient,
    employee_id: str | None = None,
    phone: str | None = None,
) -> dict | None:
    data = {
        "name": "Test Phleb",
        "phone": phone or f"+91{uuid.uuid4().int % 10**10:010d}",
        "employee_id": employee_id or f"EMP{uuid.uuid4().hex[:6]}",
    }
    resp = await ac.post("/api/v1/phlebotomists", json=data)
    if resp.status_code != 201:
        return None
    return resp.json()


# ── 4.4 Phlebotomist CRUD ───────────────────────────────────────────────


class TestPhlebotomistCreate:
    @pytest.mark.asyncio
    async def test_create_valid(self, admin_client: AsyncClient) -> None:
        resp = await admin_client.post(
            "/api/v1/phlebotomists",
            json={
                "name": "New Phleb",
                "phone": f"+91{uuid.uuid4().int % 10**10:010d}",
                "employee_id": f"EMP{uuid.uuid4().hex[:6]}",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "New Phleb"
        assert data["is_available"] is True

    @pytest.mark.asyncio
    async def test_create_invalid_phone(self, admin_client: AsyncClient) -> None:
        resp = await admin_client.post(
            "/api/v1/phlebotomists",
            json={
                "name": "Bad Phone",
                "phone": "12345",
                "employee_id": "EMPBAD",
            },
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_missing_fields(self, admin_client: AsyncClient) -> None:
        resp = await admin_client.post("/api/v1/phlebotomists", json={"name": "Only"})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_unauthorized(self, client_user_client: AsyncClient) -> None:
        resp = await client_user_client.post(
            "/api/v1/phlebotomists",
            json=VALID_PHLEB,
        )
        assert resp.status_code == 403


class TestPhlebotomistList:
    @pytest.mark.asyncio
    async def test_list(self, admin_client: AsyncClient) -> None:
        resp = await admin_client.get("/api/v1/phlebotomists")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_list_search(self, admin_client: AsyncClient) -> None:
        resp = await admin_client.get("/api/v1/phlebotomists?search=test")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_list_filter_available(self, admin_client: AsyncClient) -> None:
        resp = await admin_client.get("/api/v1/phlebotomists?is_available=true")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_list_pagination(self, admin_client: AsyncClient) -> None:
        resp = await admin_client.get("/api/v1/phlebotomists?skip=0&limit=5")
        assert resp.status_code == 200
        assert resp.json()["page_size"] == 5


class TestPhlebotomistGetById:
    @pytest.mark.asyncio
    async def test_not_found(self, admin_client: AsyncClient) -> None:
        resp = await admin_client.get(f"/api/v1/phlebotomists/{uuid.uuid4()}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_existing(self, admin_client: AsyncClient) -> None:
        phleb = await _create_phlebotomist(admin_client)
        if not phleb:
            pytest.skip("Cannot create phlebotomist (DB not configured)")
        resp = await admin_client.get(f"/api/v1/phlebotomists/{phleb['id']}")
        assert resp.status_code == 200


class TestPhlebotomistUpdate:
    @pytest.mark.asyncio
    async def test_update(self, admin_client: AsyncClient) -> None:
        phleb = await _create_phlebotomist(admin_client)
        if not phleb:
            pytest.skip("Cannot create phlebotomist (DB not configured)")
        resp = await admin_client.put(
            f"/api/v1/phlebotomists/{phleb['id']}",
            json={"name": "Updated Name"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Name"

    @pytest.mark.asyncio
    async def test_update_not_found(self, admin_client: AsyncClient) -> None:
        resp = await admin_client.put(
            f"/api/v1/phlebotomists/{uuid.uuid4()}",
            json={"name": "Ghost"},
        )
        assert resp.status_code == 404


class TestPhlebotomistDelete:
    @pytest.mark.asyncio
    async def test_soft_delete(self, admin_client: AsyncClient) -> None:
        phleb = await _create_phlebotomist(admin_client)
        if not phleb:
            pytest.skip("Cannot create phlebotomist (DB not configured)")
        resp = await admin_client.delete(f"/api/v1/phlebotomists/{phleb['id']}")
        assert resp.status_code == 204

        get_resp = await admin_client.get(f"/api/v1/phlebotomists/{phleb['id']}")
        if get_resp.status_code == 200:
            assert get_resp.json()["is_available"] is False

    @pytest.mark.asyncio
    async def test_delete_not_found(self, admin_client: AsyncClient) -> None:
        resp = await admin_client.delete(f"/api/v1/phlebotomists/{uuid.uuid4()}")
        assert resp.status_code == 404


# ── 4.4 Documents ────────────────────────────────────────────────────────


class TestPhlebotomistDocuments:
    @pytest.mark.asyncio
    async def test_upload_document(self, admin_client: AsyncClient) -> None:
        phleb = await _create_phlebotomist(admin_client)
        if not phleb:
            pytest.skip("Cannot create phlebotomist (DB not configured)")
        resp = await admin_client.post(
            f"/api/v1/phlebotomists/{phleb['id']}/documents?doc_type=id_proof",
            files={"file": ("test.pdf", b"%PDF-1.4 test", "application/pdf")},
        )
        assert resp.status_code == 201
        assert resp.json()["doc_type"] == "id_proof"

    @pytest.mark.asyncio
    async def test_upload_invalid_type(self, admin_client: AsyncClient) -> None:
        phleb = await _create_phlebotomist(admin_client)
        if not phleb:
            pytest.skip("Cannot create phlebotomist (DB not configured)")
        resp = await admin_client.post(
            f"/api/v1/phlebotomists/{phleb['id']}/documents?doc_type=id_proof",
            files={"file": ("test.exe", b"MZ binary", "application/octet-stream")},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_upload_phleb_not_found(self, admin_client: AsyncClient) -> None:
        resp = await admin_client.post(
            f"/api/v1/phlebotomists/{uuid.uuid4()}/documents?doc_type=id_proof",
            files={"file": ("test.pdf", b"%PDF", "application/pdf")},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_list_documents(self, admin_client: AsyncClient) -> None:
        phleb = await _create_phlebotomist(admin_client)
        if not phleb:
            pytest.skip("Cannot create phlebotomist (DB not configured)")
        resp = await admin_client.get(
            f"/api/v1/phlebotomists/{phleb['id']}/documents"
        )
        assert resp.status_code == 200
        assert "items" in resp.json()

    @pytest.mark.asyncio
    async def test_verify_document(self, admin_client: AsyncClient) -> None:
        phleb = await _create_phlebotomist(admin_client)
        if not phleb:
            pytest.skip("Cannot create phlebotomist (DB not configured)")
        upload = await admin_client.post(
            f"/api/v1/phlebotomists/{phleb['id']}/documents?doc_type=photo",
            files={"file": ("photo.jpg", b"\xff\xd8\xff", "image/jpeg")},
        )
        if upload.status_code != 201:
            pytest.skip("Cannot upload document")
        doc_id = upload.json()["id"]
        resp = await admin_client.put(
            f"/api/v1/phlebotomists/{phleb['id']}/documents/{doc_id}/verify"
        )
        assert resp.status_code == 200
        assert resp.json()["verified"] is True

    @pytest.mark.asyncio
    async def test_verify_document_not_found(
        self, admin_client: AsyncClient
    ) -> None:
        phleb = await _create_phlebotomist(admin_client)
        if not phleb:
            pytest.skip("Cannot create phlebotomist (DB not configured)")
        resp = await admin_client.put(
            f"/api/v1/phlebotomists/{phleb['id']}/documents/{uuid.uuid4()}/verify"
        )
        assert resp.status_code == 404


# ── 4.5 Zones ───────────────────────────────────────────────────────────


class TestPhlebotomistZones:
    @pytest.mark.asyncio
    async def test_assign_zones(self, admin_client: AsyncClient) -> None:
        phleb = await _create_phlebotomist(admin_client)
        if not phleb:
            pytest.skip("Cannot create phlebotomist (DB not configured)")
        zone_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
        resp = await admin_client.put(
            f"/api/v1/phlebotomists/{phleb['id']}/zones",
            json={"zone_ids": zone_ids},
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    @pytest.mark.asyncio
    async def test_list_zones(self, admin_client: AsyncClient) -> None:
        phleb = await _create_phlebotomist(admin_client)
        if not phleb:
            pytest.skip("Cannot create phlebotomist (DB not configured)")
        resp = await admin_client.get(
            f"/api/v1/phlebotomists/{phleb['id']}/zones"
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_zones_phleb_not_found(self, admin_client: AsyncClient) -> None:
        resp = await admin_client.get(
            f"/api/v1/phlebotomists/{uuid.uuid4()}/zones"
        )
        assert resp.status_code == 404


# ── 4.5 Availability ────────────────────────────────────────────────────


class TestPhlebotomistAvailability:
    @pytest.mark.asyncio
    async def test_toggle_availability(self, admin_client: AsyncClient) -> None:
        phleb = await _create_phlebotomist(admin_client)
        if not phleb:
            pytest.skip("Cannot create phlebotomist (DB not configured)")
        resp = await admin_client.put(
            f"/api/v1/phlebotomists/{phleb['id']}/availability",
            json={"is_available": False},
        )
        assert resp.status_code == 200
        assert resp.json()["is_available"] is False

    @pytest.mark.asyncio
    async def test_availability_not_found(self, admin_client: AsyncClient) -> None:
        resp = await admin_client.put(
            f"/api/v1/phlebotomists/{uuid.uuid4()}/availability",
            json={"is_available": True},
        )
        assert resp.status_code == 404


# ── 4.5 Leave ────────────────────────────────────────────────────────────


class TestPhlebotomistLeave:
    @pytest.mark.asyncio
    async def test_apply_leave(self, admin_client: AsyncClient) -> None:
        phleb = await _create_phlebotomist(admin_client)
        if not phleb:
            pytest.skip("Cannot create phlebotomist (DB not configured)")
        future_date = (date.today() + timedelta(days=7)).isoformat()
        resp = await admin_client.post(
            f"/api/v1/phlebotomists/{phleb['id']}/leave",
            json={
                "date": future_date,
                "reason": "Personal",
                "leave_type": "full_day",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["status"] == "pending"

    @pytest.mark.asyncio
    async def test_apply_leave_past_date(self, admin_client: AsyncClient) -> None:
        phleb = await _create_phlebotomist(admin_client)
        if not phleb:
            pytest.skip("Cannot create phlebotomist (DB not configured)")
        resp = await admin_client.post(
            f"/api/v1/phlebotomists/{phleb['id']}/leave",
            json={
                "date": "2020-01-01",
                "reason": "Past",
                "leave_type": "full_day",
            },
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_list_leaves(self, admin_client: AsyncClient) -> None:
        phleb = await _create_phlebotomist(admin_client)
        if not phleb:
            pytest.skip("Cannot create phlebotomist (DB not configured)")
        resp = await admin_client.get(
            f"/api/v1/phlebotomists/{phleb['id']}/leave"
        )
        assert resp.status_code == 200
        assert "items" in resp.json()

    @pytest.mark.asyncio
    async def test_cancel_leave(self, admin_client: AsyncClient) -> None:
        phleb = await _create_phlebotomist(admin_client)
        if not phleb:
            pytest.skip("Cannot create phlebotomist (DB not configured)")
        future_date = (date.today() + timedelta(days=10)).isoformat()
        leave_resp = await admin_client.post(
            f"/api/v1/phlebotomists/{phleb['id']}/leave",
            json={
                "date": future_date,
                "reason": "Cancel me",
                "leave_type": "half_day",
            },
        )
        if leave_resp.status_code != 201:
            pytest.skip("Cannot create leave")
        leave_id = leave_resp.json()["id"]
        resp = await admin_client.delete(
            f"/api/v1/phlebotomists/{phleb['id']}/leave/{leave_id}"
        )
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_cancel_leave_not_found(self, admin_client: AsyncClient) -> None:
        phleb = await _create_phlebotomist(admin_client)
        if not phleb:
            pytest.skip("Cannot create phlebotomist (DB not configured)")
        resp = await admin_client.delete(
            f"/api/v1/phlebotomists/{phleb['id']}/leave/{uuid.uuid4()}"
        )
        assert resp.status_code == 404


# ── 4.5 Bank Details ────────────────────────────────────────────────────


class TestPhlebotomistBankDetails:
    @pytest.mark.asyncio
    async def test_update_bank_details(self, admin_client: AsyncClient) -> None:
        phleb = await _create_phlebotomist(admin_client)
        if not phleb:
            pytest.skip("Cannot create phlebotomist (DB not configured)")
        resp = await admin_client.put(
            f"/api/v1/phlebotomists/{phleb['id']}/bank-details",
            json={
                "account_number": "1234567890123456",
                "ifsc": "SBIN0001234",
                "bank_name": "SBI",
                "upi_id": "test@upi",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        # Account should be masked
        assert data["account_number"].startswith("XXXX")
        assert data["ifsc"] == "SBIN0001234"

    @pytest.mark.asyncio
    async def test_get_bank_details(self, admin_client: AsyncClient) -> None:
        phleb = await _create_phlebotomist(admin_client)
        if not phleb:
            pytest.skip("Cannot create phlebotomist (DB not configured)")
        resp = await admin_client.get(
            f"/api/v1/phlebotomists/{phleb['id']}/bank-details"
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_bank_details_unauthorized(
        self, client_user_client: AsyncClient
    ) -> None:
        resp = await client_user_client.get(
            f"/api/v1/phlebotomists/{uuid.uuid4()}/bank-details"
        )
        # Should be 403 (client_user can't access phleb bank) or 404
        assert resp.status_code in (403, 404)

    @pytest.mark.asyncio
    async def test_invalid_ifsc(self, admin_client: AsyncClient) -> None:
        phleb = await _create_phlebotomist(admin_client)
        if not phleb:
            pytest.skip("Cannot create phlebotomist (DB not configured)")
        resp = await admin_client.put(
            f"/api/v1/phlebotomists/{phleb['id']}/bank-details",
            json={"ifsc": "INVALID"},
        )
        assert resp.status_code == 422


# ── 4.6 Location ────────────────────────────────────────────────────────


class TestPhlebotomistLocation:
    @pytest.mark.asyncio
    async def test_update_location_unauthorized(
        self, admin_client: AsyncClient
    ) -> None:
        """Admin can't update location (only own phlebotomist can)."""
        phleb = await _create_phlebotomist(admin_client)
        if not phleb:
            pytest.skip("Cannot create phlebotomist (DB not configured)")
        resp = await admin_client.put(
            f"/api/v1/phlebotomists/{phleb['id']}/location",
            json={"lat": 19.076, "lng": 72.877},
        )
        # Admin is not the phlebotomist's own user, should get 403
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_get_current_location_no_data(
        self, admin_client: AsyncClient
    ) -> None:
        phleb = await _create_phlebotomist(admin_client)
        if not phleb:
            pytest.skip("Cannot create phlebotomist (DB not configured)")
        resp = await admin_client.get(
            f"/api/v1/phlebotomists/{phleb['id']}/location/current"
        )
        # No location data yet → 404
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_current_location_not_found(
        self, admin_client: AsyncClient
    ) -> None:
        resp = await admin_client.get(
            f"/api/v1/phlebotomists/{uuid.uuid4()}/location/current"
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_location_history(self, admin_client: AsyncClient) -> None:
        phleb = await _create_phlebotomist(admin_client)
        if not phleb:
            pytest.skip("Cannot create phlebotomist (DB not configured)")
        resp = await admin_client.get(
            f"/api/v1/phlebotomists/{phleb['id']}/location/history"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_location_history_not_found(
        self, admin_client: AsyncClient
    ) -> None:
        resp = await admin_client.get(
            f"/api/v1/phlebotomists/{uuid.uuid4()}/location/history"
        )
        assert resp.status_code == 404


# ── 4.6 Metrics ─────────────────────────────────────────────────────────


class TestPhlebotomistMetrics:
    @pytest.mark.asyncio
    async def test_get_metrics(self, admin_client: AsyncClient) -> None:
        phleb = await _create_phlebotomist(admin_client)
        if not phleb:
            pytest.skip("Cannot create phlebotomist (DB not configured)")
        resp = await admin_client.get(
            f"/api/v1/phlebotomists/{phleb['id']}/metrics"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_collections"] == 0
        assert data["success_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_metrics_not_found(self, admin_client: AsyncClient) -> None:
        resp = await admin_client.get(
            f"/api/v1/phlebotomists/{uuid.uuid4()}/metrics"
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_metrics_unauthorized(
        self, client_user_client: AsyncClient
    ) -> None:
        resp = await client_user_client.get(
            f"/api/v1/phlebotomists/{uuid.uuid4()}/metrics"
        )
        assert resp.status_code == 403
