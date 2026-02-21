"""Tests for granular API rate limiting middleware — task 16.4."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.responses import PlainTextResponse

from app.middleware.rate_limit import (
    RateLimitMiddleware,
    _clear_inmemory_store,
    _inmemory_check,
    add_endpoint_limit,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_app(
    *,
    rate_limit_enabled: bool = True,
    whitelist: frozenset[str] | None = None,
) -> FastAPI:
    """Create a minimal FastAPI app with the rate-limit middleware."""
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, whitelist=whitelist or frozenset())

    @app.get("/api/v1/health")
    async def health():
        return PlainTextResponse("ok")

    @app.post("/api/v1/auth/login")
    async def login():
        return PlainTextResponse("logged in")

    @app.get("/api/v1/items")
    async def items():
        return PlainTextResponse("items")

    return app


@pytest.fixture(autouse=True)
def _clean_inmemory():
    """Clear in-memory rate-limit store before each test."""
    _clear_inmemory_store()
    yield
    _clear_inmemory_store()


@pytest.fixture()
def app():
    """App with rate limiting enabled, using in-memory fallback."""
    return _make_app()


@pytest.fixture()
def client(app):
    """TestClient that uses in-memory fallback (Redis import patched)."""
    with patch(
        "app.middleware.rate_limit.get_redis",
        side_effect=Exception("no redis"),
    ):
        # Need to import inside patch context
        yield TestClient(app)


# ---------------------------------------------------------------------------
# In-memory sliding window unit tests
# ---------------------------------------------------------------------------


class TestInMemorySlidingWindow:
    def test_allows_within_limit(self):
        for _ in range(5):
            allowed, remaining, _ = _inmemory_check("test_key", 5, 60)
        # 5th request should still be allowed
        assert allowed is True
        assert remaining == 0

    def test_blocks_over_limit(self):
        for _ in range(5):
            _inmemory_check("test_key", 5, 60)
        allowed, remaining, reset_ts = _inmemory_check("test_key", 5, 60)
        assert allowed is False
        assert remaining == 0
        assert reset_ts > 0

    def test_separate_keys_independent(self):
        for _ in range(3):
            _inmemory_check("key_a", 3, 60)
        # key_a is exhausted
        allowed_a, _, _ = _inmemory_check("key_a", 3, 60)
        assert allowed_a is False
        # key_b should still be fine
        allowed_b, _, _ = _inmemory_check("key_b", 3, 60)
        assert allowed_b is True


# ---------------------------------------------------------------------------
# Middleware integration tests (in-memory fallback)
# ---------------------------------------------------------------------------


class TestRateLimitMiddleware:
    """Integration tests using TestClient with in-memory fallback."""

    def test_rate_limit_headers_present(self, client):
        resp = client.get("/api/v1/items")
        assert resp.status_code == 200
        assert "X-RateLimit-Limit" in resp.headers
        assert "X-RateLimit-Remaining" in resp.headers
        assert "X-RateLimit-Reset" in resp.headers

    def test_returns_429_when_exhausted(self):
        """Auth login endpoint has a low limit (RATE_LIMIT_LOGIN=5)."""
        app = _make_app()
        with patch(
            "app.middleware.rate_limit.get_redis",
            side_effect=Exception("no redis"),
        ):
            c = TestClient(app)
            for _ in range(5):
                resp = c.post("/api/v1/auth/login")
                assert resp.status_code == 200

            resp = c.post("/api/v1/auth/login")
            assert resp.status_code == 429
            assert "Retry-After" in resp.headers
            body = resp.json()
            assert "Too many requests" in body["detail"]

    def test_general_endpoint_higher_limit(self):
        """General endpoints should allow 100 requests per minute."""
        app = _make_app()
        with patch(
            "app.middleware.rate_limit.get_redis",
            side_effect=Exception("no redis"),
        ):
            c = TestClient(app)
            # First 10 requests should all pass
            for _ in range(10):
                resp = c.get("/api/v1/items")
                assert resp.status_code == 200

    def test_whitelisted_ip_bypasses(self):
        """Whitelisted IPs should never be rate-limited."""
        app = _make_app(whitelist=frozenset({"testclient"}))
        with patch(
            "app.middleware.rate_limit.get_redis",
            side_effect=Exception("no redis"),
        ):
            c = TestClient(app)
            # Even after many requests, should never get 429
            # (testclient is the default IP in TestClient)
            for _ in range(200):
                resp = c.get("/api/v1/health")
                assert resp.status_code == 200

    def test_disabled_rate_limiting(self):
        """When RATE_LIMIT_ENABLED is False, no limiting is applied."""
        app = _make_app()
        with (
            patch("app.middleware.rate_limit.settings") as mock_settings,
            patch(
                "app.middleware.rate_limit.get_redis",
                side_effect=Exception("no redis"),
            ),
        ):
            mock_settings.RATE_LIMIT_ENABLED = False
            c = TestClient(app)
            for _ in range(200):
                resp = c.get("/api/v1/health")
                assert resp.status_code == 200
            # No rate limit headers when disabled
            assert "X-RateLimit-Limit" not in resp.headers


# ---------------------------------------------------------------------------
# Key building tests
# ---------------------------------------------------------------------------


class TestKeyBuilding:
    def test_key_includes_user_id_when_authenticated(self):
        """Authenticated users get user_id in rate-limit key."""
        from app.middleware.rate_limit import RateLimitMiddleware

        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.state.user_id = "user-123"
        request.url.path = "/api/v1/items"

        key = RateLimitMiddleware._build_key("192.168.1.1", "/api/v1/items", request)
        assert "uid:user-123" in key
        assert "192.168.1.1" in key

    def test_key_without_user_id_for_anonymous(self):
        """Anonymous requests key by IP only."""
        from app.middleware.rate_limit import RateLimitMiddleware

        request = MagicMock(spec=Request)
        request.state = MagicMock(spec=[])  # no user_id attr
        request.url.path = "/api/v1/items"

        key = RateLimitMiddleware._build_key("10.0.0.1", "/api/v1/items", request)
        assert "uid:" not in key
        assert "10.0.0.1" in key

    def test_auth_endpoint_scoped_to_path(self):
        """Auth endpoints should include the path prefix in the key."""
        from app.middleware.rate_limit import RateLimitMiddleware

        request = MagicMock(spec=Request)
        request.state = MagicMock(spec=[])
        request.url.path = "/api/v1/auth/login"

        key = RateLimitMiddleware._build_key("10.0.0.1", "/api/v1/auth/login", request)
        assert "ep:" in key


# ---------------------------------------------------------------------------
# add_endpoint_limit tests
# ---------------------------------------------------------------------------


class TestAddEndpointLimit:
    def test_add_custom_limit(self):
        from app.middleware.rate_limit import _ENDPOINT_LIMITS

        add_endpoint_limit("/api/v1/custom", max_requests=50, window=30)
        assert _ENDPOINT_LIMITS["/api/v1/custom"] == (50, 30)
        # Cleanup
        del _ENDPOINT_LIMITS["/api/v1/custom"]
