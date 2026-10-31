"""PostgresDeliveryLog against a real database (slow), plus the drift check for
migration 0005. Skips without TEST_DATABASE_URL / DATABASE_URL."""

import asyncio

import pytest
import sqlalchemy as sa
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext

from ripple.notify.contracts import AlertKind
from ripple.notify.delivery_log import PostgresDeliveryLog
from ripple.storage import delivery_tables
from ripple.storage.engine import engine_from_url
from tests.builders import USER
from tests.fakes.clock import DEFAULT_START
from tests.notify.test_hardening_delivery_log import DeliveryLogContract
from tests.storage.test_users_postgres import migrated  # noqa: F401 - fixture

pytestmark = pytest.mark.slow


def _truncate(engine):
    async def run():
        async with engine.begin() as conn:
            await conn.execute(sa.text("TRUNCATE TABLE delivery_log"))

    asyncio.run(run())


@pytest.fixture
def engine(migrated: str):  # noqa: F811 - pytest fixture by name
    engine = engine_from_url(migrated)
    _truncate(engine)
    yield engine
    asyncio.run(engine.dispose())


class TestPostgresDeliveryLog(DeliveryLogContract):
    @pytest.fixture
    def delivery_log(self, engine) -> PostgresDeliveryLog:
        return PostgresDeliveryLog(engine)


def test_delivery_log_survives_a_new_instance_over_the_same_database(engine):
    """The worker restart case from the WS-6 handover: a fresh log object sees the rows."""
    asyncio.run(PostgresDeliveryLog(engine).record_digest(USER, DEFAULT_START.date()))
    asyncio.run(
        PostgresDeliveryLog(engine).record_alert(USER, "o1", AlertKind.HIGH_FIT, DEFAULT_START)
    )
    fresh = PostgresDeliveryLog(engine)
    assert asyncio.run(fresh.last_digest_day(USER)) == DEFAULT_START.date()
    assert asyncio.run(fresh.last_alert_at(USER, "o1", AlertKind.HIGH_FIT)) == DEFAULT_START


def test_migration_0005_matches_delivery_tables(engine):
    """Hand-written migration 0005 and delivery_tables.py must describe the same schema."""

    async def diff():
        async with engine.connect() as conn:

            def compare(sync_conn):
                context = MigrationContext.configure(sync_conn)
                return [
                    d
                    for d in compare_metadata(context, delivery_tables.metadata)
                    if "delivery_log" in repr(d)
                ]

            return await conn.run_sync(compare)

    assert asyncio.run(diff()) == []
