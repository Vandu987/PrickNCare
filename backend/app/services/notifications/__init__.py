"""Notification service package."""

from .base import (
    BaseChannelSender,
    NotificationChannel,
    NotificationStatus,
    NotificationType,
)

# Preserve backward-compatible stubs from task 8.3
from .compat import notify_sample_hold, notify_sample_rejection
from .push import PushNotificationService
from .service import NotificationService
from .sms import SMSService


def create_notification_service(
    db=None,  # noqa: ANN001
) -> NotificationService:
    """Create a NotificationService with real channel senders registered."""
    svc = NotificationService(db=db)
    svc.register_sender(NotificationChannel.SMS, SMSService())
    return svc


__all__ = [
    "BaseChannelSender",
    "NotificationChannel",
    "NotificationService",
    "PushNotificationService",
    "NotificationStatus",
    "NotificationType",
    "SMSService",
    "create_notification_service",
    "notify_sample_hold",
    "notify_sample_rejection",
]
