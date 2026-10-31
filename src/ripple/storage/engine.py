"""Engine factory. The URL comes from the environment, never from code (secrets stay in env)."""

import os

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from ripple.core.errors import ConfigurationError

ENV_VAR = "DATABASE_URL"
DRIVER_PREFIX = "postgresql+psycopg://"


def database_url() -> str | None:
    """The configured URL, or None when no database is configured (offline tests)."""
    url = os.environ.get(ENV_VAR)
    return url or None


def engine_from_url(url: str) -> AsyncEngine:
    if not url.startswith(DRIVER_PREFIX):
        raise ConfigurationError(f"{ENV_VAR} must use the {DRIVER_PREFIX} driver (ADR-0016)")
    return create_async_engine(url, pool_pre_ping=True)
