"""Request and response models (python.md: Pydantic at every boundary).

Core models (Memory, Link, ChangeEvent, ForgetEvent) are Pydantic already and are
returned as they are; the wrappers here add what the inspector needs on top, such as
the I1 flag, and keep request bodies narrower than the core dataclasses.
"""

from datetime import datetime
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from ripple.core.change_detection import ChangeKind
from ripple.core.models import (
    ChangeEvent,
    ForgetEvent,
    Link,
    LinkClass,
    LinkCreator,
    Memory,
    Sensitivity,
    Status,
    StructuredFact,
)
from ripple.storage.candidates import CandidateStatus, ResumeCandidate
from ripple.storage.feedback import Feedback
from ripple.storage.uploads import ResumeUpload
from ripple.storage.users import User

# ---- statements -----------------------------------------------------------------------

ClientOrigin = Literal["conversation", "inspector"]
# Openings, applications and criteria are written by agents and adapters, never
# posted raw by a client (WS-1's ranking would read them as agent-written).
ClientKind = Literal["fact", "derived"]


class StatementIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1, max_length=4000)
    kind: ClientKind = "fact"
    structured: StructuredFact | None = None
    origin: ClientOrigin = "conversation"
    source_ref: str | None = Field(default=None, max_length=512)
    sensitivity: Sensitivity = Sensitivity.LOW


class IntakeOut(BaseModel):
    memory: Memory
    change_kind: ChangeKind
    links_written: int
    # None when nothing was written (same value already recorded).
    event: ChangeEvent | None


# ---- memories -------------------------------------------------------------------------


class MemoryOut(BaseModel):
    memory: Memory
    flagged: bool


class MemoriesOut(BaseModel):
    memories: list[MemoryOut]


class ParentOut(BaseModel):
    """One reason the belief is held: the parent memory and the edge to it."""

    link_id: str
    link_type: str
    link_class: LinkClass
    created_by: LinkCreator
    confidence: float
    parent: Memory


class HistoryOut(BaseModel):
    versions: list[Memory]
    events: list[ChangeEvent]


class EventMemoryOut(BaseModel):
    """A memory an event names: its text and its status now (RETIRED marks the past)."""

    content: str
    status: Status


class EventsOut(BaseModel):
    """GET /events: newest first; `total` counts every event the user has."""

    events: list[ChangeEvent]
    memories: dict[str, EventMemoryOut]
    total: int


class SourceOut(BaseModel):
    """Where a resume fact came from: the upload and, when the source_ref carries a
    span, the exact characters and the line around them (ADR-0097)."""

    upload_id: str
    filename: str
    uploaded_at: datetime
    start: int | None
    end: int | None
    quote: str | None
    line: str | None


class MemoryDetailOut(BaseModel):
    memory: Memory
    flagged: bool
    why: list[ParentOut]
    history: HistoryOut | None
    # Set when source_ref names one of the user's resume uploads; None otherwise.
    source: SourceOut | None = None


class EditIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1, max_length=4000)
    structured: StructuredFact | None = None
    # FR-12 "edit (content, valid_to)": omitted keeps the old value, an explicit null
    # makes the belief permanent, a timestamp ends it then (the sweep retires it).
    valid_to: AwareDatetime | None = None


class ForgetOut(BaseModel):
    event: ForgetEvent


# ---- questions ------------------------------------------------------------------------


class QuestionOut(BaseModel):
    """One parked question (ripple.core.answers.PendingQuestion over the wire)."""

    memory: Memory
    question: str
    reason: str
    asked_at: datetime
    event_id: str


class QuestionsOut(BaseModel):
    questions: list[QuestionOut]


Answer = Literal["still_holds", "no_longer_holds", "correction"]


class AnswerIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: Answer
    content: str | None = Field(default=None, min_length=1, max_length=4000)
    structured: StructuredFact | None = None
    valid_to: datetime | None = None


class AnswerOut(BaseModel):
    """Receipt for an answer. `memory` is the latest visible version; None when the
    answer retired the memory (I1: a RETIRED row is never returned as a belief)."""

    memory_id: str
    status: Status
    memory: Memory | None
    event: ChangeEvent


# ---- resume ---------------------------------------------------------------------------


class CandidateOut(BaseModel):
    candidate: ResumeCandidate


class CandidatesOut(BaseModel):
    candidates: list[ResumeCandidate]


class ResumeUploadOut(BaseModel):
    upload_id: str
    candidates: list[ResumeCandidate]


class ConfirmOut(BaseModel):
    candidate: ResumeCandidate
    intake: IntakeOut


CandidateFilter = CandidateStatus


# ---- openings -------------------------------------------------------------------------

OpeningSource = Literal["paste", "email"]


class OpeningIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=50_000)
    source: OpeningSource = "paste"
    source_ref: str | None = Field(default=None, max_length=512)


class ParsedFieldOut(BaseModel):
    attribute: str
    value: str | int | float | bool
    span_start: int
    span_end: int
    span_text: str
    confidence: float


class OpeningOut(BaseModel):
    opening_memory_id: str
    memory_ids: list[str]
    event_id: str | None
    source_ref: str
    summary: str
    fields: list[ParsedFieldOut]


# ---- recommendations ------------------------------------------------------------------


class RecommendationOut(BaseModel):
    opening_memory_id: str
    title: str
    company: str
    eligible: bool
    fit_score: float
    fit_reasons: list[str]
    deadline: datetime | None
    flagged: bool


class RecommendationsOut(BaseModel):
    recommendations: list[RecommendationOut]


# ---- me -------------------------------------------------------------------------------


class MeOut(BaseModel):
    id: str
    display_name: str
    created_at: datetime
    telegram_linked: bool


class LinkCodeOut(BaseModel):
    code: str
    expires_at: datetime


class ExportOut(BaseModel):
    """Everything Ripple holds about the user (FR-15), including retired history."""

    exported_at: datetime
    user: User
    memories: list[Memory]
    links: list[Link]
    change_events: list[ChangeEvent]
    forget_events: list[ForgetEvent]
    resume_candidates: list[ResumeCandidate]
    resume_uploads: list[ResumeUpload] = Field(default_factory=list)
    feedback: list[Feedback] = Field(default_factory=list)  # pilot statements (ADR-0105)


# ---- graph and vocabulary (dashboard, ADR-0087) -----------------------------------------


class GraphOut(BaseModel):
    """The user's visible memories and the links between them, for the map page.

    Same I1 boundary as GET /memories: RETIRED rows are absent, so links to them are
    absent too; SUSPECT and PENDING_USER rows carry `flagged`.
    """

    nodes: list[MemoryOut]
    links: list[Link]


class LinkTypeOut(BaseModel):
    name: str
    link_class: LinkClass


class ProfileAttributeOut(BaseModel):
    """One attribute of the user's own facts, as the domain adapter declares it."""

    name: str
    value_type: Literal["number", "integer", "bool", "text"]
    permanent: bool
    multi_valued: bool
    stated_by_user: bool
    # The only accepted values when the domain fixes them (a CGPA scale is 4 or 10).
    choices: list[int] | None = None


class VocabularyOut(BaseModel):
    """What the domain adapter declares, so the dashboard hardcodes no domain values."""

    domain: str
    kinds: list[str]
    attributes: list[str]
    link_types: list[LinkTypeOut]
    # The subject of the user's own facts in a structured statement, and the shape of
    # each attribute; null and empty for a domain without a user profile.
    profile_subject: str | None
    profile_attributes: list[ProfileAttributeOut]
