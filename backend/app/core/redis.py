"""Redis connection manager."""

import logging
from typing import Any

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

_redis_client: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    """Return the module-level Redis client, creating it if needed."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def close_redis() -> None:
    """Close the Redis connection pool."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
        logger.info("Redis connection closed.")


# ---------------------------------------------------------------------------
# Typed helpers used by security.py
# ---------------------------------------------------------------------------


async def redis_set(key: str, value: Any, ex: int | None = None) -> None:
    await get_redis().set(key, value, ex=ex)


async def redis_get(key: str) -> str | None:
    return await get_redis().get(key)


async def redis_delete(key: str) -> None:
    await get_redis().delete(key)


async def redis_exists(key: str) -> bool:
    return bool(await get_redis().exists(key))
