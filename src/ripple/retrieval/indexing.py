"""Indexing a new memory or version into a SearchBackend.

Called by the write flow after a memory row is committed. Without an Embedder the
memory is indexed for the lexical path only, which is the product's state until the
Phase 3 embedder decision (ADR-0026).
"""

from ripple.core.errors import ConfigurationError
from ripple.core.models import Memory
from ripple.core.retrieval_contract import Embedder
from ripple.retrieval.backend import SearchBackend
from ripple.retrieval.text import searchable_text


async def embed_memory(embedder: Embedder, memory: Memory) -> list[float]:
    """The vector a memory is indexed under; the same text the lexical path scores."""
    vectors = await embedder.embed([searchable_text(memory)])
    if len(vectors) != 1 or len(vectors[0]) != embedder.dimensions:
        raise ConfigurationError(
            f"embedder returned {len(vectors)} vector(s) of unexpected size; "
            f"expected one of {embedder.dimensions} dimensions"
        )
    return vectors[0]


async def index_memory(backend: SearchBackend, embedder: Embedder | None, memory: Memory) -> None:
    embedding = await embed_memory(embedder, memory) if embedder is not None else None
    await backend.index(memory, embedding)
