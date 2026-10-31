"""Per-ChangeEvent lease: one driver per open event at a time (ADR-0099).

A ripple spans several commits and waits on a resolver (possibly a slow LLM) between
them, so two processes can both believe an open event is theirs: the API finishing a
live ripple and the worker's sweep resuming it as stranded. Without mutual exclusion
both resolve the same outstanding wave and append two sets of decisions.

`RippleRunner` takes an optional `EventLease` and holds it, keyed by the event id, for
the whole of `run` or `resume`. Core knows only acquire/release; how long a lease
lives (it must expire, or a crashed holder strands its event) and where it is stored
belong to the adapter (`ripple.worker.lease.ChangeEventLease`).
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Protocol


class EventLease(Protocol):
    async def acquire(self, event_id: str) -> bool:
        """True when this caller now drives the event; False when another holder does."""
        ...

    async def release(self, event_id: str) -> None:
        """Free the lease if this caller still holds it; a no-op otherwise."""
        ...


@asynccontextmanager
async def holding(lease: EventLease | None, event_id: str) -> AsyncGenerator[bool]:
    """Yield whether this caller may drive the event; release on exit only if acquired.

    No lease injected means no exclusion (single process, tests, the bench): always True.
    """
    if lease is None:
        yield True
        return
    acquired = await lease.acquire(event_id)
    try:
        yield acquired
    finally:
        if acquired:
            await lease.release(event_id)
