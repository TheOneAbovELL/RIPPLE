"""Tool contracts: what each MCP tool accepts and returns (ADR-0080).

Inputs forbid unknown fields and are validated before any operation runs (I4 at this
boundary); the JSON schemas the server publishes are generated from these models, so
`additionalProperties: false` is what clients see. Outputs embed the core models
(Memory, Decision) as they are, plus what an agent needs on top: the I1 flag,
retrieval scores and evidence, the questions a write parked.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ripple.core.change_detection import ChangeKind
from ripple.core.models import (
    DecisionAction,
    LinkClass,
    LinkCreator,
    Memory,
    Status,
    StructuredFact,
    TriggerKind,
)
from ripple.core.retrieval_contract import RetrievalPath

# Kinds an agent may write raw. Openings and applications are built by the jobs adapter
# (structured requirements, snapshot links) and would be malformed as a bare statement.
SaveableKind = Literal["fact", "derived", "criteria"]
Reply = Literal["still_holds", "no_longer_holds", "correction"]
Visibility = Literal["visible", "flagged", "hidden"]

MAX_K = 50
MAX_CONTENT = 4000
MAX_SOURCE_REF = 512


def _require_aware(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        raise ValueError("valid_to must carry a timezone offset")
    return value


class ToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SearchIn(ToolInput):
    query: str = Field(min_length=1, max_length=2000, description="What to look for.")
    k: int = Field(default=10, ge=1, le=MAX_K, description="Maximum direct hits.")
    include_flagged: bool = Field(
        default=False,
        description="Also return SUSPECT and PENDING_USER memories, marked flagged=true.",
    )

    @field_validator("query")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("query is blank")
        return value.strip()


class SaveIn(ToolInput):
    content: str = Field(min_length=1, max_length=MAX_CONTENT)
    kind: SaveableKind = "fact"
    structured: StructuredFact | None = Field(
        default=None, description="subject / attribute / value when the fact has one."
    )
    source_ref: str | None = Field(
        default=None, max_length=MAX_SOURCE_REF, description="Where the fact came from."
    )


class UpdateIn(ToolInput):
    memory_id: str = Field(min_length=1)
    content: str = Field(min_length=1, max_length=MAX_CONTENT)
    structured: StructuredFact | None = None
    valid_to: datetime | None = Field(
        default=None, description="New expiry (timezone-aware); omitted keeps the current one."
    )

    _aware = field_validator("valid_to")(_require_aware)


class ForgetIn(ToolInput):
    memory_id: str = Field(min_length=1)


class ExplainIn(ToolInput):
    memory_id: str = Field(min_length=1)


class QuestionsIn(ToolInput):
    pass


class AnswerIn(ToolInput):
    memory_id: str = Field(min_length=1)
    reply: Reply
    content: str | None = Field(
        default=None, min_length=1, max_length=MAX_CONTENT, description="Required for a correction."
    )
    structured: StructuredFact | None = None
    valid_to: datetime | None = None

    _aware = field_validator("valid_to")(_require_aware)

    @model_validator(mode="after")
    def _correction_needs_content(self) -> "AnswerIn":
        if self.reply == "correction" and self.content is None:
            raise ValueError("a correction needs content")
        return self


# ---- outputs --------------------------------------------------------------------------


class SearchHitOut(BaseModel):
    memory: Memory
    flagged: bool
    score: float
    via: RetrievalPath
    evidence: list[str]


class SearchOut(BaseModel):
    query: str
    results: list[SearchHitOut]


class QuestionOut(BaseModel):
    memory_id: str
    memory: Memory
    question: str
    reason: str
    event_id: str
    asked_at: datetime


class WriteOut(BaseModel):
    """The receipt of ripple_save and ripple_update."""

    memory_id: str
    memory: Memory
    change_kind: ChangeKind
    links_written: int
    # None when nothing was written (the same value was already recorded).
    event_id: str | None
    # Questions this write's ripple parked for the user (FR-7).
    pending_questions: list[QuestionOut]


class ForgetOut(BaseModel):
    root_memory_id: str
    deleted_ids: list[str]
    event_id: str
    created_at: datetime


class ParentOut(BaseModel):
    """One reason the belief is held: the parent memory and the edge to it."""

    link_id: str
    link_type: str
    link_class: LinkClass
    created_by: LinkCreator
    confidence: float
    parent: Memory


class DecisionOut(BaseModel):
    memory_id: str
    wave: int
    action: DecisionAction
    reason: str
    evidence_refs: list[str]
    new_version_id: str | None
    question: str | None


class EventOut(BaseModel):
    id: str
    trigger_kind: TriggerKind
    trigger_memory_id: str
    affected_ids: list[str]
    decisions: list[DecisionOut]
    created_at: datetime
    completed_at: datetime | None


class ExplainOut(BaseModel):
    memory: Memory
    status: Status
    visibility: Visibility
    why: list[ParentOut]
    history: list[Memory]
    events: list[EventOut]


class QuestionsOut(BaseModel):
    questions: list[QuestionOut]


class AnswerOut(BaseModel):
    memory_id: str
    status: Status
    # None once the answer retired the memory (I1: a receipt never carries a RETIRED row).
    memory: Memory | None
    event_id: str


class ErrorOut(BaseModel):
    """The structured content of an is_error result."""

    error: str
    detail: str
    # Set for LLM failures: the ripples the nightly sweep will resume (ADR-0013).
    open_change_event_ids: list[str] | None = None
