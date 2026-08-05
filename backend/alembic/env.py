"""
Alembic Environment Configuration for LinguaMate AI.

Supports both SQLite (local dev) and PostgreSQL (production).
Auto-detects all ORM models via app.models imports.
"""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config, create_async_engine

from alembic import context

# ─── Alembic Config ──────────────────────────────────────────────────────────
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ─── Import our app's metadata ──────────────────────────────────────────────
from app.database import Base
from app.config import get_settings

# Import ALL models so Base.metadata sees them
from app.models import *  # noqa: F401, F403

target_metadata = Base.metadata

# ─── Get database URL from app config ────────────────────────────────────────
settings = get_settings()
database_url = settings.database_url

# For Alembic's sync operations with SQLite, convert async URL to sync
sync_database_url = database_url
if database_url.startswith("sqlite+aiosqlite"):
    sync_database_url = database_url.replace("sqlite+aiosqlite", "sqlite")
elif database_url.startswith("postgresql+asyncpg"):
    sync_database_url = database_url.replace("postgresql+asyncpg", "postgresql")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation
    we don't even need a DBAPI to be available.
    """
    context.configure(
        url=sync_database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # Required for SQLite ALTER TABLE support
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Execute migrations with the given connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,  # Required for SQLite ALTER TABLE support
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations using an async engine."""
    connectable = create_async_engine(
        database_url,
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
