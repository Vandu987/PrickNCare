"""Notification service package."""

from .base import (
    BaseChannelSender,
    NotificationChannel,
    NotificationStatus,
    NotificationType,
)

# Preserve backward-compatible stubs from task 8.3
from .compat import notify_sample_hold, notify_sample_rejection
from .service import NotificationService

__all__ = [
    "BaseChannelSender",
    "NotificationChannel",
    "NotificationService",
    "NotificationStatus",
    "NotificationType",
    "notify_sample_hold",
    "notify_sample_rejection",
]
