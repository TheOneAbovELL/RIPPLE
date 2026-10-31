"""Shared jobs-domain vocabulary (docs/plans/parallel-execution.md, contract C1).

Kinds, subjects, attribute names, link types and the ranking contract that the adapter,
the parsers, the API, the agents, the digest and the bench all read. Owned by the
coordinator; a workstream that needs a new name proposes it in its handover rather than
editing this file, so two workstreams never disagree on a string.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol

from ripple.core.links import LinkTypeRegistry
from ripple.core.models import LinkClass

DOMAIN = "jobs"
PROFILE_SUBJECT = "student"


class Kind(StrEnum):
    """Memory.kind values the jobs adapter declares (core interprets none of them)."""

    FACT = "fact"
    DERIVED = "derived"
    OPENING = "opening"
    APPLICATION = "application"
    CRITERIA = "criteria"


class ProfileAttribute(StrEnum):
    """StructuredFact.attribute for subject PROFILE_SUBJECT."""

    CGPA = "cgpa"
    # 10 (default in the pilot) or 4; parsers store the raw number, the scale is confirmed
    # with the fact. Eligibility compares only within one scale (WS-2 integration note).
    CGPA_SCALE = "cgpa_scale"
    BATCH = "batch"
    BRANCH = "branch"
    SKILL = "skill"
    PROJECT = "project"
    PREFERENCE = "preference"
    AVAILABILITY = "availability"
    RESUME = "resume"
    ACCEPTED_OFFER = "accepted_offer"
    LOOKING = "looking"


class OpeningAttribute(StrEnum):
    """StructuredFact.attribute for subject opening_subject(<opening memory id>)."""

    TITLE = "title"
    COMPANY = "company"
    ROLE_TYPE = "role_type"  # internship | full_time
    CGPA_CUTOFF = "cgpa_cutoff"
    BATCH = "batch"
    # ISO 8601 date-time with timezone as a string when the JD gives a full date; the
    # raw text at low confidence otherwise (ADR-0035). Consumers treat a value that
    # datetime.fromisoformat rejects as unknown, never as an error.
    DEADLINE = "deadline"
    LOCATION = "location"
    REQUIRED_SKILL = "required_skill"
    SOURCE_URL = "source_url"


class DerivedAttribute(StrEnum):
    """StructuredFact.attribute of the beliefs the jobs adapter derives (ADR-0031)."""

    ELIGIBLE = "eligible"  # bool, subject opening_subject(anchor id)
    FIT_SCORE = "fit_score"  # float 0..1, subject opening_subject(anchor id)
    REMIND_AT = "remind_at"  # ISO 8601 string, subject opening_subject(anchor id)
    CRITERIA = "criteria"  # str, subject PROFILE_SUBJECT


# One memory per value; a second value is a sibling, never an update (ADR-0020).
MULTI_VALUED_PROFILE_ATTRIBUTES: frozenset[str] = frozenset(
    {ProfileAttribute.SKILL, ProfileAttribute.PROJECT, ProfileAttribute.PREFERENCE}
)

# Profile attributes that have no end date of their own: a new one is a permanent fact,
# classified without asking a model whether it is temporary (ADR-0116). Availability,
# preferences and "looking" can lapse, so the change detector still decides those.
PERMANENT_PROFILE_ATTRIBUTES: frozenset[str] = frozenset(
    {
        ProfileAttribute.CGPA,
        ProfileAttribute.CGPA_SCALE,
        ProfileAttribute.BATCH,
        ProfileAttribute.BRANCH,
        ProfileAttribute.SKILL,
        ProfileAttribute.PROJECT,
        ProfileAttribute.RESUME,
        ProfileAttribute.ACCEPTED_OFFER,
    }
)
# The (subject, attribute) pairs Intake classifies as permanent (core keys on both, so an
# opening field never borrows a profile attribute's permanence).
PERMANENT_PROFILE_FACTS: frozenset[tuple[str, str]] = frozenset(
    (PROFILE_SUBJECT, attribute) for attribute in PERMANENT_PROFILE_ATTRIBUTES
)

# The value type `profile.profile_fact` accepts for each attribute, published by
# GET /vocabulary so clients build the right input without hardcoding the domain.
PROFILE_VALUE_TYPES: dict[str, str] = {
    ProfileAttribute.CGPA: "number",
    ProfileAttribute.CGPA_SCALE: "integer",
    ProfileAttribute.BATCH: "integer",
    ProfileAttribute.LOOKING: "bool",
}  # every other profile attribute is non-empty text

# Attributes whose value must be one of a fixed set (profile.profile_fact refuses others).
PROFILE_VALUE_CHOICES: dict[str, tuple[int, ...]] = {ProfileAttribute.CGPA_SCALE: (4, 10)}

# Written by a flow of its own (the resume review), never typed as a statement.
PROFILE_ATTRIBUTES_NOT_STATED: frozenset[str] = frozenset({ProfileAttribute.RESUME})


def opening_subject(opening_memory_id: str) -> str:
    return f"opening:{opening_memory_id}"


def is_opening_subject(subject: str) -> bool:
    return subject.startswith("opening:")


class JobsLinkType(StrEnum):
    ELIGIBILITY_OF = "eligibility_of"
    FIT_OF = "fit_of"
    REMINDER_FOR = "reminder_for"
    CRITERIA_FROM = "criteria_from"
    SENT_WITH_RESUME = "sent_with_resume"


JOBS_LINK_TYPES: Mapping[str, LinkClass] = {
    JobsLinkType.ELIGIBILITY_OF: LinkClass.DEPENDS_ON,
    JobsLinkType.FIT_OF: LinkClass.DEPENDS_ON,
    JobsLinkType.REMINDER_FOR: LinkClass.DEPENDS_ON,
    JobsLinkType.CRITERIA_FROM: LinkClass.DEPENDS_ON,
    JobsLinkType.SENT_WITH_RESUME: LinkClass.SNAPSHOT_OF,
}


def jobs_registry() -> LinkTypeRegistry:
    """Generic link types plus the jobs ones (docs/03, link types table)."""
    return LinkTypeRegistry(JOBS_LINK_TYPES)


# ---- parser outputs: produced by WS-2 parsers, consumed by the API and the adapter ----


@dataclass(frozen=True)
class TextSpan:
    """Character offsets into the source text; `text` is the exact substring (FR-2)."""

    start: int
    end: int
    text: str


@dataclass(frozen=True)
class ParsedField:
    attribute: str  # an OpeningAttribute or ProfileAttribute value
    value: str | int | float | bool
    span: TextSpan
    confidence: float = 1.0


@dataclass(frozen=True)
class ParsedOpening:
    """One JD parsed into fields with spans; the adapter turns it into memories."""

    source_ref: str  # url, "email:<id>" or "paste:<id>"
    raw_text: str
    fields: tuple[ParsedField, ...]
    summary: str  # one line: title at company

    def get(self, attribute: str) -> ParsedField | None:
        return next((f for f in self.fields if f.attribute == attribute), None)

    def all(self, attribute: str) -> tuple[ParsedField, ...]:
        return tuple(f for f in self.fields if f.attribute == attribute)


@dataclass(frozen=True)
class CandidateFact:
    """A profile fact extracted from a resume, not yet confirmed by the user (I5)."""

    attribute: str  # ProfileAttribute value
    value: str | int | float | bool
    span: TextSpan
    confidence: float = 1.0
    content: str = ""  # human-readable sentence; the memory content once confirmed


# ---- ranking contract: produced by the adapter, consumed by digest, API and agents ----


@dataclass(frozen=True)
class Recommendation:
    opening_memory_id: str
    title: str
    company: str
    eligible: bool
    fit_score: float  # 0..1
    fit_reasons: tuple[str, ...]  # each one cites a JD line or a profile fact
    deadline: datetime | None
    flagged: bool = False  # built on a SUSPECT or PENDING_USER memory (I1)

    def hours_until_deadline(self, now: datetime) -> float | None:
        """Hours from `now` (an injected clock) to the deadline; negative once passed."""
        if self.deadline is None:
            return None
        return (self.deadline - now).total_seconds() / 3600.0


class RecommendationSource(Protocol):
    """What the digest and the API call to get a user's ranked openings."""

    async def recommendations_for(
        self, user_id: str, *, now: datetime, limit: int = 10
    ) -> Sequence[Recommendation]: ...
