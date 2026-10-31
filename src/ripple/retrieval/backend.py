"""SearchBackend: the two ranked candidate lists a retriever fuses (ADR-0026, ADR-0050).

A backend knows nothing about validity: it ranks every memory it has indexed, RETIRED
ones included, and the retriever filters through ripple.core.visibility afterwards.
Keeping the backend ignorant of status is deliberate: the I1 rule lives in exactly one
place, and a backend bug can only cost recall, never leak a retired memory.

Two implementations: ripple.retrieval.inmemory_search (tests, BM25 over tokens) and
ripple.retrieval.postgres_search (PostgreSQL full-text search and pgvector).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from ripple.core.models import Memory


@dataclass(frozen=True)
class SearchHit:
    memory_id: str
    score: float  # higher is better; only comparable within one call


class SearchBackend(Protocol):
    async def lexical(self, user_id: str, query: str, k: int) -> list[SearchHit]:
        """Top-k memories of the user by lexical relevance, best first, ties by id."""
        ...

    async def dense(self, user_id: str, vector: Sequence[float], k: int) -> list[SearchHit]:
        """Top-k memories of the user by cosine similarity to `vector`, best first."""
        ...

    async def index(self, memory: Memory, embedding: Sequence[float] | None) -> None:
        """Make a new memory or version searchable; `embedding` is None without an Embedder."""
        ...
