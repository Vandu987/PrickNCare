"""Tests for notification service base architecture — task 10.1."""

from __future__ import annotations

import pytest

from app.services.notifications.base import (
    DEFAULT_CHANNEL_MAP,
    TEMPLATES,
    BaseChannelSender,
    NotificationChannel,
    NotificationStatus,
    NotificationType,
    StubSender,
)
from app.services.notifications.service import NotificationService


class TestEnums:
    def test_notification_types(self):
        assert len(NotificationType) == 8
        assert NotificationType.OTP.value == "otp"
        assert NotificationType.SAMPLE_REJECTED.value == "sample_rejected"

    def test_notification_channels(self):
        assert len(NotificationChannel) == 4
        expected = {"sms", "email", "push", "whatsapp"}
        assert {c.value for c in NotificationChannel} == expected

    def test_notification_status(self):
        assert len(NotificationStatus) == 4
        assert NotificationStatus.PENDING.value == "pending"


class TestDefaultChannelMap:
    def test_all_types_have_defaults(self):
        for nt in NotificationType:
            assert nt in DEFAULT_CHANNEL_MAP, f"{nt} missing from DEFAULT_CHANNEL_MAP"

    def test_otp_uses_sms(self):
        assert DEFAULT_CHANNEL_MAP[NotificationType.OTP] == [NotificationChannel.SMS]


class TestTemplates:
    def test_otp_sms_template_exists(self):
        key = (NotificationType.OTP, NotificationChannel.SMS)
        assert key in TEMPLATES
        assert "{otp}" in TEMPLATES[key]


class TestNotificationService:
    @pytest.fixture
    def service(self):
        return NotificationService(db=None)

    def test_get_template(self, service: NotificationService):
        tpl = service.get_template(NotificationType.OTP, NotificationChannel.SMS)
        assert tpl is not None
        assert "{otp}" in tpl

    def test_get_template_missing(self, service: NotificationService):
        tpl = service.get_template(NotificationType.OTP, NotificationChannel.EMAIL)
        assert tpl is None

    def test_render_template(self, service: NotificationService):
        rendered = service.render_template("Hello {name}", {"name": "World"})
        assert rendered == "Hello World"

    def test_render_template_missing_key(self, service: NotificationService):
        # Should not crash on missing keys
        tpl = "Hello {name}"
        rendered = service.render_template(tpl, {})
        assert rendered == tpl  # unchanged

    @pytest.mark.asyncio
    async def test_send_uses_default_channels(self, service: NotificationService):
        results = await service.send(
            notification_type=NotificationType.OTP,
            recipient="+919999999999",
            data={"otp": "1234", "validity_minutes": 5},
        )
        assert len(results) == 1
        assert results[0]["channel"] == NotificationChannel.SMS
        assert results[0]["status"] == NotificationStatus.SENT

    @pytest.mark.asyncio
    async def test_send_explicit_channels(self, service: NotificationService):
        results = await service.send(
            notification_type=NotificationType.ORDER_CREATED,
            recipient="test@example.com",
            data={"booking_id": "B001"},
            channels=[NotificationChannel.EMAIL],
        )
        assert len(results) == 1
        assert results[0]["channel"] == NotificationChannel.EMAIL

    @pytest.mark.asyncio
    async def test_send_multiple_channels(self, service: NotificationService):
        results = await service.send(
            notification_type=NotificationType.ORDER_CREATED,
            recipient="+919999999999",
            data={"booking_id": "B001"},
        )
        # ORDER_CREATED defaults to SMS + EMAIL
        assert len(results) == 2

    def test_register_sender(self, service: NotificationService):
        class FakeSender(BaseChannelSender):
            channel = NotificationChannel.SMS

            async def send(self, recipient, message, data=None):
                return True

        sender = FakeSender()
        service.register_sender(NotificationChannel.SMS, sender)
        assert service._senders[NotificationChannel.SMS] is sender


class TestStubSender:
    @pytest.mark.asyncio
    async def test_stub_returns_true(self):
        sender = StubSender(NotificationChannel.SMS)
        result = await sender.send("+919999999999", "test message")
        assert result is True


class TestBackwardCompat:
    """Ensure old imports still work."""

    def test_compat_imports(self):
        from app.services.notifications import (
            notify_sample_hold,
            notify_sample_rejection,
        )

        assert callable(notify_sample_rejection)
        assert callable(notify_sample_hold)
