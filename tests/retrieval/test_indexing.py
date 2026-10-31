import asyncio

import pytest

from ripple.core.errors import ConfigurationError
from ripple.retrieval.indexing import embed_memory, index_memory
from ripple.retrieval.inmemory_search import InMemorySearchBackend
from ripple.retrieval.text import searchable_text
from tests.builders import USER, fact
from tests.fakes.embedder import DeterministicFakeEmbedder


def test_index_memory_without_embedder_indexes_lexically_only():
    backend, m = InMemorySearchBackend(), fact("student", "cgpa", 7.6)
    asyncio.run(index_memory(backend, None, m))
    assert [h.memory_id for h in asyncio.run(backend.lexical(USER, "cgpa", 5))] == [m.id]
    assert backend.embedding_of(m.id) is None


def test_index_memory_with_embedder_stores_the_vector_of_the_searchable_text():
    backend, embedder, m = (
        InMemorySearchBackend(),
        DeterministicFakeEmbedder(8),
        fact("student", "cgpa", 7.6),
    )
    asyncio.run(index_memory(backend, embedder, m))
    assert embedder.calls == [[searchable_text(m)]]
    [expected] = asyncio.run(DeterministicFakeEmbedder(8).embed([searchable_text(m)]))
    assert backend.embedding_of(m.id) == tuple(expected)


class _WrongSizeEmbedder:
    dimensions = 8

    async def embed(self, texts):
        return [[0.0] * 3 for _ in texts]


def test_embed_memory_rejects_a_vector_of_the_wrong_dimension():
    with pytest.raises(ConfigurationError, match="dimensions"):
        asyncio.run(embed_memory(_WrongSizeEmbedder(), fact("student", "cgpa", 7.6)))
