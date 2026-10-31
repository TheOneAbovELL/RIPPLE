"""Profile facts: typed builders for the student's own facts (I5: values come from the
user or a confirmed resume span, never from this code).

Two shapes, one per write path:
- `profile_statement` for `ripple.core.intake.Intake` (change detection + linker);
- `profile_memory` / `record_profile_fact` for direct writes through
  `ripple.core.writes.record_memory` (tests, the resume confirmation flow).
Single-valued attributes (cgpa, batch, branch, ...) hold one fact; skills, projects and
preferences are one memory per value.
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Literal

from ripple.core.clock import Clock
from ripple.core.errors import InvalidObjectError
from ripple.core.intake import Statement
from ripple.core.models import (
    ChangeEvent,
    Link,
    LinkCreator,
    Memory,
    Sensitivity,
    Status,
    StructuredFact,
    TriggerKind,
)
from ripple.core.ripple import RippleRunner
from ripple.core.store import Store
from ripple.core.writes import record_memory, update_memory
from ripple.domains.jobs.schemas import normalise_skill, parse_batch, parse_cgpa
from ripple.domains.jobs.vocabulary import (
    DOMAIN,
    MULTI_VALUED_PROFILE_ATTRIBUTES,
    PROFILE_SUBJECT,
    CandidateFact,
    DerivedAttribute,
    JobsLinkType,
    Kind,
    OpeningAttribute,
    ProfileAttribute,
    jobs_registry,
)

MULTI_VALUED = MULTI_VALUED_PROFILE_ATTRIBUTES
# Attributes the search criteria are computed from (beliefs.compute_criteria).
CRITERIA_INPUTS = frozenset(
    {
        ProfileAttribute.CGPA,
        ProfileAttribute.CGPA_SCALE,
        ProfileAttribute.BATCH,
        ProfileAttribute.SKILL,
    }
)

_SENSITIVITY: dict[str, Sensitivity] = {
    ProfileAttribute.CGPA: Sensitivity.MEDIUM,
    ProfileAttribute.ACCEPTED_OFFER: Sensitivity.HIGH,
    ProfileAttribute.RESUME: Sensitivity.MEDIUM,
}


def profile_fact(attribute: ProfileAttribute, value: str | int | float | bool) -> StructuredFact:
    """The structured triple for a profile attribute, with the value checked and typed."""
    typed: str | int | float | bool
    match attribute:
        case ProfileAttribute.CGPA:
            typed = parse_cgpa(value)
        case ProfileAttribute.BATCH:
            typed = parse_batch(value)
        case ProfileAttribute.CGPA_SCALE:
            if isinstance(value, bool) or value not in (4, 10):
                raise InvalidObjectError(f"cgpa_scale must be 4 or 10, got {value!r}")
            typed = int(value)
        case ProfileAttribute.LOOKING:
            if not isinstance(value, bool):
                raise InvalidObjectError(f"looking must be a bool, got {value!r}")
            typed = value
        case _:
            if not isinstance(value, str) or not value.strip():
                raise InvalidObjectError(f"{attribute} needs a non-empty text value")
            typed = value.strip()
    return StructuredFact(subject=PROFILE_SUBJECT, attribute=attribute, value=typed)


def profile_content(attribute: ProfileAttribute, value: str | int | float | bool) -> str:
    """Default sentence when the user's own words are not available."""
    match attribute:
        case ProfileAttribute.CGPA:
            return f"CGPA is {value}"
        case ProfileAttribute.BATCH:
            return f"graduating batch is {value}"
        case ProfileAttribute.CGPA_SCALE:
            return f"CGPA is on a {value}-point scale"
        case ProfileAttribute.BRANCH:
            return f"branch is {value}"
        case ProfileAttribute.SKILL:
            return f"knows {value}"
        case ProfileAttribute.PROJECT:
            return f"built {value}"
        case ProfileAttribute.PREFERENCE:
            return f"prefers {value}"
        case ProfileAttribute.AVAILABILITY:
            return f"availability: {value}"
        case ProfileAttribute.RESUME:
            return f"resume: {value}"
        case ProfileAttribute.ACCEPTED_OFFER:
            return f"accepted an offer from {value}"
        case ProfileAttribute.LOOKING:
            return "looking for openings" if value else "not looking for openings"


def profile_statement(
    user_id: str,
    attribute: ProfileAttribute,
    value: str | int | float | bool,
    *,
    content: str | None = None,
    source_ref: str | None = None,
    origin: Literal["conversation", "inspector", "agent"] = "conversation",
    created_by: str = "user",
    confidence: float = 1.0,
) -> Statement:
    return Statement(
        user_id=user_id,
        domain=DOMAIN,
        kind=Kind.FACT,
        content=content or profile_content(attribute, value),
        structured=profile_fact(attribute, value),
        source_ref=source_ref,
        created_by=created_by,
        origin=origin,
        sensitivity=_SENSITIVITY.get(attribute, Sensitivity.LOW),
        confidence=confidence,
    )


def profile_memory(
    user_id: str,
    attribute: ProfileAttribute,
    value: str | int | float | bool,
    now: datetime,
    *,
    content: str | None = None,
    source_ref: str | None = None,
    created_by: str = "user",
    confidence: float = 1.0,
) -> Memory:
    return Memory(
        user_id=user_id,
        domain=DOMAIN,
        kind=Kind.FACT,
        content=content or profile_content(attribute, value),
        structured=profile_fact(attribute, value),
        valid_from=now,
        recorded_at=now,
        confidence=confidence,
        sensitivity=_SENSITIVITY.get(attribute, Sensitivity.LOW),
        source_ref=source_ref,
        created_by=created_by,
    )


def statement_from_candidate(
    user_id: str, candidate: CandidateFact, *, resume_ref: str
) -> Statement:
    """A resume fact the user has confirmed becomes an ordinary profile statement."""
    try:
        attribute = ProfileAttribute(candidate.attribute)
    except ValueError as exc:
        raise InvalidObjectError(f"{candidate.attribute!r} is not a ProfileAttribute") from exc
    return profile_statement(
        user_id,
        attribute,
        candidate.value,
        content=candidate.content or None,
        source_ref=f"{resume_ref}#{candidate.span.start}-{candidate.span.end}",
        confidence=candidate.confidence,
    )


def _same_value(a: StructuredFact, b: StructuredFact) -> bool:
    if a.attribute in MULTI_VALUED:
        return normalise_skill(a.value) == normalise_skill(b.value)
    return a.value == b.value


def _live_profile_facts(memories: list[Memory], attribute: str) -> list[Memory]:
    return [
        m
        for m in memories
        if m.status is not Status.RETIRED
        and m.kind == Kind.FACT
        and m.structured is not None
        and m.structured.subject == PROFILE_SUBJECT
        and m.structured.attribute == attribute
    ]


def rule_targets(fact: Memory, memories: Sequence[Memory]) -> list[tuple[Memory, str]]:
    """The live beliefs a profile fact must reach, with the link type, by domain rule.

    The dependency is mechanical (ADR-0031 point 5, ADR-0034, ADR-0116): cgpa, its
    scale, batch and skills feed the search criteria; the scale feeds every
    eligibility belief; a skill feeds the fit of every opening that requires it.
    """
    if fact.structured is None or fact.structured.subject != PROFILE_SUBJECT:
        return []
    attribute = fact.structured.attribute
    targets: list[tuple[Memory, str]] = []
    live = [m for m in memories if m.status is not Status.RETIRED and m.structured is not None]
    if attribute in CRITERIA_INPUTS:
        targets += [
            (m, JobsLinkType.CRITERIA_FROM)
            for m in live
            if m.kind == Kind.CRITERIA and m.structured.attribute == DerivedAttribute.CRITERIA  # type: ignore[union-attr]
        ]
    if attribute == ProfileAttribute.CGPA_SCALE:
        targets += [
            (m, JobsLinkType.ELIGIBILITY_OF)
            for m in live
            if m.kind == Kind.DERIVED and m.structured.attribute == DerivedAttribute.ELIGIBLE  # type: ignore[union-attr]
        ]
    if attribute == ProfileAttribute.SKILL:
        skill = normalise_skill(fact.structured.value)
        requiring = {
            m.structured.subject  # type: ignore[union-attr]
            for m in live
            if m.kind == Kind.FACT
            and m.structured.attribute == OpeningAttribute.REQUIRED_SKILL  # type: ignore[union-attr]
            and normalise_skill(m.structured.value) == skill  # type: ignore[union-attr]
        }
        targets += [
            (m, JobsLinkType.FIT_OF)
            for m in live
            if m.kind == Kind.DERIVED
            and m.structured.attribute == DerivedAttribute.FIT_SCORE  # type: ignore[union-attr]
            and m.structured.subject in requiring  # type: ignore[union-attr]
        ]
    return targets


def _rule_links(fact: Memory, memories: list[Memory], created_at: datetime) -> list[Link]:
    """Deterministic links from a new profile fact to the beliefs that must read it.

    A belief only links to the parents it read when it was derived, so a fact recorded
    afterwards would never reach it (the "hidden link" case). For the jobs beliefs the
    dependency is mechanical: a skill matters to every fit belief whose opening requires
    it, cgpa, batch and skills matter to the search criteria (ADR-0031, point 5), and
    the cgpa scale matters to every eligibility belief (ADR-0034:
    the rule must see the scale to know whether the CGPA and the cutoff compare).
    """
    registry = jobs_registry()
    targets = rule_targets(fact, memories)
    return [
        Link(
            parent_id=fact.id,
            dependent_id=belief.id,
            link_type=link_type,
            link_class=registry.class_of(link_type),
            created_by=LinkCreator.RULE,
            created_at=created_at,
        )
        for belief, link_type in targets
    ]


async def _link_beliefs_derived_since(
    store: Store, fact: Memory, memories: list[Memory], now: datetime
) -> None:
    """Rule links the held fact lacks, for beliefs derived after it was recorded.

    Written on the current version before it is superseded: `update_memory` then copies
    them to the new version in the same transaction as its ChangeEvent (ADR-0014), so a
    crash can never leave an open event whose graph misses them.
    """
    linked = {link.dependent_id for link in await store.dependents_of(fact.id)}
    missing = [link for link in _rule_links(fact, memories, now) if link.dependent_id not in linked]
    if not missing:
        return
    async with store.transaction() as tx:
        for link in missing:
            await tx.add_link(link)


async def record_profile_fact(
    store: Store,
    clock: Clock,
    runner: RippleRunner,
    user_id: str,
    attribute: ProfileAttribute,
    value: str | int | float | bool,
    *,
    content: str | None = None,
    source_ref: str | None = None,
    created_by: str = "user",
    trace_id: str | None = None,
) -> tuple[Memory, ChangeEvent | None]:
    """Record one profile fact and ripple it; the adapter's own write path.

    - The same value already held: nothing is written; returns (existing, None).
    - A single-valued attribute (cgpa, batch, ...) already held with another value: a
      new version through `update_memory`, so every belief built on it ripples (M2 of
      the WS-1 review; the Intake path does the same through change detection).
    - Otherwise a new memory, with rule links to the beliefs that must read it.
    """
    structured = profile_fact(attribute, value)
    memories = await store.memories_for_user(user_id)
    held = _live_profile_facts(memories, attribute)
    for existing in held:
        assert existing.structured is not None
        if _same_value(existing.structured, structured):
            return existing, None
    if attribute not in MULTI_VALUED and held:
        current = max(held, key=lambda m: (m.recorded_at, m.id))
        if attribute == ProfileAttribute.CGPA_SCALE:
            await _link_beliefs_derived_since(store, current, memories, clock.now())
        new, event = await update_memory(
            store,
            clock,
            current.id,
            content=content or profile_content(attribute, value),
            structured=structured,
            valid_to=None,
            created_by=created_by,
            kind=TriggerKind.RIPPLE,
            source_ref=source_ref,
            trace_id=trace_id,
        )
        return new, await runner.run(event)
    memory = profile_memory(
        user_id,
        attribute,
        value,
        clock.now(),
        content=content,
        source_ref=source_ref,
        created_by=created_by,
    )
    links = _rule_links(memory, memories, memory.recorded_at)
    event = await record_memory(
        store, clock, memory, links, kind=TriggerKind.RIPPLE, trace_id=trace_id
    )
    return memory, await runner.run(event)
