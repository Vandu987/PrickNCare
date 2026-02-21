"""Main NotificationService — dispatches notifications to channel senders."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from .base import (
    DEFAULT_CHANNEL_MAP,
    TEMPLATES,
    BaseChannelSender,
    NotificationChannel,
    NotificationStatus,
    NotificationType,
    StubSender,
)

logger = logging.getLogger(__name__)


class NotificationService:
    """Orchestrates sending notifications across channels and logging results."""

    def __init__(self, db: AsyncSession | None = None) -> None:
        self.db = db
        # Channel senders — stubs by default; real implementations registered later
        self._senders: dict[NotificationChannel, BaseChannelSender] = {
            ch: StubSender(ch) for ch in NotificationChannel
        }

    def register_sender(
        self, channel: NotificationChannel, sender: BaseChannelSender
    ) -> None:
        """Register a real sender for a channel (replaces stub)."""
        self._senders[channel] = sender

    @staticmethod
    def get_template(
        notification_type: NotificationType,
        channel: NotificationChannel,
    ) -> str | None:
        """Look up message template for a notification type + channel."""
        return TEMPLATES.get((notification_type, channel))

    @staticmethod
    def render_template(template: str, data: dict[str, Any]) -> str:
        """Render a template string with data, ignoring missing keys."""
        try:
            return template.format_map({**data})
        except KeyError:
            return template

    async def send(
        self,
        notification_type: NotificationType,
        recipient: str,
        data: dict[str, Any] | None = None,
        channels: list[NotificationChannel] | None = None,
        recipient_id: uuid.UUID | None = None,
    ) -> list[dict[str, Any]]:
        """Send notification across specified (or default) channels.

        Returns a list of result dicts per channel attempted.
        """
        data = data or {}
        channels = channels or DEFAULT_CHANNEL_MAP.get(notification_type, [])
        results: list[dict[str, Any]] = []

        for channel in channels:
            template = self.get_template(notification_type, channel)
            message = self.render_template(template, data) if template else str(data)

            sender = self._senders.get(channel)
            success = False
            error_message = None

            if sender is None:
                error_message = f"No sender registered for {channel.value}"
                logger.warning(error_message)
            else:
                try:
                    success = await sender.send(recipient, message, data)
                except Exception as exc:
                    error_message = str(exc)
                    logger.exception(
                        "Failed to send %s via %s to %s",
                        notification_type.value,
                        channel.value,
                        recipient,
                    )

            status = NotificationStatus.SENT if success else NotificationStatus.FAILED

            # Log to DB if session available
            if self.db is not None:
                await self._log(
                    notification_type=notification_type,
                    channel=channel,
                    recipient_id=recipient_id,
                    recipient_contact=recipient,
                    status=status,
                    message_content=message,
                    error_message=error_message,
                )

            results.append(
                {
                    "channel": channel,
                    "status": status,
                    "message": message,
                    "error": error_message,
                }
            )

        return results

    async def _log(
        self,
        *,
        notification_type: NotificationType,
        channel: NotificationChannel,
        recipient_id: uuid.UUID | None,
        recipient_contact: str,
        status: NotificationStatus,
        message_content: str,
        error_message: str | None,
    ) -> None:
        """Persist a NotificationLog row."""
        from app.models.notifications import NotificationLog

        is_email = "@" in recipient_contact
        log = NotificationLog(
            notification_type=notification_type,
            channel=channel,
            recipient_id=recipient_id,
            recipient_email=recipient_contact if is_email else None,
            recipient_phone=recipient_contact if not is_email else None,
            status=status,
            message_content=message_content,
            error_message=error_message,
            sent_at=(datetime.now(UTC) if status == NotificationStatus.SENT else None),
        )
        self.db.add(log)  # type: ignore[union-attr]
        try:
            await self.db.flush()  # type: ignore[union-attr]
        except Exception:
            logger.exception("Failed to log notification")
