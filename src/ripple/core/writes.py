"""The write flow: every change is a memory write that opens a ChangeEvent (ADR-0015).

Three entry points cover the four trigger kinds:
- record_memory: a new memory from a conversation, the Scout or a user edit of a fact
  that had no previous version (trigger_kind ripple or user_edit).
- update_memory: a new version of an existing memory (user_edit from the inspector,
  or the change detector recognising an updated fact).
- Expiry and user answers open their events in ripple.core.sweep and
  ripple.core.answers.

Each returns the open ChangeEvent; the caller hands it to RippleRunner.run.
"""

from collections.abc import Sequence
from datetime import datetime

from ripple.core.clock import Clock
from ripple.core.models import ChangeEvent, Link, Memory, StructuredFact, TriggerKind
from ripple.core.store import Store, Transaction
from ripple.core.versioning import write_new_version


async def open_event(
    tx: Transaction,
    trigger: Memory,
    kind: TriggerKind,
    now: datetime,
    *,
    trace_id: str | None = None,
) -> ChangeEvent:
    event = ChangeEvent(
        user_id=trigger.user_id,
        trigger_kind=kind,
        trigger_memory_id=trigger.id,
        created_at=now,
        trace_id=trace_id,
    )
    await tx.add_change_event(event)
    return event


async def record_memory(
    store: Store,
    clock: Clock,
    memory: Memory,
    links: Sequence[Link],
    *,
    kind: TriggerKind = TriggerKind.RIPPLE,
    trace_id: str | None = None,
) -> ChangeEvent:
    """Write a new memory with its links and open its ChangeEvent, atomically."""
    now = clock.now()
    async with store.transaction() as tx:
        await tx.add_memory(memory)
        for link in links:
            await tx.add_link(link)
        return await open_event(tx, memory, kind, now, trace_id=trace_id)


async def update_memory(
    store: Store,
    clock: Clock,
    old_id: str,
    *,
    content: str,
    structured: StructuredFact | None,
    valid_to: datetime | None,
    created_by: str,
    kind: TriggerKind,
    source_ref: str | None = None,
    trace_id: str | None = None,
) -> tuple[Memory, ChangeEvent]:
    """Write version n+1 of a memory (links copied, ADR-0014) and open its ChangeEvent."""
    now = clock.now()
    async with store.transaction() as tx:
        old = await tx.latest_version(old_id)
        new = await write_new_version(
            tx,
            old,
            content=content,
            structured=structured,
            valid_to=valid_to,
            created_by=created_by,
            now=now,
            source_ref=source_ref,
        )
        event = await open_event(tx, new, kind, now, trace_id=trace_id)
        return new, event
