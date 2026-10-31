"""Reciprocal rank fusion of ranked candidate lists (ADR-0050).

Lexical and dense scores live on different scales (BM25 is unbounded, cosine is in
[-1, 1]), so fusing by rank rather than by score needs no calibration and cannot be
dominated by one path. RRF_K = 60 is the constant from Cormack et al. (2009); it
flattens the difference between rank 1 and rank 2 enough that an item found by both
paths beats an item found by only one.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from ripple.core.retrieval_contract import RetrievalPath
from ripple.retrieval.backend import SearchHit

RRF_K = 60


@dataclass(frozen=True)
class FusedHit:
    memory_id: str
    score: float
    via: RetrievalPath  # the path that ranked it best; ties go to the first list given


def reciprocal_rank_fusion(
    ranked: Sequence[tuple[RetrievalPath, Sequence[SearchHit]]],
) -> list[FusedHit]:
    """Fuse ranked lists into one, best first; ties broken by memory id for determinism."""
    scores: dict[str, float] = {}
    best_rank: dict[str, tuple[int, int]] = {}  # memory id -> (rank, list position)
    via: dict[str, RetrievalPath] = {}
    for position, (path, hits) in enumerate(ranked):
        for rank, hit in enumerate(hits, start=1):
            scores[hit.memory_id] = scores.get(hit.memory_id, 0.0) + 1.0 / (RRF_K + rank)
            candidate = (rank, position)
            if hit.memory_id not in best_rank or candidate < best_rank[hit.memory_id]:
                best_rank[hit.memory_id] = candidate
                via[hit.memory_id] = path
    fused = [FusedHit(memory_id, score, via[memory_id]) for memory_id, score in scores.items()]
    fused.sort(key=lambda hit: (-hit.score, hit.memory_id))
    return fused
