"""Slow tests against the compose services (docs/plans/phase-0.md, tasks 0.3 and 0.4).

They are the acceptance checks for "services start" and "alembic upgrade head". Skipped
when no database URL is set so the offline suite never touches a network.

The migration test downgrades to base first, so it needs a DISPOSABLE database: set
TEST_DATABASE_URL to one; it falls back to DATABASE_URL only because CI's database is
throwaway by construction.
"""

import asyncio
import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text

from ripple.storage.engine import database_url, engine_from_url

pytestmark = pytest.mark.slow

REPO_ROOT = Path(__file__).resolve().parents[2]


def _require_database(monkeypatch: pytest.MonkeyPatch) -> str:
    url = os.environ.get("TEST_DATABASE_URL") or database_url()
    if url is None:
        pytest.skip("TEST_DATABASE_URL/DATABASE_URL not set; start infra/docker-compose.yml first")
    # Alembic's env.py reads DATABASE_URL, so point it at the test database for this test.
    monkeypatch.setenv("DATABASE_URL", url)
    return url


async def _scalar(url: str, sql: str) -> object:
    engine = engine_from_url(url)
    try:
        async with engine.connect() as connection:
            return (await connection.execute(text(sql))).scalar_one()
    finally:
        await engine.dispose()


def test_services_postgres_is_reachable_with_pgvector_available(monkeypatch):
    url = _require_database(monkeypatch)
    version = asyncio.run(_scalar(url, "select version()"))
    assert "PostgreSQL" in str(version)
    available = asyncio.run(
        _scalar(url, "select count(*) from pg_available_extensions where name = 'vector'")
    )
    assert available == 1


def test_migrations_upgrade_head_on_empty_db(monkeypatch):
    url = _require_database(monkeypatch)
    config = Config(str(REPO_ROOT / "alembic.ini"))
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    head = asyncio.run(_scalar(url, "select version_num from alembic_version"))
    assert head == ScriptDirectory.from_config(config).get_current_head()
    installed = asyncio.run(
        _scalar(url, "select count(*) from pg_extension where extname = 'vector'")
    )
    assert installed == 1
