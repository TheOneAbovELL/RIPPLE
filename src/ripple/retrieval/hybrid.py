"""HybridRetriever: lexical + dense candidates, fused, graph-expanded, I1-filtered.

Implements ripple.core.retrieval_contract.Retriever (contract C2). Pipeline per query:

1. Ask the backend for lexical candidates and, when an Embedder is configured, dense
   candidates; fuse the two ranked lists by reciprocal rank (ripple.retrieval.fusion).
   The backend is asked for more than k candidates because it ranks RETIRED memories
   too and the visibility filter below removes some; without oversampling a query whose
   best lexical matches are old versions would come back empty.
2. Load the candidates from the Store and keep the k best that visibility allows: these
   are the direct hits (via LEXICAL or DENSE).
3. Expand one hop (configurable) along links in both directions. depends_on links whose
   parent is superseded are history (ADR-0014) and are skipped; snapshot_of links are
   always followed, as ADR-0014 and docs/03 require for retrieval, so an application
   can cite the resume version it was sent with while that version is visible. Only
   neighbours that visibility allows are collected, so an invisible one never spends
   the neighbour budget nor seeds the next hop. Neighbours arrive via GRAPH with the
   direct hit they descend from in their evidence and a damped copy of its score.
4. Run everything through ripple.core.visibility.visible_for_retrieval last. This is
   the guarantee: whatever the steps above do, RETIRED can never leak through any path
   and a flagged memory always carries its flag (I1).

Result size: up to k direct hits plus up to k neighbours. Ordering is deterministic:
score descending, then memory id.
"""

import logging
from collections.abc import Sequence
from dataclasses import dataclass

from ripple.core.errors import ConfigurationError
from ripple.core.models import LinkClass, Memory
from ripple.core.retrieval_contract import Embedder, RetrievalPath, RetrievedMemory
from ripple.core.store import MemoryNotFoundError, Store
from ripple.core.visibility import visible_for_retrieval
from ripple.retrieval.backend import SearchBackend, SearchHit
from ripple.retrieval.fusion import FusedHit, reciprocal_rank_fusion

log = logging.getLogger(__name__)

# A graph neighbour scores half of the hit that reached it: always below that hit, and
# comparable across hits so neighbours of the best hit come first.
GRAPH_DAMPING = 0.5


def candidate_count(k: int) -> int:
    """How many backend candidates to ask for so that k survive the visibility filter."""
    return 4 * k + 16


@dataclass(frozen=True)
class _Collected:
    memory: Memory
    score: float
    via: RetrievalPath
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class _Frontier:
    memory: Memory
    score: float
    direct_hit_id: str  # the direct hit this branch descends from (cited as evidence)


class HybridRetriever:
    def __init__(
        self,
        store: Store,
        backend: SearchBackend,
        embedder: Embedder | None = None,
        *,
        k: int = 10,
        graph_hops: int = 1,
    ) -> None:
        if k < 1:
            raise ConfigurationError("retriever k must be at least 1")
        if graph_hops < 0:
            raise ConfigurationError("graph_hops cannot be negative")
        self._store = store
        self._backend = backend
        self._embedder = embedder
        self._default_k = k
        self._graph_hops = graph_hops

    async def search(
        self,
        user_id: str,
        query: str,
        *,
        k: int | None = None,
        include_flagged: bool = False,
        expand_graph: bool = True,
    ) -> list[RetrievedMemory]:
        limit = self._default_k if k is None else k
        if limit < 1:
            raise ValueError("k must be at least 1")
        if not query.strip():
            return []

        fused = await self._candidates(user_id, query, candidate_count(limit))
        loaded = await self._load(fused)
        seeds = [
            (memory, hit)
            for memory, hit in loaded
            if _visible(memory, include_flagged=include_flagged)
        ][:limit]
        collected: dict[str, _Collected] = {
            memory.id: _Collected(memory, hit.score, hit.via, _source_evidence(memory))
            for memory, hit in seeds
        }
        if expand_graph and self._graph_hops > 0:
            await self._expand(
                [_Frontier(memory, hit.score, memory.id) for memory, hit in seeds],
                collected,
                max_neighbours=limit,
                include_flagged=include_flagged,
            )

        ordered = sorted(collected.values(), key=lambda item: (-item.score, item.memory.id))
        # The final filter is the I1 guarantee, whatever the steps above did.
        visible = visible_for_retrieval(
            (item.memory for item in ordered), include_flagged=include_flagged
        )
        by_id = {item.memory.id: item for item in ordered}
        return [
            RetrievedMemory(
                memory=shown.memory,
                score=by_id[shown.memory.id].score,
                flagged=shown.flagged,
                via=by_id[shown.memory.id].via,
                evidence=by_id[shown.memory.id].evidence,
            )
            for shown in visible
        ]

    # ---- step 1: candidates ----------------------------------------------------------

    async def _candidates(self, user_id: str, query: str, count: int) -> list[FusedHit]:
        ranked: list[tuple[RetrievalPath, Sequence[SearchHit]]] = [
            (RetrievalPath.LEXICAL, await self._backend.lexical(user_id, query, count))
        ]
        if self._embedder is not None:
            vector = (await self._embedder.embed([query]))[0]
            ranked.append((RetrievalPath.DENSE, await self._backend.dense(user_id, vector, count)))
        return reciprocal_rank_fusion(ranked)

    # ---- step 2: load ----------------------------------------------------------------

    async def _load(self, fused: Sequence[FusedHit]) -> list[tuple[Memory, FusedHit]]:
        try:
            memories = await self._store.get_memories(hit.memory_id for hit in fused)
        except MemoryNotFoundError:
            # The in-memory backend can outlive a forgotten row; the Postgres backend
            # cannot. Fall back to one read per hit and drop the missing ones: that
            # costs recall only, never correctness.
            pairs: list[tuple[Memory, FusedHit]] = []
            for hit in fused:
                memory = await self._get_or_warn(hit.memory_id)
                if memory is not None:
                    pairs.append((memory, hit))
            return pairs
        return list(zip(memories, fused, strict=True))

    async def _get_or_warn(self, memory_id: str) -> Memory | None:
        try:
            return await self._store.get_memory(memory_id)
        except MemoryNotFoundError:
            log.warning("search index names a missing memory", extra={"memory_id": memory_id})
            return None

    # ---- step 3: graph expansion ----------------------------------------------------

    async def _expand(
        self,
        frontier: list[_Frontier],
        collected: dict[str, _Collected],
        *,
        max_neighbours: int,
        include_flagged: bool,
    ) -> None:
        liveness: dict[str, bool] = {}  # parent id -> is its own latest version
        added = 0
        for _ in range(self._graph_hops):
            next_frontier: list[_Frontier] = []
            for seed in frontier:
                for neighbour_id in await self._linked_ids(seed.memory.id, liveness):
                    if neighbour_id in collected or added >= max_neighbours:
                        continue
                    neighbour = await self._get_or_warn(neighbour_id)
                    if neighbour is None or not _visible(
                        neighbour, include_flagged=include_flagged
                    ):
                        continue
                    score = seed.score * GRAPH_DAMPING
                    evidence = (*_source_evidence(neighbour), seed.direct_hit_id)
                    collected[neighbour.id] = _Collected(
                        neighbour, score, RetrievalPath.GRAPH, evidence
                    )
                    next_frontier.append(_Frontier(neighbour, score, seed.direct_hit_id))
                    added += 1
            frontier = next_frontier
            if not frontier:
                break

    async def _linked_ids(self, memory_id: str, liveness: dict[str, bool]) -> list[str]:
        """Other endpoints of the memory's links worth following, in link order."""
        neighbours: list[str] = []
        for link in await self._store.parents_of(memory_id):
            if link.link_class is LinkClass.SNAPSHOT_OF or await self._is_live(
                link.parent_id, liveness
            ):
                neighbours.append(link.parent_id)
        # In the dependents direction this memory is the parent; it was collected, so it
        # is visible and therefore its own latest version: no history check needed.
        neighbours.extend(link.dependent_id for link in await self._store.dependents_of(memory_id))
        return neighbours

    async def _is_live(self, parent_id: str, liveness: dict[str, bool]) -> bool:
        # A depends_on link is history when its parent is superseded (ADR-0014).
        if parent_id not in liveness:
            liveness[parent_id] = (await self._store.latest_version(parent_id)).id == parent_id
        return liveness[parent_id]


def _visible(memory: Memory, *, include_flagged: bool) -> bool:
    return bool(visible_for_retrieval([memory], include_flagged=include_flagged))


def _source_evidence(memory: Memory) -> tuple[str, ...]:
    return (memory.source_ref,) if memory.source_ref else ()
