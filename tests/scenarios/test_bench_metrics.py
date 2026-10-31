"""Worked examples for the metric functions (bench/metrics.py, ADR-0063, ADR-0120).

The expected numbers are computed by hand in docs/learning/bench.md, section "Worked
example"; the edge-case tests at the end pin definitions the worked example leaves open.
"""

from datetime import UTC, datetime

import pytest
from bench.metrics import (
    ConvergenceRecord,
    TargetOutcome,
    TTCReport,
    correct_updates,
    cost_per_ripple,
    questions_asked,
    questions_needed,
    scenario_metrics,
    stale_ids_at,
    stale_kept,
    stale_recommendation_rate,
    stale_retrieval_rate,
    suite_metrics,
    target_outcomes,
    time_to_consistency,
    wrongful_changes,
)
from bench.replay import (
    EventSnapshot,
    GoldState,
    MemorySnapshot,
    RecommendationSnapshot,
    ReplayTrace,
    RetrievedSnapshot,
    VersionState,
)

from ripple.core.models import ChangeEvent, Decision, DecisionAction, TriggerKind
from ripple.core.retrieval_contract import RetrievalPath, RetrievedMemory
from tests.builders import USER, derived, fact

START = datetime(2026, 10, 19, 9, 0, tzinfo=UTC)


def _v(id: str, status: str = "VALID", version: int = 1, content: str = "x") -> VersionState:
    return VersionState(id=id, status=status, version=version, content=content)


def _mem(alias: str, root: VersionState | None, latest: VersionState | None) -> MemorySnapshot:
    return MemorySnapshot(alias=alias, root=root, latest=latest)


def _event(index, action, memories, gold=None, recs=(), day=0.0, calls=0) -> EventSnapshot:
    return EventSnapshot(
        index=index,
        action=action,
        simulated_day=day,
        memories={m.alias: m for m in memories},
        recommendations=tuple(recs),
        gold=gold or {},
        resolver_calls=calls,
        pending_questions=0,
    )


# ---- the worked example: cgpa -> eligibility -> recommendation, one update then one keep


def worked_trace() -> ReplayTrace:
    """Event 1: cgpa rises; gold wants eligibility v2 "eligible" and recommendation v2
    "apply". The system updated eligibility correctly but left recommendation alone.
    Event 2: an unrelated opening deadline moves; gold wants everything else unchanged,
    but the system rewrote recommendation to "apply" (late and unasked)."""
    seed = _event(
        0,
        "seed",
        [
            _mem("cgpa", _v("cgpa", content="CGPA is 7.6"), _v("cgpa", content="CGPA is 7.6")),
            _mem(
                "eligibility",
                _v("eligibility", content="not eligible"),
                _v("eligibility", content="not eligible"),
            ),
            _mem(
                "recommendation",
                _v("recommendation", content="skip"),
                _v("recommendation", content="skip"),
            ),
            _mem(
                "acme", _v("acme", content="Acme SDE intern"), _v("acme", content="Acme SDE intern")
            ),
        ],
        recs=[
            RecommendationSnapshot(
                "acme", "acme", True, 1.0, False, ("eligibility", "recommendation")
            )
        ],
    )
    after_cgpa = _event(
        1,
        "update:cgpa",
        [
            _mem(
                "cgpa",
                _v("cgpa", "RETIRED", 1, "CGPA is 7.6"),
                _v("cgpa-v2", "VALID", 2, "CGPA is 7.9"),
            ),
            _mem(
                "eligibility",
                _v("eligibility", "RETIRED", 1, "not eligible"),
                _v("elig-v2", "VALID", 2, "eligible"),
            ),
            _mem(
                "recommendation",
                _v("recommendation", content="skip"),
                _v("recommendation", content="skip"),
            ),
            _mem(
                "acme", _v("acme", content="Acme SDE intern"), _v("acme", content="Acme SDE intern")
            ),
        ],
        gold={
            "cgpa": GoldState(status="RETIRED"),
            "eligibility@latest": GoldState(status="VALID", version=2, content="eligible"),
            "recommendation@latest": GoldState(status="VALID", version=2, content="apply"),
            "acme": GoldState(status="VALID", version=1),
        },
        recs=[
            RecommendationSnapshot("acme", "acme", True, 1.0, False, ("elig-v2", "recommendation"))
        ],
        day=0.0,
        calls=1,
    )
    after_deadline = _event(
        2,
        "update:acme",
        [
            _mem(
                "cgpa",
                _v("cgpa", "RETIRED", 1, "CGPA is 7.6"),
                _v("cgpa-v2", "VALID", 2, "CGPA is 7.9"),
            ),
            _mem(
                "eligibility",
                _v("eligibility", "RETIRED", 1, "not eligible"),
                _v("elig-v2", "VALID", 2, "eligible"),
            ),
            _mem(
                "recommendation",
                _v("recommendation", "RETIRED", 1, "skip"),
                _v("rec-v2", "VALID", 2, "apply"),
            ),
            _mem(
                "acme",
                _v("acme", "RETIRED", 1, "Acme SDE intern"),
                _v("acme-v2", "VALID", 2, "Acme SDE intern, new deadline"),
            ),
        ],
        gold={
            "acme@latest": GoldState(status="VALID", version=2),
            "eligibility@latest": GoldState(status="VALID", version=2, content="eligible"),
            "recommendation@latest": GoldState(status="VALID", version=1, content="skip"),
        },
        recs=[RecommendationSnapshot("acme-v2", "acme", True, 1.0, False, ("elig-v2", "rec-v2"))],
        day=3.0,
        calls=3,
    )
    return ReplayTrace("worked", "check_everything", START, [seed, after_cgpa, after_deadline])


def test_target_outcomes_flattens_every_event_target_pair_in_order():
    outcomes = target_outcomes(worked_trace())
    assert [(o.event_index, o.target) for o in outcomes] == [
        (1, "cgpa"),
        (1, "eligibility@latest"),
        (1, "recommendation@latest"),
        (1, "acme"),
        (2, "acme@latest"),
        (2, "eligibility@latest"),
        (2, "recommendation@latest"),
    ]
    by_key = {(o.event_index, o.target): o for o in outcomes}
    assert by_key[(1, "eligibility@latest")] == TargetOutcome(
        1,
        "eligibility@latest",
        before=_v("eligibility", content="not eligible"),
        observed=_v("elig-v2", "VALID", 2, "eligible"),
        should_change=True,
        matches_gold=True,
        moved=True,
    )
    assert by_key[(1, "recommendation@latest")].should_change is True
    assert by_key[(1, "recommendation@latest")].moved is False
    assert by_key[(2, "recommendation@latest")].should_change is False
    assert by_key[(2, "recommendation@latest")].moved is True
    assert by_key[(1, "acme")].should_change is False and by_key[(1, "acme")].moved is False


def test_correct_updates_counts_should_change_targets_that_match_gold():
    # event 1: cgpa (RETIRED, correct), eligibility@latest (correct); recommendation stale.
    # event 2: acme@latest (correct). → 3
    assert correct_updates(target_outcomes(worked_trace())) == 3


def test_stale_kept_counts_should_change_targets_that_did_not_move():
    # event 1: recommendation@latest should be v2 "apply" and is still v1 "skip". → 1
    assert stale_kept(target_outcomes(worked_trace())) == 1


def test_wrongful_changes_counts_should_stay_targets_that_moved():
    # event 2: recommendation@latest should stay v1 "skip" and became v2 "apply". → 1
    assert wrongful_changes(target_outcomes(worked_trace())) == 1


def test_questions_asked_counts_ask_decisions_across_events():
    asked = Decision(memory_id="e", wave=1, action=DecisionAction.ASK, reason="unsure")
    kept = Decision(memory_id="r", wave=1, action=DecisionAction.KEEP, reason="fine")
    events = [
        ChangeEvent(
            user_id=USER,
            trigger_kind=TriggerKind.USER_EDIT,
            trigger_memory_id="c",
            decisions=[asked, kept],
            created_at=START,
        ),
        ChangeEvent(
            user_id=USER,
            trigger_kind=TriggerKind.USER_ANSWER,
            trigger_memory_id="e",
            decisions=[asked],
            created_at=START,
        ),
    ]
    assert questions_asked(events) == 2
    assert questions_asked([]) == 0


def test_stale_retrieval_rate_counts_unflagged_hits_on_gold_stale_rows():
    stale = fact("student", "cgpa", 7.6, id="cgpa")
    fresh = derived("eligible", id="elig-v2")
    flagged_stale = derived("skip", id="recommendation")
    retrieved = [
        RetrievedMemory(stale, 0.9, flagged=False, via=RetrievalPath.LEXICAL),
        RetrievedMemory(fresh, 0.8, flagged=False, via=RetrievalPath.LEXICAL),
        RetrievedMemory(flagged_stale, 0.7, flagged=True, via=RetrievalPath.GRAPH),
        RetrievedMemory(fresh, 0.6, flagged=False, via=RetrievalPath.GRAPH),
    ]
    # 1 unflagged stale hit out of 4 results; the flagged stale one was warned about.
    assert stale_retrieval_rate(retrieved, {"cgpa", "recommendation"}) == 0.25
    assert stale_retrieval_rate([], {"cgpa"}) == 0.0


def test_stale_recommendation_rate_counts_unflagged_recommendations_on_stale_beliefs():
    trace = worked_trace()
    # event 1: the one recommendation rests on "recommendation" (gold: v2 "apply", row
    # still v1 "skip") → stale. event 2: rests on rec-v2 "apply" (gold: v1 "skip" → the
    # latest row's content differs from gold) → stale. 2 of 2 pairs.
    assert stale_recommendation_rate(trace.events) == 1.0
    # With the second recommendation flagged, only the first counts: 1 of 2.
    flagged = trace.events[2]
    flagged_event = EventSnapshot(
        index=flagged.index,
        action=flagged.action,
        simulated_day=flagged.simulated_day,
        memories=flagged.memories,
        recommendations=(
            RecommendationSnapshot("acme-v2", "acme", True, 1.0, True, ("elig-v2", "rec-v2")),
        ),
        gold=flagged.gold,
        resolver_calls=flagged.resolver_calls,
        pending_questions=0,
    )
    assert stale_recommendation_rate([trace.events[0], trace.events[1], flagged_event]) == 0.5
    assert stale_recommendation_rate([trace.events[0]]) == 0.0


def test_time_to_consistency_reports_per_target_convergence_and_the_never_share():
    report = time_to_consistency(worked_trace())
    assert report == TTCReport(
        records=(
            ConvergenceRecord("cgpa", 1, ttc_events=0, ttc_days=0.0),
            ConvergenceRecord("eligibility@latest", 1, ttc_events=0, ttc_days=0.0),
            # Gold at event 2 asks for v1 "skip" again, so the event-1 window closes
            # before the v2 "apply" written at event 2 could count as convergence.
            ConvergenceRecord("recommendation@latest", 1, ttc_events=None, ttc_days=None),
            ConvergenceRecord("acme@latest", 2, ttc_events=0, ttc_days=0.0),
        ),
        share_never_converged=0.25,
    )


def test_time_to_consistency_counts_events_and_days_until_the_state_matches_gold():
    """newest_wins-like trace: the dependent catches up two events (five days) later."""
    first = _event(
        1,
        "update:cgpa",
        [_mem("elig", _v("elig", content="old"), _v("elig", content="old"))],
        gold={"elig@latest": GoldState(content="new")},
        day=0.0,
    )
    second = _event(
        2,
        "advance_days:2",
        [_mem("elig", _v("elig", content="old"), _v("elig", content="old"))],
        day=2.0,
    )
    third = _event(
        3,
        "update:elig",
        [_mem("elig", _v("elig", "RETIRED", 1, "old"), _v("elig-v2", "VALID", 2, "new"))],
        day=5.0,
    )
    seed = _event(0, "seed", [_mem("elig", _v("elig", content="old"), _v("elig", content="old"))])
    report = time_to_consistency(
        ReplayTrace("late", "newest_wins", START, [seed, first, second, third])
    )
    assert report.records == (ConvergenceRecord("elig@latest", 1, ttc_events=2, ttc_days=5.0),)
    assert report.share_never_converged == 0.0


def test_cost_per_ripple_divides_resolver_calls_by_change_events():
    events = [
        ChangeEvent(
            user_id=USER,
            trigger_kind=TriggerKind.USER_EDIT,
            trigger_memory_id="c",
            created_at=START,
        ),
        ChangeEvent(
            user_id=USER, trigger_kind=TriggerKind.EXPIRY, trigger_memory_id="x", created_at=START
        ),
    ]
    assert cost_per_ripple(events, resolver_calls=5) == 2.5
    assert cost_per_ripple([], resolver_calls=0) == 0.0


# ---- edge cases the worked example leaves open ----------------------------------------


def _forget_trace() -> ReplayTrace:
    """Event 1 forgets cgpa (gold: deleted); event 2 asserts it is still gone."""
    seed = _event(0, "seed", [_mem("cgpa", _v("cgpa"), _v("cgpa"))])
    gone = _mem("cgpa", None, None)
    first = _event(1, "forget:cgpa", [gone], gold={"cgpa": GoldState(deleted=True)})
    second = _event(2, "advance_days:1", [gone], gold={"cgpa": GoldState(deleted=True)}, day=1.0)
    return ReplayTrace("forget", "ripple", START, [seed, first, second])


def test_a_deletion_is_a_should_change_target_once_and_a_should_stay_target_after():
    outcomes = target_outcomes(_forget_trace())
    assert [(o.should_change, o.moved, o.matches_gold) for o in outcomes] == [
        (True, True, True),
        (False, False, True),
    ]
    assert correct_updates(outcomes) == 1 and wrongful_changes(outcomes) == 0


def test_a_target_unconverged_at_the_end_of_the_trace_never_converged():
    old = [_mem("elig", _v("elig", content="old"), _v("elig", content="old"))]
    seed = _event(0, "seed", old)
    first = _event(1, "update:cgpa", old, gold={"elig@latest": GoldState(content="new")})
    later = _event(2, "advance_days:3", old, day=3.0)
    report = time_to_consistency(ReplayTrace("never", "append_only", START, [seed, first, later]))
    assert report.records == (ConvergenceRecord("elig@latest", 1, None, None),)
    assert report.share_never_converged == 1.0
    assert time_to_consistency(ReplayTrace("empty", "ripple", START, [seed])) == TTCReport((), 0.0)


def test_stale_ids_name_retired_deleted_and_wrong_content_rows_only():
    snapshot = _event(
        1,
        "update:cgpa",
        [
            _mem("cgpa", _v("cgpa", "RETIRED"), _v("cgpa-v2", "VALID", 2, "CGPA is 7.9")),
            _mem("elig", _v("elig", content="not eligible"), _v("elig", content="not eligible")),
            _mem("acme", _v("acme", content="Acme"), _v("acme", content="Acme")),
            _mem("old", _v("old", content="gone soon"), _v("old", content="gone soon")),
            _mem("fresh", _v("fresh"), _v("fresh-v2", "VALID", 2)),
            _mem("lost", None, None),
        ],
        gold={
            "cgpa": GoldState(status="RETIRED"),
            "cgpa@latest": GoldState(status="VALID", version=2),
            "elig@latest": GoldState(status="VALID", content="eligible"),
            # Gold pins a newer version without its text: the old row is stale.
            "acme@latest": GoldState(status="VALID", version=2),
            # A row ahead of gold's version is over-correction, not staleness.
            "fresh@latest": GoldState(status="VALID", version=1),
            "old": GoldState(deleted=True),
            "lost": GoldState(status="VALID"),
        },
    )
    assert stale_ids_at(snapshot) == {"cgpa", "elig", "acme", "old"}


def test_events_without_gold_count_their_recommendations_in_the_denominator_only():
    trace = worked_trace()
    quiet = _event(
        3,
        "advance_days:1",
        list(trace.events[2].memories.values()),
        recs=[RecommendationSnapshot("acme-v2", "acme", True, 1.0, False, ("elig-v2", "rec-v2"))],
        day=4.0,
    )
    assert stale_recommendation_rate([*trace.events, quiet]) == 2 / 3


def test_questions_needed_counts_should_change_targets_whose_gold_is_pending_user():
    seed = _event(0, "seed", [_mem("elig", _v("elig"), _v("elig"))])
    parked = [_mem("elig", _v("elig", "PENDING_USER"), _v("elig", "PENDING_USER"))]
    pending = {"elig": GoldState(status="PENDING_USER")}
    asked = _event(1, "update:cutoff", parked, gold=pending)
    still = _event(2, "advance_days:1", parked, gold=pending)
    # The second event's gold is already satisfied: no new question is needed.
    assert questions_needed(ReplayTrace("ask", "ripple", START, [seed, asked, still])) == 1


def _with_retrieval(trace: ReplayTrace) -> ReplayTrace:
    """The worked trace with a probe after event 1: the unflagged old recommendation row
    (gold-stale), the fresh eligibility row and a flagged stale row (warned, not stale)."""
    event = trace.events[1]
    probed = EventSnapshot(
        index=event.index,
        action=event.action,
        simulated_day=event.simulated_day,
        memories=event.memories,
        recommendations=event.recommendations,
        gold=event.gold,
        resolver_calls=event.resolver_calls,
        pending_questions=0,
        retrieved=(
            RetrievedSnapshot("recommendation", "recommendation", False, "lexical"),
            RetrievedSnapshot("eligibility", "elig-v2", False, "lexical"),
            RetrievedSnapshot("cgpa", "cgpa", True, "lexical"),
        ),
    )
    events = [trace.events[0], probed, *trace.events[2:]]
    return ReplayTrace(trace.scenario, trace.strategy, START, events)


def _change_event(*actions: DecisionAction) -> ChangeEvent:
    decisions = [
        Decision(memory_id=f"m{i}", wave=1, action=action, reason="r")
        for i, action in enumerate(actions)
    ]
    return ChangeEvent(
        user_id=USER,
        trigger_kind=TriggerKind.USER_EDIT,
        trigger_memory_id="c",
        decisions=decisions,
        created_at=START,
    )


def test_scenario_metrics_collects_every_count_of_the_worked_example():
    metrics = scenario_metrics(
        _with_retrieval(worked_trace()),
        [_change_event(DecisionAction.RETIRE), _change_event(DecisionAction.KEEP)],
        resolver_calls=3,
    )
    assert (metrics.should_change, metrics.should_stay) == (4, 3)
    assert (metrics.correct_updates, metrics.stale_kept, metrics.wrongful_changes) == (3, 1, 1)
    assert metrics.wrong_updates == 0
    assert (metrics.recommendations_shown, metrics.stale_recommendations) == (2, 2)
    assert (metrics.retrieved, metrics.stale_retrieved) == (3, 1)
    assert (metrics.change_events, metrics.resolver_calls, metrics.llm_calls) == (2, 3, 0)
    assert metrics.ttc.share_never_converged == 0.25


def test_suite_metrics_pool_counts_before_taking_ratios():
    big = scenario_metrics(worked_trace(), [_change_event(), _change_event()], resolver_calls=4)
    small = scenario_metrics(_forget_trace(), [_change_event(DecisionAction.ASK)], resolver_calls=0)
    result = suite_metrics([big, small])
    metrics, totals = result["memory_metrics"], result["memory_totals"]
    assert isinstance(metrics, dict) and isinstance(totals, dict)
    # Pooled: (3 + 1) correct over (4 + 1) should-change, not the mean of 3/4 and 1/1.
    assert metrics["update_accuracy"] == pytest.approx(4 / 5)
    assert metrics["stale_kept"] == 1 / 2 and metrics["wrongful_changes"] == 1 / 2
    assert metrics["questions_asked"] == 1 / 2
    assert metrics["cost_per_ripple"] == pytest.approx(4 / 3)
    assert metrics["ttc_share_never_converged"] == pytest.approx(1 / 5)
    # No probe ran and no LLM was called: undefined, never a flattering 0.
    assert metrics["stale_retrieval_rate"] is None
    assert metrics["tokens_per_ripple"] is None and metrics["usd_per_ripple"] is None
    assert totals["scenarios"] == 2 and totals["should_change"] == 5
    assert totals["ttc_records"] == 5 and totals["ttc_never_converged"] == 1


def test_suite_metrics_of_no_scenarios_are_all_undefined():
    metrics = suite_metrics([])["memory_metrics"]
    assert isinstance(metrics, dict)
    assert all(value is None for value in metrics.values())


def test_a_repeated_unchanged_gold_keeps_the_convergence_window_open():
    old = [_mem("elig", _v("elig", content="old"), _v("elig", content="old"))]
    new = [_mem("elig", _v("elig", "RETIRED", 1, "old"), _v("elig-v2", "VALID", 2, "new"))]
    wanted = {"elig@latest": GoldState(content="new")}
    seed = _event(0, "seed", old)
    first = _event(1, "update:cgpa", old, gold=wanted)
    again = _event(2, "update:cgpa", new, gold=wanted, day=2.0)
    report = time_to_consistency(ReplayTrace("again", "ripple", START, [seed, first, again]))
    # The event-1 record converges at event 2 instead of closing there; event 2 opens
    # its own record (the target still had to change before it) and meets it at once.
    assert report.records == (
        ConvergenceRecord("elig@latest", 1, ttc_events=1, ttc_days=2.0),
        ConvergenceRecord("elig@latest", 2, ttc_events=0, ttc_days=0.0),
    )


def test_recommending_an_opening_gold_retired_is_stale_even_on_fresh_beliefs():
    seed = _event(0, "seed", [_mem("acme", _v("acme"), _v("acme"))])
    shown = _event(
        1,
        "advance_days:30",
        [_mem("acme", _v("acme"), _v("acme"))],
        gold={"acme": GoldState(status="RETIRED")},
        recs=[RecommendationSnapshot("acme", "acme", True, 1.0, False, ())],
    )
    assert stale_recommendation_rate([seed, shown]) == 1.0


def test_questions_needed_counts_one_question_when_two_targets_name_one_row():
    seed = _event(0, "seed", [_mem("elig", _v("elig"), _v("elig"))])
    parked = [_mem("elig", _v("elig", "PENDING_USER"), _v("elig", "PENDING_USER"))]
    pending = GoldState(status="PENDING_USER")
    asked = _event(1, "update:cutoff", parked, gold={"elig": pending, "elig@latest": pending})
    assert questions_needed(ReplayTrace("ask", "ripple", START, [seed, asked])) == 1


def test_dependent_accuracy_leaves_out_the_alias_the_event_wrote():
    metrics = scenario_metrics(worked_trace(), [], resolver_calls=0)
    # Event 1 acted on cgpa, event 2 on acme: their own targets are not dependents.
    assert (metrics.should_change_dependents, metrics.correct_dependents) == (2, 1)


def test_suite_metrics_pool_retrieval_counts_across_scenarios():
    probed = scenario_metrics(_with_retrieval(worked_trace()), [], resolver_calls=0)
    quiet = scenario_metrics(worked_trace(), [], resolver_calls=0)
    metrics = suite_metrics([probed, quiet])["memory_metrics"]
    assert isinstance(metrics, dict)
    assert metrics["stale_retrieval_rate"] == pytest.approx(1 / 3)
    assert metrics["dependent_update_accuracy"] == pytest.approx(2 / 4)
