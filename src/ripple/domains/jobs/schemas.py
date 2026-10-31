"""Typed views over jobs memories (ADR-0030, ADR-0031).

Memories carry `StructuredFact` triples with string attributes; everything in this
adapter that needs "the CGPA as a float" or "the deadline as a datetime" reads it
through the views here, so value parsing and the derived-attribute names live in one
place. The views are pure: build them from memories you already hold.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from ripple.core.errors import InvalidObjectError
from ripple.core.models import Memory, Status, StructuredFact
from ripple.core.visibility import FLAGGED
from ripple.domains.jobs.vocabulary import (
    PROFILE_SUBJECT,
    Kind,
    OpeningAttribute,
    ProfileAttribute,
    TextSpan,
    is_opening_subject,
    opening_subject,
)

# The anchor's own structured triple: (opening_subject(<first version id>), OPENING_KEY,
# source_ref). Versioning carries `structured` over (writes.update_memory, the inspector
# edit), so every version of an anchor names the same opening and its fields and beliefs
# stay attached to it (ADR-0030, point 6). Proposed for vocabulary.py in the handover.
OPENING_KEY = "opening_key"

# Every stored cgpa_cutoff is on the ten-point scale (parsers.numbers.CGPA_SCALE_MAX),
# and a profile without a live cgpa_scale fact is too (data model, ADR-0034).
TEN_POINT_SCALE = 10


def anchor_structured(anchor_id: str, source_ref: str) -> StructuredFact:
    return StructuredFact(
        subject=opening_subject(anchor_id), attribute=OPENING_KEY, value=source_ref
    )


def opening_key(anchor: Memory) -> str:
    """The subject every field and belief of this opening carries, stable across versions."""
    if anchor.structured is not None and anchor.structured.attribute == OPENING_KEY:
        return anchor.structured.subject
    return opening_subject(anchor.id)


def span_ref(source_ref: str, span: TextSpan) -> str:
    """`<source>#<start>-<end>`: the memory's provenance down to the characters (FR-2)."""
    return f"{source_ref}#{span.start}-{span.end}"


def normalise_skill(value: str | int | float | bool) -> str:
    """Skills match case-insensitively and ignore surrounding whitespace."""
    return str(value).strip().casefold()


def parse_deadline(value: str | int | float | bool) -> datetime:
    """A deadline is stored as an ISO 8601 string with a timezone (vocabulary.py)."""
    if not isinstance(value, str):
        raise InvalidObjectError(f"deadline must be an ISO 8601 string, got {value!r}")
    try:
        moment = datetime.fromisoformat(value)
    except ValueError as exc:
        raise InvalidObjectError(f"deadline {value!r} is not ISO 8601") from exc
    if moment.tzinfo is None:
        raise InvalidObjectError(f"deadline {value!r} has no timezone")
    return moment


def parse_cgpa(value: str | int | float | bool) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise InvalidObjectError(f"cgpa must be a number, got {value!r}")
    if not 0.0 <= float(value) <= 10.0:
        raise InvalidObjectError(f"cgpa {value!r} is outside 0..10")
    return float(value)


def parse_batch(value: str | int | float | bool) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidObjectError(f"batch must be an integer year, got {value!r}")
    return value


def _usable(memory: Memory, include_flagged: bool) -> bool:
    return memory.status is Status.VALID or (include_flagged and memory.status in FLAGGED)


def _latest(memories: Iterable[Memory]) -> Memory | None:
    """The most recently recorded of several candidates; None when there is none."""
    chosen: Memory | None = None
    for memory in memories:
        if chosen is None or (memory.recorded_at, memory.id) > (chosen.recorded_at, chosen.id):
            chosen = memory
    return chosen


def _facts(
    memories: Iterable[Memory], subject: str, include_flagged: bool
) -> dict[str, list[Memory]]:
    """Facts about `subject` by attribute: VALID ones, plus SUSPECT and PENDING_USER ones
    when the caller shows them with a flag (ranking, I1). RETIRED never."""
    by_attribute: dict[str, list[Memory]] = {}
    for memory in memories:
        if (
            _usable(memory, include_flagged)
            and memory.kind == Kind.FACT
            and memory.structured is not None
            and memory.structured.subject == subject
        ):
            by_attribute.setdefault(memory.structured.attribute, []).append(memory)
    return by_attribute


def _by_value(memories: Iterable[Memory]) -> tuple[Memory, ...]:
    """Multi-valued facts in value order: the store's order within one clock tick is
    not deterministic, and belief content must be (ADR-0031)."""
    return tuple(
        sorted(
            memories,
            key=lambda m: (
                normalise_skill(m.structured.value) if m.structured else "",
                m.recorded_at,
                m.id,
            ),
        )
    )


@dataclass(frozen=True)
class ProfileView:
    """The student's profile facts (VALID unless include_flagged), one per single-valued
    attribute."""

    cgpa: Memory | None
    batch: Memory | None
    branch: Memory | None
    skills: tuple[Memory, ...]
    preferences: tuple[Memory, ...]
    cgpa_scale: Memory | None = None

    @classmethod
    def from_memories(
        cls, memories: Iterable[Memory], *, include_flagged: bool = False
    ) -> "ProfileView":
        facts = _facts(memories, PROFILE_SUBJECT, include_flagged)
        return cls(
            cgpa=_latest(facts.get(ProfileAttribute.CGPA, [])),
            batch=_latest(facts.get(ProfileAttribute.BATCH, [])),
            branch=_latest(facts.get(ProfileAttribute.BRANCH, [])),
            skills=_by_value(facts.get(ProfileAttribute.SKILL, [])),
            preferences=_by_value(facts.get(ProfileAttribute.PREFERENCE, [])),
            cgpa_scale=_latest(facts.get(ProfileAttribute.CGPA_SCALE, [])),
        )

    @property
    def cgpa_value(self) -> float | None:
        return (
            None
            if self.cgpa is None or self.cgpa.structured is None
            else parse_cgpa(self.cgpa.structured.value)
        )

    @property
    def cgpa_scale_value(self) -> int:
        """4 or 10; the ten-point default when no live scale fact exists."""
        if self.cgpa_scale is None or self.cgpa_scale.structured is None:
            return TEN_POINT_SCALE
        return int(self.cgpa_scale.structured.value)

    @property
    def cgpa_on_cutoff_scale(self) -> bool:
        """Whether the CGPA compares with a JD cutoff without a conversion."""
        return self.cgpa_scale_value == TEN_POINT_SCALE

    @property
    def batch_value(self) -> int | None:
        return (
            None
            if self.batch is None or self.batch.structured is None
            else parse_batch(self.batch.structured.value)
        )

    @property
    def skill_values(self) -> dict[str, Memory]:
        """normalised skill -> the fact that states it (first one wins on duplicates)."""
        values: dict[str, Memory] = {}
        for skill in self.skills:
            if skill.structured is not None:
                values.setdefault(normalise_skill(skill.structured.value), skill)
        return values


@dataclass(frozen=True)
class OpeningView:
    """One opening: its anchor plus its field facts (VALID unless include_flagged)."""

    anchor: Memory
    title: Memory | None
    company: Memory | None
    role_type: Memory | None
    cgpa_cutoff: Memory | None
    batch: Memory | None
    deadline: Memory | None
    location: Memory | None
    required_skills: tuple[Memory, ...]

    @classmethod
    def from_memories(
        cls, anchor: Memory, memories: Iterable[Memory], *, include_flagged: bool = False
    ) -> "OpeningView":
        if anchor.kind != Kind.OPENING:
            raise InvalidObjectError(f"memory {anchor.id!r} is a {anchor.kind}, not an opening")
        facts = _facts(memories, opening_key(anchor), include_flagged)

        def one(attribute: OpeningAttribute) -> Memory | None:
            return _latest(facts.get(attribute, []))

        return cls(
            anchor=anchor,
            title=one(OpeningAttribute.TITLE),
            company=one(OpeningAttribute.COMPANY),
            role_type=one(OpeningAttribute.ROLE_TYPE),
            cgpa_cutoff=one(OpeningAttribute.CGPA_CUTOFF),
            batch=one(OpeningAttribute.BATCH),
            deadline=one(OpeningAttribute.DEADLINE),
            location=one(OpeningAttribute.LOCATION),
            required_skills=_by_value(facts.get(OpeningAttribute.REQUIRED_SKILL, [])),
        )

    @property
    def subject(self) -> str:
        return opening_key(self.anchor)

    @property
    def label(self) -> str:
        """How the opening is named in derived content: the parser's one-line summary."""
        return self.anchor.content

    @property
    def title_value(self) -> str:
        if self.title is not None and self.title.structured is not None:
            return str(self.title.structured.value)
        return self.anchor.content

    @property
    def company_value(self) -> str:
        if self.company is not None and self.company.structured is not None:
            return str(self.company.structured.value)
        return ""

    @property
    def cgpa_cutoff_value(self) -> float | None:
        if self.cgpa_cutoff is None or self.cgpa_cutoff.structured is None:
            return None
        return parse_cgpa(self.cgpa_cutoff.structured.value)

    @property
    def batch_value(self) -> int | None:
        if self.batch is None or self.batch.structured is None:
            return None
        return parse_batch(self.batch.structured.value)

    @property
    def deadline_value(self) -> datetime | None:
        """None when absent or not a full ISO date-time: a deadline edited to prose ("to be
        announced") is unknown, never an error mid-ripple (vocabulary.py, ADR-0035)."""
        if self.deadline is None or self.deadline.structured is None:
            return None
        try:
            return parse_deadline(self.deadline.structured.value)
        except InvalidObjectError:
            return None

    @property
    def required_skill_values(self) -> dict[str, Memory]:
        """normalised skill -> the JD fact that requires it (first one wins)."""
        values: dict[str, Memory] = {}
        for skill in self.required_skills:
            if skill.structured is not None:
                values.setdefault(normalise_skill(skill.structured.value), skill)
        return values


def anchor_of(memories: Iterable[Memory]) -> Memory | None:
    """The opening anchor among a belief's parents, whatever its status."""
    return next((m for m in memories if m.kind == Kind.OPENING), None)


def opening_subject_of(memory: Memory) -> str | None:
    """The opening subject a field, belief or anchor carries; None for anything else."""
    if memory.structured is None or not is_opening_subject(memory.structured.subject):
        return None
    return memory.structured.subject
