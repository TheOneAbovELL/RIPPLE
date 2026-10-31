"""HybridRetriever against the in-memory store and backend."""

import asyncio
from datetime import timedelta

import pytest

from ripple.core.errors import ConfigurationError
from ripple.core.models import Status
from ripple.core.retrieval_contract import RetrievalPath
from ripple.retrieval.fusion import RRF_K
from ripple.retrieval.hybrid import GRAPH_DAMPING, HybridRetriever, candidate_count
from tests.builders import USER, derived, fact, link, memory, snapshot_link
from tests.fakes.clock import DEFAULT_START

DAY = timedelta(days=1)


def _search(retriever: HybridRetriever, query: str, **kwargs):
    return asyncio.run(retriever.search(USER, query, **kwargs))


def _ids(results):
    return [r.memory.id for r in results]


# ---- direct hits ---------------------------------------------------------------------


def test_search_returns_lexical_hit_with_source_evidence(seeder):
    python = memory(content="likes Python", source_ref="msg-7")
    seeder.seed([python, memory(content="likes Rust")])
    [hit] = _search(HybridRetriever(seeder.store, seeder.backend), "python")
    assert hit.memory == python
    assert hit.via is RetrievalPath.LEXICAL
    assert hit.flagged is False
    assert hit.evidence == ("msg-7",)


def test_search_empty_query_returns_nothing(seeder):
    seeder.seed([memory(content="likes Python")])
    assert _search(HybridRetriever(seeder.store, seeder.backend), "   ") == []


def test_search_other_users_memories_never_appear(seeder):
    seeder.seed([memory(content="likes Python", user_id="student-2")])
    assert _search(HybridRetriever(seeder.store, seeder.backend), "python") == []


def test_search_k_limits_direct_hits(seeder):
    seeder.seed([memory(content=f"python note {i}") for i in range(6)])
    assert len(_search(HybridRetriever(seeder.store, seeder.backend), "python", k=4)) == 4


def test_search_default_k_comes_from_the_constructor(seeder):
    seeder.seed([memory(content=f"python note {i}") for i in range(6)])
    assert len(_search(HybridRetriever(seeder.store, seeder.backend, k=2), "python")) == 2


def test_search_rejects_non_positive_k(seeder):
    with pytest.raises(ValueError):
        _search(HybridRetriever(seeder.store, seeder.backend), "python", k=0)


def test_retriever_rejects_non_positive_k_and_negative_hops_at_construction(seeder):
    with pytest.raises(ConfigurationError):
        HybridRetriever(seeder.store, seeder.backend, k=0)
    with pytest.raises(ConfigurationError):
        HybridRetriever(seeder.store, seeder.backend, graph_hops=-1)


def test_search_oversamples_so_retired_top_matches_do_not_starve_valid_ones(seeder):
    # Six old versions outrank the live memory lexically; with k=1 and no oversampling the
    # one candidate would be retired and the answer empty.
    retired = [
        memory(content="python python python", status=Status.RETIRED, at=DEFAULT_START - i * DAY)
        for i in range(1, 7)
    ]
    live = memory(content="python")
    seeder.seed([*retired, live])
    assert candidate_count(1) > len(retired)
    assert _ids(_search(HybridRetriever(seeder.store, seeder.backend, k=1), "python")) == [live.id]


def test_search_tolerates_an_index_entry_whose_memory_was_forgotten(seeder):
    ghost, live = memory(content="python ghost"), memory(content="python")
    seeder.seed([live])
    asyncio.run(seeder.backend.index(ghost, None))  # indexed, never stored
    assert _ids(_search(HybridRetriever(seeder.store, seeder.backend), "python")) == [live.id]


# ---- flags ---------------------------------------------------------------------------


def test_search_hides_flagged_memories_unless_asked_and_then_flags_them(seeder):
    valid = memory(content="python valid")
    suspect = memory(content="python suspect", status=Status.SUSPECT)
    pending = memory(content="python pending", status=Status.PENDING_USER)
    seeder.seed([valid, suspect, pending])
    retriever = HybridRetriever(seeder.store, seeder.backend)
    assert _ids(_search(retriever, "python")) == [valid.id]
    flagged = _search(retriever, "python", include_flagged=True)
    assert {r.memory.id: r.flagged for r in flagged} == {
        valid.id: False,
        suspect.id: True,
        pending.id: True,
    }


# ---- graph expansion -----------------------------------------------------------------


def test_search_graph_expansion_pulls_the_live_parent_with_damped_score_and_evidence(seeder):
    cgpa_v1 = fact("student", "cgpa", 7.6, content="grade was", status=Status.RETIRED)
    cgpa_v2 = fact(
        "student",
        "cgpa",
        7.9,
        content="grade is",
        version=2,
        supersedes_id=cgpa_v1.id,
        at=DEFAULT_START + DAY,
    )
    eligibility = derived("eligible for Acme")
    # ADR-0014: the old link stays on v1 (history) and a copy points at v2.
    seeder.seed(
        [cgpa_v1, cgpa_v2, eligibility],
        [link(cgpa_v1, eligibility), link(cgpa_v2, eligibility, at=DEFAULT_START + DAY)],
    )
    results = _search(HybridRetriever(seeder.store, seeder.backend), "acme")
    assert _ids(results) == [eligibility.id, cgpa_v2.id]
    parent = results[1]
    assert parent.via is RetrievalPath.GRAPH
    assert parent.evidence == ("msg-1", eligibility.id)
    assert parent.score == pytest.approx(results[0].score * GRAPH_DAMPING)


def test_search_graph_expansion_skips_history_links_even_when_their_parent_is_visible(seeder):
    # Versioning always retires a superseded row, so I1 would hide v1 anyway; this guards
    # the history rule itself (ADR-0014) with an artificially still-VALID old version.
    cgpa_v1 = fact("student", "cgpa", 7.6, content="grade was")
    cgpa_v2 = fact(
        "student",
        "cgpa",
        7.9,
        content="grade is",
        version=2,
        supersedes_id=cgpa_v1.id,
        at=DEFAULT_START + DAY,
    )
    eligibility = derived("eligible for Acme")
    seeder.seed(
        [cgpa_v1, cgpa_v2, eligibility],
        [link(cgpa_v1, eligibility), link(cgpa_v2, eligibility, at=DEFAULT_START + DAY)],
    )
    results = _search(HybridRetriever(seeder.store, seeder.backend), "acme")
    assert _ids(results) == [eligibility.id, cgpa_v2.id]


def test_search_graph_expansion_reaches_dependents_too(seeder):
    cgpa = fact("student", "cgpa", 7.6)
    eligibility = derived("not eligible for Acme")
    seeder.seed([cgpa, eligibility], [link(cgpa, eligibility)])
    results = _search(HybridRetriever(seeder.store, seeder.backend), "cgpa")
    assert _ids(results) == [cgpa.id, eligibility.id]
    assert results[1].via is RetrievalPath.GRAPH


def test_search_graph_expansion_follows_snapshot_links_to_a_visible_parent(seeder):
    # ADR-0014: retrieval always shows snapshot_of links, so an application can cite the
    # resume version it was sent with while that version is still visible.
    resume_v1 = memory(content="resume v1", kind="resume")
    application = derived("applied to Acme with resume")
    seeder.seed([resume_v1, application], [snapshot_link(resume_v1, application)])
    results = _search(HybridRetriever(seeder.store, seeder.backend), "acme")
    assert [(r.memory.id, r.via) for r in results] == [
        (application.id, RetrievalPath.LEXICAL),
        (resume_v1.id, RetrievalPath.GRAPH),
    ]


def test_search_graph_expansion_hides_a_superseded_snapshot_parent(seeder):
    resume_v1 = memory(content="resume v1", kind="resume", status=Status.RETIRED)
    resume_v2 = memory(
        content="resume v2",
        kind="resume",
        version=2,
        supersedes_id=resume_v1.id,
        at=DEFAULT_START + DAY,
    )
    application = derived("applied to Acme with resume")
    seeder.seed([resume_v1, resume_v2, application], [snapshot_link(resume_v1, application)])
    results = _search(HybridRetriever(seeder.store, seeder.backend), "acme")
    assert _ids(results) == [application.id]


def test_search_graph_neighbour_that_is_retired_is_never_shown(seeder):
    cgpa = fact("student", "cgpa", 7.6)
    stale = derived("stale belief about Acme", status=Status.RETIRED)
    seeder.seed([cgpa, stale], [link(cgpa, stale)])
    results = _search(HybridRetriever(seeder.store, seeder.backend), "cgpa")
    assert _ids(results) == [cgpa.id]


def test_search_invisible_neighbours_do_not_spend_the_neighbour_budget(seeder):
    cgpa = fact("student", "cgpa", 7.6)
    retired_first = derived("old belief", status=Status.RETIRED)
    valid_later = derived("current belief")
    seeder.seed(
        [cgpa, retired_first, valid_later],
        [link(cgpa, retired_first), link(cgpa, valid_later, at=DEFAULT_START + DAY)],
    )
    results = _search(HybridRetriever(seeder.store, seeder.backend, k=1), "cgpa")
    assert _ids(results) == [cgpa.id, valid_later.id]


def test_search_invisible_neighbours_do_not_seed_the_next_hop(seeder):
    cgpa = fact("student", "cgpa", 7.6)
    retired_middle = derived("retired eligibility", status=Status.RETIRED)
    grandchild = derived("recommendation built on the retired belief")
    seeder.seed(
        [cgpa, retired_middle, grandchild],
        [link(cgpa, retired_middle), link(retired_middle, grandchild)],
    )
    results = _search(HybridRetriever(seeder.store, seeder.backend, graph_hops=2), "cgpa")
    assert _ids(results) == [cgpa.id]


def test_search_graph_neighbour_that_is_suspect_is_flagged_only_when_asked(seeder):
    cgpa = fact("student", "cgpa", 7.6)
    suspect = derived("eligibility under review", status=Status.SUSPECT)
    seeder.seed([cgpa, suspect], [link(cgpa, suspect)])
    retriever = HybridRetriever(seeder.store, seeder.backend)
    assert _ids(_search(retriever, "cgpa")) == [cgpa.id]
    results = _search(retriever, "cgpa", include_flagged=True)
    assert [(r.memory.id, r.flagged, r.via) for r in results] == [
        (cgpa.id, False, RetrievalPath.LEXICAL),
        (suspect.id, True, RetrievalPath.GRAPH),
    ]


def test_search_retired_direct_candidate_never_seeds_expansion(seeder):
    old = memory(content="python old", status=Status.RETIRED)
    neighbour = derived("belief that only the old version linked to")
    seeder.seed([old, neighbour], [link(old, neighbour)])
    assert _search(HybridRetriever(seeder.store, seeder.backend), "python") == []


def test_search_expand_graph_false_returns_direct_hits_only(seeder):
    cgpa = fact("student", "cgpa", 7.6)
    eligibility = derived("not eligible for Acme")
    seeder.seed([cgpa, eligibility], [link(cgpa, eligibility)])
    results = _search(HybridRetriever(seeder.store, seeder.backend), "cgpa", expand_graph=False)
    assert _ids(results) == [cgpa.id]


def test_search_graph_hops_zero_returns_direct_hits_only(seeder):
    cgpa = fact("student", "cgpa", 7.6)
    eligibility = derived("not eligible for Acme")
    seeder.seed([cgpa, eligibility], [link(cgpa, eligibility)])
    results = _search(HybridRetriever(seeder.store, seeder.backend, graph_hops=0), "cgpa")
    assert _ids(results) == [cgpa.id]


def test_search_graph_hops_two_reaches_the_grandchild_citing_the_direct_hit(seeder):
    cgpa = fact("student", "cgpa", 7.6)
    eligibility = derived("not eligible for Acme")
    recommendation = derived("skip Acme this season")
    seeder.seed(
        [cgpa, eligibility, recommendation],
        [link(cgpa, eligibility), link(eligibility, recommendation)],
    )
    one_hop = _search(HybridRetriever(seeder.store, seeder.backend), "cgpa")
    assert _ids(one_hop) == [cgpa.id, eligibility.id]
    two_hops = _search(HybridRetriever(seeder.store, seeder.backend, graph_hops=2), "cgpa")
    assert _ids(two_hops) == [cgpa.id, eligibility.id, recommendation.id]
    # Contract: a GRAPH result cites the direct hit it was reached from, not the hop.
    assert two_hops[2].evidence == ("msg-1", cgpa.id)
    assert two_hops[2].score == pytest.approx(one_hop[0].score * GRAPH_DAMPING**2)


def test_search_graph_neighbours_are_capped_at_k(seeder):
    cgpa = fact("student", "cgpa", 7.6)
    dependents = [derived(f"belief {i}") for i in range(5)]
    seeder.seed([cgpa, *dependents], [link(cgpa, d) for d in dependents])
    results = _search(HybridRetriever(seeder.store, seeder.backend, k=2), "cgpa")
    assert len(results) == 3  # one direct hit plus at most k neighbours
    assert results[0].memory.id == cgpa.id


def test_search_direct_hit_is_not_duplicated_as_a_neighbour(seeder):
    cgpa = fact("student", "cgpa", 7.6, content="cgpa fact")
    eligibility = derived("cgpa too low for Acme")
    seeder.seed([cgpa, eligibility], [link(cgpa, eligibility)])
    results = _search(HybridRetriever(seeder.store, seeder.backend), "cgpa")
    assert sorted(_ids(results)) == sorted([cgpa.id, eligibility.id])
    assert all(r.via is RetrievalPath.LEXICAL for r in results)


# ---- dense path and fusion -----------------------------------------------------------


def test_search_with_embedder_fuses_dense_and_lexical_ranks(dense_seeder, embedder):
    # "offer from Acme" is rank 1 in both lists: its fused score is exactly 2/(RRF_K+1),
    # which a lexical-only run (1/(RRF_K+1)) cannot produce.
    both = memory(content="offer from Acme")
    other = memory(content="Acme campus talk")
    dense_seeder.seed([both, other])
    retriever = HybridRetriever(dense_seeder.store, dense_seeder.backend, embedder)
    results = _search(retriever, "Acme offer")
    assert results[0].memory.id == both.id
    assert results[0].score == pytest.approx(2 / (RRF_K + 1))
    assert results[0].via is RetrievalPath.LEXICAL  # rank 1 in both; the first list wins ties
    assert embedder.calls[-1] == ["Acme offer"]


def test_search_dense_only_match_arrives_via_dense(dense_seeder, embedder):
    # No lexical overlap with the query at all: the hit can only come from the dense path.
    offer = memory(content="offer from Acme")
    dense_seeder.seed([offer])
    retriever = HybridRetriever(dense_seeder.store, dense_seeder.backend, embedder)
    results = _search(retriever, "Globex")
    assert [(r.memory.id, r.via) for r in results] == [(offer.id, RetrievalPath.DENSE)]


def test_search_without_embedder_never_calls_dense(seeder):
    class ExplodingDense:
        async def lexical(self, user_id, query, k):
            return await seeder.backend.lexical(user_id, query, k)

        async def dense(self, user_id, vector, k):
            raise AssertionError("dense must not run without an embedder")

        async def index(self, memory, embedding):
            await seeder.backend.index(memory, embedding)

    seeder.seed([memory(content="likes Python")])
    assert len(_search(HybridRetriever(seeder.store, ExplodingDense()), "python")) == 1


# ---- ordering ------------------------------------------------------------------------


def test_search_ordering_is_deterministic_across_runs(seeder):
    memories = [memory(content="python") for _ in range(4)]
    seeder.seed(memories)
    retriever = HybridRetriever(seeder.store, seeder.backend)
    first = _ids(_search(retriever, "python"))
    assert first == sorted(first)
    assert all(_ids(_search(retriever, "python")) == first for _ in range(3))
