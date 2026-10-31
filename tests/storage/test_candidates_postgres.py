"""PostgresCandidateStore against a real database (slow); skips without a URL."""

import asyncio

import pytest

from ripple.storage.candidates import PostgresCandidateStore
from ripple.storage.engine import engine_from_url
from ripple.storage.users import PostgresUserStore, User
from tests.api.store_contracts import CandidateStoreContract
from tests.fakes.clock import DEFAULT_START
from tests.storage.test_users_postgres import migrated, truncate_owned  # noqa: F401 - fixture

pytestmark = pytest.mark.slow


class TestPostgresCandidateStore(CandidateStoreContract):
    @pytest.fixture
    def engine(self, migrated: str):  # noqa: F811 - pytest fixture by name
        engine = engine_from_url(migrated)
        truncate_owned(engine)
        yield engine
        asyncio.run(engine.dispose())

    @pytest.fixture
    def owner(self, engine) -> str:
        """resume_candidates.user_id is a foreign key, so the owner must exist."""
        user = User(display_name="Asha", created_at=DEFAULT_START)
        asyncio.run(PostgresUserStore(engine).add_user(user))
        return user.id

    @pytest.fixture
    def candidate_store(self, engine):
        return PostgresCandidateStore(engine)
