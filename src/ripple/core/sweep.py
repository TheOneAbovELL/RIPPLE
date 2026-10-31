"""The nightly sweep (ADR-0015, ADR-0013): expiry and recovery, both deterministic.

- Expiry: a VALID memory whose valid_to has passed is retired and its expiry rippled
  (trigger_kind=expiry). No LLM decides that a date has passed.
- Recovery: an open ChangeEvent older than `stale_after` is resumed, so a crash
  between commits cannot strand SUSPECT memories. An event another process still
  drives (its runner holds the per-event lease, ADR-0099) comes back open from
  `resume`; the sweep logs it as skipped, leaves it out of its result, and the next
  sweep tries again.
Weak-link re-verification (FR-16) joins this module when the Linker exists.
"""

import logging
from datetime import timedelta

from ripple.core.clock import Clock
from ripple.core.models import ChangeEvent, Status, TriggerKind
from ripple.core.ripple import RippleDriver
from ripple.core.store import Store
from ripple.core.writes import open_event

log = logging.getLogger("ripple.core.sweep")

DEFAULT_STALE_AFTER = timedelta(hours=1)


class NightlySweep:
    def __init__(
        self,
        store: Store,
        runner: RippleDriver,
        clock: Clock,
        *,
        stale_after: timedelta = DEFAULT_STALE_AFTER,
    ) -> None:
        self._store = store
        self._runner = runner
        self._clock = clock
        self._stale_after = stale_after

    async def run(self, user_id: str) -> list[ChangeEvent]:
        """Resume what was interrupted first, then retire what has expired."""
        return [*await self.resume_open(user_id), *await self.expire(user_id)]

    async def expire(self, user_id: str) -> list[ChangeEvent]:
        now = self._clock.now()
        events: list[ChangeEvent] = []
        for candidate in await self._store.memories_expiring_at(user_id, now):
            async with self._store.transaction() as tx:
                memory = await tx.get_memory(candidate.id)
                if memory.status is not Status.VALID or not memory.expired_at(now):
                    continue  # an earlier ripple in this sweep already changed it
                await tx.replace_memory(memory.model_copy(update={"status": Status.RETIRED}))
                event = await open_event(tx, memory, TriggerKind.EXPIRY, now)
            events.append(await self._runner.run(event))
        return events

    async def resume_open(self, user_id: str) -> list[ChangeEvent]:
        """The stale open events this sweep resumed; leased ones are skipped and logged."""
        cutoff = self._clock.now() - self._stale_after
        events: list[ChangeEvent] = []
        for event in await self._store.open_change_events(user_id):
            if event.created_at > cutoff:
                continue
            resumed = await self._runner.resume(event)
            if resumed.is_open:
                # resume either completes, raises, or declines because the event is
                # leased by its live driver: never resolve a wave twice.
                log.info(
                    "resume skipped: event leased elsewhere",
                    extra={"event_id": event.id, "user_id": user_id},
                )
                continue
            events.append(resumed)
        return events
