"""Async SQLAlchemy engine, session factory, and get_db dependency."""

import asyncio
import logging
from collections.abc import AsyncGenerator

from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Engine (created once at module level; disposed in lifespan shutdown)
# ---------------------------------------------------------------------------

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _build_engine() -> AsyncEngine:
    return create_async_engine(
        settings.DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,  # health-check connections before use
        echo=settings.DEBUG,
        connect_args={
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0,
        },
    )


def get_engine() -> AsyncEngine:
    """Return the module-level engine, creating it if needed."""
    global _engine
    if _engine is None:
        _engine = _build_engine()
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the module-level session factory, creating it if needed."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _session_factory


# ---------------------------------------------------------------------------
# Lifecycle helpers (called from main.py lifespan)
# ---------------------------------------------------------------------------


async def init_db() -> None:
    """Verify connectivity with exponential back-off (max 3 attempts)."""
    engine = get_engine()
    for attempt in range(1, 4):
        try:
            async with engine.connect():
                logger.info("Database connection established.")
                return
        except OperationalError as exc:
            if attempt == 3:
                raise
            wait = 2**attempt  # 2 s, 4 s
            logger.warning(
                "DB connection attempt %d failed (%s). Retrying in %ds…",
                attempt,
                exc,
                wait,
            )
            await asyncio.sleep(wait)


async def close_db() -> None:
    """Dispose the engine and reset module-level singletons."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("Database engine disposed.")


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an AsyncSession; roll back on error, always close."""
    session: AsyncSession = get_session_factory()()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
