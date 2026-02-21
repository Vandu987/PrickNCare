"""Base notification types, channels, and abstract classes."""

from __future__ import annotations

import enum
from abc import ABC, abstractmethod
from typing import Any


class NotificationType(enum.StrEnum):
    OTP = "otp"
    ORDER_CREATED = "order_created"
    ORDER_ASSIGNED = "order_assigned"
    ORDER_ACCEPTED = "order_accepted"
    PHLEBO_ON_WAY = "phlebo_on_way"
    ORDER_COMPLETED = "order_completed"
    SAMPLE_REJECTED = "sample_rejected"
    PAYMENT_RECEIVED = "payment_received"


class NotificationChannel(enum.StrEnum):
    SMS = "sms"
    EMAIL = "email"
    PUSH = "push"
    WHATSAPP = "whatsapp"


class NotificationStatus(enum.StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    DELIVERED = "delivered"


# Default channels per notification type
DEFAULT_CHANNEL_MAP: dict[NotificationType, list[NotificationChannel]] = {
    NotificationType.OTP: [NotificationChannel.SMS],
    NotificationType.ORDER_CREATED: [
        NotificationChannel.SMS,
        NotificationChannel.EMAIL,
    ],
    NotificationType.ORDER_ASSIGNED: [NotificationChannel.PUSH],
    NotificationType.ORDER_ACCEPTED: [
        NotificationChannel.SMS,
        NotificationChannel.PUSH,
    ],
    NotificationType.PHLEBO_ON_WAY: [
        NotificationChannel.SMS,
        NotificationChannel.PUSH,
    ],
    NotificationType.ORDER_COMPLETED: [
        NotificationChannel.SMS,
        NotificationChannel.EMAIL,
    ],
    NotificationType.SAMPLE_REJECTED: [
        NotificationChannel.SMS,
        NotificationChannel.EMAIL,
    ],
    NotificationType.PAYMENT_RECEIVED: [
        NotificationChannel.SMS,
        NotificationChannel.EMAIL,
    ],
}


# Stub templates
TEMPLATES: dict[tuple[NotificationType, NotificationChannel], str] = {
    (
        NotificationType.OTP,
        NotificationChannel.SMS,
    ): "Your OTP is {otp}. Valid for {validity_minutes} minutes.",
    (
        NotificationType.ORDER_CREATED,
        NotificationChannel.SMS,
    ): "Order {booking_id} created successfully.",
    (
        NotificationType.ORDER_CREATED,
        NotificationChannel.EMAIL,
    ): "Your order {booking_id} has been placed.",
    (
        NotificationType.ORDER_ASSIGNED,
        NotificationChannel.PUSH,
    ): "Order {booking_id} assigned to you.",
    (
        NotificationType.ORDER_ACCEPTED,
        NotificationChannel.SMS,
    ): "Your order {booking_id} has been accepted by phlebotomist.",
    (
        NotificationType.ORDER_ACCEPTED,
        NotificationChannel.PUSH,
    ): "You accepted order {booking_id}.",
    (
        NotificationType.PHLEBO_ON_WAY,
        NotificationChannel.SMS,
    ): "Phlebotomist is on the way for order {booking_id}.",
    (
        NotificationType.PHLEBO_ON_WAY,
        NotificationChannel.PUSH,
    ): "Navigate to patient for order {booking_id}.",
    (
        NotificationType.ORDER_COMPLETED,
        NotificationChannel.SMS,
    ): "Order {booking_id} completed. Thank you!",
    (
        NotificationType.ORDER_COMPLETED,
        NotificationChannel.EMAIL,
    ): "Your order {booking_id} has been completed.",
    (
        NotificationType.SAMPLE_REJECTED,
        NotificationChannel.SMS,
    ): "Sample rejected for order {booking_id}: {reason}.",
    (
        NotificationType.SAMPLE_REJECTED,
        NotificationChannel.EMAIL,
    ): "Sample rejected for order {booking_id}: {reason}.",
    (
        NotificationType.PAYMENT_RECEIVED,
        NotificationChannel.SMS,
    ): "Payment of {amount} received for order {booking_id}.",
    (
        NotificationType.PAYMENT_RECEIVED,
        NotificationChannel.EMAIL,
    ): "Payment of {amount} received for order {booking_id}.",
}


class BaseChannelSender(ABC):
    """Abstract base class for channel-specific senders."""

    channel: NotificationChannel

    @abstractmethod
    async def send(
        self,
        recipient: str,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> bool:
        """Send notification. Returns True on success."""
        ...


class StubSender(BaseChannelSender):
    """Stub sender that logs but doesn't actually send."""

    def __init__(self, channel: NotificationChannel) -> None:
        self.channel = channel

    async def send(
        self,
        recipient: str,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> bool:
        import logging

        logger = logging.getLogger(__name__)
        logger.info(
            "STUB [%s] -> %s: %s",
            self.channel.value,
            recipient,
            message[:100],
        )
        return True
