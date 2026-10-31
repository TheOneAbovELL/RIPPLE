"""Per-ChangeEvent lease (ADR-0099): one driver per open event, across processes.

The lease here is a fake shared by two runners, standing in for the Redis lease the
API process and the worker would share in production.
"""

import asyncio
import logging
from datetime import timedelta

import pytest

from ripple.core.models import ChangeEvent, Status, TriggerKind
from ripple.core.resolver import Resolution, ResolutionContext
from ripple.core.ripple import RippleRunner
from ripple.core.sweep import NightlySweep
from ripple.core.writes import update_memory
from tests.builders import USER, derived, fact, link
from tests.fakes.clock import FakeClock
from tests.fakes.engine import ScriptedEngine
from tests.fakes.resolver import ExplodingResolver, ScriptedResolver, keep
from tests.fakes.store import InMemoryStore


class FakeEventLease:
    """Process-wide lease table; records every call so release can be asserted."""

    def __init__(self) -> None:
        self.held: set[str] = set()
        self.calls: list[tuple[str, str]] = []

    async def acquire(self, event_id: str) -> bool:
        self.calls.append(("acquire", event_id))
        if event_id in self.held:
            return False
        self.held.add(event_id)
        return True

    async def release(self, event_id: str) -> None:
        self.calls.append(("release", event_id))
        self.held.discard(event_id)


class GatedResolver:
    """Blocks inside resolve until released: a slow LLM call mid-ripple."""

    def __init__(self) -> None:
        self.entered = asyncio.Event()
        self.proceed = asyncio.Event()
        self.calls = 0

    async def resolve(self, context: ResolutionContext) -> Resolution:
        self.calls += 1
        self.entered.set()
        await self.proceed.wait()
        return keep()


def _runner(store, resolver, clock, *waves, event_lease=None) -> RippleRunner:
    class Factory(ScriptedEngine):
        def __init__(self, max_depth: int = 8) -> None:
            super().__init__(*waves, max_depth=max_depth)

    return RippleRunner(
        store,
        resolver,
        clock,
        engine_factory=Factory,  # type: ignore[arg-type]
        event_lease=event_lease,
    )


def _cgpa_edit(store: InMemoryStore, clock: FakeClock):
    """cgpa -> eligibility, then an edit of the cgpa: an open event with one dependent."""
    cgpa = fact("student", "cgpa", 7.6)
    eligibility = derived("not eligible")

    async def write():
        async with store.transaction() as tx:
            await tx.add_memory(cgpa)
            await tx.add_memory(eligibility)
            await tx.add_link(link(cgpa, eligibility))

    asyncio.run(write())
    _, event = asyncio.run(
        update_memory(
            store,
            clock,
            cgpa.id,
            content="CGPA is 7.9",
            structured=None,
            valid_to=None,
            created_by="user",
            kind=TriggerKind.USER_EDIT,
        )
    )
    return eligibility, event


def _stranded(store: InMemoryStore, clock: FakeClock):
    """The edit's ripple crashed after marking its wave: open event, SUSPECT member."""
    eligibility, event = _cgpa_edit(store, clock)
    exploding = ExplodingResolver(ScriptedResolver({}), explode_on_call=1)
    with pytest.raises(ConnectionError):
        asyncio.run(_runner(store, exploding, clock, [eligibility.id]).run(event))
    stored = asyncio.run(store.get_change_event(event.id))
    assert stored.is_open and asyncio.run(store.get_memory(eligibility.id)).status is Status.SUSPECT
    return eligibility, stored


# ---- run ------------------------------------------------------------------------------


def test_run_holds_the_lease_for_the_whole_ripple_and_releases_it():
    store, clock, lease = InMemoryStore(), FakeClock(), FakeEventLease()
    eligibility, event = _cgpa_edit(store, clock)
    done = asyncio.run(
        _runner(store, ScriptedResolver({}), clock, [eligibility.id], event_lease=lease).run(event)
    )
    assert done.completed_at is not None
    assert lease.calls == [("acquire", event.id), ("release", event.id)]
    assert lease.held == set()


def test_run_leaves_the_event_open_and_untouched_when_another_holder_has_the_lease():
    store, clock, lease = InMemoryStore(), FakeClock(), FakeEventLease()
    eligibility, event = _cgpa_edit(store, clock)
    lease.held.add(event.id)  # another process drives it
    resolver = ScriptedResolver({})

    returned = asyncio.run(
        _runner(store, resolver, clock, [eligibility.id], event_lease=lease).run(event)
    )

    assert returned.is_open
    assert resolver.contexts == []
    assert asyncio.run(store.get_memory(eligibility.id)).status is Status.VALID
    assert asyncio.run(store.get_change_event(event.id)).affected_ids == []
    assert ("release", event.id) not in lease.calls  # never ours to free


def test_run_releases_the_lease_when_the_resolver_raises():
    store, clock, lease = InMemoryStore(), FakeClock(), FakeEventLease()
    eligibility, event = _cgpa_edit(store, clock)
    exploding = ExplodingResolver(ScriptedResolver({}), explode_on_call=1)
    with pytest.raises(ConnectionError):
        asyncio.run(
            _runner(store, exploding, clock, [eligibility.id], event_lease=lease).run(event)
        )
    assert lease.held == set()  # a crash inside the process frees it for the sweep


# ---- resume ---------------------------------------------------------------------------


def test_resume_returns_the_event_open_and_resolves_nothing_when_another_holder_has_the_lease():
    store, clock, lease = InMemoryStore(), FakeClock(), FakeEventLease()
    eligibility, stranded = _stranded(store, clock)
    lease.held.add(stranded.id)
    resolver = ScriptedResolver({})

    returned = asyncio.run(_runner(store, resolver, clock, event_lease=lease).resume(stranded))

    assert returned.is_open and returned.decisions == stranded.decisions
    assert resolver.contexts == []
    assert asyncio.run(store.get_memory(eligibility.id)).status is Status.SUSPECT
    assert asyncio.run(store.get_change_event(stranded.id)) == stranded


def test_resume_with_the_lease_finishes_the_stranded_wave_and_releases():
    store, clock, lease = InMemoryStore(), FakeClock(), FakeEventLease()
    eligibility, stranded = _stranded(store, clock)
    resolver = ScriptedResolver({})

    done = asyncio.run(_runner(store, resolver, clock, event_lease=lease).resume(stranded))

    assert done.completed_at is not None
    assert [c.memory.id for c in resolver.contexts] == [eligibility.id]
    assert lease.held == set()


def test_resume_reads_the_stored_event_so_a_stale_snapshot_is_not_driven_twice():
    """The sweep listed the event, then its owner finished it before the sweep acquired."""
    store, clock, lease = InMemoryStore(), FakeClock(), FakeEventLease()
    _, snapshot = _stranded(store, clock)
    first = asyncio.run(
        _runner(store, ScriptedResolver({}), clock, event_lease=lease).resume(snapshot)
    )
    late = ScriptedResolver({})

    returned = asyncio.run(_runner(store, late, clock, event_lease=lease).resume(snapshot))

    assert late.contexts == []
    assert returned == first
    # Driving the snapshot would have completed it with its empty decision list,
    # erasing the first holder's decisions (I2).
    assert asyncio.run(store.get_change_event(snapshot.id)) == first
    assert len(first.decisions) == 1


def test_run_returns_the_stored_event_when_another_holder_already_completed_it():
    store, clock, lease = InMemoryStore(), FakeClock(), FakeEventLease()
    eligibility, snapshot = _cgpa_edit(store, clock)
    first = asyncio.run(
        _runner(store, ScriptedResolver({}), clock, [eligibility.id], event_lease=lease).run(
            snapshot
        )
    )
    late = ScriptedResolver({})

    returned = asyncio.run(
        _runner(store, late, clock, [eligibility.id], event_lease=lease).run(snapshot)
    )

    assert late.contexts == []
    assert returned == first == asyncio.run(store.get_change_event(snapshot.id))


class CountingStore(InMemoryStore):
    def __init__(self) -> None:
        super().__init__()
        self.event_reads = 0

    async def get_change_event(self, event_id: str) -> ChangeEvent:
        self.event_reads += 1
        return await super().get_change_event(event_id)


def test_runner_without_a_lease_drives_the_callers_event_without_rereading_it():
    store, clock = CountingStore(), FakeClock()
    eligibility, event = _cgpa_edit(store, clock)
    done = asyncio.run(_runner(store, ScriptedResolver({}), clock, [eligibility.id]).run(event))
    assert done.completed_at is not None
    assert store.event_reads == 0


def test_a_sweep_cannot_resume_an_event_a_live_ripple_is_still_resolving():
    """The double-resolution in DEVLOG/ADR-0056: a slow LLM outlives stale_after."""
    store, clock, lease = InMemoryStore(), FakeClock(), FakeEventLease()
    eligibility, event = _cgpa_edit(store, clock)
    slow = GatedResolver()
    sweeper = ScriptedResolver({})
    live = _runner(store, slow, clock, [eligibility.id], event_lease=lease)
    sweep = NightlySweep(
        store,
        _runner(store, sweeper, clock, event_lease=lease),
        clock,
        stale_after=timedelta(hours=1),
    )

    async def race() -> tuple[ChangeEvent, list[ChangeEvent]]:
        api = asyncio.create_task(live.run(event))
        await slow.entered.wait()  # wave 1 is marked and the LLM call is in flight
        clock.advance(timedelta(hours=2))  # long past stale_after
        swept = await sweep.resume_open(USER)
        slow.proceed.set()
        return await api, swept

    finished, swept = asyncio.run(race())

    assert swept == []  # skipped, not resumed
    assert sweeper.contexts == [] and slow.calls == 1
    assert finished.completed_at is not None
    assert [d.memory_id for d in finished.decisions] == [eligibility.id]


# ---- sweep ----------------------------------------------------------------------------


def test_sweep_reports_a_leased_event_as_skipped_and_resumes_it_once_free(caplog):
    store, clock, lease = InMemoryStore(), FakeClock(), FakeEventLease()
    eligibility, stranded = _stranded(store, clock)
    clock.advance(timedelta(hours=2))
    sweep = NightlySweep(
        store, _runner(store, ScriptedResolver({}), clock, event_lease=lease), clock
    )
    lease.held.add(stranded.id)

    with caplog.at_level(logging.INFO, logger="ripple.core.sweep"):
        assert asyncio.run(sweep.resume_open(USER)) == []
    skipped = [
        r for r in caplog.records if r.getMessage() == "resume skipped: event leased elsewhere"
    ]
    assert [getattr(r, "event_id", None) for r in skipped] == [stranded.id]
    assert asyncio.run(store.get_memory(eligibility.id)).status is Status.SUSPECT

    lease.held.discard(stranded.id)  # the other holder finished or its ttl passed
    resumed = asyncio.run(sweep.resume_open(USER))
    assert [e.id for e in resumed] == [stranded.id] and resumed[0].completed_at is not None
    assert asyncio.run(store.get_memory(eligibility.id)).status is Status.VALID


def test_run_continues_from_the_store_when_a_crashed_holder_progressed_the_event():
    """A retried run with the original snapshot must not resolve a finished wave again."""
    store, clock, lease = InMemoryStore(), FakeClock(), FakeEventLease()
    eligibility, snapshot = _cgpa_edit(store, clock)
    recommendation = derived("skip Acme")

    async def extend():
        async with store.transaction() as tx:
            await tx.add_memory(recommendation)
            await tx.add_link(link(eligibility, recommendation))

    asyncio.run(extend())
    waves = ([eligibility.id], [recommendation.id])
    crashing = ExplodingResolver(ScriptedResolver({}), explode_on_call=2)  # dies in wave 2
    with pytest.raises(ConnectionError):
        asyncio.run(_runner(store, crashing, clock, *waves, event_lease=lease).run(snapshot))
    retry = ScriptedResolver({})

    done = asyncio.run(_runner(store, retry, clock, *waves, event_lease=lease).run(snapshot))

    assert [c.memory.id for c in retry.contexts] == [recommendation.id]
    assert [d.memory_id for d in done.decisions] == [eligibility.id, recommendation.id]
