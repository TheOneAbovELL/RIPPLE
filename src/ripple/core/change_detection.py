"""Change detection (FR-5, ADR-0020): is an incoming statement new, an update, or temporary?

The deterministic path handles structured facts: the same subject and attribute as a
VALID memory means an update of that memory. Prose goes to a ChangeDetector
implementation (the LLM one lives in ripple.llm). Either way the answer is a
ChangeClassification that the intake flow turns into a write (ADR-0015).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol

from ripple.core.errors import InvalidObjectError
from ripple.core.models import Memory, Status, StructuredFact


class ChangeKind(StrEnum):
    NEW = "new"
    UPDATE = "update"
    TEMPORARY = "temporary"
    UNCHANGED = "unchanged"  # already recorded with the same value; nothing to write


@dataclass(frozen=True)
class ChangeClassification:
    kind: ChangeKind
    reason: str
    # For UPDATE: the memory (any version) being superseded.
    updates_memory_id: str | None = None
    # For TEMPORARY: when the statement stops holding.
    valid_to: datetime | None = None

    def __post_init__(self) -> None:
        if (self.kind is ChangeKind.UPDATE) != (self.updates_memory_id is not None):
            raise InvalidObjectError("updates_memory_id is set exactly for an update")
        if self.kind is ChangeKind.TEMPORARY and self.valid_to is None:
            raise InvalidObjectError("a temporary change needs valid_to")


class ChangeDetector(Protocol):
    async def classify(
        self, content: str, structured: StructuredFact | None, candidates: Sequence[Memory]
    ) -> ChangeClassification: ...


def detect_structured_update(
    structured: StructuredFact | None,
    candidates: Sequence[Memory],
    *,
    multi_valued: frozenset[str] = frozenset(),
    permanent: frozenset[tuple[str, str]] = frozenset(),
) -> ChangeClassification | None:
    """Same subject and attribute as a VALID candidate: an update, decided without an LLM.

    Attributes in `multi_valued` (declared by the domain adapter, e.g. skills) hold one
    memory per value: the same value is UNCHANGED, a different value is a new memory,
    never an update of a sibling. (subject, attribute) pairs in `permanent` (declared by
    the adapter: a student's CGPA or skill has no end date) are NEW without asking a
    ChangeDetector whether they are temporary; only facts that can lapse (availability,
    say) go to it. The shortcut steps aside when an earlier value of the same fact is
    SUSPECT or PENDING_USER: writing a NEW fact beside it would leave two live values.
    """
    if structured is None:
        return None
    for candidate in candidates:
        if (
            candidate.status is Status.VALID
            and candidate.structured is not None
            and candidate.structured.subject == structured.subject
            and candidate.structured.attribute == structured.attribute
        ):
            if candidate.structured.value == structured.value:
                return ChangeClassification(
                    kind=ChangeKind.UNCHANGED,
                    reason="same value already recorded; nothing changes",
                )
            if structured.attribute in multi_valued:
                continue  # another value of a multi-valued attribute: a sibling, not an update
            return ChangeClassification(
                kind=ChangeKind.UPDATE,
                reason=f"{structured.subject}.{structured.attribute} already recorded; new value",
                updates_memory_id=candidate.id,
            )
    if (structured.subject, structured.attribute) in permanent and not any(
        _in_doubt_with_same_key(candidate, structured, multi_valued) for candidate in candidates
    ):
        return ChangeClassification(
            kind=ChangeKind.NEW,
            reason=f"new {structured.subject}.{structured.attribute}; permanent by the domain",
        )
    return None


def _in_doubt_with_same_key(
    candidate: Memory, structured: StructuredFact, multi_valued: frozenset[str]
) -> bool:
    """An earlier value of the same fact that a ripple or a question holds open (for a
    multi-valued attribute, only the same value counts: another value is a sibling)."""
    if candidate.status not in (Status.SUSPECT, Status.PENDING_USER):
        return False
    if candidate.structured is None:
        return False
    same_key = (
        candidate.structured.subject == structured.subject
        and candidate.structured.attribute == structured.attribute
    )
    if structured.attribute in multi_valued:
        return same_key and candidate.structured.value == structured.value
    return same_key
