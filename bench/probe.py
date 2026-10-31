"""Retrieval probe: what a retriever shows after each event, for the stale retrieval rate.

H2 asks whether Ripple's stale retrieval rate is far below standard memory retrieval.
The scenario runner calls `retrieval_probe` after every event that carries gold
(ADR-0120): for each gold target's alias it queries the real `HybridRetriever`
(contract C2, lexical BM25 over an in-memory index, graph expansion on, flagged
results included with their flag, every match returned) with the content the alias was
first written with.
The queries come from the scenario, never from the system's state, so every strategy
is asked the same questions; only what each strategy left in the store differs.

No embedder: the dense path waits for its ADR (CLAUDE.md, embeddings pending), so the
probe measures the lexical half of retrieval plus graph expansion.
"""

from collections.abc import Sequence

from bench.replay import RetrievedSnapshot
from ripple.core.store import Store
from ripple.retrieval.hybrid import HybridRetriever
from ripple.retrieval.inmemory_search import InMemorySearchBackend

# k is the size of the store: every visible match comes back, so no top-k cut applies.
# A cut would make the counts depend on tie order, and ties are broken by memory id,
# which is a random uuid for every new version (core's new_id): two runs of one
# configuration then disagreed (smoke append_only, ADR-0120 point 4).
PROBE_SCOPE = "every match"


async def retrieval_probe(
    store: Store, user_id: str, queries: Sequence[tuple[str, str]]
) -> tuple[RetrievedSnapshot, ...]:
    """Results for each (alias, query) in order. The index is rebuilt from the store
    every time, every status included, as the production backend indexes every row
    and leaves visibility to the retriever (I1)."""
    backend = InMemorySearchBackend()
    memories = await store.memories_for_user(user_id)
    for memory in memories:
        await backend.index(memory, None)
    retriever = HybridRetriever(store, backend, k=max(1, len(memories)))
    shown: list[RetrievedSnapshot] = []
    for alias, query in queries:
        for result in await retriever.search(user_id, query, include_flagged=True):
            shown.append(
                RetrievedSnapshot(
                    query_alias=alias,
                    memory_id=result.memory.id,
                    flagged=result.flagged,
                    via=result.via.value,
                )
            )
    return tuple(shown)
