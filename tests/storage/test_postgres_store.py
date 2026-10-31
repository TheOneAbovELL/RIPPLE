"""PostgresStore against a real database (slow). Needs TEST_DATABASE_URL or DATABASE_URL
pointing at a disposable Postgres with pgvector; CI provides one."""

import asyncio
import os
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext

from ripple.storage import (
    search_schema,  # noqa: F401  (extends tables.memories with the embedding column)
    tables,
)
from ripple.storage.engine import database_url, engine_from_url
from ripple.storage.postgres import PostgresStore
from tests.core.store_contract import StoreContract

pytestmark = pytest.mark.slow

REPO_ROOT = Path(__file__).resolve().parents[2]


def _url(monkeypatch: pytest.MonkeyPatch) -> str:
    url = os.environ.get("TEST_DATABASE_URL") or database_url()
    if url is None:
        pytest.skip("TEST_DATABASE_URL/DATABASE_URL not set")
    monkeypatch.setenv("DATABASE_URL", url)
    return url


@pytest.fixture(scope="module")
def migrated(request: pytest.FixtureRequest):
    monkeypatch = pytest.MonkeyPatch()
    url = _url(monkeypatch)
    config = Config(str(REPO_ROOT / "alembic.ini"))
    command.upgrade(config, "head")
    yield url
    monkeypatch.undo()


class TestPostgresStore(StoreContract):
    @pytest.fixture
    def store(self, migrated: str):
        engine = engine_from_url(migrated)

        async def truncate():
            async with engine.begin() as conn:
                for table in ("links", "change_events", "forget_events", "memories"):
                    await conn.execute(sa.text(f"TRUNCATE TABLE {table} CASCADE"))

        asyncio.run(truncate())
        yield PostgresStore(engine)
        asyncio.run(engine.dispose())


def test_migrations_match_table_metadata(migrated: str):
    """Hand-written migration 0002 and tables.py must describe the same schema."""
    engine = engine_from_url(migrated)

    async def diff():
        async with engine.connect() as conn:

            def compare(sync_conn):
                context = MigrationContext.configure(sync_conn)
                return compare_metadata(context, tables.metadata)

            return await conn.run_sync(compare)

    try:
        assert asyncio.run(diff()) == []
    finally:
        asyncio.run(engine.dispose())
