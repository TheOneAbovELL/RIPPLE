"""PostgresUploadStore and the conditional candidate update against a real database
(slow), plus the drift check for migration 0006. Skips without a database URL."""

import asyncio

import pytest
import sqlalchemy as sa
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext

from ripple.storage import uploads_tables
from ripple.storage.candidates import PostgresCandidateStore
from ripple.storage.engine import engine_from_url
from ripple.storage.uploads import PostgresUploadStore
from ripple.storage.users import PostgresUserStore, User
from tests.api.test_hardening_confirm import ConditionalReplaceContract
from tests.api.test_hardening_uploads import UploadStoreContract, upload
from tests.fakes.clock import DEFAULT_START
from tests.storage.test_users_postgres import migrated, truncate_owned  # noqa: F401 - fixture

pytestmark = pytest.mark.slow


@pytest.fixture
def engine(migrated: str):  # noqa: F811 - pytest fixture by name
    engine = engine_from_url(migrated)
    truncate_owned(engine)  # users cascade to resume_uploads

    async def run():
        async with engine.begin() as conn:
            await conn.execute(sa.text("TRUNCATE TABLE resume_uploads"))

    asyncio.run(run())
    yield engine
    asyncio.run(engine.dispose())


@pytest.fixture
def owner(engine) -> str:
    user = User(display_name="Asha", created_at=DEFAULT_START)
    asyncio.run(PostgresUserStore(engine).add_user(user))
    return user.id


@pytest.fixture
def owner_row(engine) -> str:
    """Same as `owner`, under a name the contract classes' own `owner` can depend on."""
    user = User(display_name="Asha", created_at=DEFAULT_START)
    asyncio.run(PostgresUserStore(engine).add_user(user))
    return user.id


class TestPostgresUploadStore(UploadStoreContract):
    @pytest.fixture
    def upload_store(self, engine):
        return PostgresUploadStore(engine)

    @pytest.fixture
    def owner(self, owner_row: str) -> str:
        # The contract's in-memory owner is a bare id; Postgres needs the user row the
        # foreign key points at (found on the first live run, 2026-10-31).
        return owner_row


class TestPostgresConditionalReplace(ConditionalReplaceContract):
    @pytest.fixture
    def candidate_store(self, engine):
        return PostgresCandidateStore(engine)

    @pytest.fixture
    def owner(self, owner_row: str) -> str:
        return owner_row


def test_deleting_the_user_row_cascades_to_uploads(engine, owner):
    store = PostgresUploadStore(engine)
    asyncio.run(store.add_upload(upload(owner)))
    asyncio.run(PostgresUserStore(engine).delete_user(owner))
    assert asyncio.run(store.uploads_for_user(owner)) == []


def test_migration_0006_matches_uploads_tables(engine):
    async def diff():
        async with engine.connect() as conn:

            def compare(sync_conn):
                context = MigrationContext.configure(sync_conn)
                return [
                    d
                    for d in compare_metadata(context, uploads_tables.metadata)
                    if "resume_uploads" in repr(d)
                ]

            return await conn.run_sync(compare)

    assert asyncio.run(diff()) == []
