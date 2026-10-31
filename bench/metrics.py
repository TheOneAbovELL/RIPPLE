"""RippleBench metric functions (ADR-0063 definitions; suite aggregation ADR-0120).

The definitions were fixed in ADR-0063 for the author to implement (roadmap Phase 3,
"[human] Metric functions"); on 2026-10-31 the author asked the collaborator to
implement them (docs/plans/final-delivery.md). Each body follows its docstring
literally; the worked examples in tests/scenarios/test_bench_metrics.py and the hand
computations in docs/learning/bench.md are the specification.

Inputs are the replay traces (bench/replay.py) the scenario runner records after every
event, the ChangeEvents the store holds at the end of a scenario, and for retrieval the
`RetrievedMemory` lists from contract C2. Nothing here calls an LLM or touches a store.

Vocabulary used by every definition:
- *target*: a key of an event's `expect` block, "alias" (the root row) or "alias@latest".
- *before(t)*: the target's state in the snapshot of event t-1 (index t-1 in the trace;
  index 0 is the seeded state).
- *gold(t)*: the target's GoldState at event t; *observed(t)*: its VersionState at t.
- *should change at t*: gold(t) is not satisfied by before(t)
  (`not gold.matches(before)`).
- *should stay at t*: gold(t) is satisfied by before(t).
- *moved*: observed(t) differs from before(t) in status, version or content, or one of
  them is None and the other is not (the row id is compared too; a new version always
  differs in version as well, so this changes nothing).
- *gold-stale row* (ADR-0123, amending this module's ADR-0063 wording): the row a gold
  target addresses when gold is RETIRED or deleted, names a content the row does not
  hold, or names a version newer than the row's (a newer version should exist).

`scenario_metrics` and `suite_metrics` (ADR-0120) combine the functions into the
`memory_metrics` object bench.run writes: counts are pooled over scenarios before any
ratio is taken, and per-scenario averages are totals divided by scenarios.
"""

import statistics
from collections.abc import Iterable, Sequence, Set
from dataclasses import dataclass

from bench.replay import EventSnapshot, GoldState, ReplayTrace, VersionState
from ripple.core.models import ChangeEvent, DecisionAction
from ripple.core.retrieval_contract import RetrievedMemory

PENDING_USER = "PENDING_USER"
GONE_STATUSES = frozenset({"RETIRED"})


@dataclass(frozen=True)
class TargetOutcome:
    """One (event, target) pair with everything a memory-level metric needs."""

    event_index: int
    target: str
    before: VersionState | None
    observed: VersionState | None
    should_change: bool
    matches_gold: bool
    moved: bool


@dataclass(frozen=True)
class ConvergenceRecord:
    """Time-to-consistency for one target that should change at `event_index`."""

    target: str
    event_index: int
    ttc_events: int | None  # None = never converged within the trace (or window closed)
    ttc_days: float | None  # simulated days between event t and convergence


@dataclass(frozen=True)
class TTCReport:
    records: tuple[ConvergenceRecord, ...]
    share_never_converged: float  # len(ttc_events is None) / len(records); 0.0 if no records


def target_outcomes(trace: ReplayTrace) -> list[TargetOutcome]:
    """Flatten a trace into (event, target) outcomes; the input to the memory metrics.

    For every event t >= 1 and every target in gold(t):
    before = trace.events[t-1].state_of(target); observed = trace.events[t].state_of(target);
    should_change = not gold.matches(before); matches_gold = gold.matches(observed);
    moved = before != observed (dataclass equality, None-aware).
    Order: events ascending, targets in the order the scenario lists them.
    """
    outcomes: list[TargetOutcome] = []
    for position in range(1, len(trace.events)):
        previous, current = trace.events[position - 1], trace.events[position]
        for target, gold in current.gold.items():
            before = previous.state_of(target)
            observed = current.state_of(target)
            outcomes.append(
                TargetOutcome(
                    event_index=current.index,
                    target=target,
                    before=before,
                    observed=observed,
                    should_change=not gold.matches(before),
                    matches_gold=gold.matches(observed),
                    moved=before != observed,
                )
            )
    return outcomes


def correct_updates(outcomes: Sequence[TargetOutcome]) -> int:
    """Count of outcomes with should_change and matches_gold.

    Example: cgpa rises; gold says eligibility@latest becomes version 2 "eligible";
    the system wrote exactly that → 1. If it wrote version 2 with other content → 0
    (it moved, but wrongly; see the remainder in `docs/learning/bench.md`).
    """
    return sum(1 for o in outcomes if o.should_change and o.matches_gold)


def stale_kept(outcomes: Sequence[TargetOutcome]) -> int:
    """Count of outcomes with should_change and not moved: the system did nothing to a
    belief that had to change. The headline failure of append_only and newest_wins,
    and of a ripple that stopped early (keep, truncation, missing link).
    """
    return sum(1 for o in outcomes if o.should_change and not o.moved)


def wrongful_changes(outcomes: Sequence[TargetOutcome]) -> int:
    """Count of outcomes with not should_change and moved: over-correction. A belief
    gold says must stay as it was (same status, version and content) was retired,
    updated or re-flagged. The headline failure of check_everything with an
    imperfect resolver, and of a ripple that follows a link it should not (snapshot_of).
    """
    return sum(1 for o in outcomes if not o.should_change and o.moved)


def questions_asked(events: Sequence[ChangeEvent]) -> int:
    """Number of Decisions with action ASK across the given ChangeEvents (one per memory
    parked in PENDING_USER). Baselines that never call a resolver score 0. Whether a
    question was *needed* is `gold(t).status == "PENDING_USER"` for that memory; the
    ratio needed/asked is derived in the report, not here.
    """
    return sum(1 for event in events for d in event.decisions if d.action is DecisionAction.ASK)


def questions_needed(trace: ReplayTrace) -> int:
    """Should-change targets whose gold status is PENDING_USER: a question the gold
    expects the system to open at that event (the "needed?" of docs/04). Two targets
    that address one row ("x" and "x@latest" before any new version) are one question."""
    needed: set[tuple[int, str]] = set()
    for o in target_outcomes(trace):
        if o.should_change and _gold_of(trace, o).status == PENDING_USER:
            row = o.observed.id if o.observed is not None else o.target
            needed.add((o.event_index, row))
    return len(needed)


def stale_ids_at(snapshot: EventSnapshot) -> frozenset[str]:
    """Ids of rows gold says are stale at this event: for every gold target, the row
    the target addresses (root for "alias", latest for "alias@latest") when gold's
    status is RETIRED or deleted, when gold names a content the row does not hold, or
    when gold names a version newer than the row's (ADR-0123: gold often pins a derived
    belief's new version without its text; the old version is then what is stale).
    Rows no gold target names are never stale (gold is the labelled set, ADR-0063)."""
    stale: set[str] = set()
    for target, gold in snapshot.gold.items():
        row = snapshot.state_of(target)
        if row is None:
            continue
        gone = gold.deleted or gold.status in GONE_STATUSES
        wrong_content = gold.content is not None and row.content != gold.content
        behind = gold.version is not None and row.version < gold.version
        if gone or wrong_content or behind:
            stale.add(row.id)
    return frozenset(stale)


def stale_hits(shown: Iterable[tuple[str, bool]], stale_ids: Set[str]) -> int:
    """Unflagged (memory id, flagged) pairs whose id is gold-stale; the shared numerator
    of both stale rates, so a trace replayed from JSON counts exactly as a live run."""
    return sum(1 for memory_id, flagged in shown if not flagged and memory_id in stale_ids)


def stale_retrieval_rate(retrieved: Sequence[RetrievedMemory], stale_ids: Set[str]) -> float:
    """Share of retrieved memories shown *without* a flag whose id is in `stale_ids`.

    `stale_ids` is the gold-stale set at the moment of retrieval: ids of memory rows
    whose gold status at that event is RETIRED or deleted, whose gold content differs
    from the row's content, or whose gold version is newer (`stale_ids_at`). A flagged
    result (SUSPECT/PENDING_USER, I1) is
    not counted as stale: the agent was warned. Returns 0.0 for an empty list.
    rate = |{r : not r.flagged and r.memory.id in stale_ids}| / |retrieved|
    """
    if not retrieved:
        return 0.0
    hits = stale_hits(((r.memory.id, r.flagged) for r in retrieved), stale_ids)
    return hits / len(retrieved)


def stale_recommendation_counts(snapshots: Sequence[EventSnapshot]) -> tuple[int, int]:
    """(stale unflagged pairs, all pairs) behind `stale_recommendation_rate`; pooled
    across scenarios by `suite_metrics` before the ratio is taken."""
    stale = shown = 0
    for snapshot in snapshots:
        if snapshot.index == 0:
            continue
        stale_ids = stale_ids_at(snapshot)
        for rec in snapshot.recommendations:
            shown += 1
            # The opening itself counts too (ADR-0123): recommending a retired opening
            # is acting on a stale belief as much as resting on one.
            rests_on = (rec.opening_id, *rec.based_on)
            if not rec.flagged and any(memory_id in stale_ids for memory_id in rests_on):
                stale += 1
    return stale, shown


def stale_recommendation_rate(snapshots: Sequence[EventSnapshot]) -> float:
    """Share of (event, recommendation) pairs shown without a flag while resting on a
    belief gold says is stale at that event.

    A recommendation at event t is stale when its opening id or any id in `based_on`
    is the id of a gold-stale row at t (`stale_ids_at`: gold RETIRED/deleted, gold
    content differing from the row's, or gold version newer; ADR-0123), resolved
    through the snapshot's memories: a root id matches the root state, a latest id
    matches the latest state. Pairs with flagged=True
    are excluded from the numerator, never from the denominator. Returns 0.0 when no
    recommendation was shown. Events with no gold contribute pairs to the denominator
    only. Seed snapshots (index 0) are skipped.
    """
    stale, shown = stale_recommendation_counts(snapshots)
    return stale / shown if shown else 0.0


def time_to_consistency(trace: ReplayTrace) -> TTCReport:
    """docs/proposals/0003: for every target that should change at event t, the number
    of events k >= 0 until observed(t+k) satisfies gold(t), and the simulated days
    between the two snapshots. The window closes when a later event t' > t carries a
    new gold for the same target before convergence: ttc is then None (never). A gold
    that repeats gold(t) unchanged is not new and keeps the window open (ADR-0123). A
    target still unconverged at the end of the trace is None. Records are ordered like
    `target_outcomes`. share_never_converged = (#None) / (#records), 0.0 if no records.
    Append_only has None everywhere that propagation is needed; newest_wins has 0 for
    the direct fact and None for its dependents; ripple's distribution is the claim.
    """
    position_of = {snapshot.index: position for position, snapshot in enumerate(trace.events)}
    records: list[ConvergenceRecord] = []
    for outcome in target_outcomes(trace):
        if not outcome.should_change:
            continue
        start = position_of[outcome.event_index]
        gold = trace.events[start].gold[outcome.target]
        ttc_events: int | None = None
        ttc_days: float | None = None
        for position in range(start, len(trace.events)):
            later = trace.events[position]
            # A newer gold for the target closes the window, even if the state now
            # happens to satisfy the old gold (the worked example's recommendation).
            if position > start and later.gold.get(outcome.target, gold) != gold:
                break
            if gold.matches(later.state_of(outcome.target)):
                ttc_events = position - start
                ttc_days = later.simulated_day - trace.events[start].simulated_day
                break
        records.append(ConvergenceRecord(outcome.target, outcome.event_index, ttc_events, ttc_days))
    never = sum(1 for r in records if r.ttc_events is None)
    return TTCReport(tuple(records), never / len(records) if records else 0.0)


def cost_per_ripple(events: Sequence[ChangeEvent], resolver_calls: int) -> float:
    """resolver_calls / number of ChangeEvents (every trigger opens exactly one event:
    user_edit, ripple, expiry, user_answer). 0.0 when there are no events. The bench
    reports it beside the strategy name, so check_everything's cost is the ceiling
    that H1's "<20% of its cost" refers to.
    """
    return resolver_calls / len(events) if events else 0.0


# ---- per-scenario and suite aggregation (ADR-0120) -------------------------------------


@dataclass(frozen=True)
class ScenarioMetrics:
    """Every count one scenario contributes; ratios are taken only after pooling."""

    scenario: str
    should_change: int
    should_stay: int
    correct_updates: int
    stale_kept: int
    wrongful_changes: int
    questions_asked: int
    questions_needed: int
    change_events: int
    resolver_calls: int
    llm_calls: int
    recommendations_shown: int
    stale_recommendations: int
    retrieved: int
    stale_retrieved: int
    ttc: TTCReport
    # Should-change targets other than the alias the event acted on (its write is the
    # same under every strategy), and how many of those were correct.
    should_change_dependents: int = 0
    correct_dependents: int = 0

    @property
    def wrong_updates(self) -> int:
        """Should change, moved, but not to the gold state (ADR-0063's remainder)."""
        return self.should_change - self.correct_updates - self.stale_kept


def scenario_metrics(
    trace: ReplayTrace,
    events: Sequence[ChangeEvent],
    *,
    resolver_calls: int,
    llm_calls: int = 0,
) -> ScenarioMetrics:
    """All memory metrics of one replayed scenario. Retrieval counts come from the
    probe results the trace carries (EventSnapshot.retrieved, ADR-0120)."""
    outcomes = target_outcomes(trace)
    acted_on = {s.index: s.action.partition(":")[2] for s in trace.events}
    dependents = [
        o
        for o in outcomes
        if o.should_change and o.target.partition("@")[0] != acted_on[o.event_index]
    ]
    stale_recs, shown = stale_recommendation_counts(trace.events)
    retrieved = stale_retrieved = 0
    for snapshot in trace.events:
        if snapshot.index == 0:
            continue
        stale_ids = stale_ids_at(snapshot)
        pairs = [(r.memory_id, r.flagged) for r in snapshot.retrieved]
        retrieved += len(pairs)
        stale_retrieved += stale_hits(pairs, stale_ids)
    return ScenarioMetrics(
        scenario=trace.scenario,
        should_change=sum(1 for o in outcomes if o.should_change),
        should_stay=sum(1 for o in outcomes if not o.should_change),
        correct_updates=correct_updates(outcomes),
        stale_kept=stale_kept(outcomes),
        wrongful_changes=wrongful_changes(outcomes),
        questions_asked=questions_asked(events),
        questions_needed=questions_needed(trace),
        change_events=len(events),
        resolver_calls=resolver_calls,
        llm_calls=llm_calls,
        recommendations_shown=shown,
        stale_recommendations=stale_recs,
        retrieved=retrieved,
        stale_retrieved=stale_retrieved,
        ttc=time_to_consistency(trace),
        should_change_dependents=len(dependents),
        correct_dependents=correct_updates(dependents),
    )


MEMORY_TOTAL_KEYS = (
    "scenarios",
    "should_change",
    "should_stay",
    "correct_updates",
    "stale_kept",
    "wrong_updates",
    "wrongful_changes",
    "questions_asked",
    "questions_needed",
    "change_events",
    "resolver_calls",
    "llm_calls",
    "recommendations_shown",
    "stale_recommendations",
    "retrieved",
    "stale_retrieved",
    "should_change_dependents",
    "correct_dependents",
    "ttc_records",
    "ttc_never_converged",
)


def suite_metrics(per_scenario: Sequence[ScenarioMetrics]) -> dict[str, object]:
    """The `memory_metrics` object of a run (keys of paper.registry.MEMORY_METRICS
    first, then the readings reported beside them) and the pooled `totals`.

    Rates pool counts over scenarios (micro average): update_accuracy is
    Σcorrect / Σshould_change, so a scenario with ten should-change targets weighs ten
    times one with one. stale_kept, wrongful_changes and questions_asked are averages
    per scenario (totals / scenarios), as the registry's float format expects.
    tokens_per_ripple and usd_per_ripple are None when no LLM was called: the scripted
    oracle spends no tokens, and a 0 would read as "free" rather than "not measured".
    None also marks a ratio whose denominator is 0.
    """
    totals: dict[str, int] = dict.fromkeys(MEMORY_TOTAL_KEYS, 0)
    totals["scenarios"] = len(per_scenario)
    converged_events: list[int] = []
    converged_days: list[float] = []
    for m in per_scenario:
        for key in MEMORY_TOTAL_KEYS[1:-2]:
            totals[key] += getattr(m, key)
        totals["ttc_records"] += len(m.ttc.records)
        for record in m.ttc.records:
            if record.ttc_events is None or record.ttc_days is None:
                totals["ttc_never_converged"] += 1
            else:
                converged_events.append(record.ttc_events)
                converged_days.append(record.ttc_days)
    scenarios = totals["scenarios"]
    metrics: dict[str, object] = {
        "update_accuracy": _ratio(totals["correct_updates"], totals["should_change"]),
        "stale_kept": _ratio(totals["stale_kept"], scenarios),
        "wrongful_changes": _ratio(totals["wrongful_changes"], scenarios),
        "questions_asked": _ratio(totals["questions_asked"], scenarios),
        "stale_retrieval_rate": _ratio(totals["stale_retrieved"], totals["retrieved"]),
        "stale_recommendation_rate": _ratio(
            totals["stale_recommendations"], totals["recommendations_shown"]
        ),
        "ttc_share_never_converged": _ratio(totals["ttc_never_converged"], totals["ttc_records"]),
        "cost_per_ripple": _ratio(totals["resolver_calls"], totals["change_events"]),
        "tokens_per_ripple": None,
        "usd_per_ripple": None,
        # Beside the registry keys: the shares behind the per-scenario averages.
        "dependent_update_accuracy": _ratio(
            totals["correct_dependents"], totals["should_change_dependents"]
        ),
        "stale_kept_share": _ratio(totals["stale_kept"], totals["should_change"]),
        "wrong_update_share": _ratio(totals["wrong_updates"], totals["should_change"]),
        "wrongful_change_share": _ratio(totals["wrongful_changes"], totals["should_stay"]),
        "questions_needed": _ratio(totals["questions_needed"], scenarios),
        "resolver_calls_per_scenario": _ratio(totals["resolver_calls"], scenarios),
        "ttc_median_events": _median(converged_events),
        "ttc_median_days": _median(converged_days),
    }
    return {"memory_metrics": metrics, "memory_totals": totals}


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _median(values: Sequence[float]) -> float | None:
    return float(statistics.median(values)) if values else None


def _gold_of(trace: ReplayTrace, outcome: TargetOutcome) -> GoldState:
    for snapshot in trace.events:
        if snapshot.index == outcome.event_index:
            return snapshot.gold[outcome.target]
    raise KeyError(outcome.event_index)
