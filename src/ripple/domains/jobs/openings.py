"""Recording an opening: one anchor plus one fact per parsed field (ADR-0030).

The anchor, its fields and the `field --depends_on_fact--> anchor` links commit in one
transaction with one ChangeEvent (trigger: the anchor), which the caller's runner then
drives. Forgetting the anchor cascades to every field (I7); the field facts are what the
derivation (`derive.py`) and the rules (`rules.py`) read.
"""

from dataclasses import dataclass

from ripple.core.clock import Clock
from ripple.core.errors import InvalidObjectError
from ripple.core.ids import new_id
from ripple.core.models import (
    ChangeEvent,
    Link,
    LinkCreator,
    Memory,
    Status,
    StructuredFact,
    TriggerKind,
)
from ripple.core.ripple import RippleRunner
from ripple.core.store import Store
from ripple.core.writes import open_event
from ripple.domains.jobs.schemas import (
    anchor_structured,
    opening_key,
    parse_batch,
    parse_cgpa,
    parse_deadline,
    span_ref,
)
from ripple.domains.jobs.vocabulary import (
    DOMAIN,
    Kind,
    OpeningAttribute,
    ParsedField,
    ParsedOpening,
    jobs_registry,
)

FIELD_LINK_TYPE = "depends_on_fact"
SCOUT = "scout"

# Every attribute except required_skill holds one value per opening; two batch or two
# deadline fields would make the views pick one arbitrarily (ADR-0030, point 5).
MULTI_VALUED_OPENING_ATTRIBUTES = frozenset({OpeningAttribute.REQUIRED_SKILL})


class OpeningAlreadyRecordedError(InvalidObjectError):
    """The same source is already held as a live opening; re-recording would duplicate it."""

    def __init__(self, source_ref: str, anchor_id: str) -> None:
        self.source_ref = source_ref
        self.anchor_id = anchor_id
        super().__init__(f"opening from {source_ref!r} is already recorded as {anchor_id!r}")


@dataclass(frozen=True)
class RecordedOpening:
    anchor: Memory
    fields: tuple[Memory, ...]
    event: ChangeEvent

    def field(self, attribute: str) -> Memory | None:
        return next(
            (f for f in self.fields if f.structured and f.structured.attribute == attribute), None
        )

    def all_fields(self, attribute: str) -> tuple[Memory, ...]:
        return tuple(f for f in self.fields if f.structured and f.structured.attribute == attribute)


def _validate(field: ParsedField, raw_text: str) -> None:
    """Refuse a malformed field before anything is written (I4 for parser output)."""
    if field.attribute not in set(OpeningAttribute):
        raise InvalidObjectError(f"{field.attribute!r} is not an OpeningAttribute")
    match field.attribute:
        case OpeningAttribute.CGPA_CUTOFF:
            parse_cgpa(field.value)
        case OpeningAttribute.BATCH:
            parse_batch(field.value)
        case OpeningAttribute.DEADLINE:
            parse_deadline(field.value)
        case _:
            if not str(field.value).strip():
                raise InvalidObjectError(f"{field.attribute} has an empty value")
    if not 0.0 <= field.confidence <= 1.0:
        raise InvalidObjectError("field confidence must be in [0, 1]")
    # The span text becomes the content that fit reasons quote as "JD says"; it must be
    # the JD's own words, never a fallback this code made up (FR-2, I5).
    if not field.span.text.strip():
        raise InvalidObjectError(f"{field.attribute} has an empty span")
    if raw_text[field.span.start : field.span.end] != field.span.text:
        raise InvalidObjectError(f"{field.attribute} span does not match the source text")


def _validate_opening(parsed: ParsedOpening) -> None:
    if not parsed.summary.strip():
        raise InvalidObjectError("an opening needs a one-line summary")
    seen: set[str] = set()
    for field in parsed.fields:
        _validate(field, parsed.raw_text)
        if field.attribute in seen and field.attribute not in MULTI_VALUED_OPENING_ATTRIBUTES:
            raise InvalidObjectError(f"{field.attribute} appears twice; it holds one value")
        seen.add(field.attribute)


def field_memory(
    anchor: Memory, parsed: ParsedOpening, field: ParsedField, *, created_by: str = SCOUT
) -> Memory:
    """A field fact: the JD's own words as content, the typed triple as structured."""
    _validate(field, parsed.raw_text)
    return Memory(
        user_id=anchor.user_id,
        domain=DOMAIN,
        kind=Kind.FACT,
        content=field.span.text.strip(),
        structured=StructuredFact(
            subject=opening_key(anchor), attribute=field.attribute, value=field.value
        ),
        valid_from=anchor.valid_from,
        recorded_at=anchor.recorded_at,
        confidence=field.confidence,
        source_ref=span_ref(parsed.source_ref, field.span),
        created_by=created_by,
    )


async def find_opening(store: Store, user_id: str, source_ref: str) -> Memory | None:
    """The live (not RETIRED) anchor recorded from this source, if any."""
    return next(
        (
            m
            for m in await store.memories_for_user(user_id)
            if m.kind == Kind.OPENING
            and m.source_ref == source_ref
            and m.status is not Status.RETIRED
        ),
        None,
    )


async def record_opening(
    store: Store,
    clock: Clock,
    user_id: str,
    parsed: ParsedOpening,
    runner: RippleRunner,
    *,
    created_by: str = SCOUT,
    trace_id: str | None = None,
) -> RecordedOpening:
    """Write the anchor, its field facts and their links atomically, then ripple.

    Raises OpeningAlreadyRecordedError when the source is already a live opening (the
    Scout re-fetching a JD, or the same paste twice). If the ripple fails after the
    commit, the opening is stored and its open ChangeEvent is resumed by the sweep.
    """
    _validate_opening(parsed)
    existing = await find_opening(store, user_id, parsed.source_ref)
    if existing is not None:
        raise OpeningAlreadyRecordedError(parsed.source_ref, existing.id)
    now = clock.now()
    registry = jobs_registry()
    anchor_id = new_id()
    anchor = Memory(
        id=anchor_id,
        user_id=user_id,
        domain=DOMAIN,
        kind=Kind.OPENING,
        content=parsed.summary.strip(),
        structured=anchor_structured(anchor_id, parsed.source_ref),
        valid_from=now,
        recorded_at=now,
        source_ref=parsed.source_ref,
        created_by=created_by,
    )
    fields = tuple(field_memory(anchor, parsed, f, created_by=created_by) for f in parsed.fields)
    links = [
        Link(
            parent_id=anchor.id,
            dependent_id=field.id,
            link_type=FIELD_LINK_TYPE,
            link_class=registry.class_of(FIELD_LINK_TYPE),
            created_by=LinkCreator.RULE,
            created_at=now,
        )
        for field in fields
    ]
    async with store.transaction() as tx:
        await tx.add_memory(anchor)
        for field in fields:
            await tx.add_memory(field)
        for link in links:
            await tx.add_link(link)
        event = await open_event(tx, anchor, TriggerKind.RIPPLE, now, trace_id=trace_id)
    event = await runner.run(event)
    return RecordedOpening(anchor=anchor, fields=fields, event=event)


async def opening_memories(store: Store, anchor_id: str) -> list[Memory]:
    """Every memory, any status, that carries this opening's subject (anchor versions,
    fields and beliefs)."""
    anchor = await store.get_memory(anchor_id)
    subject = opening_key(anchor)
    return [
        m
        for m in await store.memories_for_user(anchor.user_id)
        if m.structured is not None and m.structured.subject == subject
    ]
