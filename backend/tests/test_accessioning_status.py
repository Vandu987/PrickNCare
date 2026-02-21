"""Tests for order status updates after accessioning — task 8.3."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.v1.accessioning import _determine_and_update_order_status
from app.models.orders import Order, OrderStatus, OrderStatusHistory
from app.models.samples import SampleAccessioning, SampleIntegrity, SampleStatus
from app.models.users import User, UserRole

# ── Helpers ──────────────────────────────────────────────────────────────


def _fake_user() -> User:
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.role = UserRole.SUPER_ADMIN
    return user


def _fake_order(
    order_id: uuid.UUID | None = None,
    status: OrderStatus = OrderStatus.COLLECTED,
) -> Order:
    o = MagicMock(spec=Order)
    o.id = order_id or uuid.uuid4()
    o.status = status
    o.booking_id = "ORD-TEST-STATUS"
    o.patient_name = "Test Patient"
    return o


def _fake_sample(
    order_id: uuid.UUID,
    status: SampleStatus = SampleStatus.ACCEPTED,
    rejection_reason: str | None = None,
) -> SampleAccessioning:
    r = MagicMock(spec=SampleAccessioning)
    r.id = uuid.uuid4()
    r.order_id = order_id
    r.vial_type = "edta_purple"
    r.quantity = 1
    r.integrity = SampleIntegrity.OK
    r.status = status
    r.rejection_reason = rejection_reason
    r.notes = None
    return r


# ── Unit tests for _determine_and_update_order_status ────────────────────


@pytest.mark.asyncio
async def test_all_accepted_sets_completed():
    """All samples ACCEPTED → order status = COMPLETED."""
    order = _fake_order()
    user = _fake_user()
    db = AsyncMock()
    samples = [
        _fake_sample(order.id, SampleStatus.ACCEPTED),
        _fake_sample(order.id, SampleStatus.ACCEPTED),
    ]

    await _determine_and_update_order_status(order, samples, user, db)

    assert order.status == OrderStatus.COMPLETED
    db.add.assert_called_once()
    added = db.add.call_args[0][0]
    assert isinstance(added, OrderStatusHistory)
    assert added.status == OrderStatus.COMPLETED


@pytest.mark.asyncio
async def test_any_rejected_sets_sample_rejected():
    """Any sample REJECTED → order status = SAMPLE_REJECTED."""
    order = _fake_order()
    user = _fake_user()
    db = AsyncMock()
    samples = [
        _fake_sample(order.id, SampleStatus.ACCEPTED),
        _fake_sample(order.id, SampleStatus.REJECTED, "hemolyzed"),
    ]

    with patch(
        "app.api.v1.accessioning.notify_sample_rejection", new_callable=AsyncMock
    ) as mock_notify:
        await _determine_and_update_order_status(order, samples, user, db)

    assert order.status == OrderStatus.SAMPLE_REJECTED
    mock_notify.assert_awaited_once()


@pytest.mark.asyncio
async def test_hold_no_rejected_sets_sample_hold():
    """Any sample HOLD (none rejected) → order status = SAMPLE_HOLD."""
    order = _fake_order()
    user = _fake_user()
    db = AsyncMock()
    samples = [
        _fake_sample(order.id, SampleStatus.ACCEPTED),
        _fake_sample(order.id, SampleStatus.HOLD),
    ]

    with patch(
        "app.api.v1.accessioning.notify_sample_hold", new_callable=AsyncMock
    ) as mock_notify:
        await _determine_and_update_order_status(order, samples, user, db)

    assert order.status == OrderStatus.SAMPLE_HOLD
    mock_notify.assert_awaited_once()


@pytest.mark.asyncio
async def test_rejected_takes_priority_over_hold():
    """REJECTED takes priority over HOLD."""
    order = _fake_order()
    user = _fake_user()
    db = AsyncMock()
    samples = [
        _fake_sample(order.id, SampleStatus.HOLD),
        _fake_sample(order.id, SampleStatus.REJECTED, "leaked"),
    ]

    with patch(
        "app.api.v1.accessioning.notify_sample_rejection", new_callable=AsyncMock
    ):
        await _determine_and_update_order_status(order, samples, user, db)

    assert order.status == OrderStatus.SAMPLE_REJECTED


@pytest.mark.asyncio
async def test_no_change_when_status_same():
    """No history entry when status doesn't change."""
    order = _fake_order(status=OrderStatus.COMPLETED)
    user = _fake_user()
    db = AsyncMock()
    samples = [_fake_sample(order.id, SampleStatus.ACCEPTED)]

    await _determine_and_update_order_status(order, samples, user, db)

    db.add.assert_not_called()


# ── Notification stubs ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_notify_rejection_logs(caplog):
    """notify_sample_rejection logs the rejection info."""
    from app.services.notifications import notify_sample_rejection

    order = _fake_order()
    samples = [_fake_sample(order.id, SampleStatus.REJECTED, "hemolyzed")]

    with caplog.at_level("INFO"):
        await notify_sample_rejection(order, samples)

    assert "NOTIFICATION STUB" in caplog.text
    assert "rejection" in caplog.text.lower()


@pytest.mark.asyncio
async def test_notify_hold_logs(caplog):
    """notify_sample_hold logs the hold info."""
    from app.services.notifications import notify_sample_hold

    order = _fake_order()
    samples = [_fake_sample(order.id, SampleStatus.HOLD)]

    with caplog.at_level("INFO"):
        await notify_sample_hold(order, samples)

    assert "NOTIFICATION STUB" in caplog.text
    assert "hold" in caplog.text.lower()


# ── Valid transitions ────────────────────────────────────────────────────


def test_valid_transitions_include_new_statuses():
    """Ensure COLLECTED can transition to new statuses."""
    from app.api.v1.orders import _VALID_TRANSITIONS

    collected_targets = _VALID_TRANSITIONS[OrderStatus.COLLECTED]
    assert OrderStatus.COMPLETED in collected_targets
    assert OrderStatus.SAMPLE_REJECTED in collected_targets
    assert OrderStatus.SAMPLE_HOLD in collected_targets


def test_sample_hold_can_transition():
    """SAMPLE_HOLD can transition to COMPLETED or SAMPLE_REJECTED."""
    from app.api.v1.orders import _VALID_TRANSITIONS

    hold_targets = _VALID_TRANSITIONS[OrderStatus.SAMPLE_HOLD]
    assert OrderStatus.COMPLETED in hold_targets
    assert OrderStatus.SAMPLE_REJECTED in hold_targets
