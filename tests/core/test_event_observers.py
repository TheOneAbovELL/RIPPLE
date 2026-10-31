"""EventObserver (ADR-0079): told once per completed event, after the commit, never fatal."""

import asyncio
import logging

from ripple.core.models import ChangeEvent
from ripple.core.ripple import RippleRunner
from tests.core.test_event_lease import FakeEventLease, _cgpa_edit
from tests.fakes.clock import FakeClock
from tests.fakes.engine import ScriptedEngine
from tests.fakes.resolver import ScriptedResolver, keep
from tests.fakes.store import InMemoryStore


class RecordingObserver:
    def __init__(self, store: InMemoryStore) -> None:
        self.store = store
        self.seen: list[ChangeEvent] = []
        self.stored_completed: list[bool] = []

    async def event_completed(self, event: ChangeEvent) -> None:
        self.seen.append(event)
        stored = await self.store.get_change_event(event.id)
        self.stored_completed.append(not stored.is_open)


class FailingObserver:
    async def event_completed(self, event: ChangeEvent) -> None:
        raise ConnectionError("queue is down")


def _with_observers(store, clock, eligibility_id, observers, event_lease=None):
    class Factory(ScriptedEngine):
        def __init__(self, max_depth: int = 8) -> None:
            super().__init__([eligibility_id], max_depth=max_depth)

    return RippleRunner(
        store,
        ScriptedResolver({eligibility_id: keep()}),
        clock,
        engine_factory=Factory,  # type: ignore[arg-type]
        event_lease=event_lease,
        observers=observers,
    )


def test_observer_is_told_once_after_the_completion_is_committed():
    store, clock = InMemoryStore(), FakeClock()
    eligibility, event = _cgpa_edit(store, clock)
    observer = RecordingObserver(store)

    done = asyncio.run(_with_observers(store, clock, eligibility.id, [observer]).run(event))

    assert [e.id for e in observer.seen] == [event.id]
    assert observer.seen[0].completed_at == done.completed_at is not None
    assert observer.stored_completed == [True]


def test_a_failing_observer_is_logged_and_neither_fails_the_run_nor_stops_the_next(caplog):
    store, clock = InMemoryStore(), FakeClock()
    eligibility, event = _cgpa_edit(store, clock)
    after = RecordingObserver(store)

    with caplog.at_level(logging.ERROR, logger="ripple.core.ripple"):
        done = asyncio.run(
            _with_observers(store, clock, eligibility.id, [FailingObserver(), after]).run(event)
        )

    assert not done.is_open
    assert [e.id for e in after.seen] == [event.id]
    assert any(r.getMessage() == "event observer failed" for r in caplog.records)


def test_observer_is_not_told_when_another_holder_leases_the_event():
    store, clock = InMemoryStore(), FakeClock()
    eligibility, event = _cgpa_edit(store, clock)
    lease = FakeEventLease()
    lease.held.add(event.id)
    observer = RecordingObserver(store)

    returned = asyncio.run(
        _with_observers(store, clock, eligibility.id, [observer], event_lease=lease).run(event)
    )

    assert returned.is_open and observer.seen == []
