"""API tests for accessioning creation — task 8.2."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.main import app
from app.models.orders import Order, OrderStatus, PatientGender
from app.models.samples import SampleAccessioning, SampleIntegrity, SampleStatus
from app.models.users import User, UserRole

# ── Helpers ──────────────────────────────────────────────────────────────


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
PHLEB_USER = _fake_user(UserRole.PHLEBOTOMIST)


def _override_auth(user: User) -> None:
    from app.api.deps import get_current_active_user, get_current_user

    app.dependency_overrides[get_current_active_user] = lambda: user
    app.dependency_overrides[get_current_user] = lambda: user


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def _fake_order(
    order_id: uuid.UUID | None = None,
    status: OrderStatus = OrderStatus.COLLECTED,
) -> Order:
    o = MagicMock(spec=Order)
    o.id = order_id or uuid.uuid4()
    o.status = status
    o.booking_id = "ORD-TEST-001"
    o.patient_name = "Test Patient"
    o.patient_age = 30
    o.patient_gender = PatientGender.MALE
    return o


def _fake_accessioning_record(
    order_id: uuid.UUID,
    acc_id: uuid.UUID | None = None,
    status: SampleStatus = SampleStatus.ACCEPTED,
) -> SampleAccessioning:
    r = MagicMock(spec=SampleAccessioning)
    r.id = acc_id or uuid.uuid4()
    r.order_id = order_id
    r.vial_type = "edta_purple"
    r.quantity = 2
    r.integrity = SampleIntegrity.OK
    r.status = status
    r.rejection_reason = None
    r.notes = "test notes"
    r.accessioned_by = ADMIN_USER.id
    r.created_at = datetime.now(UTC)
    r.updated_at = datetime.now(UTC)
    return r


# ── POST /accessioning/{order_id} ───────────────────────────────────────


@pytest.mark.asyncio
async def test_create_accessioning_success(client):
    """Super admin can create accessioning records for a COLLECTED order."""
    _override_auth(ADMIN_USER)
    order_id = uuid.uuid4()
    fake_order = _fake_order(order_id=order_id)
    fake_record = _fake_accessioning_record(order_id)

    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=fake_order)
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock(
        side_effect=lambda r: setattr(r, "id", fake_record.id)
        or setattr(r, "created_at", fake_record.created_at)
        or setattr(r, "updated_at", fake_record.updated_at)
    )

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db

    resp = await client.post(
        f"/api/v1/accessioning/{order_id}",
        json={
            "samples": [
                {
                    "vial_type": "edta_purple",
                    "quantity": 2,
                    "integrity": "ok",
                    "status": "accepted",
                }
            ],
            "notes": "test notes",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["order_id"] == str(order_id)
    assert len(data["items"]) == 1
    _clear_overrides()


@pytest.mark.asyncio
async def test_create_accessioning_order_not_found(client):
    """Returns 404 when order doesn't exist."""
    _override_auth(ADMIN_USER)
    order_id = uuid.uuid4()

    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=None)

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db

    resp = await client.post(
        f"/api/v1/accessioning/{order_id}",
        json={"samples": [{"vial_type": "edta_purple", "quantity": 1}]},
    )
    assert resp.status_code == 404
    _clear_overrides()


@pytest.mark.asyncio
async def test_create_accessioning_wrong_status(client):
    """Returns 400 when order is not COLLECTED."""
    _override_auth(ADMIN_USER)
    order_id = uuid.uuid4()
    fake_order = _fake_order(order_id=order_id, status=OrderStatus.PENDING)

    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=fake_order)

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db

    resp = await client.post(
        f"/api/v1/accessioning/{order_id}",
        json={"samples": [{"vial_type": "edta_purple", "quantity": 1}]},
    )
    assert resp.status_code == 400
    assert "COLLECTED" in resp.json()["error"]["message"]
    _clear_overrides()


@pytest.mark.asyncio
async def test_create_accessioning_rejected_without_reason(client):
    """Returns 422 when status=rejected but no rejection_reason."""
    _override_auth(ADMIN_USER)
    order_id = uuid.uuid4()
    fake_order = _fake_order(order_id=order_id)

    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=fake_order)

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db

    resp = await client.post(
        f"/api/v1/accessioning/{order_id}",
        json={
            "samples": [
                {
                    "vial_type": "edta_purple",
                    "quantity": 1,
                    "integrity": "hemolyzed",
                    "status": "rejected",
                }
            ],
        },
    )
    assert resp.status_code == 422
    _clear_overrides()


@pytest.mark.asyncio
async def test_create_accessioning_rbac_phlebotomist_denied(client):
    """Phlebotomist cannot create accessioning records."""
    _override_auth(PHLEB_USER)
    order_id = uuid.uuid4()

    resp = await client.post(
        f"/api/v1/accessioning/{order_id}",
        json={"samples": [{"vial_type": "edta_purple", "quantity": 1}]},
    )
    assert resp.status_code == 403
    _clear_overrides()


# ── GET /accessioning/{order_id} ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_accessioning_success(client):
    """Returns accessioning details for an order."""
    _override_auth(ADMIN_USER)
    order_id = uuid.uuid4()
    fake_record = _fake_accessioning_record(order_id)

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [fake_record]

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db

    resp = await client.get(f"/api/v1/accessioning/{order_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["order_id"] == str(order_id)
    assert len(data["items"]) == 1
    assert data["items"][0]["vial_type"] == "edta_purple"
    _clear_overrides()


@pytest.mark.asyncio
async def test_get_accessioning_not_found(client):
    """Returns 404 when no records exist."""
    _override_auth(ADMIN_USER)
    order_id = uuid.uuid4()

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db

    resp = await client.get(f"/api/v1/accessioning/{order_id}")
    assert resp.status_code == 404
    _clear_overrides()


# ── PUT /accessioning/record/{accessioning_id} ──────────────────────────


@pytest.mark.asyncio
async def test_update_accessioning_success(client):
    """Can update hold -> accepted."""
    _override_auth(ADMIN_USER)
    order_id = uuid.uuid4()
    acc_id = uuid.uuid4()
    fake_record = _fake_accessioning_record(
        order_id, acc_id=acc_id, status=SampleStatus.HOLD
    )

    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=fake_record)
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db

    resp = await client.put(
        f"/api/v1/accessioning/record/{acc_id}",
        json={"status": "accepted"},
    )
    assert resp.status_code == 200
    _clear_overrides()


@pytest.mark.asyncio
async def test_update_accessioning_not_found(client):
    """Returns 404 for nonexistent record."""
    _override_auth(ADMIN_USER)
    acc_id = uuid.uuid4()

    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=None)

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db

    resp = await client.put(
        f"/api/v1/accessioning/record/{acc_id}",
        json={"status": "accepted"},
    )
    assert resp.status_code == 404
    _clear_overrides()
