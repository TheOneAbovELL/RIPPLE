"""PostgresUserStore against a real database (slow), plus the drift check for
migration 0003. Needs TEST_DATABASE_URL or DATABASE_URL; skips otherwise."""

import asyncio
import os
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext

from ripple.storage import tables, users_tables
from ripple.storage.engine import database_url, engine_from_url
from ripple.storage.users import PostgresUserStore
from tests.api.store_contracts import UserStoreContract

pytestmark = pytest.mark.slow

REPO_ROOT = Path(__file__).resolve().parents[2]
OWNED_TABLES = ("resume_candidates", "telegram_link_codes", "api_tokens", "users")


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
    command.upgrade(Config(str(REPO_ROOT / "alembic.ini")), "head")
    yield url
    monkeypatch.undo()


def truncate_owned(engine):
    async def run():
        async with engine.begin() as conn:
            for table in OWNED_TABLES:
                await conn.execute(sa.text(f"TRUNCATE TABLE {table} CASCADE"))

    asyncio.run(run())


class TestPostgresUserStore(UserStoreContract):
    @pytest.fixture
    def user_store(self, migrated: str):
        engine = engine_from_url(migrated)
        truncate_owned(engine)
        yield PostgresUserStore(engine)
        asyncio.run(engine.dispose())


def test_migration_0003_matches_users_tables(migrated: str):
    """Hand-written migration 0003 and users_tables.py must describe the same schema.
    Both table modules are imported so the shared metadata is complete."""
    assert {t.name for t in users_tables.metadata.sorted_tables} >= set(OWNED_TABLES)
    assert users_tables.metadata is tables.metadata
    engine = engine_from_url(migrated)

    async def diff():
        async with engine.connect() as conn:

            def compare(sync_conn):
                context = MigrationContext.configure(sync_conn)
                return compare_metadata(context, users_tables.metadata)

            return await conn.run_sync(compare)

    try:
        assert asyncio.run(diff()) == []
    finally:
        asyncio.run(engine.dispose())
