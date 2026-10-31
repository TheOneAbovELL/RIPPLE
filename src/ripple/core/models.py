"""Domain models (docs/03-data-model.md).

Every model is immutable: a state change is a new object written through a Store
transaction, which is what lets the runner commit a whole wave or nothing (NFR-4) and
keeps ChangeEvents honest (I2). Domain-specific vocabulary (kinds, link types) is plain
strings declared by adapters; core interprets only the enums below.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ripple.core.ids import new_id


class Status(StrEnum):
    VALID = "VALID"
    SUSPECT = "SUSPECT"
    RETIRED = "RETIRED"
    PENDING_USER = "PENDING_USER"


class LinkClass(StrEnum):
    """The only link semantics core knows (ADR-0013)."""

    DEPENDS_ON = "depends_on"
    SNAPSHOT_OF = "snapshot_of"


class Sensitivity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class LinkCreator(StrEnum):
    RULE = "rule"
    LLM = "llm"
    MODEL = "model"
    HUMAN = "human"


class TriggerKind(StrEnum):
    RIPPLE = "ripple"
    EXPIRY = "expiry"
    USER_EDIT = "user_edit"
    USER_ANSWER = "user_answer"


class DecisionAction(StrEnum):
    KEEP = "keep"
    UPDATE = "update"
    RETIRE = "retire"
    ASK = "ask"


def _require_aware(value: datetime | None, name: str) -> None:
    if value is not None and value.tzinfo is None:
        raise ValueError(f"{name} must be timezone-aware")


class StructuredFact(BaseModel):
    """subject / attribute / value, the part rules and the rule linker can read."""

    model_config = ConfigDict(frozen=True)

    subject: str = Field(min_length=1)
    attribute: str = Field(min_length=1)
    value: str | int | float | bool


class Memory(BaseModel):
    # Serialized output always carries every field, so the OpenAPI output schema marks
    # them required (the dashboard's generated client then needs no `id ?? ""`).
    model_config = ConfigDict(frozen=True, json_schema_serialization_defaults_required=True)

    id: str = Field(default_factory=new_id)
    user_id: str = Field(min_length=1)
    domain: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    content: str = Field(min_length=1)
    structured: StructuredFact | None = None
    status: Status = Status.VALID
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    recorded_at: datetime
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    sensitivity: Sensitivity = Sensitivity.LOW
    source_ref: str | None = None
    created_by: str = Field(min_length=1)
    version: int = Field(default=1, ge=1)
    supersedes_id: str | None = None

    @model_validator(mode="after")
    def _check(self) -> "Memory":
        _require_aware(self.valid_from, "valid_from")
        _require_aware(self.valid_to, "valid_to")
        _require_aware(self.recorded_at, "recorded_at")
        if self.valid_from and self.valid_to and self.valid_to <= self.valid_from:
            raise ValueError("valid_to must be after valid_from")
        if (self.version > 1) != (self.supersedes_id is not None):
            raise ValueError("supersedes_id is set exactly when version > 1")
        if self.supersedes_id == self.id:
            raise ValueError("a memory cannot supersede itself")
        return self

    @property
    def is_temporary(self) -> bool:
        return self.valid_to is not None

    def expired_at(self, now: datetime) -> bool:
        return self.valid_to is not None and self.valid_to <= now


class Link(BaseModel):
    """Dependency edge, stored parent_id -> dependent_id (docs/03, direction convention)."""

    # Serialized output always carries every field, so the OpenAPI output schema marks
    # them required (the dashboard's generated client then needs no `id ?? ""`).
    model_config = ConfigDict(frozen=True, json_schema_serialization_defaults_required=True)

    id: str = Field(default_factory=new_id)
    parent_id: str = Field(min_length=1)
    dependent_id: str = Field(min_length=1)
    link_type: str = Field(min_length=1)
    link_class: LinkClass
    strength: float = Field(default=1.0, ge=0.0, le=1.0)
    created_by: LinkCreator
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    created_at: datetime
    verified_at: datetime | None = None

    @model_validator(mode="after")
    def _check(self) -> "Link":
        _require_aware(self.created_at, "created_at")
        _require_aware(self.verified_at, "verified_at")
        if self.parent_id == self.dependent_id:
            raise ValueError("a memory cannot depend on itself")
        return self


class Decision(BaseModel):
    model_config = ConfigDict(frozen=True)

    memory_id: str = Field(min_length=1)
    # 0 = a deterministic restoration recorded before any wave (answers); waves start at 1.
    wave: int = Field(ge=0)
    action: DecisionAction
    reason: str = Field(min_length=1)
    evidence_refs: list[str] = []
    new_version_id: str | None = None
    # The question the user sees; only an ask carries one (FR-7).
    question: str | None = None

    @model_validator(mode="after")
    def _check(self) -> "Decision":
        if (self.action is DecisionAction.UPDATE) != (self.new_version_id is not None):
            raise ValueError("new_version_id is set exactly when action is update")
        if self.question is not None and self.action is not DecisionAction.ASK:
            raise ValueError("only an ask decision carries a question")
        return self


class ChangeEvent(BaseModel):
    """One per ripple (ADR-0015); created in the trigger's transaction, appended per wave."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=new_id)
    user_id: str = Field(min_length=1)
    trigger_kind: TriggerKind
    trigger_memory_id: str = Field(min_length=1)
    affected_ids: list[str] = []
    decisions: list[Decision] = []
    # asked memory id -> ids its ask parked as SUSPECT; an answer restores exactly these.
    parked: dict[str, list[str]] = {}
    cost_usd: float | None = None
    latency_ms: int = Field(default=0, ge=0)
    trace_id: str | None = None
    created_at: datetime
    completed_at: datetime | None = None

    @model_validator(mode="after")
    def _check(self) -> "ChangeEvent":
        _require_aware(self.created_at, "created_at")
        _require_aware(self.completed_at, "completed_at")
        return self

    @property
    def is_open(self) -> bool:
        return self.completed_at is None


class ForgetEvent(BaseModel):
    """Forget is deletion, not a state change, so it is logged apart from ChangeEvents (I7)."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=new_id)
    user_id: str = Field(min_length=1)
    root_memory_id: str = Field(min_length=1)
    deleted_ids: list[str]
    created_at: datetime

    @model_validator(mode="after")
    def _check(self) -> "ForgetEvent":
        _require_aware(self.created_at, "created_at")
        return self
