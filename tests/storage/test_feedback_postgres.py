"""PostgresFeedbackStore against a real database (slow), plus the drift check for
migration 0009. Skips without a database URL."""

import asyncio

import pytest
import sqlalchemy as sa
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext

# Imported for its side effect too: until the coordinator registers feedback_tables in
# ripple.storage.__init__, this import puts pilot_feedback on the shared metadata.
from ripple.core.forget import forget
from ripple.storage import feedback_tables
from ripple.storage.engine import engine_from_url
from ripple.storage.feedback import PostgresFeedbackStore
from ripple.storage.postgres import PostgresStore
from ripple.storage.users import PostgresUserStore, User
from tests.builders import memory
from tests.fakes.clock import DEFAULT_START, FakeClock
from tests.storage.test_feedback_store import TARGETS, FeedbackStoreContract, feedback
from tests.storage.test_users_postgres import migrated, truncate_owned  # noqa: F401 - fixture

pytestmark = pytest.mark.slow


@pytest.fixture
def engine(migrated: str):  # noqa: F811 - pytest fixture by name
    engine = engine_from_url(migrated)
    truncate_owned(engine)  # users cascade to pilot_feedback

    async def run():
        async with engine.begin() as conn:
            await conn.execute(sa.text("TRUNCATE TABLE pilot_feedback, memories CASCADE"))
        # target_memory_id is a foreign key: the contract's targets must exist.
        async with PostgresStore(engine).transaction() as tx:
            for target in TARGETS:
                await tx.add_memory(memory(id=target, kind="opening", content="SDE intern"))

    asyncio.run(run())
    yield engine
    asyncio.run(engine.dispose())


def _user(engine) -> str:
    user = User(display_name="Asha", created_at=DEFAULT_START)
    asyncio.run(PostgresUserStore(engine).add_user(user))
    return user.id


class TestPostgresFeedbackStore(FeedbackStoreContract):
    # user_id is a foreign key in Postgres, so the contract's users must exist.
    @pytest.fixture
    def owner(self, engine) -> str:
        return _user(engine)

    @pytest.fixture
    def other(self, engine) -> str:
        return _user(engine)

    @pytest.fixture
    def feedback_store(self, engine):
        return PostgresFeedbackStore(engine)


def test_feedback_postgres_deleting_the_user_row_cascades(engine):
    owner = _user(engine)
    store = PostgresFeedbackStore(engine)
    asyncio.run(store.record(feedback(owner)))
    asyncio.run(PostgresUserStore(engine).delete_user(owner))
    assert asyncio.run(store.feedback_for_user(owner)) == []


def test_feedback_postgres_forgetting_the_target_removes_its_rows(engine):
    """I7: a note never outlives the memory it is about, whichever path forgets."""
    owner = _user(engine)
    store = PostgresFeedbackStore(engine)
    kept = feedback(owner, TARGETS[2])
    asyncio.run(store.record(feedback(owner, TARGETS[1], note="my real CGPA is 7.2")))
    asyncio.run(store.record(kept))
    asyncio.run(forget(PostgresStore(engine), FakeClock(), TARGETS[1]))
    assert asyncio.run(store.feedback_for_user(owner)) == [kept]


def test_feedback_postgres_racing_records_create_one_row(engine):
    owner = _user(engine)
    store = PostgresFeedbackStore(engine)

    async def race():
        return await asyncio.gather(
            store.record(feedback(owner, note="a")), store.record(feedback(owner, note="b"))
        )

    results = asyncio.run(race())
    assert sorted(created for _, created in results) == [False, True]
    assert results[0][0] == results[1][0]
    assert len(asyncio.run(store.feedback_for_user(owner))) == 1


def test_migration_0009_matches_feedback_tables(engine):
    async def diff():
        async with engine.connect() as conn:

            def compare(sync_conn):
                context = MigrationContext.configure(sync_conn)
                return [
                    d
                    for d in compare_metadata(context, feedback_tables.metadata)
                    if "pilot_feedback" in repr(d)
                ]

            return await conn.run_sync(compare)

    assert asyncio.run(diff()) == []
