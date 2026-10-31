"""Fixtures for the retrieval tests: an in-memory store and backend, seeded together."""

import asyncio
from collections.abc import Iterable

import pytest

from ripple.core.models import Link, Memory
from ripple.core.retrieval_contract import Embedder
from ripple.retrieval.indexing import index_memory
from ripple.retrieval.inmemory_search import InMemorySearchBackend
from tests.fakes.embedder import DeterministicFakeEmbedder
from tests.fakes.store import InMemoryStore


class Seeder:
    """Writes memories and links to the store and indexes the memories in the backend."""

    def __init__(
        self,
        store: InMemoryStore,
        backend: InMemorySearchBackend,
        embedder: Embedder | None = None,
    ) -> None:
        self.store = store
        self.backend = backend
        self.embedder = embedder

    def seed(self, memories: Iterable[Memory], links: Iterable[Link] = ()) -> None:
        memories, links = list(memories), list(links)

        async def write():
            async with self.store.transaction() as tx:
                for m in memories:
                    await tx.add_memory(m)
                for edge in links:
                    await tx.add_link(edge)
            for m in memories:
                await index_memory(self.backend, self.embedder, m)

        asyncio.run(write())


@pytest.fixture
def store() -> InMemoryStore:
    return InMemoryStore()


@pytest.fixture
def backend() -> InMemorySearchBackend:
    return InMemorySearchBackend()


@pytest.fixture
def embedder() -> DeterministicFakeEmbedder:
    return DeterministicFakeEmbedder(dimensions=16)


@pytest.fixture
def seeder(store: InMemoryStore, backend: InMemorySearchBackend) -> Seeder:
    return Seeder(store, backend)


@pytest.fixture
def dense_seeder(
    store: InMemoryStore, backend: InMemorySearchBackend, embedder: DeterministicFakeEmbedder
) -> Seeder:
    return Seeder(store, backend, embedder)
