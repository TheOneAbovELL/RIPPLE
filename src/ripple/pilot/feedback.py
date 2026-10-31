"""Recording a student's feedback, shared by `POST /feedback` and the bot (ADR-0105).

One function so the API and the Telegram dispatcher apply the same rules: the target
must be the student's own memory; recommendation kinds need an opening, question kinds
need a memory the resolver asked about. It writes one feedback row and nothing else:
no memory, no ChangeEvent, no message (I6).
"""

from ripple.core.clock import Clock
from ripple.core.errors import RippleError
from ripple.core.store import MemoryNotFoundError, StoreReader
from ripple.domains.jobs.vocabulary import Kind
from ripple.storage.feedback import (
    QUESTION_KINDS,
    RECOMMENDATION_KINDS,
    Feedback,
    FeedbackKind,
    FeedbackStore,
)


class FeedbackTargetNotFoundError(RippleError):
    """Unknown memory or another user's; callers answer as if it did not exist."""


class FeedbackKindMismatchError(RippleError):
    """The kind is about something the target is not (an opening, an asked memory)."""


async def record_feedback(
    store: StoreReader,
    feedback_store: FeedbackStore,
    clock: Clock,
    *,
    user_id: str,
    target_memory_id: str,
    kind: FeedbackKind,
    note: str | None = None,
) -> tuple[Feedback, bool]:
    """The stored row and whether this call created it (first statement wins)."""
    try:
        target = await store.get_memory(target_memory_id)
    except MemoryNotFoundError as exc:
        raise FeedbackTargetNotFoundError(target_memory_id) from exc
    if target.user_id != user_id:
        raise FeedbackTargetNotFoundError(target_memory_id)
    if kind in RECOMMENDATION_KINDS and target.kind != Kind.OPENING:
        raise FeedbackKindMismatchError(f"{kind.value} is about a recommended opening")
    if kind in QUESTION_KINDS and not await store.events_asking(target.id):
        raise FeedbackKindMismatchError(f"{kind.value} is about a question the agent asked")
    return await feedback_store.record(
        Feedback(
            user_id=user_id,
            target_memory_id=target.id,
            kind=kind,
            note=note,
            created_at=clock.now(),
        )
    )
