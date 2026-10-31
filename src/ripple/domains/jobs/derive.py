"""Deterministic derivation of jobs beliefs (ADR-0031): eligibility, fit and reminder
for one opening; search criteria for the profile.

Each belief is written through `ripple.core.writes.record_memory` with its links to
the facts it was computed from (and to the opening anchor), then rippled by the
runner, so a belief enters the graph exactly like any other memory write.
"""

import logging
from dataclasses import dataclass

from ripple.core.clock import Clock
from ripple.core.errors import ConfigurationError, InvalidObjectError
from ripple.core.models import ChangeEvent, Link, LinkCreator, Memory, Status
from ripple.core.ripple import RippleRunner
from ripple.core.store import MemoryNotFoundError, Store
from ripple.core.writes import record_memory
from ripple.domains.jobs.beliefs import (
    Belief,
    compute_criteria,
    compute_eligibility,
    compute_fit,
    compute_reminder,
)
from ripple.domains.jobs.schemas import OpeningView, ProfileView
from ripple.domains.jobs.vocabulary import DOMAIN, PROFILE_SUBJECT, Kind, jobs_registry

CURATOR = "curator"

log = logging.getLogger("ripple.domains.jobs.derive")


@dataclass(frozen=True)
class DerivedBeliefs:
    eligibility: Memory | None
    fit: Memory | None
    reminder: Memory | None


def _existing(belief: Belief, memories: list[Memory]) -> Memory | None:
    """A live belief (not RETIRED) for the same subject and attribute already held.

    SUSPECT and PENDING_USER count: the ripple or the user is deciding about it, and a
    second copy would sit beside it in the ranking.
    """
    return next(
        (
            m
            for m in memories
            if m.status is not Status.RETIRED
            and m.structured is not None
            and m.structured.subject == belief.structured.subject
            and m.structured.attribute == belief.structured.attribute
        ),
        None,
    )


async def _write(
    store: Store,
    clock: Clock,
    runner: RippleRunner,
    user_id: str,
    belief: Belief,
    *,
    trace_id: str | None,
) -> Memory:
    now = clock.now()
    registry = jobs_registry()
    memory = Memory(
        user_id=user_id,
        domain=DOMAIN,
        kind=belief.kind,
        content=belief.content,
        structured=belief.structured,
        valid_from=now,
        recorded_at=now,
        created_by=CURATOR,
    )
    links = [
        Link(
            parent_id=parent.id,
            dependent_id=memory.id,
            link_type=belief.link_type,
            link_class=registry.class_of(belief.link_type),
            created_by=LinkCreator.RULE,
            created_at=now,
        )
        for parent in belief.parents
    ]
    event = await record_memory(store, clock, memory, links, trace_id=trace_id)
    await runner.run(event)
    return memory


async def _derive(
    store: Store,
    clock: Clock,
    runner: RippleRunner,
    user_id: str,
    belief: Belief | None,
    memories: list[Memory],
    *,
    trace_id: str | None,
) -> Memory | None:
    """Write the belief unless nothing can be derived or it is already held.

    An existing live belief is returned untouched: the ripple keeps it current, and
    rewriting it here would be a change with no trigger (ADR-0015).
    """
    if belief is None:
        return None
    existing = _existing(belief, memories)
    if existing is not None:
        return existing
    return await _write(store, clock, runner, user_id, belief, trace_id=trace_id)


async def derive_for_opening(
    store: Store,
    clock: Clock,
    runner: RippleRunner,
    anchor_id: str,
    *,
    trace_id: str | None = None,
) -> DerivedBeliefs:
    """Eligibility, fit and reminder for one recorded opening, from current facts.

    Accepts any version id of the anchor and works on the latest; refuses a closed or
    questioned opening, whose beliefs the rules are about to retire or park.
    """
    anchor = await store.latest_version(anchor_id)
    if anchor.status is not Status.VALID:
        raise InvalidObjectError(
            f"opening {anchor.id!r} is {anchor.status.value}; derive only for an open opening"
        )
    memories = await store.memories_for_user(anchor.user_id)
    profile = ProfileView.from_memories(memories)
    opening = OpeningView.from_memories(anchor, memories)
    user_id = anchor.user_id
    eligibility = await _derive(
        store,
        clock,
        runner,
        user_id,
        compute_eligibility(profile, opening),
        memories,
        trace_id=trace_id,
    )
    fit = await _derive(
        store, clock, runner, user_id, compute_fit(profile, opening), memories, trace_id=trace_id
    )
    reminder = await _derive(
        store, clock, runner, user_id, compute_reminder(opening), memories, trace_id=trace_id
    )
    return DerivedBeliefs(eligibility=eligibility, fit=fit, reminder=reminder)


async def derive_criteria(
    store: Store,
    clock: Clock,
    runner: RippleRunner,
    user_id: str,
    *,
    trace_id: str | None = None,
) -> Memory | None:
    """The Scout's search criteria, derived from the profile facts (criteria_from)."""
    memories = await store.memories_for_user(user_id)
    profile = ProfileView.from_memories(memories)
    return await _derive(
        store, clock, runner, user_id, compute_criteria(profile), memories, trace_id=trace_id
    )


class ProfileDerivationObserver:
    """A RippleRunner EventObserver: derive what a profile change makes derivable.

    The ripple keeps existing beliefs current; it cannot create a belief that did not
    exist. When the student states a first CGPA, batch or skill, the search criteria and
    the eligibility or fit of openings saved earlier become derivable for the first
    time. After any completed event triggered by a profile fact, this derives them;
    `_derive` returns a belief that already exists untouched, so repeats are no-ops
    (ADR-0116). Bound to its runner after construction because the runner takes it.
    """

    def __init__(self, store: Store, clock: Clock) -> None:
        self._store = store
        self._clock = clock
        self._runner: RippleRunner | None = None

    def attach(self, runner: RippleRunner) -> None:
        self._runner = runner

    async def event_completed(self, event: ChangeEvent) -> None:
        if self._runner is None:
            raise ConfigurationError("ProfileDerivationObserver used before attach(runner)")
        try:
            trigger = await self._store.get_memory(event.trigger_memory_id)
        except MemoryNotFoundError:
            return  # forgotten since; nothing to derive from
        if (
            trigger.kind != Kind.FACT
            or trigger.structured is None
            or trigger.structured.subject != PROFILE_SUBJECT
        ):
            return
        runner, user_id = self._runner, event.user_id
        await derive_criteria(self._store, self._clock, runner, user_id, trace_id=event.trace_id)
        openings = await self._store.memories_for_user(user_id, [Status.VALID])
        for anchor in (m for m in openings if m.kind == Kind.OPENING):
            try:
                await derive_for_opening(
                    self._store, self._clock, runner, anchor.id, trace_id=event.trace_id
                )
            except (InvalidObjectError, MemoryNotFoundError) as exc:
                # One opening whose field cannot be read (a cutoff edited to prose) or
                # that closed or was forgotten meanwhile must not starve the others.
                log.warning(
                    "derivation skipped for one opening",
                    extra={"anchor_id": anchor.id, "event_id": event.id, "error": str(exc)},
                )
