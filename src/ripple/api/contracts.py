"""Protocols the API depends on but does not implement (docs/plans/parallel-execution.md).

The parsers are WS-2's, the opening recorder and the recommendation source are
WS-1's. The API is built and tested against these shapes with fakes; the coordinator
injects the real implementations through `Services` at integration. Nothing here
imports a sibling workstream's module.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from ripple.core.errors import RippleError
from ripple.core.intake import Statement
from ripple.domains.jobs.vocabulary import (
    CandidateFact,
    ParsedOpening,
    Recommendation,
    RecommendationSource,
)

__all__ = [
    "CandidateFact",
    "CandidateStatements",
    "OpeningParser",
    "OpeningRecorder",
    "OpeningUnparseableError",
    "OpeningWritten",
    "ParsedOpening",
    "Recommendation",
    "RecommendationSource",
    "ResumeParse",
    "ResumeParser",
    "ResumeUnparseableError",
]


class ResumeUnparseableError(RippleError):
    """The PDF has no usable text layer or the structuring step could not read it."""


class OpeningUnparseableError(RippleError):
    """The pasted text is not a job description the parser can structure."""


@dataclass(frozen=True)
class ResumeParse:
    """What a resume upload yields: the text the parser read and the facts it found in
    it. The text is persisted (ADR-0097) because every fact's span indexes into it."""

    text: str
    facts: Sequence[CandidateFact]


class ResumeParser(Protocol):
    """WS-2: pypdf text extraction, then LLM structuring into candidate facts (ADR-0024)."""

    async def parse(self, pdf: bytes, *, source_ref: str) -> ResumeParse: ...


class CandidateStatements(Protocol):
    """WS-2's candidate_to_statement: a confirmed candidate becomes an Intake statement."""

    def statement_for(
        self, user_id: str, candidate: CandidateFact, *, source_ref: str
    ) -> Statement: ...


class OpeningParser(Protocol):
    """WS-2: a pasted JD or forwarded email body into fields with spans (FR-2)."""

    async def parse(self, text: str, *, source_ref: str) -> ParsedOpening: ...


@dataclass(frozen=True)
class OpeningWritten:
    """What the API tells the client after an opening was recorded. Named apart from
    WS-1's richer `ripple.domains.jobs.openings.RecordedOpening`, which the integration
    adapter reduces to these ids."""

    opening_memory_id: str
    memory_ids: tuple[str, ...]
    event_id: str | None = None


class OpeningRecorder(Protocol):
    """WS-1's `record_opening`: writes the anchor, its field facts and links, then ripples."""

    async def record(self, user_id: str, opening: ParsedOpening) -> OpeningWritten: ...


@dataclass(frozen=True)
class ProfileAttributeSpec:
    """How a client states one of the user's own facts: the value's type, whether a new
    value is permanent (classified without a model, ADR-0116), whether values are
    siblings rather than versions (ADR-0020), and whether the user types it at all."""

    name: str
    value_type: str  # number | integer | bool | text
    permanent: bool
    multi_valued: bool
    stated_by_user: bool
    choices: tuple[int, ...] | None = None  # the only accepted values, when fixed


@dataclass(frozen=True)
class DomainVocabulary:
    """The memory kinds and structured-fact attributes a domain adapter declares."""

    kinds: tuple[str, ...]
    attributes: tuple[str, ...]
    profile_subject: str | None = None
    profile_attributes: tuple[ProfileAttributeSpec, ...] = ()


def jobs_vocabulary() -> DomainVocabulary:
    from ripple.domains.jobs.vocabulary import (
        MULTI_VALUED_PROFILE_ATTRIBUTES,
        PERMANENT_PROFILE_ATTRIBUTES,
        PROFILE_ATTRIBUTES_NOT_STATED,
        PROFILE_SUBJECT,
        PROFILE_VALUE_CHOICES,
        PROFILE_VALUE_TYPES,
        Kind,
        OpeningAttribute,
        ProfileAttribute,
    )

    return DomainVocabulary(
        kinds=tuple(k.value for k in Kind),
        attributes=tuple(a.value for a in (*ProfileAttribute, *OpeningAttribute)),
        profile_subject=PROFILE_SUBJECT,
        profile_attributes=tuple(
            ProfileAttributeSpec(
                name=a.value,
                value_type=PROFILE_VALUE_TYPES.get(a, "text"),
                permanent=a in PERMANENT_PROFILE_ATTRIBUTES,
                multi_valued=a in MULTI_VALUED_PROFILE_ATTRIBUTES,
                stated_by_user=a not in PROFILE_ATTRIBUTES_NOT_STATED,
                choices=PROFILE_VALUE_CHOICES.get(a),
            )
            for a in ProfileAttribute
        ),
    )
