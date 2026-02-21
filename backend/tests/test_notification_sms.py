"""Tests for SMS service — provider abstraction, retry logic, failure handling."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.services.notifications.sms import SMSService, _TransientSMSError


@pytest.fixture
def msg91_svc():
    return SMSService(provider="msg91")


@pytest.fixture
def twilio_svc():
    return SMSService(provider="twilio")


# ---------------------------------------------------------------------------
# Provider switching
# ---------------------------------------------------------------------------


class TestProviderSwitching:
    async def test_unknown_provider_returns_false(self):
        svc = SMSService(provider="unknown")
        assert await svc.send("+91999", "hi") is False

    async def test_defaults_to_settings_provider(self):
        with patch("app.services.notifications.sms.settings") as mock_settings:
            mock_settings.SMS_PROVIDER = "twilio"
            svc = SMSService()
            assert svc.provider == "twilio"


# ---------------------------------------------------------------------------
# MSG91 provider
# ---------------------------------------------------------------------------


class TestMSG91:
    async def test_send_success(self, msg91_svc: SMSService):
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = lambda: None

        with (
            patch("app.services.notifications.sms.settings") as s,
            patch("httpx.AsyncClient.post", return_value=mock_resp),
        ):
            s.SMS_API_KEY = "test-key"
            s.MSG91_SENDER_ID = "PRKNCA"
            s.MSG91_ROUTE = 4
            result = await msg91_svc.send("+919999999999", "Test SMS")

        assert result is True

    async def test_missing_api_key(self, msg91_svc: SMSService):
        with patch("app.services.notifications.sms.settings") as s:
            s.SMS_API_KEY = ""
            result = await msg91_svc.send("+919999999999", "Test")

        assert result is False


# ---------------------------------------------------------------------------
# Twilio provider
# ---------------------------------------------------------------------------


class TestTwilio:
    async def test_send_success(self, twilio_svc: SMSService):
        mock_resp = AsyncMock()
        mock_resp.status_code = 201
        mock_resp.raise_for_status = lambda: None

        with (
            patch("app.services.notifications.sms.settings") as s,
            patch("httpx.AsyncClient.post", return_value=mock_resp),
        ):
            s.TWILIO_ACCOUNT_SID = "AC_test"
            s.TWILIO_AUTH_TOKEN = "token"
            s.TWILIO_FROM_NUMBER = "+1234567890"
            result = await twilio_svc.send("+919999999999", "Test SMS")

        assert result is True

    async def test_missing_credentials(self, twilio_svc: SMSService):
        with patch("app.services.notifications.sms.settings") as s:
            s.TWILIO_ACCOUNT_SID = ""
            s.TWILIO_AUTH_TOKEN = ""
            s.TWILIO_FROM_NUMBER = ""
            result = await twilio_svc.send("+919999999999", "Test")

        assert result is False


# ---------------------------------------------------------------------------
# Retry logic
# ---------------------------------------------------------------------------


class TestRetryLogic:
    async def test_retries_on_transient_error_then_succeeds(
        self, msg91_svc: SMSService
    ):
        call_count = 0

        async def flaky_send(phone, message):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise _TransientSMSError("503")
            return True

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await SMSService._send_with_retry(flaky_send, "+91", "hi")

        assert result is True
        assert call_count == 3

    async def test_fails_after_max_retries(self, msg91_svc: SMSService):
        async def always_fail(phone, message):
            raise _TransientSMSError("503")

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await SMSService._send_with_retry(always_fail, "+91", "hi")

        assert result is False

    async def test_no_retry_on_non_transient_error(self):
        call_count = 0

        async def client_error(phone, message):
            nonlocal call_count
            call_count += 1
            resp = httpx.Response(400, request=httpx.Request("POST", "http://x"))
            raise httpx.HTTPStatusError("bad", request=resp.request, response=resp)

        result = await SMSService._send_with_retry(client_error, "+91", "hi")
        assert result is False
        assert call_count == 1

    async def test_retries_on_network_error(self):
        call_count = 0

        async def network_flake(phone, message):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.ConnectError("connection refused")
            return True

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await SMSService._send_with_retry(network_flake, "+91", "hi")

        assert result is True
        assert call_count == 2


# ---------------------------------------------------------------------------
# Integration with NotificationService
# ---------------------------------------------------------------------------


class TestRegistration:
    async def test_create_notification_service_has_sms_sender(self):
        from app.services.notifications import (
            NotificationChannel,
            create_notification_service,
        )

        svc = create_notification_service()
        sender = svc._senders[NotificationChannel.SMS]
        assert isinstance(sender, SMSService)
