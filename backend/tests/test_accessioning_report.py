"""API tests for accessioning report — task 8.5."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.main import app
from app.models.orders import Order
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
PHLEB_USER = _fake_user(UserRole.PHLEBOTOMIST)


def _override_auth(user: User) -> None:
    from app.api.deps import get_current_active_user, get_current_user

    app.dependency_overrides[get_current_active_user] = lambda: user
    app.dependency_overrides[get_current_user] = lambda: user


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def _fake_order(order_id: uuid.UUID | None = None) -> Order:
    o = MagicMock(spec=Order)
    o.id = order_id or uuid.uuid4()
    o.patient_name = "Test Patient"
    o.booking_id = "BK-001"
    return o


def _fake_sample(
    order: Order,
    integrity: SampleIntegrity = SampleIntegrity.OK,
    status: SampleStatus = SampleStatus.ACCEPTED,
    vial_type: str = "edta_purple",
    rejection_reason: str | None = None,
) -> SampleAccessioning:
    s = MagicMock(spec=SampleAccessioning)
    s.id = uuid.uuid4()
    s.order_id = order.id
    s.order = order
    s.integrity = integrity
    s.status = status
    s.vial_type = vial_type
    s.rejection_reason = rejection_reason
    s.created_at = datetime(2025, 6, 15, 10, 0, 0, tzinfo=UTC)
    return s


# ── Tests ────────────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_report_forbidden_for_phlebotomist(client):
    _override_auth(PHLEB_USER)
    try:
        resp = await client.get(
            "/api/v1/accessioning/report",
            params={"date_from": "2025-06-01", "date_to": "2025-06-30"},
        )
        assert resp.status_code == 403
    finally:
        _clear_overrides()


@pytest.mark.anyio
async def test_report_missing_dates(client):
    _override_auth(ADMIN_USER)
    try:
        resp = await client.get("/api/v1/accessioning/report")
        assert resp.status_code == 422
    finally:
        _clear_overrides()


@pytest.mark.anyio
async def test_report_empty(client):
    _override_auth(ADMIN_USER)

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_result)

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        resp = await client.get(
            "/api/v1/accessioning/report",
            params={"date_from": "2025-06-01", "date_to": "2025-06-30"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_samples_received"] == 0
        assert data["rejection_rate"] == 0.0
        assert data["hold_rate"] == 0.0
        assert data["average_samples_per_order"] == 0.0
        assert data["rejected_samples_list"] == []
    finally:
        _clear_overrides()


@pytest.mark.anyio
async def test_report_with_data(client):
    _override_auth(ADMIN_USER)

    order1 = _fake_order()
    order2 = _fake_order()
    samples = [
        _fake_sample(order1, SampleIntegrity.OK, SampleStatus.ACCEPTED),
        _fake_sample(
            order1,
            SampleIntegrity.HEMOLYZED,
            SampleStatus.REJECTED,
            rejection_reason="Hemolyzed sample",
        ),
        _fake_sample(order2, SampleIntegrity.OK, SampleStatus.HOLD),
        _fake_sample(order2, SampleIntegrity.LIPEMIC, SampleStatus.ACCEPTED),
    ]

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = samples
    mock_db.execute = AsyncMock(return_value=mock_result)

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        resp = await client.get(
            "/api/v1/accessioning/report",
            params={"date_from": "2025-06-01", "date_to": "2025-06-30"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_samples_received"] == 4
        assert data["rejection_rate"] == 25.0
        assert data["hold_rate"] == 25.0
        assert data["average_samples_per_order"] == 2.0
        assert len(data["rejected_samples_list"]) == 1
        assert (
            data["rejected_samples_list"][0]["rejection_reason"] == "Hemolyzed sample"
        )
        # Integrity breakdown
        assert data["breakdown_by_integrity"]["ok"]["count"] == 2
        assert data["breakdown_by_integrity"]["hemolyzed"]["count"] == 1
        assert data["breakdown_by_status"]["accepted"]["count"] == 2
    finally:
        _clear_overrides()


@pytest.mark.anyio
async def test_report_city_admin_allowed(client):
    city_admin = _fake_user(UserRole.CITY_ADMIN)
    _override_auth(city_admin)

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_result)

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        resp = await client.get(
            "/api/v1/accessioning/report",
            params={"date_from": "2025-06-01", "date_to": "2025-06-30"},
        )
        assert resp.status_code == 200
    finally:
        _clear_overrides()
