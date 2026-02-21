"""Tests for client-wise and zone-wise report APIs (task 14.3)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from unittest.mock import MagicMock

import pytest
from httpx import AsyncClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_user(role: str = "super_admin") -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.role.value = role
    return u


def _make_order(
    client_id: uuid.UUID,
    pincode_id: uuid.UUID,
    status: str = "completed",
    amount: float = 100.0,
    payment_status: str = "paid",
    assigned_at: datetime | None = None,
    collected_at: datetime | None = None,
) -> MagicMock:
    o = MagicMock()
    o.id = uuid.uuid4()
    o.client_id = client_id
    o.pincode_id = pincode_id
    o.appointment_date = date(2025, 1, 15)
    o.amount = amount

    # Status enum mock
    s = MagicMock()
    s.value = status
    o.status = s
    # Make == work with OrderStatus enum members
    o.status.__eq__ = lambda self, other: self.value == other.value

    ps = MagicMock()
    ps.value = payment_status
    o.payment_status = ps

    o.assigned_at = assigned_at
    o.collected_at = collected_at
    return o


def _make_client(
    client_id: uuid.UUID,
    name: str = "Test Client",
    payment_terms: str = "prepaid",
) -> MagicMock:
    c = MagicMock()
    c.id = client_id
    c.name = name
    pt = MagicMock()
    pt.value = payment_terms
    c.payment_terms = pt
    c.payment_terms.__eq__ = lambda self, other: self.value == other.value
    return c


def _make_zone(zone_id: uuid.UUID, name: str, city_id: uuid.UUID) -> MagicMock:
    z = MagicMock()
    z.id = zone_id
    z.name = name
    z.city_id = city_id
    return z


def _make_pincode(pin_id: uuid.UUID, zone_id: uuid.UUID) -> MagicMock:
    p = MagicMock()
    p.id = pin_id
    p.zone_id = zone_id
    return p


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_client_wise_report_unauthenticated(client: AsyncClient):
    """Unauthenticated requests should get 401/403."""
    resp = await client.get(
        "/api/v1/reports/client-wise",
        params={"date_from": "2025-01-01", "date_to": "2025-01-31"},
    )
    assert resp.status_code in (401, 403)


@pytest.mark.anyio
async def test_zone_wise_report_unauthenticated(client: AsyncClient):
    resp = await client.get(
        "/api/v1/reports/zone-wise",
        params={"date_from": "2025-01-01", "date_to": "2025-01-31"},
    )
    assert resp.status_code in (401, 403)


@pytest.mark.anyio
async def test_client_wise_missing_params(client: AsyncClient):
    """Missing required date params should return 422."""
    resp = await client.get("/api/v1/reports/client-wise")
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_zone_wise_missing_params(client: AsyncClient):
    resp = await client.get("/api/v1/reports/zone-wise")
    assert resp.status_code == 422
