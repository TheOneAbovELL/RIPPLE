"""User answers to `ask` decisions (ADR-0013 step 4, ADR-0015, FR-7).

Every answer first restores exactly the memories the ask parked (recorded on the
ChangeEvent that asked, so a memory parked by a *different* ask stays flagged). Then:
- still holds: the memory returns to VALID; the event completes at once.
- no longer holds: the memory is retired and that retirement ripples.
- corrected: a new version is written and ripples.
Restorations are recorded as wave-0 decisions, so I2 holds without a resolver call.
"""

from dataclasses import dataclass
from datetime import datetime

from ripple.core.clock import Clock
from ripple.core.errors import RippleError
from ripple.core.models import (
    ChangeEvent,
    Decision,
    DecisionAction,
    Memory,
    Status,
    StructuredFact,
    TriggerKind,
)
from ripple.core.ripple import RippleDriver
from ripple.core.store import Store, Transaction
from ripple.core.versioning import write_new_version
from ripple.core.writes import open_event


@dataclass(frozen=True)
class PendingQuestion:
    memory: Memory
    question: str
    reason: str
    event_id: str
    asked_at: datetime


async def pending_questions(store: Store, user_id: str) -> list[PendingQuestion]:
    """Every PENDING_USER memory of the user with the question its ask recorded (FR-7)."""
    pending: list[PendingQuestion] = []
    for memory in await store.memories_for_user(user_id, [Status.PENDING_USER]):
        events = await store.events_asking(memory.id)
        if not events:
            continue
        event = events[-1]
        decision = next(
            d
            for d in reversed(event.decisions)
            if d.memory_id == memory.id and d.action is DecisionAction.ASK
        )
        pending.append(
            PendingQuestion(
                memory=memory,
                question=decision.question or f"Does this still hold? {memory.content}",
                reason=decision.reason,
                event_id=event.id,
                asked_at=event.created_at,
            )
        )
    return pending


class NotPendingError(RippleError):
    def __init__(self, memory_id: str, status: Status) -> None:
        self.memory_id = memory_id
        super().__init__(f"memory {memory_id!r} is {status.value}, not PENDING_USER")


async def _pending(tx: Transaction, memory_id: str) -> Memory:
    memory = await tx.get_memory(memory_id)
    if memory.status is not Status.PENDING_USER:
        raise NotPendingError(memory_id, memory.status)
    return memory


async def _restore_parked(tx: Transaction, memory: Memory) -> list[Decision]:
    """Return parked descendants of the ask to VALID, if nothing else re-flagged them."""
    decisions: list[Decision] = []
    for event in await tx.events_asking(memory.id):
        for parked_id in event.parked.get(memory.id, []):
            try:
                dependent = await tx.get_memory(parked_id)
            except Exception:
                continue
            if dependent.status is Status.SUSPECT:
                await tx.replace_memory(dependent.model_copy(update={"status": Status.VALID}))
                decisions.append(
                    Decision(
                        memory_id=parked_id,
                        wave=0,
                        action=DecisionAction.KEEP,
                        reason="restored: the question above it was answered",
                        evidence_refs=[f"answer:{memory.id}"],
                    )
                )
    return decisions


async def confirm_still_holds(
    store: Store, clock: Clock, memory_id: str, *, trace_id: str | None = None
) -> ChangeEvent:
    now = clock.now()
    async with store.transaction() as tx:
        memory = await _pending(tx, memory_id)
        await tx.replace_memory(memory.model_copy(update={"status": Status.VALID}))
        decisions = [
            Decision(
                memory_id=memory.id,
                wave=0,
                action=DecisionAction.KEEP,
                reason="user confirmed it still holds",
                evidence_refs=[f"answer:{memory.id}"],
            ),
            *await _restore_parked(tx, memory),
        ]
        event = await open_event(tx, memory, TriggerKind.USER_ANSWER, now, trace_id=trace_id)
        event = event.model_copy(
            update={
                "affected_ids": [d.memory_id for d in decisions],
                "decisions": decisions,
                "completed_at": now,
            }
        )
        await tx.replace_change_event(event)
        return event


async def answer_no_longer_holds(
    store: Store,
    clock: Clock,
    runner: RippleDriver,
    memory_id: str,
    *,
    trace_id: str | None = None,
) -> ChangeEvent:
    now = clock.now()
    async with store.transaction() as tx:
        memory = await _pending(tx, memory_id)
        restored = await _restore_parked(tx, memory)
        await tx.replace_memory(memory.model_copy(update={"status": Status.RETIRED}))
        decisions = [
            Decision(
                memory_id=memory.id,
                wave=0,
                action=DecisionAction.RETIRE,
                reason="user said it no longer holds",
                evidence_refs=[f"answer:{memory.id}"],
            ),
            *restored,
        ]
        event = await open_event(tx, memory, TriggerKind.USER_ANSWER, now, trace_id=trace_id)
        event = event.model_copy(
            update={"affected_ids": [d.memory_id for d in restored], "decisions": decisions}
        )
        await tx.replace_change_event(event)
    return await runner.run(event)


async def answer_with_correction(
    store: Store,
    clock: Clock,
    runner: RippleDriver,
    memory_id: str,
    *,
    content: str,
    structured: StructuredFact | None = None,
    valid_to: datetime | None = None,
    trace_id: str | None = None,
) -> ChangeEvent:
    now = clock.now()
    async with store.transaction() as tx:
        memory = await _pending(tx, memory_id)
        restored = await _restore_parked(tx, memory)
        new = await write_new_version(
            tx,
            memory,
            content=content,
            structured=structured if structured is not None else memory.structured,
            valid_to=valid_to,
            created_by="user",
            now=now,
        )
        event = await open_event(tx, new, TriggerKind.USER_ANSWER, now, trace_id=trace_id)
        event = event.model_copy(
            update={"affected_ids": [d.memory_id for d in restored], "decisions": restored}
        )
        await tx.replace_change_event(event)
    return await runner.run(event)
