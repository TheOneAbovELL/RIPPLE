"""Post-commit indexing hook for retrieval (ADR-0026, WS-5 request).

A MemoryIndexer is told about every memory row the write flow and the runner commit,
and about every id the forget API deletes, so a search backend can keep its lexical
and dense indexes in step with the store. Core defines the protocol; ripple.retrieval
implements it. Calls happen after the transaction commits, never inside it.
"""

from typing import Protocol

from ripple.core.models import Memory


class MemoryIndexer(Protocol):
    async def index(self, memory: Memory) -> None: ...

    async def remove(self, memory_id: str) -> None: ...
