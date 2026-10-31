"""Baseline memory strategies behind one protocol (ADR-0060; docs/04 "Baselines").

A strategy is what happens *after* a trigger has been written and its ChangeEvent
opened: the scenario runner (bench/scenario.py) performs the write exactly the same way
for every strategy and then hands the open event to `strategy.run`. The store, the
resolver and the clock are shared, so the only variable is the propagation policy and
the cost is comparable: every resolver call goes through one `CountingResolver`.

- ripple: the real `RippleRunner` over the dependency graph (the system under test).
- append_only: nothing propagates; the version the write superseded is restored to
  VALID, so every statement ever made stays retrievable (the plain-log baseline).
- newest_wins: nothing propagates; the superseded version stays RETIRED and every
  dependent is left as it was.
- check_everything: no graph for scope; every VALID memory of the user is sent to the
  resolver after each write. Implemented as the `RippleRunner` driven by a one-shot
  engine that ignores the graph, so the commit protocol, decisions and ChangeEvents
  are the same as Ripple's and I2 holds for the baseline too. The graph is read only
  to apply the wave parents first, so an ask never re-parks a member the resolver
  already kept (ADR-0104).

Expiry of temporary facts (valid_to) is a property of the data model (ADR-0015) that
every strategy shares; what differs is whether the expiry ripples. Baselines never
ask the user (no resolver call, no ask), so questions_asked is 0 for append_only and
newest_wins by construction.
"""

from collections.abc import Sequence
from typing import Protocol, cast

from ripple.core.clock import Clock
from ripple.core.engine import DependencyGraph, Wave, WaveEngine, WaveOutcome
from ripple.core.models import ChangeEvent, Decision, DecisionAction, Status
from ripple.core.resolver import Resolution, ResolutionContext, Resolver
from ripple.core.ripple import RippleRunner
from ripple.core.store import MemoryNotFoundError, Store, Transaction

STRATEGY_NAMES: tuple[str, ...] = ("ripple", "append_only", "newest_wins", "check_everything")
# docs/04 ablations of the ripple strategy that run offline (ADR-0122). The other three
# (llm_linker, no_curator, no_evidence) need a real LLM or the agents and are not built.
ABLATIONS: tuple[str, ...] = ("no_graph", "no_ask_user")


class MemoryStrategy(Protocol):
    """The two calls the sweep and the answer flow make on a RippleRunner."""

    @property
    def name(self) -> str: ...

    @property
    def resolver_calls(self) -> int: ...

    async def run(self, event: ChangeEvent) -> ChangeEvent: ...

    async def resume(self, event: ChangeEvent) -> ChangeEvent: ...


class CountingResolver:
    """Wraps the shared resolver so every strategy's cost is counted the same way."""

    def __init__(self, inner: Resolver) -> None:
        self._inner = inner
        self.calls = 0

    async def resolve(self, context: ResolutionContext) -> Resolution:
        self.calls += 1
        return await self._inner.resolve(context)


def as_runner(strategy: MemoryStrategy) -> RippleRunner:
    """`NightlySweep` and `ripple.core.answers` are typed against the concrete
    RippleRunner but only call `run` and `resume`, which every strategy provides.
    The cast is the documented seam; a `RippleDriver` protocol in core is requested in
    docs/plans/parallel-execution/ws-7.md."""
    return cast(RippleRunner, strategy)


# ---- ripple ---------------------------------------------------------------------------


class RippleStrategy:
    name = "ripple"

    def __init__(
        self,
        store: Store,
        resolver: Resolver,
        clock: Clock,
        *,
        engine_factory: type[WaveEngine] | None = None,
    ) -> None:
        self._resolver = CountingResolver(resolver)
        self.runner = RippleRunner(store, self._resolver, clock, engine_factory=engine_factory)

    @property
    def resolver_calls(self) -> int:
        return self._resolver.calls

    async def run(self, event: ChangeEvent) -> ChangeEvent:
        return await self.runner.run(event)

    async def resume(self, event: ChangeEvent) -> ChangeEvent:
        return await self.runner.resume(event)


# ---- append_only and newest_wins -----------------------------------------------------


class _NoPropagation:
    """Shared body: complete the event without touching any dependent."""

    name = "no_propagation"

    def __init__(self, store: Store, resolver: Resolver, clock: Clock) -> None:
        self._store = store
        self._resolver = CountingResolver(resolver)  # never called; keeps cost comparable
        self._clock = clock

    @property
    def resolver_calls(self) -> int:
        return self._resolver.calls

    async def run(self, event: ChangeEvent) -> ChangeEvent:
        # One transaction: whatever the strategy changes and the event that records it
        # commit together, so a crash cannot leave a state change without its decision.
        async with self._store.transaction() as tx:
            decisions = await self._before_completion(tx, event)
            event = event.model_copy(
                update={
                    "affected_ids": [*event.affected_ids, *(d.memory_id for d in decisions)],
                    "decisions": [*event.decisions, *decisions],
                    "completed_at": self._clock.now(),
                }
            )
            await tx.replace_change_event(event)
        return event

    async def resume(self, event: ChangeEvent) -> ChangeEvent:
        return event if not event.is_open else await self.run(event)

    async def _before_completion(self, tx: Transaction, event: ChangeEvent) -> list[Decision]:
        return []


class NewestWinsStrategy(_NoPropagation):
    name = "newest_wins"


class AppendOnlyStrategy(_NoPropagation):
    name = "append_only"

    async def _before_completion(self, tx: Transaction, event: ChangeEvent) -> list[Decision]:
        """Undo the retirement the version write performed: an append-only log keeps
        the old statement. Recorded as a wave-0 KEEP so I2 still holds."""
        trigger = await tx.get_memory(event.trigger_memory_id)
        if trigger.supersedes_id is None:
            return []  # expiry, retire-by-answer and new memories supersede nothing
        try:
            old = await tx.get_memory(trigger.supersedes_id)
        except MemoryNotFoundError:
            return []
        if old.status is not Status.RETIRED:
            return []
        await tx.replace_memory(old.model_copy(update={"status": Status.VALID}))
        return [
            Decision(
                memory_id=old.id,
                wave=0,
                action=DecisionAction.KEEP,
                reason="append_only baseline: superseded versions stay valid",
                evidence_refs=[f"baseline:{self.name}"],
            )
        ]


# ---- check_everything ---------------------------------------------------------------


def one_shot_engine(memory_ids: Sequence[str]) -> type[WaveEngine]:
    """An engine whose only wave is the given ids, whatever the graph says.

    Still an engine in the ADR-0013 sense (pure, no I/O, no LLM: I3), but it does
    not look at the graph; that is the whole point of the check-everything baseline.
    """

    class OneShotEngine(WaveEngine):
        def first_wave(self, graph: DependencyGraph, seeds: Sequence[str]) -> Wave | None:
            members = tuple(memory_id for memory_id in memory_ids if memory_id not in seeds)
            self._wave_number = 1
            return Wave(number=1, memory_ids=members) if members else None

        def next_wave(self, graph: DependencyGraph, outcomes: Sequence[WaveOutcome]) -> Wave | None:
            return None

    return OneShotEngine


def parents_first(memory_ids: Sequence[str], graph: DependencyGraph) -> list[str]:
    """`memory_ids` reordered so no member comes before one of its ancestors among them,
    except an ancestor it shares a cycle with (a cycle has no right order).

    Stable: among members that are ready, the earlier one in `memory_ids` goes first.
    A member is ready when every ancestor is placed or lies on a cycle through it, so
    members below a cycle still wait for the whole cycle.
    """
    members = set(memory_ids)
    ancestors: dict[str, set[str]] = {m: set() for m in memory_ids}
    for member in memory_ids:
        for below in graph.descendants(member):
            if below in members and below != member:
                ancestors[below].add(member)
    placed: list[str] = []
    done: set[str] = set()
    remaining = list(memory_ids)
    while remaining:
        ready = [m for m in remaining if all(a in done or m in ancestors[a] for a in ancestors[m])]
        # Some member is always ready: the condensation of the graph is acyclic, so a
        # source component exists among the remaining members.
        chosen = ready[0]
        placed.append(chosen)
        done.add(chosen)
        remaining.remove(chosen)
    return placed


class CheckEverythingStrategy:
    name = "check_everything"

    def __init__(self, store: Store, resolver: Resolver, clock: Clock) -> None:
        self._store = store
        self._resolver = CountingResolver(resolver)
        self._clock = clock

    @property
    def resolver_calls(self) -> int:
        return self._resolver.calls

    async def run(self, event: ChangeEvent) -> ChangeEvent:
        valid = await self._store.memories_for_user(event.user_id, [Status.VALID])
        # Explicit order, not the store's: an ask parks only VALID descendants, so the
        # order members are applied in changes the outcome. Parents first (ADR-0104):
        # every member then keeps its own decision, as a graph-blind re-check would,
        # whatever its alias is called. Ties break on (recorded_at, id).
        ordered = sorted(valid, key=lambda m: (m.recorded_at, m.id))
        graph = DependencyGraph.from_links(await self._store.links_for_user(event.user_id))
        ids = [
            memory_id
            for memory_id in parents_first([m.id for m in ordered], graph)
            if memory_id != event.trigger_memory_id
        ]
        runner = RippleRunner(
            self._store, self._resolver, self._clock, engine_factory=one_shot_engine(ids)
        )
        return await runner.run(event)

    async def resume(self, event: ChangeEvent) -> ChangeEvent:
        # Nothing new is scoped on resume; the runner finishes whatever was left SUSPECT.
        runner = RippleRunner(
            self._store, self._resolver, self._clock, engine_factory=one_shot_engine(())
        )
        return await runner.resume(event)


# ---- ablations (ADR-0122) -----------------------------------------------------------------


class NoAskResolver:
    """The ask-user ablation: whatever the resolver would have asked about is kept as it
    is, unflagged, because a system without ask-user has nobody to ask. Keep, not retire
    or a guessed update: an ask carries no new content, and keeping is what a store
    without questions does with a belief it cannot settle."""

    def __init__(self, inner: Resolver) -> None:
        self._inner = inner

    async def resolve(self, context: ResolutionContext) -> Resolution:
        resolution = await self._inner.resolve(context)
        if resolution.action is not DecisionAction.ASK:
            return resolution
        return Resolution(
            action=DecisionAction.KEEP,
            reason=f"no_ask_user ablation: kept instead of asking ({resolution.reason})",
        )


class NoGraphRippleStrategy(CheckEverythingStrategy):
    """The without-graph ablation: Ripple's runner with no dependency graph to scope by,
    so every VALID memory is re-checked after each write. That is check_everything's
    scope by construction (the task's "check_everything-style scope"); it is run under
    the ripple name and the ablation flag so the ablation table reads from its own
    folders, and the graph is read only for the parents-first order (ADR-0104)."""

    name = "ripple"


# ---- factory ---------------------------------------------------------------------------


def build_strategy(
    name: str,
    *,
    store: Store,
    resolver: Resolver,
    clock: Clock,
    engine_factory: type[WaveEngine] | None = None,
    ablation: str | None = None,
) -> MemoryStrategy:
    """`engine_factory` applies to the ripple strategy only (tests inject ScriptedEngine);
    so does `ablation` (one of ABLATIONS)."""
    if ablation is not None:
        if name != "ripple" or ablation not in ABLATIONS:
            raise ValueError(f"ablation {ablation!r} needs strategy ripple and one of {ABLATIONS}")
        if ablation == "no_graph":
            # No graph, so no engine to inject: the one-shot scope replaces it.
            return NoGraphRippleStrategy(store, resolver, clock)
        return RippleStrategy(store, NoAskResolver(resolver), clock, engine_factory=engine_factory)
    match name:
        case "ripple":
            return RippleStrategy(store, resolver, clock, engine_factory=engine_factory)
        case "append_only":
            return AppendOnlyStrategy(store, resolver, clock)
        case "newest_wins":
            return NewestWinsStrategy(store, resolver, clock)
        case "check_everything":
            return CheckEverythingStrategy(store, resolver, clock)
    raise ValueError(f"unknown strategy {name!r}; choose one of {', '.join(STRATEGY_NAMES)}")
