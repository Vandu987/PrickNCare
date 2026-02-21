"""Tests for OTP generation, storage, verification and SMS gateway — task 3.4."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.security import (
    check_otp_rate_limit,
    generate_otp,
    increment_otp_rate_limit,
    store_otp,
    verify_otp,
)
from app.core.sms_gateway import MSG91Provider, TwilioProvider, get_sms_provider

# ---------------------------------------------------------------------------
# generate_otp
# ---------------------------------------------------------------------------


class TestGenerateOtp:
    def test_returns_string(self) -> None:
        assert isinstance(generate_otp(), str)

    def test_length_is_six(self) -> None:
        assert len(generate_otp()) == 6

    def test_all_digits(self) -> None:
        assert generate_otp().isdigit()

    def test_zero_padded(self) -> None:
        # 1_000_000 attempts — statistically at least one will start < 100000
        results = {generate_otp() for _ in range(500)}
        assert all(len(r) == 6 for r in results)

    def test_uniqueness(self) -> None:
        otps = [generate_otp() for _ in range(20)]
        # Not all identical (astronomically unlikely)
        assert len(set(otps)) > 1


# ---------------------------------------------------------------------------
# store_otp
# ---------------------------------------------------------------------------


class TestStoreOtp:
    @pytest.mark.asyncio
    async def test_stores_otp_and_resets_attempts(self) -> None:
        calls: list = []
        mock_set = AsyncMock(side_effect=lambda *a, **kw: calls.append((a, kw)))

        with patch("app.core.security.redis_set", mock_set):
            await store_otp("+919876543210", "123456")

        assert mock_set.await_count == 2
        keys = [c[0][0] for c in calls]
        assert any("otp:+919876543210" == k for k in keys)
        assert any("otp_attempts:+919876543210" == k for k in keys)

    @pytest.mark.asyncio
    async def test_otp_stored_with_ttl(self) -> None:
        mock_set = AsyncMock()
        with patch("app.core.security.redis_set", mock_set):
            await store_otp("+91123", "000000")

        # First call should carry ex= TTL
        first_call_kwargs = mock_set.call_args_list[0][1]
        assert first_call_kwargs.get("ex") is not None
        assert first_call_kwargs["ex"] > 0


# ---------------------------------------------------------------------------
# verify_otp
# ---------------------------------------------------------------------------


class TestVerifyOtp:
    @pytest.mark.asyncio
    async def test_correct_otp_returns_true(self) -> None:
        with (
            patch("app.core.security.redis_get", new_callable=AsyncMock) as mock_get,
            patch("app.core.security.redis_set", new_callable=AsyncMock),
            patch("app.core.security.redis_delete", new_callable=AsyncMock),
        ):
            mock_get.side_effect = ["123456", "0"]  # stored OTP, attempts
            result = await verify_otp("+91123", "123456")
        assert result is True

    @pytest.mark.asyncio
    async def test_wrong_otp_returns_false(self) -> None:
        with (
            patch("app.core.security.redis_get", new_callable=AsyncMock) as mock_get,
            patch("app.core.security.redis_set", new_callable=AsyncMock),
        ):
            mock_get.side_effect = ["123456", "0"]
            result = await verify_otp("+91123", "000000")
        assert result is False

    @pytest.mark.asyncio
    async def test_expired_otp_returns_false(self) -> None:
        with patch(
            "app.core.security.redis_get", new_callable=AsyncMock, return_value=None
        ):
            result = await verify_otp("+91123", "123456")
        assert result is False

    @pytest.mark.asyncio
    async def test_correct_otp_deletes_from_redis(self) -> None:
        mock_del = AsyncMock()
        with (
            patch("app.core.security.redis_get", new_callable=AsyncMock) as mock_get,
            patch("app.core.security.redis_set", new_callable=AsyncMock),
            patch("app.core.security.redis_delete", mock_del),
        ):
            mock_get.side_effect = ["654321", "0"]
            await verify_otp("+91123", "654321")
        assert mock_del.await_count >= 1

    @pytest.mark.asyncio
    async def test_max_attempts_burns_otp(self) -> None:
        """On the max attempt, OTP is deleted whether correct or not."""
        from app.core.config import settings

        mock_del = AsyncMock()
        with (
            patch("app.core.security.redis_get", new_callable=AsyncMock) as mock_get,
            patch("app.core.security.redis_set", new_callable=AsyncMock),
            patch("app.core.security.redis_delete", mock_del),
        ):
            # attempts already at max - 1, so this call triggers burn
            mock_get.side_effect = [
                "999999",
                str(settings.OTP_MAX_ATTEMPTS - 1),
            ]
            await verify_otp("+91123", "000000")  # wrong OTP
        assert mock_del.await_count >= 1

    @pytest.mark.asyncio
    async def test_correct_on_last_attempt_returns_true(self) -> None:
        from app.core.config import settings

        with (
            patch("app.core.security.redis_get", new_callable=AsyncMock) as mock_get,
            patch("app.core.security.redis_set", new_callable=AsyncMock),
            patch("app.core.security.redis_delete", new_callable=AsyncMock),
        ):
            mock_get.side_effect = [
                "777777",
                str(settings.OTP_MAX_ATTEMPTS - 1),
            ]
            result = await verify_otp("+91123", "777777")
        assert result is True


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------


class TestOtpRateLimit:
    @pytest.mark.asyncio
    async def test_allowed_when_no_prior_requests(self) -> None:
        with patch(
            "app.core.security.redis_get", new_callable=AsyncMock, return_value=None
        ):
            assert await check_otp_rate_limit("+91123") is True

    @pytest.mark.asyncio
    async def test_allowed_below_limit(self) -> None:
        from app.core.config import settings

        count = str(settings.OTP_RATE_LIMIT_PER_HOUR - 1)
        with patch(
            "app.core.security.redis_get", new_callable=AsyncMock, return_value=count
        ):
            assert await check_otp_rate_limit("+91123") is True

    @pytest.mark.asyncio
    async def test_blocked_at_limit(self) -> None:
        from app.core.config import settings

        count = str(settings.OTP_RATE_LIMIT_PER_HOUR)
        with patch(
            "app.core.security.redis_get", new_callable=AsyncMock, return_value=count
        ):
            assert await check_otp_rate_limit("+91123") is False

    @pytest.mark.asyncio
    async def test_increment_sets_key(self) -> None:
        mock_set = AsyncMock()
        with (
            patch(
                "app.core.security.redis_exists",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch(
                "app.core.security.redis_get", new_callable=AsyncMock, return_value=None
            ),
            patch("app.core.security.redis_set", mock_set),
        ):
            await increment_otp_rate_limit("+91123")
        mock_set.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_increment_sets_ttl_on_first_hit(self) -> None:
        mock_set = AsyncMock()
        with (
            patch(
                "app.core.security.redis_exists",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch(
                "app.core.security.redis_get", new_callable=AsyncMock, return_value=None
            ),
            patch("app.core.security.redis_set", mock_set),
        ):
            await increment_otp_rate_limit("+91123")
        kwargs = mock_set.call_args[1]
        assert kwargs.get("ex") == 3600


# ---------------------------------------------------------------------------
# SMS gateway factory
# ---------------------------------------------------------------------------


class TestSmsGatewayFactory:
    def test_default_is_msg91(self) -> None:
        with patch("app.core.sms_gateway.settings") as mock_settings:
            mock_settings.SMS_PROVIDER = "msg91"
            provider = get_sms_provider()
        assert isinstance(provider, MSG91Provider)

    def test_twilio_selected(self) -> None:
        with patch("app.core.sms_gateway.settings") as mock_settings:
            mock_settings.SMS_PROVIDER = "twilio"
            provider = get_sms_provider()
        assert isinstance(provider, TwilioProvider)

    def test_unknown_provider_falls_back_to_msg91(self) -> None:
        with patch("app.core.sms_gateway.settings") as mock_settings:
            mock_settings.SMS_PROVIDER = "unknown"
            provider = get_sms_provider()
        assert isinstance(provider, MSG91Provider)


# ---------------------------------------------------------------------------
# SMS provider send_otp (mocked HTTP)
# ---------------------------------------------------------------------------


class TestMsg91Provider:
    @pytest.mark.asyncio
    async def test_send_otp_returns_true_on_success(self) -> None:
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"type": "success"}

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("app.core.sms_gateway.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await MSG91Provider().send_otp("+919876543210", "123456")

        assert result is True

    @pytest.mark.asyncio
    async def test_send_otp_returns_false_on_failure(self) -> None:
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"type": "error", "message": "Bad key"}

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("app.core.sms_gateway.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await MSG91Provider().send_otp("+919876543210", "123456")

        assert result is False

    @pytest.mark.asyncio
    async def test_send_otp_returns_false_on_exception(self) -> None:
        with patch("app.core.sms_gateway.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(
                side_effect=Exception("network error")
            )
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await MSG91Provider().send_otp("+91123", "000000")

        assert result is False


class TestTwilioProvider:
    @pytest.mark.asyncio
    async def test_send_otp_returns_true_on_success(self) -> None:
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"status": "queued"}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)

        with (
            patch("app.core.sms_gateway.httpx.AsyncClient") as mock_cls,
            patch("app.core.sms_gateway.settings") as mock_settings,
        ):
            mock_settings.TWILIO_ACCOUNT_SID = "ACtest"
            mock_settings.TWILIO_AUTH_TOKEN = "token"
            mock_settings.TWILIO_FROM_NUMBER = "+15005550006"
            mock_settings.OTP_EXPIRE_MINUTES = 5
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await TwilioProvider().send_otp("+919876543210", "654321")

        assert result is True

    @pytest.mark.asyncio
    async def test_send_otp_returns_false_on_failed_status(self) -> None:
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"status": "failed"}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)

        with (
            patch("app.core.sms_gateway.httpx.AsyncClient") as mock_cls,
            patch("app.core.sms_gateway.settings") as mock_settings,
        ):
            mock_settings.TWILIO_ACCOUNT_SID = "ACtest"
            mock_settings.TWILIO_AUTH_TOKEN = "token"
            mock_settings.TWILIO_FROM_NUMBER = "+15005550006"
            mock_settings.OTP_EXPIRE_MINUTES = 5
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await TwilioProvider().send_otp("+919876543210", "654321")

        assert result is False
