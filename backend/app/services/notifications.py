"""Notification stubs for order status changes (task 8.3)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.orders import Order
    from app.models.samples import SampleAccessioning

logger = logging.getLogger(__name__)


async def notify_sample_rejection(
    order: Order, rejected_samples: list[SampleAccessioning]
) -> None:
    """Stub: notify client about rejected samples (email/SMS)."""
    sample_details = ", ".join(
        f"{s.vial_type} (reason: {s.rejection_reason})" for s in rejected_samples
    )
    logger.info(
        "NOTIFICATION STUB — Sample rejection for order %s (booking %s): %s. "
        "TODO: send email/SMS to client.",
        order.id,
        order.booking_id,
        sample_details,
    )


async def notify_sample_hold(
    order: Order, held_samples: list[SampleAccessioning]
) -> None:
    """Stub: notify client about samples on hold (email/SMS)."""
    sample_details = ", ".join(f"{s.vial_type}" for s in held_samples)
    logger.info(
        "NOTIFICATION STUB — Sample hold for order %s (booking %s): %s. "
        "TODO: send email/SMS to client.",
        order.id,
        order.booking_id,
        sample_details,
    )
