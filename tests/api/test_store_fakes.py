"""The in-memory UserStore and CandidateStore satisfy the shared contracts."""

import pytest

from tests.api.fakes import InMemoryCandidateStore, InMemoryUserStore
from tests.api.store_contracts import (
    CandidateStoreContract,
    UserStoreContract,
)


class TestInMemoryUserStore(UserStoreContract):
    @pytest.fixture
    def user_store(self):
        return InMemoryUserStore()


class TestInMemoryCandidateStore(CandidateStoreContract):
    @pytest.fixture
    def candidate_store(self):
        return InMemoryCandidateStore()
