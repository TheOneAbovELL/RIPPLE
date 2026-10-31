"""Retrieval contract (docs/02 RAG, I1; docs/plans/parallel-execution.md, contract C2).

Core defines what a retriever returns and promises; ripple.retrieval implements it and
the agents consume it through this protocol only. Every result passes
ripple.core.visibility, so RETIRED memories never appear and flagged ones carry the flag.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from ripple.core.models import Memory


class RetrievalPath(StrEnum):
    LEXICAL = "lexical"
    DENSE = "dense"
    GRAPH = "graph"  # pulled in by graph expansion from a direct hit


@dataclass(frozen=True)
class RetrievedMemory:
    memory: Memory
    score: float
    flagged: bool  # SUSPECT or PENDING_USER; only present when the caller opted in
    via: RetrievalPath
    # Source references the agent may cite: the memory's source_ref and, for graph
    # expansion, the id of the direct hit it was reached from.
    evidence: tuple[str, ...] = ()


class Retriever(Protocol):
    async def search(
        self,
        user_id: str,
        query: str,
        *,
        k: int = 10,
        include_flagged: bool = False,
        expand_graph: bool = True,
    ) -> list[RetrievedMemory]:
        """Top-k visible memories for the query, graph-expanded by one hop when asked."""
        ...


class Embedder(Protocol):
    """Dense vectors for texts. The real model is chosen in ADR-0026; tests use a fake."""

    @property
    def dimensions(self) -> int: ...

    async def embed(self, texts: Sequence[str]) -> list[list[float]]: ...
