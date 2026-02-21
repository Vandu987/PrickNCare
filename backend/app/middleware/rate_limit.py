"""Redis-backed sliding-window rate limiting middleware — task 3.6 / 16.4.

Limits are applied in this priority order (most specific wins):
  1. Per-endpoint override (registered via ``add_endpoint_limit``)
  2. Per-role limit (from ``settings.RATE_LIMIT_*``)
  3. Per-IP default (``settings.RATE_LIMIT_DEFAULT``)

Responses include standard headers::

    X-RateLimit-Limit     – max requests allowed in the window
    X-RateLimit-Remaining – requests still available
    X-RateLimit-Reset     – UNIX timestamp when the window resets
    Retry-After           – seconds to wait (only on 429)

When Redis is unavailable an **in-memory** sliding-window fallback is used
so the service stays protected even without Redis.

Whitelisted IPs (e.g. internal services) bypass all limits.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from collections.abc import Callable, Coroutine
from threading import Lock
from typing import Any

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_RL_PREFIX = "rl:"  # rl:<key> → sorted-set of timestamps

# Whitelisted client IPs that always bypass rate limiting.
_WHITELISTED_IPS: frozenset[str] = frozenset({"127.0.0.1", "::1"})

# Role → requests-per-minute mapping (pulled from settings at import time).
_ROLE_LIMITS: dict[str, int] = {
    "super_admin": settings.RATE_LIMIT_ADMIN,
    "city_admin": settings.RATE_LIMIT_ADMIN,
    "client_user": settings.RATE_LIMIT_CLIENT,
    "phlebotomist": settings.RATE_LIMIT_PHLEBOTOMIST,
}

# Endpoint path prefix → (max_requests, window_seconds).
# Populated via ``add_endpoint_limit`` or pre-seeded below.
_ENDPOINT_LIMITS: dict[str, tuple[int, int]] = {
    "/api/v1/auth/login": (settings.RATE_LIMIT_LOGIN, 60),
    "/api/v1/auth/otp/request": (settings.RATE_LIMIT_LOGIN, 60),
    "/api/v1/auth/register": (settings.RATE_LIMIT_AUTH, 60),
    "/api/v1/auth/": (settings.RATE_LIMIT_AUTH, 60),
}

_DEFAULT_WINDOW = 60  # seconds


# ---------------------------------------------------------------------------
# Public helper — lets route modules register custom limits at startup
# ---------------------------------------------------------------------------


def add_endpoint_limit(path_prefix: str, max_requests: int, window: int = 60) -> None:
    """Register a per-endpoint rate limit.

    Call this at module level in any router file **before** ``app`` is built::

        add_endpoint_limit("/api/v1/bookings", max_requests=30, window=60)
    """
    _ENDPOINT_LIMITS[path_prefix] = (max_requests, window)


# ---------------------------------------------------------------------------
# In-memory fallback (thread-safe sliding window using sorted lists)
# ---------------------------------------------------------------------------

_mem_store: dict[str, list[float]] = defaultdict(list)
_mem_lock = Lock()


def _inmemory_check(key: str, max_requests: int, window: int) -> tuple[bool, int, int]:
    """Thread-safe in-memory sliding window check."""
    now = time.time()
    window_start = now - window
    full_key = f"{_RL_PREFIX}{key}"

    with _mem_lock:
        timestamps = _mem_store[full_key]
        # Prune expired entries
        _mem_store[full_key] = timestamps = [
            ts for ts in timestamps if ts > window_start
        ]

        if len(timestamps) >= max_requests:
            reset_ts = int(timestamps[0] + window) if timestamps else int(now + window)
            return False, 0, reset_ts

        timestamps.append(now)
        remaining = max_requests - len(timestamps)
        reset_ts = int(now + window)
        return True, remaining, reset_ts


def _clear_inmemory_store() -> None:
    """Clear the in-memory store (for testing)."""
    with _mem_lock:
        _mem_store.clear()


# ---------------------------------------------------------------------------
# Sliding-window counter (Redis sorted-set of timestamps)
# ---------------------------------------------------------------------------


async def _sliding_window_check(
    key: str,
    max_requests: int,
    window: int,
) -> tuple[bool, int, int]:
    """Atomic sliding-window check using a Redis sorted set.

    Falls back to in-memory if Redis is unavailable.

    Returns ``(allowed, remaining, reset_ts)`` where:
      - ``allowed`` – True if the request should be served
      - ``remaining`` – requests left after this one
      - ``reset_ts``  – UNIX timestamp of window expiry
    """
    try:
        from app.core.redis import get_redis

        redis = get_redis()
        # Quick connectivity check on first use is handled by eval itself.
    except Exception:
        logger.warning("Redis unavailable, using in-memory rate limiter")
        return _inmemory_check(key, max_requests, window)

    now = time.time()
    window_start = now - window
    full_key = f"{_RL_PREFIX}{key}"

    lua_script = """
local key        = KEYS[1]
local now        = tonumber(ARGV[1])
local window_start = tonumber(ARGV[2])
local window     = tonumber(ARGV[3])
local max_req    = tonumber(ARGV[4])

redis.call('ZREMRANGEBYSCORE', key, '-inf', window_start)

local count = redis.call('ZCARD', key)

if count >= max_req then
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    local reset_ts = now + window
    if #oldest >= 2 then
        reset_ts = tonumber(oldest[2]) + window
    end
    return {0, 0, math.floor(reset_ts)}
end

redis.call('ZADD', key, now, now .. ':' .. math.random(1000000))
redis.call('EXPIRE', key, window + 1)

local new_count = redis.call('ZCARD', key)
local remaining = max_req - new_count
local reset_ts  = math.floor(now + window)
return {1, remaining, reset_ts}
"""
    try:
        result = await redis.eval(
            lua_script,
            1,
            full_key,
            str(now),
            str(window_start),
            str(window),
            str(max_requests),
        )
        allowed = bool(result[0])
        remaining = int(result[1])
        reset_ts = int(result[2])
        return allowed, remaining, reset_ts
    except Exception:
        logger.warning("Redis eval failed, falling back to in-memory rate limiter")
        return _inmemory_check(key, max_requests, window)


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limiting middleware.

    Disabled entirely when ``settings.RATE_LIMIT_ENABLED`` is ``False``.

    Mount **after** the application is created::

        app.add_middleware(RateLimitMiddleware)
    """

    def __init__(self, app: ASGIApp, whitelist: frozenset[str] | None = None) -> None:
        super().__init__(app)
        self._whitelist: frozenset[str] = whitelist or _WHITELISTED_IPS

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Coroutine[Any, Any, Response]],
    ) -> Response:
        # Global kill-switch
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        client_ip = self._get_client_ip(request)

        # Whitelisted IPs bypass all limits.
        if client_ip in self._whitelist:
            return await call_next(request)

        path = request.url.path
        max_requests, window = self._resolve_limit(path, request)

        # Build a rate-limit key scoped to IP + user_id (+ path for endpoint overrides).
        rl_key = self._build_key(client_ip, path, request)

        allowed, remaining, reset_ts = await _sliding_window_check(
            rl_key, max_requests, window
        )

        if not allowed:
            retry_after = max(0, reset_ts - int(time.time()))
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please slow down."},
                headers={
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_ts),
                    "Retry-After": str(retry_after),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_ts)
        return response

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        """Extract the real client IP, honouring X-Forwarded-For."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _resolve_limit(self, path: str, request: Request) -> tuple[int, int]:
        """Return (max_requests, window_seconds) for this request."""
        # 1. Endpoint-specific override (longest matching prefix wins).
        for prefix, limit_pair in sorted(
            _ENDPOINT_LIMITS.items(), key=lambda x: len(x[0]), reverse=True
        ):
            if path.startswith(prefix):
                return limit_pair

        # 2. Per-role limit (JWT role stored in request state by RBAC dep).
        role: str | None = getattr(request.state, "user_role", None)
        if role and role in _ROLE_LIMITS:
            return _ROLE_LIMITS[role], _DEFAULT_WINDOW

        # 3. Default per-IP limit.
        return settings.RATE_LIMIT_DEFAULT, _DEFAULT_WINDOW

    @staticmethod
    def _build_key(client_ip: str, path: str, request: Request) -> str:
        """Derive a Redis key for this (client, path) combination.

        Includes ``user_id`` when the request is authenticated so that
        each user gets their own bucket rather than sharing one with
        all users behind the same IP / NAT.
        """
        # Extract user_id if present (set by auth dependency).
        user_id: str | None = getattr(request.state, "user_id", None)
        identity = f"ip:{client_ip}"
        if user_id:
            identity = f"ip:{client_ip}:uid:{user_id}"

        # Endpoint-specific: scope to identity + path prefix.
        for prefix in _ENDPOINT_LIMITS:
            if path.startswith(prefix):
                return f"{identity}:ep:{prefix}"
        # Role-based or default: scope to identity only (global bucket).
        return identity
