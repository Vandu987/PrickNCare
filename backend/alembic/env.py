import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

import app.models.audit  # noqa: F401
import app.models.clients  # noqa: F401
import app.models.orders  # noqa: F401
import app.models.packages  # noqa: F401
import app.models.payments  # noqa: F401
import app.models.phlebotomists  # noqa: F401
import app.models.samples  # noqa: F401
import app.models.users  # noqa: F401
import app.models.zones  # noqa: F401
from alembic import context

# Import all models so Alembic can detect them for autogenerate
from app.models import Base  # noqa: F401 — registers all mappers

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Read DATABASE_URL: env var takes precedence → fallback to app settings
_db_url = os.environ.get("DATABASE_URL")
if not _db_url:
    from app.core.config import settings  # noqa: PLC0415

    _db_url = settings.DATABASE_URL

config.set_main_option("sqlalchemy.url", _db_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without a live DB connection (SQL script output)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):  # type: ignore[no-untyped-def]
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations using an async engine (asyncpg)."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
