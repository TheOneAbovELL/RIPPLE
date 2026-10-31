"""RippleRunner: drives one ChangeEvent from its trigger to completed_at (ADR-0013).

Per wave, two commits:
  1. mark the wave SUSPECT and record exactly those ids in the event (so retrieval
     flags them, I1, and resume knows what is outstanding);
  2. after the Resolver has answered for every member, re-read each member inside the
     transaction, apply the decisions and append them to the event.
Only updated or retired memories seed the next wave; keep halts; ask parks the memory
in PENDING_USER and marks its subtree SUSPECT, recording the parked ids on the event
so an answer can restore exactly them. A crash between commits leaves an open event
that `resume` picks up (the sweep calls it).

An optional EventLease (ADR-0099) makes the runner the only driver of an event while
it works on it: `run` and `resume` hold the lease keyed by the event id from start to
completion. When another holder has it they return the event untouched and still
open; an open event coming back from `resume` therefore always means "skipped". With a
lease the runner also re-reads the stored event after acquiring and drives that, so a
snapshot that another holder progressed or completed is not driven a second time.
Without a lease nothing here differs from the runner before ADR-0099.

I3 by construction: the engine is a pure object; the only component that may call an
LLM is the injected Resolver, and it is called here, never inside the engine.
"""

import logging
from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from ripple.core.clock import Clock
from ripple.core.engine import DEFAULT_MAX_DEPTH, DependencyGraph, Wave, WaveEngine, WaveOutcome
from ripple.core.indexing import MemoryIndexer
from ripple.core.lease import EventLease, holding
from ripple.core.links import policy_for
from ripple.core.models import ChangeEvent, Decision, DecisionAction, Memory, Status
from ripple.core.resolver import Resolution, ResolutionContext, Resolver
from ripple.core.store import MemoryNotFoundError, Store, Transaction
from ripple.core.versioning import write_new_version

log = logging.getLogger("ripple.core.ripple")


class RippleDriver(Protocol):
    """What the sweep and the answers need from a runner; the bench swaps strategies in."""

    async def run(self, event: ChangeEvent) -> ChangeEvent: ...

    async def resume(self, event: ChangeEvent) -> ChangeEvent: ...


class EventObserver(Protocol):
    """Told once an event has completed and its completion is committed (ADR-0079).

    The seam for follow-up work core does not know about, such as scouting again when
    a domain's search criteria changed. Called after the commit, so the observer's
    failure cannot undo the ripple; it is logged and the next observer still runs.
    """

    async def event_completed(self, event: ChangeEvent) -> None: ...


class RippleRunner:
    def __init__(
        self,
        store: Store,
        resolver: Resolver,
        clock: Clock,
        *,
        engine_factory: type[WaveEngine] | None = None,
        max_depth: int = DEFAULT_MAX_DEPTH,
        indexer: MemoryIndexer | None = None,
        event_lease: EventLease | None = None,
        observers: Sequence[EventObserver] = (),
    ) -> None:
        self._store = store
        self._resolver = resolver
        self._clock = clock
        self._engine_factory = engine_factory or WaveEngine
        self._max_depth = max_depth
        self._indexer = indexer
        self._event_lease = event_lease
        self._observers = tuple(observers)

    # ---- public --------------------------------------------------------------

    async def run(self, event: ChangeEvent) -> ChangeEvent:
        """Execute every wave of a freshly opened event and complete it.

        Returns the event unchanged and open when another holder leases it.
        """
        async with holding(self._event_lease, event.id) as held:
            if not held:
                self._log_leased("run", event)
                return event
            if self._event_lease is None:
                return await self._run(event)
            current = await self._store.get_change_event(event.id)
            if not current.is_open:
                return current
            # From the store, through resume: a holder that progressed the event and
            # crashed is continued, not restarted. For an untouched event resume
            # replays nothing and finds nothing outstanding, so it equals run.
            return await self._resume(current)

    async def resume(self, event: ChangeEvent) -> ChangeEvent:
        """Continue an open event after a crash.

        Replays the recorded decisions through a fresh engine so its visited set and
        depth match the store. Whatever was marked SUSPECT but never decided is the
        outstanding wave and is resolved first; then the engine carries on. Returns the
        event unchanged and open when another holder leases it.
        """
        if not event.is_open:
            return event
        async with holding(self._event_lease, event.id) as held:
            if not held:
                self._log_leased("resume", event)
                return event
            if self._event_lease is not None:
                # The caller's copy may predate another holder's progress or completion.
                event = await self._store.get_change_event(event.id)
                if not event.is_open:
                    return event
            return await self._resume(event)

    # ---- internals ------------------------------------------------------------

    @staticmethod
    def _log_leased(step: str, event: ChangeEvent) -> None:
        log.info(
            "ripple skipped: event leased elsewhere",
            extra={"event_id": event.id, "user_id": event.user_id, "step": step},
        )

    async def _run(self, event: ChangeEvent) -> ChangeEvent:
        trigger = await self._store.get_memory(event.trigger_memory_id)
        engine = self._engine_factory(max_depth=self._max_depth)
        graph = await self._graph(trigger.user_id)
        wave = engine.first_wave(graph, [trigger.id])
        return await self._drive(event, trigger, engine, wave)

    async def _resume(self, event: ChangeEvent) -> ChangeEvent:
        trigger = await self._store.get_memory(event.trigger_memory_id)
        engine = self._engine_factory(max_depth=self._max_depth)
        graph = await self._graph(trigger.user_id)
        wave = engine.first_wave(graph, [trigger.id])
        by_wave: dict[int, list[Decision]] = {}
        for decision in event.decisions:
            if decision.wave >= 1:
                by_wave.setdefault(decision.wave, []).append(decision)
        for number in sorted(by_wave):
            wave = engine.next_wave(graph, [self._outcome(d) for d in by_wave[number]])
        decided = {d.memory_id for d in event.decisions}
        outstanding = [
            memory_id
            for memory_id in event.affected_ids
            if memory_id not in decided and await self._is_suspect(memory_id)
        ]
        if outstanding:
            number = wave.number if wave is not None else (max(by_wave, default=0) + 1)
            wave = Wave(number=number, memory_ids=tuple(outstanding))
            return await self._drive(event, trigger, engine, wave, skip_marking=True)
        return await self._drive(event, trigger, engine, wave)

    async def _drive(
        self,
        event: ChangeEvent,
        trigger: Memory,
        engine: WaveEngine,
        wave: Wave | None,
        *,
        skip_marking: bool = False,
    ) -> ChangeEvent:
        while wave is not None:
            if not skip_marking:
                event = await self._mark_suspect(event, wave)
            skip_marking = False
            resolutions = await self._resolve_wave(trigger, wave)
            event, outcomes = await self._apply(event, wave, resolutions)
            graph = await self._graph(trigger.user_id)
            wave = engine.next_wave(graph, outcomes)
        if engine.truncated:
            log.warning(
                "ripple truncated at max depth",
                extra={"event_id": event.id, "max_depth": engine.max_depth},
            )
        return await self._complete(event)

    async def _graph(self, user_id: str) -> DependencyGraph:
        return DependencyGraph.from_links(await self._store.links_for_user(user_id))

    async def _is_suspect(self, memory_id: str) -> bool:
        try:
            return (await self._store.get_memory(memory_id)).status is Status.SUSPECT
        except MemoryNotFoundError:
            return False

    async def _mark_suspect(self, event: ChangeEvent, wave: Wave) -> ChangeEvent:
        """Commit one. Only ids that are SUSPECT afterwards count as affected."""
        marked: list[str] = []
        async with self._store.transaction() as tx:
            for memory_id in wave.memory_ids:
                try:
                    memory = await tx.get_memory(memory_id)
                except MemoryNotFoundError:
                    log.info(
                        "wave member forgotten",
                        extra={"memory_id": memory_id, "event_id": event.id},
                    )
                    continue
                if memory.status is Status.VALID:
                    await tx.replace_memory(memory.model_copy(update={"status": Status.SUSPECT}))
                    marked.append(memory_id)
                elif memory.status is Status.SUSPECT:
                    marked.append(memory_id)
                # RETIRED (history) and PENDING_USER members are not resolvable; skip.
            event = event.model_copy(update={"affected_ids": [*event.affected_ids, *marked]})
            await tx.replace_change_event(event)
        return event

    async def _resolve_wave(self, trigger: Memory, wave: Wave) -> list[tuple[Memory, Resolution]]:
        # Resolver calls (possibly an LLM) happen outside any transaction.
        resolved: list[tuple[Memory, Resolution]] = []
        for memory_id in wave.memory_ids:
            try:
                memory = await self._store.get_memory(memory_id)
            except MemoryNotFoundError:
                log.info("wave member forgotten", extra={"memory_id": memory_id})
                continue
            if memory.status is not Status.SUSPECT:
                continue
            parents = await self._current_parents(memory_id)
            context = ResolutionContext(
                trigger=trigger, memory=memory, parents=parents, wave=wave.number
            )
            resolved.append((memory, await self._resolver.resolve(context)))
        return resolved

    async def _current_parents(self, memory_id: str) -> list[Memory]:
        """Latest version of each propagating parent, once each (history links collapse)."""
        parents: list[Memory] = []
        seen: set[str] = set()
        for link in await self._store.parents_of(memory_id):
            if not policy_for(link.link_class).propagates:
                continue
            parent = await self._store.latest_version(link.parent_id)
            if parent.id not in seen:
                seen.add(parent.id)
                parents.append(parent)
        return parents

    async def _apply(
        self,
        event: ChangeEvent,
        wave: Wave,
        resolutions: Sequence[tuple[Memory, Resolution]],
    ) -> tuple[ChangeEvent, list[WaveOutcome]]:
        """Commit two. Rows are re-read inside the transaction; anything no longer
        SUSPECT (forgotten, answered, swept meanwhile) is skipped and logged."""
        now = self._clock.now()
        decisions: list[Decision] = []
        outcomes: list[WaveOutcome] = []
        parked: dict[str, list[str]] = dict(event.parked)
        async with self._store.transaction() as tx:
            for stale, resolution in resolutions:
                try:
                    memory = await tx.get_memory(stale.id)
                except MemoryNotFoundError:
                    log.info("skipping forgotten member", extra={"memory_id": stale.id})
                    continue
                if memory.status is not Status.SUSPECT:
                    log.info(
                        "skipping member changed since resolution",
                        extra={"memory_id": memory.id, "status": memory.status.value},
                    )
                    continue
                decision, outcome, parked_below = await self._apply_one(
                    tx, memory, resolution, wave.number, now
                )
                decisions.append(decision)
                outcomes.append(outcome)
                if parked_below:
                    parked[memory.id] = parked_below
            event = event.model_copy(
                update={"decisions": [*event.decisions, *decisions], "parked": parked}
            )
            await tx.replace_change_event(event)
        if self._indexer is not None:
            # After the commit: new versions written by this wave become searchable.
            for decision in decisions:
                if decision.new_version_id is not None:
                    await self._indexer.index(await self._store.get_memory(decision.new_version_id))
        return event, outcomes

    async def _apply_one(
        self,
        tx: Transaction,
        memory: Memory,
        resolution: Resolution,
        wave: int,
        now: datetime,
    ) -> tuple[Decision, WaveOutcome, list[str]]:
        def decision(new_version_id: str | None = None) -> Decision:
            return Decision(
                memory_id=memory.id,
                wave=wave,
                action=resolution.action,
                reason=resolution.reason,
                evidence_refs=list(resolution.evidence_refs),
                new_version_id=new_version_id,
                question=resolution.question,
            )

        match resolution.action:
            case DecisionAction.KEEP:
                await tx.replace_memory(memory.model_copy(update={"status": Status.VALID}))
                return decision(), WaveOutcome(memory.id, changed=False), []
            case DecisionAction.RETIRE:
                await tx.replace_memory(memory.model_copy(update={"status": Status.RETIRED}))
                return decision(), WaveOutcome(memory.id, changed=True), []
            case DecisionAction.UPDATE:
                assert resolution.new_content is not None  # enforced by Resolution
                new = await write_new_version(
                    tx,
                    memory,
                    content=resolution.new_content,
                    # A resolver rewrites content; fields it did not touch carry over.
                    structured=resolution.new_structured or memory.structured,
                    valid_to=resolution.new_valid_to or memory.valid_to,
                    created_by="curator",
                    now=now,
                )
                return (
                    decision(new_version_id=new.id),
                    WaveOutcome(memory.id, changed=True, successor_id=new.id),
                    [],
                )
            case DecisionAction.ASK:
                await tx.replace_memory(memory.model_copy(update={"status": Status.PENDING_USER}))
                graph = DependencyGraph.from_links(await tx.links_for_user(memory.user_id))
                parked_below: list[str] = []
                for below in graph.descendants(memory.id):
                    dependent = await tx.get_memory(below)
                    if dependent.status is Status.VALID:
                        await tx.replace_memory(
                            dependent.model_copy(update={"status": Status.SUSPECT})
                        )
                        parked_below.append(below)
                return decision(), WaveOutcome(memory.id, changed=False), parked_below

    async def _complete(self, event: ChangeEvent) -> ChangeEvent:
        async with self._store.transaction() as tx:
            event = event.model_copy(update={"completed_at": self._clock.now()})
            await tx.replace_change_event(event)
        await self._notify(event)
        return event

    async def _notify(self, event: ChangeEvent) -> None:
        for observer in self._observers:
            try:
                await observer.event_completed(event)
            except Exception:
                # The ripple is committed and correct; a follow-up that failed (a queue
                # that is down) must not turn the user's write into an error. Logged
                # with its traceback; the daily run is the backstop (ADR-0079).
                log.exception(
                    "event observer failed",
                    extra={"event_id": event.id, "observer": type(observer).__name__},
                )

    @staticmethod
    def _outcome(decision: Decision) -> WaveOutcome:
        changed = decision.action in (DecisionAction.UPDATE, DecisionAction.RETIRE)
        return WaveOutcome(
            decision.memory_id, changed=changed, successor_id=decision.new_version_id
        )
