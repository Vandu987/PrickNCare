"""Tests for JWT auth, password hashing, token blacklist — task 3.3."""

import time
from unittest.mock import AsyncMock, patch

import pytest
from jose import jwt

from app.core.config import settings
from app.core.security import (
    blacklist_token,
    clear_session,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    hash_password,
    is_session_expired,
    is_token_blacklisted,
    revoke_refresh_token,
    update_last_activity,
    validate_access_token,
    verify_password,
    verify_refresh_token,
)

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------


class TestPasswordHashing:
    def test_hash_returns_string(self) -> None:
        h = hash_password("secret")
        assert isinstance(h, str)

    def test_hash_is_not_plaintext(self) -> None:
        assert hash_password("secret") != "secret"

    def test_verify_correct_password(self) -> None:
        h = hash_password("mysecret")
        assert verify_password("mysecret", h) is True

    def test_verify_wrong_password(self) -> None:
        h = hash_password("mysecret")
        assert verify_password("wrong", h) is False

    def test_two_hashes_of_same_password_differ(self) -> None:
        assert hash_password("abc") != hash_password("abc")


# ---------------------------------------------------------------------------
# Access token creation / decoding
# ---------------------------------------------------------------------------


class TestAccessToken:
    def test_create_returns_token_and_jti(self) -> None:
        token, jti = create_access_token("user-1", "client")
        assert isinstance(token, str) and len(token) > 10
        assert isinstance(jti, str) and len(jti) == 36  # UUID

    def test_jti_unique_per_call(self) -> None:
        _, jti1 = create_access_token("u", "client")
        _, jti2 = create_access_token("u", "client")
        assert jti1 != jti2

    def test_decode_returns_payload(self) -> None:
        token, jti = create_access_token("user-42", "super_admin")
        payload = decode_access_token(token)
        assert payload["sub"] == "user-42"
        assert payload["role"] == "super_admin"
        assert payload["jti"] == jti

    def test_payload_has_exp_and_iat(self) -> None:
        token, _ = create_access_token("u", "client")
        payload = decode_access_token(token)
        assert "exp" in payload
        assert "iat" in payload

    def test_exp_is_in_future(self) -> None:
        token, _ = create_access_token("u", "client")
        payload = decode_access_token(token)
        assert payload["exp"] > time.time()

    def test_decode_rejects_tampered_token(self) -> None:
        from jose import JWTError

        token, _ = create_access_token("u", "client")
        tampered = token[:-4] + "xxxx"
        with pytest.raises(JWTError):
            decode_access_token(tampered)

    def test_decode_rejects_wrong_secret(self) -> None:
        from jose import JWTError

        payload = {"sub": "u", "role": "client"}
        bad_token = jwt.encode(payload, "wrong-secret", algorithm="HS256")
        with pytest.raises(JWTError):
            decode_access_token(bad_token)

    def test_algorithm_matches_settings(self) -> None:
        token, _ = create_access_token("u", "client")
        header = jwt.get_unverified_header(token)
        assert header["alg"] == settings.JWT_ALGORITHM


# ---------------------------------------------------------------------------
# Refresh token (Redis-backed)
# ---------------------------------------------------------------------------


class TestRefreshToken:
    @pytest.mark.asyncio
    async def test_create_returns_token_string(self) -> None:
        with patch("app.core.security.redis_set", new_callable=AsyncMock):
            token = await create_refresh_token("user-1", "jti-1")
        assert isinstance(token, str) and len(token) > 20

    @pytest.mark.asyncio
    async def test_create_stores_in_redis(self) -> None:
        mock_set = AsyncMock()
        with patch("app.core.security.redis_set", mock_set):
            await create_refresh_token("user-1", "jti-1")
        mock_set.assert_awaited_once()
        key = mock_set.call_args[0][0]
        assert "user-1" in key and "jti-1" in key

    @pytest.mark.asyncio
    async def test_verify_returns_true_for_correct_token(self) -> None:
        stored = "valid-token-value"
        with patch(
            "app.core.security.redis_get", new_callable=AsyncMock, return_value=stored
        ):
            result = await verify_refresh_token("u", "j", stored)
        assert result is True

    @pytest.mark.asyncio
    async def test_verify_returns_false_for_wrong_token(self) -> None:
        with patch(
            "app.core.security.redis_get",
            new_callable=AsyncMock,
            return_value="real-token",
        ):
            result = await verify_refresh_token("u", "j", "fake-token")
        assert result is False

    @pytest.mark.asyncio
    async def test_verify_returns_false_when_not_in_redis(self) -> None:
        with patch(
            "app.core.security.redis_get", new_callable=AsyncMock, return_value=None
        ):
            result = await verify_refresh_token("u", "j", "any-token")
        assert result is False

    @pytest.mark.asyncio
    async def test_revoke_deletes_from_redis(self) -> None:
        mock_del = AsyncMock()
        with patch("app.core.security.redis_delete", mock_del):
            await revoke_refresh_token("user-1", "jti-1")
        mock_del.assert_awaited_once()
        assert "user-1" in mock_del.call_args[0][0]


# ---------------------------------------------------------------------------
# Token blacklisting
# ---------------------------------------------------------------------------


class TestTokenBlacklist:
    @pytest.mark.asyncio
    async def test_blacklist_stores_jti(self) -> None:
        mock_set = AsyncMock()
        with patch("app.core.security.redis_set", mock_set):
            await blacklist_token("some-jti")
        mock_set.assert_awaited_once()
        key = mock_set.call_args[0][0]
        assert "some-jti" in key

    @pytest.mark.asyncio
    async def test_is_blacklisted_true_when_present(self) -> None:
        with patch(
            "app.core.security.redis_exists", new_callable=AsyncMock, return_value=True
        ):
            assert await is_token_blacklisted("jti") is True

    @pytest.mark.asyncio
    async def test_is_blacklisted_false_when_absent(self) -> None:
        with patch(
            "app.core.security.redis_exists", new_callable=AsyncMock, return_value=False
        ):
            assert await is_token_blacklisted("jti") is False


# ---------------------------------------------------------------------------
# Session timeout
# ---------------------------------------------------------------------------


class TestSessionTimeout:
    @pytest.mark.asyncio
    async def test_update_activity_sets_key(self) -> None:
        mock_set = AsyncMock()
        with patch("app.core.security.redis_set", mock_set):
            await update_last_activity("user-1")
        mock_set.assert_awaited_once()
        key = mock_set.call_args[0][0]
        assert "user-1" in key

    @pytest.mark.asyncio
    async def test_session_expired_when_key_missing(self) -> None:
        with patch(
            "app.core.security.redis_exists", new_callable=AsyncMock, return_value=False
        ):
            assert await is_session_expired("user-1") is True

    @pytest.mark.asyncio
    async def test_session_active_when_key_present(self) -> None:
        with patch(
            "app.core.security.redis_exists", new_callable=AsyncMock, return_value=True
        ):
            assert await is_session_expired("user-1") is False

    @pytest.mark.asyncio
    async def test_clear_session_deletes_key(self) -> None:
        mock_del = AsyncMock()
        with patch("app.core.security.redis_delete", mock_del):
            await clear_session("user-1")
        mock_del.assert_awaited_once()
        assert "user-1" in mock_del.call_args[0][0]


# ---------------------------------------------------------------------------
# validate_access_token (full pipeline)
# ---------------------------------------------------------------------------


class TestValidateAccessToken:
    @pytest.mark.asyncio
    async def test_valid_token_returns_payload(self) -> None:
        token, jti = create_access_token("user-1", "client")
        with (
            patch(
                "app.core.security.is_token_blacklisted",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch(
                "app.core.security.is_session_expired",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch("app.core.security.update_last_activity", new_callable=AsyncMock),
        ):
            payload = await validate_access_token(token)
        assert payload["sub"] == "user-1"

    @pytest.mark.asyncio
    async def test_blacklisted_token_raises(self) -> None:
        from jose import JWTError

        token, _ = create_access_token("user-1", "client")
        with patch(
            "app.core.security.is_token_blacklisted",
            new_callable=AsyncMock,
            return_value=True,
        ):
            with pytest.raises(JWTError):
                await validate_access_token(token)

    @pytest.mark.asyncio
    async def test_expired_session_raises(self) -> None:
        from jose import JWTError

        token, _ = create_access_token("user-1", "client")
        with (
            patch(
                "app.core.security.is_token_blacklisted",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch(
                "app.core.security.is_session_expired",
                new_callable=AsyncMock,
                return_value=True,
            ),
        ):
            with pytest.raises(JWTError):
                await validate_access_token(token)

    @pytest.mark.asyncio
    async def test_invalid_signature_raises(self) -> None:
        from jose import JWTError

        bad = jwt.encode({"sub": "u"}, "wrong", algorithm="HS256")
        with pytest.raises(JWTError):
            await validate_access_token(bad)
