"""TTC replay harness: per-event snapshots of memory states and recommendations (ADR-0062).

docs/proposals/0003-time-to-consistency.md asks for one thing the rate metrics cannot
give: how long a stale belief survives. The scenario runner (bench/scenario.py) calls
`snapshot_after_event` after seeding and after every event; the result is a
`ReplayTrace` that `bench.run` writes into results/<run>/snapshots/<scenario>.json.
The [human] metric functions in bench/metrics.py read these traces; nothing here
computes a metric.

The `ActionLayer` is the bench's name for contract C1's `RecommendationSource`
(src/ripple/domains/jobs/vocabulary.py): the real ranking from the jobs adapter plugs
in once it exists. Until then `StubActionLayer` projects memory state onto a
recommendation set with one deliberately naive rule, documented on the class. It is a
stub, not a ranker: its purpose is to give TTC and the stale-action window something
to measure, under the same rule for every strategy.
"""

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Protocol

from ripple.core.engine import DependencyGraph
from ripple.core.models import Memory, Status
from ripple.core.store import MemoryNotFoundError, Store
from ripple.domains.jobs.vocabulary import JobsLinkType, Kind, Recommendation

FLAGGED = frozenset({Status.SUSPECT, Status.PENDING_USER})


# ---- snapshot types ----------------------------------------------------------------


@dataclass(frozen=True)
class VersionState:
    """One row of a version chain as the system held it after an event."""

    id: str
    status: str
    version: int
    content: str


@dataclass(frozen=True)
class MemorySnapshot:
    """The root row and the latest version of one scenario alias; None when forgotten."""

    alias: str
    root: VersionState | None
    latest: VersionState | None

    def select(self, selector: str) -> VersionState | None:
        """`""` → the root row (the alias as written); `"latest"` → the newest version."""
        if selector == "latest":
            return self.latest
        if selector == "":
            return self.root
        raise ValueError(f"unknown selector {selector!r}; use alias or alias@latest")


@dataclass(frozen=True)
class GoldState:
    """What the scenario's `expect` block says about one target after one event."""

    status: str | None = None
    content: str | None = None
    version: int | None = None
    deleted: bool = False

    def mismatches(self, target: str, state: VersionState | None) -> list[str]:
        """Human-readable differences, empty when the state satisfies this gold."""
        if state is None:
            return [] if self.deleted else [f"{target}: missing"]
        if self.deleted:
            return [f"{target}: expected deleted, found {state.status}"]
        problems: list[str] = []
        if self.status is not None and state.status != self.status:
            problems.append(f"{target}: status {state.status}, expected {self.status}")
        if self.content is not None and state.content != self.content:
            problems.append(f"{target}: content {state.content!r}, expected {self.content!r}")
        if self.version is not None and state.version != self.version:
            problems.append(f"{target}: version {state.version}, expected {self.version}")
        return problems

    def matches(self, state: VersionState | None) -> bool:
        return not self.mismatches("", state)


@dataclass(frozen=True)
class RecommendationSnapshot:
    """One recommendation as shown after an event, plus the memories it was built on."""

    opening_id: str
    opening_alias: str | None
    eligible: bool
    fit_score: float
    flagged: bool
    # Ids of the VALID or flagged memories below the opening at snapshot time: the
    # beliefs a stale-action check compares against gold.
    based_on: tuple[str, ...]


@dataclass(frozen=True)
class RetrievedSnapshot:
    """One result of the retrieval probe (ADR-0120): what a retriever showed, and how."""

    query_alias: str  # the gold target alias whose seeded content was the query
    memory_id: str
    flagged: bool
    via: str


@dataclass(frozen=True)
class EventSnapshot:
    """State after one event. Index 0 is the seeded state before any event."""

    index: int
    action: str  # "seed", "update:cgpa", "advance_days:31", ...
    simulated_day: float  # days since the scenario clock started
    memories: Mapping[str, MemorySnapshot]
    recommendations: tuple[RecommendationSnapshot, ...]
    gold: Mapping[str, GoldState]  # target ("cgpa" or "cgpa@latest") -> expectation
    resolver_calls: int  # cumulative for the scenario so far
    pending_questions: int  # PENDING_USER rows at snapshot time
    # Results of the retrieval probe after this event; empty for the seed and for
    # events without gold (ADR-0120). The stale retrieval rate is computed from these.
    retrieved: tuple[RetrievedSnapshot, ...] = ()

    def state_of(self, target: str) -> VersionState | None:
        alias, _, selector = target.partition("@")
        snapshot = self.memories.get(alias)
        return None if snapshot is None else snapshot.select(selector)


@dataclass
class ReplayTrace:
    scenario: str
    strategy: str
    started_at: datetime
    events: list[EventSnapshot] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """JSON-ready form, written to results/<run>/snapshots/<scenario>.json."""
        return {
            "scenario": self.scenario,
            "strategy": self.strategy,
            "started_at": self.started_at.isoformat(),
            "events": [
                {
                    "index": e.index,
                    "action": e.action,
                    "simulated_day": e.simulated_day,
                    "memories": {alias: asdict(m) for alias, m in e.memories.items()},
                    "recommendations": [asdict(r) for r in e.recommendations],
                    "gold": {target: asdict(g) for target, g in e.gold.items()},
                    "resolver_calls": e.resolver_calls,
                    "pending_questions": e.pending_questions,
                    "retrieved": [asdict(r) for r in e.retrieved],
                }
                for e in self.events
            ],
        }


# ---- action layer ----------------------------------------------------------------


class ActionLayer(Protocol):
    """What the replay asks after every event; identical to C1 `RecommendationSource`."""

    async def recommendations_for(
        self, user_id: str, *, now: datetime, limit: int = 10
    ) -> Sequence[Recommendation]: ...


class StubActionLayer:
    """A deterministic placeholder ranking, NOT the jobs adapter's ranking (WS-1).

    Rule, applied to every strategy alike:
    - every VALID memory of kind `opening` is a candidate;
    - `eligible` is False when a non-retired dependent reached through an
      `eligibility_of` link has content starting with "not " (the one content
      heuristic; the jobs scenarios phrase negative eligibility that way);
    - `flagged` is True when any memory below the opening is SUSPECT or PENDING_USER;
    - `fit_score` is 1.0 (the stub does not judge fit);
    - order: earliest deadline first (openings without one last), then opening id.
    Only eligible openings are recommended. Replace with the adapter's
    `RecommendationSource` once it exists; the trace format does not change.
    """

    def __init__(self, store: Store) -> None:
        self._store = store

    async def recommendations_for(
        self, user_id: str, *, now: datetime, limit: int = 10
    ) -> Sequence[Recommendation]:
        graph = DependencyGraph.from_links(await self._store.links_for_user(user_id))
        openings = [
            m
            for m in await self._store.memories_for_user(user_id, [Status.VALID])
            if m.kind == Kind.OPENING
        ]
        ranked: list[Recommendation] = []
        for opening in openings:
            below = await self._below(graph, opening.id)
            if await self._negative_eligibility(opening.id, below):
                continue
            ranked.append(
                Recommendation(
                    opening_memory_id=opening.id,
                    title=opening.content,
                    company=_company_of(opening),
                    eligible=True,
                    fit_score=1.0,
                    fit_reasons=(),
                    deadline=_deadline_of(opening),
                    flagged=any(m.status in FLAGGED for m in below),
                )
            )
        ranked.sort(key=lambda r: (r.deadline is None, r.deadline or now, r.opening_memory_id))
        return ranked[:limit]

    async def _below(self, graph: DependencyGraph, opening_id: str) -> list[Memory]:
        return await memories_below(self._store, graph, opening_id)

    async def _negative_eligibility(self, opening_id: str, below: Sequence[Memory]) -> bool:
        for memory in below:
            if memory.content.lower().startswith("not ") and await self._reached_by(
                opening_id, memory.id, JobsLinkType.ELIGIBILITY_OF
            ):
                return True
        return False

    async def _reached_by(self, parent_id: str, dependent_id: str, link_type: str) -> bool:
        return any(
            link.parent_id == parent_id and link.link_type == link_type
            for link in await self._store.parents_of(dependent_id)
        )


async def memories_below(store: Store, graph: DependencyGraph, memory_id: str) -> list[Memory]:
    """Non-retired memories in the depends_on subtree of `memory_id`, breadth-first."""
    below: list[Memory] = []
    for dependent_id in graph.descendants(memory_id):
        try:
            memory = await store.get_memory(dependent_id)
        except MemoryNotFoundError:
            continue
        if memory.status is not Status.RETIRED:
            below.append(memory)
    return below


def _company_of(opening: Memory) -> str:
    return opening.structured.subject if opening.structured is not None else "unknown"


def _deadline_of(opening: Memory) -> datetime | None:
    if opening.structured is None or opening.structured.attribute != "deadline":
        return None
    try:
        parsed = datetime.fromisoformat(str(opening.structured.value))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


# ---- snapshot capture --------------------------------------------------------------


async def snapshot_after_event(
    store: Store,
    action_layer: ActionLayer,
    *,
    user_id: str,
    ids: Mapping[str, str],
    index: int,
    action: str,
    now: datetime,
    started_at: datetime,
    gold: Mapping[str, GoldState],
    resolver_calls: int,
) -> EventSnapshot:
    memories: dict[str, MemorySnapshot] = {}
    for alias, memory_id in ids.items():
        memories[alias] = await _memory_snapshot(store, alias, memory_id)
    id_to_alias = {memory_id: alias for alias, memory_id in ids.items()}
    graph = DependencyGraph.from_links(await store.links_for_user(user_id))
    recommendations: list[RecommendationSnapshot] = []
    for rec in await action_layer.recommendations_for(user_id, now=now):
        # Which beliefs the recommendation rests on is read from the graph, not from
        # the action layer, so a real ranking later gets the same accounting.
        based_on = tuple(m.id for m in await memories_below(store, graph, rec.opening_memory_id))
        root_id = (await store.version_chain(rec.opening_memory_id))[0].id
        recommendations.append(
            RecommendationSnapshot(
                opening_id=rec.opening_memory_id,
                opening_alias=id_to_alias.get(root_id),
                eligible=rec.eligible,
                fit_score=rec.fit_score,
                flagged=rec.flagged,
                based_on=based_on,
            )
        )
    pending = len(await store.memories_for_user(user_id, [Status.PENDING_USER]))
    return EventSnapshot(
        index=index,
        action=action,
        simulated_day=(now - started_at).total_seconds() / 86400.0,
        memories=memories,
        recommendations=tuple(recommendations),
        gold=dict(gold),
        resolver_calls=resolver_calls,
        pending_questions=pending,
    )


async def _memory_snapshot(store: Store, alias: str, root_id: str) -> MemorySnapshot:
    try:
        root = await store.get_memory(root_id)
    except MemoryNotFoundError:
        return MemorySnapshot(alias=alias, root=None, latest=None)
    latest = await store.latest_version(root_id)
    return MemorySnapshot(alias=alias, root=_state(root), latest=_state(latest))


def _state(memory: Memory) -> VersionState:
    return VersionState(
        id=memory.id, status=memory.status.value, version=memory.version, content=memory.content
    )
