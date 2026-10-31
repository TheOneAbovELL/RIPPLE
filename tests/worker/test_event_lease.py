"""The worker's adapter of core's EventLease (ADR-0099) and its wiring."""

import asyncio
from datetime import timedelta

from ripple.core.models import Status
from ripple.core.ripple import RippleRunner
from ripple.core.sweep import NightlySweep
from ripple.worker import settings
from ripple.worker.jobs import nightly_sweep
from ripple.worker.lease import (
    EVENT_LEASE_TTL,
    ChangeEventLease,
    InMemoryLease,
    event_lease_key,
    sweep_lease_key,
)
from ripple.worker.wiring import job_context_from_env
from tests.fakes.clock import FakeClock
from tests.fakes.engine import ScriptedEngine
from tests.fakes.resolver import ScriptedResolver
from tests.fakes.store import InMemoryStore
from tests.worker.support import context, user_with_expiry_and_stranded_ripple
from tests.worker.test_wiring import ENV


def test_change_event_lease_excludes_a_second_holder_of_the_same_event():
    backend = InMemoryLease(FakeClock())
    api, worker = ChangeEventLease(backend), ChangeEventLease(backend)
    assert asyncio.run(api.acquire("evt-1")) is True
    assert asyncio.run(worker.acquire("evt-1")) is False
    assert asyncio.run(worker.acquire("evt-2")) is True  # one key per event


def test_change_event_lease_is_free_again_after_release():
    backend = InMemoryLease(FakeClock())
    lease = ChangeEventLease(backend)
    asyncio.run(lease.acquire("evt-1"))
    asyncio.run(lease.release("evt-1"))
    assert backend.holds(event_lease_key("evt-1")) is False
    assert asyncio.run(lease.acquire("evt-1")) is True


def test_change_event_lease_expires_after_its_ttl_so_a_crashed_holder_frees_the_event():
    clock = FakeClock()
    lease = ChangeEventLease(InMemoryLease(clock), ttl=timedelta(minutes=10))
    asyncio.run(lease.acquire("evt-1"))
    clock.advance(timedelta(minutes=9))
    assert asyncio.run(lease.acquire("evt-1")) is False
    clock.advance(timedelta(minutes=1))
    assert asyncio.run(lease.acquire("evt-1")) is True


def test_change_event_lease_keys_never_collide_with_sweep_keys():
    backend = InMemoryLease(FakeClock())
    assert asyncio.run(backend.acquire(sweep_lease_key("u1"), timedelta(hours=1)))
    assert asyncio.run(ChangeEventLease(backend).acquire("u1")) is True
    assert event_lease_key("u1") != sweep_lease_key("u1")


def test_event_lease_ttl_outlives_every_cron_timeout_that_drives_ripples():
    # A ripple driven by the sweep or the Scout is killed at its cron timeout at the
    # latest; the event lease must still be held until then.
    for name in ("cron:nightly_sweep_job", "cron:scout_run_job"):
        job = next(j for j in settings.CRON_JOBS if j.name == name)
        assert job.timeout_s is not None
        assert timedelta(seconds=job.timeout_s) < EVENT_LEASE_TTL


def test_job_context_runner_holds_an_event_lease_on_the_shared_backend():
    shared = InMemoryLease(FakeClock())
    ctx = job_context_from_env(ENV, lease=shared)
    event_lease = ctx.runner._event_lease  # wiring is the thing under test
    assert isinstance(event_lease, ChangeEventLease)
    assert event_lease._lease is shared


def test_nightly_sweep_job_skips_an_event_whose_lease_is_held_and_finishes_the_rest():
    clock, store = FakeClock(), InMemoryStore()
    _, eligibility, stranded = user_with_expiry_and_stranded_ripple(store, clock, "u1")
    leases = InMemoryLease(clock)
    resolver = ScriptedResolver({})
    # No scripted waves: the expiry ripple has no dependents, and a resume takes its
    # outstanding wave from the event, not the engine.
    runner = RippleRunner(
        store,
        resolver,
        clock,
        engine_factory=ScriptedEngine,  # type: ignore[arg-type]
        event_lease=ChangeEventLease(leases),  # as the wiring does
    )
    assert asyncio.run(leases.acquire(event_lease_key(stranded.id), EVENT_LEASE_TTL))
    ctx = context(
        clock=clock,
        store=store,
        users={"u1": "chat-1"},
        runner=runner,
        sweep=NightlySweep(store, runner, clock),
        leases=leases,
    )

    report = asyncio.run(nightly_sweep(ctx))

    assert report.events_by_user == {"u1": 1}  # the expiry ripple only
    assert asyncio.run(store.get_change_event(stranded.id)).is_open
    assert asyncio.run(store.get_memory(eligibility.id)).status is Status.SUSPECT
    assert resolver.contexts == []
