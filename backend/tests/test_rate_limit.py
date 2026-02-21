"""Tests for Redis-based rate limiting middleware — task 3.6."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middleware.rate_limit import (
    _ENDPOINT_LIMITS,
    RateLimitMiddleware,
    _sliding_window_check,
    add_endpoint_limit,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app(whitelist: frozenset[str] | None = None) -> FastAPI:
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, whitelist=whitelist or frozenset())

    @app.get("/test")
    async def _endpoint() -> dict:
        return {"ok": True}

    @app.get("/api/v1/auth/login")
    async def _login() -> dict:
        return {"ok": True}

    return app


def _make_allowed_result(remaining: int = 5, reset_ts: int | None = None) -> list:
    return [1, remaining, reset_ts or int(time.time()) + 60]


def _make_denied_result(reset_ts: int | None = None) -> list:
    return [0, 0, reset_ts or int(time.time()) + 10]


# ---------------------------------------------------------------------------
# _sliding_window_check (unit)
# ---------------------------------------------------------------------------


class TestSlidingWindowCheck:
    @pytest.mark.asyncio
    async def test_allowed_returns_true(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.eval = AsyncMock(return_value=[1, 9, int(time.time()) + 60])

        with patch("app.middleware.rate_limit.get_redis", return_value=mock_redis):
            allowed, remaining, reset_ts = await _sliding_window_check(
                "test_key", 10, 60
            )

        assert allowed is True
        assert remaining == 9
        assert reset_ts > 0

    @pytest.mark.asyncio
    async def test_denied_returns_false(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.eval = AsyncMock(return_value=[0, 0, int(time.time()) + 45])

        with patch("app.middleware.rate_limit.get_redis", return_value=mock_redis):
            allowed, remaining, reset_ts = await _sliding_window_check(
                "test_key", 10, 60
            )

        assert allowed is False
        assert remaining == 0

    @pytest.mark.asyncio
    async def test_passes_correct_args_to_redis(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.eval = AsyncMock(return_value=[1, 5, int(time.time()) + 60])

        with patch("app.middleware.rate_limit.get_redis", return_value=mock_redis):
            await _sliding_window_check("my_key", 100, 120)

        call_args = mock_redis.eval.call_args
        # KEYS[1] should be "rl:my_key"
        assert call_args.args[2] == "rl:my_key"
        # window in ARGV[3]
        assert call_args.args[5] == "120"
        # max_requests in ARGV[4]
        assert call_args.args[6] == "100"


# ---------------------------------------------------------------------------
# RateLimitMiddleware — whitelist bypass
# ---------------------------------------------------------------------------


class TestWhitelistBypass:
    def test_whitelisted_ip_bypasses_limit(self) -> None:
        app = _make_app(whitelist=frozenset({"10.0.0.1"}))
        client = TestClient(app, headers={"X-Forwarded-For": "10.0.0.1"})

        # No Redis mock needed — middleware should short-circuit before any check.
        with patch(
            "app.middleware.rate_limit._sliding_window_check",
            new_callable=AsyncMock,
        ) as mock_check:
            resp = client.get("/test")

        assert resp.status_code == 200
        mock_check.assert_not_called()

    def test_non_whitelisted_ip_is_checked(self) -> None:
        app = _make_app(whitelist=frozenset({"10.0.0.1"}))
        client = TestClient(app, headers={"X-Forwarded-For": "192.168.1.1"})

        with patch(
            "app.middleware.rate_limit._sliding_window_check",
            new_callable=AsyncMock,
            return_value=(True, 99, int(time.time()) + 60),
        ) as mock_check:
            resp = client.get("/test")

        assert resp.status_code == 200
        mock_check.assert_called_once()


# ---------------------------------------------------------------------------
# RateLimitMiddleware — 429 response
# ---------------------------------------------------------------------------


class TestRateLimitBlocking:
    def test_blocked_request_returns_429(self) -> None:
        app = _make_app()
        client = TestClient(app, headers={"X-Forwarded-For": "5.5.5.5"})

        with patch(
            "app.middleware.rate_limit._sliding_window_check",
            new_callable=AsyncMock,
            return_value=(False, 0, int(time.time()) + 30),
        ):
            resp = client.get("/test")

        assert resp.status_code == 429

    def test_blocked_response_has_retry_after_header(self) -> None:
        reset_ts = int(time.time()) + 42
        app = _make_app()
        client = TestClient(app, headers={"X-Forwarded-For": "5.5.5.5"})

        with patch(
            "app.middleware.rate_limit._sliding_window_check",
            new_callable=AsyncMock,
            return_value=(False, 0, reset_ts),
        ):
            resp = client.get("/test")

        assert "Retry-After" in resp.headers
        assert int(resp.headers["Retry-After"]) >= 0

    def test_blocked_response_has_ratelimit_headers(self) -> None:
        app = _make_app()
        client = TestClient(app, headers={"X-Forwarded-For": "5.5.5.5"})

        with patch(
            "app.middleware.rate_limit._sliding_window_check",
            new_callable=AsyncMock,
            return_value=(False, 0, int(time.time()) + 60),
        ):
            resp = client.get("/test")

        assert "X-RateLimit-Limit" in resp.headers
        assert resp.headers["X-RateLimit-Remaining"] == "0"
        assert "X-RateLimit-Reset" in resp.headers

    def test_blocked_response_body_has_detail(self) -> None:
        app = _make_app()
        client = TestClient(app, headers={"X-Forwarded-For": "5.5.5.5"})

        with patch(
            "app.middleware.rate_limit._sliding_window_check",
            new_callable=AsyncMock,
            return_value=(False, 0, int(time.time()) + 60),
        ):
            resp = client.get("/test")

        assert "detail" in resp.json()


# ---------------------------------------------------------------------------
# RateLimitMiddleware — allowed response headers
# ---------------------------------------------------------------------------


class TestRateLimitAllowedHeaders:
    def test_allowed_response_has_ratelimit_headers(self) -> None:
        app = _make_app()
        client = TestClient(app, headers={"X-Forwarded-For": "6.6.6.6"})

        with patch(
            "app.middleware.rate_limit._sliding_window_check",
            new_callable=AsyncMock,
            return_value=(True, 47, int(time.time()) + 60),
        ):
            resp = client.get("/test")

        assert resp.status_code == 200
        assert "X-RateLimit-Limit" in resp.headers
        assert resp.headers["X-RateLimit-Remaining"] == "47"
        assert "X-RateLimit-Reset" in resp.headers

    def test_no_retry_after_on_allowed_request(self) -> None:
        app = _make_app()
        client = TestClient(app, headers={"X-Forwarded-For": "6.6.6.6"})

        with patch(
            "app.middleware.rate_limit._sliding_window_check",
            new_callable=AsyncMock,
            return_value=(True, 10, int(time.time()) + 60),
        ):
            resp = client.get("/test")

        assert "Retry-After" not in resp.headers


# ---------------------------------------------------------------------------
# Limit resolution
# ---------------------------------------------------------------------------


class TestLimitResolution:
    def test_endpoint_limit_used_for_login_path(self) -> None:
        """Login endpoint should use its specific (lower) limit."""
        app = _make_app()
        client = TestClient(app, headers={"X-Forwarded-For": "7.7.7.7"})

        with patch(
            "app.middleware.rate_limit._sliding_window_check",
            new_callable=AsyncMock,
            return_value=(True, 4, int(time.time()) + 60),
        ) as mock_check:
            resp = client.get("/api/v1/auth/login")

        assert resp.status_code == 200
        # Verify the limit passed was the login-specific one.
        call_args = mock_check.call_args
        max_requests = call_args.args[1]
        assert max_requests == _ENDPOINT_LIMITS["/api/v1/auth/login"][0]

    def test_default_limit_used_for_generic_path(self) -> None:
        from app.core.config import settings

        app = _make_app()
        client = TestClient(app, headers={"X-Forwarded-For": "8.8.8.8"})

        with patch(
            "app.middleware.rate_limit._sliding_window_check",
            new_callable=AsyncMock,
            return_value=(True, 99, int(time.time()) + 60),
        ) as mock_check:
            client.get("/test")

        call_args = mock_check.call_args
        max_requests = call_args.args[1]
        assert max_requests == settings.RATE_LIMIT_DEFAULT

    def test_role_limit_applied_when_user_role_in_state(self) -> None:
        from app.core.config import settings

        app = FastAPI()
        app.add_middleware(RateLimitMiddleware, whitelist=frozenset())

        @app.get("/protected")
        async def _ep(request: Request) -> dict:  # noqa: F821
            return {"ok": True}

        # Inject user_role into request.state via a custom middleware shim.
        from starlette.middleware.base import BaseHTTPMiddleware as _BHM

        class _StateInjector(_BHM):
            async def dispatch(self, request, call_next):
                request.state.user_role = "city_admin"
                return await call_next(request)

        app.add_middleware(_StateInjector)

        client = TestClient(app, headers={"X-Forwarded-For": "9.9.9.9"})

        with patch(
            "app.middleware.rate_limit._sliding_window_check",
            new_callable=AsyncMock,
            return_value=(True, 499, int(time.time()) + 60),
        ) as mock_check:
            client.get("/protected")

        call_args = mock_check.call_args
        max_requests = call_args.args[1]
        assert max_requests == settings.RATE_LIMIT_ADMIN


# ---------------------------------------------------------------------------
# add_endpoint_limit helper
# ---------------------------------------------------------------------------


class TestAddEndpointLimit:
    def test_adds_entry_to_endpoint_limits(self) -> None:
        add_endpoint_limit("/api/v1/special", 25, 30)
        assert "/api/v1/special" in _ENDPOINT_LIMITS
        assert _ENDPOINT_LIMITS["/api/v1/special"] == (25, 30)

    def test_default_window_is_60(self) -> None:
        add_endpoint_limit("/api/v1/another", 10)
        assert _ENDPOINT_LIMITS["/api/v1/another"][1] == 60


# ---------------------------------------------------------------------------
# X-Forwarded-For parsing
# ---------------------------------------------------------------------------


class TestClientIpExtraction:
    def test_first_ip_from_forwarded_for_used(self) -> None:
        app = _make_app()
        # Multiple IPs in X-Forwarded-For; only the first should be used.
        client = TestClient(
            app, headers={"X-Forwarded-For": "1.2.3.4, 5.6.7.8, 9.10.11.12"}
        )

        with patch(
            "app.middleware.rate_limit._sliding_window_check",
            new_callable=AsyncMock,
            return_value=(True, 5, int(time.time()) + 60),
        ) as mock_check:
            client.get("/test")

        rl_key = mock_check.call_args.args[0]
        assert "1.2.3.4" in rl_key
        assert "5.6.7.8" not in rl_key
