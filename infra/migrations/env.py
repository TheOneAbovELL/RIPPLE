"""Alembic environment: async engine driven through run_sync (ADR-0016)."""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import Connection

from ripple.core.errors import ConfigurationError
from ripple.storage.base import Base
from ripple.storage.engine import ENV_VAR, database_url, engine_from_url
from ripple.storage.loop import use_selector_event_loop

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _url() -> str:
    url = database_url()
    if url is None:
        raise ConfigurationError(f"{ENV_VAR} is not set; migrations need a database")
    return url


def run_migrations_offline() -> None:
    """Emit SQL without a connection (alembic upgrade --sql)."""
    context.configure(url=_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def _run_sync(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = engine_from_url(_url())
    async with engine.connect() as connection:
        await connection.run_sync(_run_sync)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    use_selector_event_loop()  # psycopg async on Windows (src/ripple/storage/loop.py)
    asyncio.run(run_migrations_online())
