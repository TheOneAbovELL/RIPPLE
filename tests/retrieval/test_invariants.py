"""Named invariant test for I1 at the retriever level (CLAUDE.md).

tests/core/test_invariants.py proves the visibility rule; this one proves the retriever
routes every path (lexical, dense, graph) through it.
"""

import asyncio

from ripple.core.models import Status
from ripple.core.retrieval_contract import RetrievalPath
from ripple.retrieval.hybrid import HybridRetriever
from tests.builders import USER, derived, fact, link


def test_invariant_I1_retriever_never_returns_retired_and_flags_suspect(dense_seeder, embedder):
    cgpa = fact("student", "cgpa", 7.6, content="cgpa is 7.6")
    retired_hit = fact("student", "cgpa", 7.1, content="cgpa was 7.1", status=Status.RETIRED)
    suspect_hit = derived("cgpa may change after re-evaluation", status=Status.SUSPECT)
    pending_hit = derived("cgpa confirmation requested", status=Status.PENDING_USER)
    retired_neighbour = derived("outdated eligibility", status=Status.RETIRED)
    suspect_neighbour = derived("eligibility under review", status=Status.SUSPECT)
    valid_neighbour = derived("eligible for Globex")
    dense_seeder.seed(
        [
            cgpa,
            retired_hit,
            suspect_hit,
            pending_hit,
            retired_neighbour,
            suspect_neighbour,
            valid_neighbour,
        ],
        [link(cgpa, retired_neighbour), link(cgpa, suspect_neighbour), link(cgpa, valid_neighbour)],
    )
    retriever = HybridRetriever(dense_seeder.store, dense_seeder.backend, embedder, k=20)

    plain = asyncio.run(retriever.search(USER, "cgpa"))
    assert {r.memory.id for r in plain} == {cgpa.id, valid_neighbour.id}
    assert all(r.flagged is False for r in plain)
    # The dense path ranks every embedded memory, so the neighbour may arrive as a direct
    # dense hit rather than via GRAPH; which path found it is irrelevant to I1.
    assert {r.memory.id: r.via for r in plain}[cgpa.id] is RetrievalPath.LEXICAL

    flagged = asyncio.run(retriever.search(USER, "cgpa", include_flagged=True))
    by_id = {r.memory.id: r for r in flagged}
    assert Status.RETIRED not in {r.memory.status for r in flagged}
    assert set(by_id) == {
        cgpa.id,
        suspect_hit.id,
        pending_hit.id,
        suspect_neighbour.id,
        valid_neighbour.id,
    }
    assert all(by_id[m.id].flagged for m in (suspect_hit, pending_hit, suspect_neighbour))
    assert not by_id[cgpa.id].flagged and not by_id[valid_neighbour.id].flagged
