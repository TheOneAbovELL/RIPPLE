"""Builders for test objects (tests.md): sensible defaults, override what the test is about.

Every builder takes `at` for timestamps so tests stay deterministic under FakeClock.
"""

from datetime import datetime

from ripple.core.ids import new_id
from ripple.core.models import (
    ChangeEvent,
    Decision,
    DecisionAction,
    Link,
    LinkClass,
    LinkCreator,
    Memory,
    Sensitivity,
    Status,
    StructuredFact,
    TriggerKind,
)
from tests.fakes.clock import DEFAULT_START

USER = "student-1"
DOMAIN = "jobs"


def memory(
    *,
    content: str = "CGPA is 7.6",
    kind: str = "fact",
    structured: StructuredFact | None = None,
    status: Status = Status.VALID,
    user_id: str = USER,
    domain: str = DOMAIN,
    at: datetime = DEFAULT_START,
    valid_from: datetime | None = None,
    valid_to: datetime | None = None,
    confidence: float = 1.0,
    sensitivity: Sensitivity = Sensitivity.LOW,
    source_ref: str | None = "msg-1",
    created_by: str = "user",
    version: int = 1,
    supersedes_id: str | None = None,
    id: str | None = None,
) -> Memory:
    return Memory(
        id=id if id is not None else new_id(),
        user_id=user_id,
        domain=domain,
        kind=kind,
        content=content,
        structured=structured,
        status=status,
        recorded_at=at,
        valid_from=valid_from,
        valid_to=valid_to,
        confidence=confidence,
        sensitivity=sensitivity,
        source_ref=source_ref,
        created_by=created_by,
        version=version,
        supersedes_id=supersedes_id,
    )


def fact(subject: str, attribute: str, value: str | int | float | bool, **overrides) -> Memory:
    overrides.setdefault("content", f"{subject} {attribute} is {value}")
    return memory(
        kind="fact",
        structured=StructuredFact(subject=subject, attribute=attribute, value=value),
        **overrides,
    )


def derived(content: str, **overrides) -> Memory:
    overrides.setdefault("created_by", "curator")
    overrides.setdefault("kind", "derived")
    return memory(content=content, **overrides)


def link(
    parent: Memory | str,
    dependent: Memory | str,
    *,
    link_type: str = "depends_on_fact",
    link_class: LinkClass = LinkClass.DEPENDS_ON,
    created_by: LinkCreator = LinkCreator.RULE,
    strength: float = 1.0,
    confidence: float = 1.0,
    at: datetime = DEFAULT_START,
) -> Link:
    return Link(
        parent_id=parent if isinstance(parent, str) else parent.id,
        dependent_id=dependent if isinstance(dependent, str) else dependent.id,
        link_type=link_type,
        link_class=link_class,
        created_by=created_by,
        strength=strength,
        confidence=confidence,
        created_at=at,
    )


def snapshot_link(parent: Memory | str, dependent: Memory | str, **overrides) -> Link:
    overrides.setdefault("link_type", "sent_with_resume")
    return link(parent, dependent, link_class=LinkClass.SNAPSHOT_OF, **overrides)


def decision(
    memory: Memory | str,
    action: DecisionAction = DecisionAction.KEEP,
    *,
    wave: int = 1,
    reason: str = "test decision",
    evidence_refs: list[str] | None = None,
    new_version_id: str | None = None,
) -> Decision:
    return Decision(
        memory_id=memory if isinstance(memory, str) else memory.id,
        wave=wave,
        action=action,
        reason=reason,
        evidence_refs=evidence_refs or [],
        new_version_id=new_version_id,
    )


def change_event(
    trigger: Memory | str,
    *,
    trigger_kind: TriggerKind = TriggerKind.RIPPLE,
    user_id: str = USER,
    at: datetime = DEFAULT_START,
    affected_ids: list[str] | None = None,
    decisions: list[Decision] | None = None,
    completed_at: datetime | None = None,
) -> ChangeEvent:
    return ChangeEvent(
        user_id=user_id,
        trigger_kind=trigger_kind,
        trigger_memory_id=trigger if isinstance(trigger, str) else trigger.id,
        affected_ids=affected_ids or [],
        decisions=decisions or [],
        created_at=at,
        completed_at=completed_at,
    )
