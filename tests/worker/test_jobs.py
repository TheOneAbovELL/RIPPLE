import asyncio
from datetime import timedelta
from pathlib import Path

import pytest

from ripple.core.models import Status, TriggerKind
from ripple.core.sweep import NightlySweep
from ripple.notify.errors import TelegramSendError
from ripple.worker import settings
from ripple.worker.jobs import (
    SWEEP_LEASE_TTL,
    JobFailedForUsersError,
    daily_digest,
    hourly_alerts,
    nightly_sweep,
    scout_run,
)
from ripple.worker.lease import InMemoryLease, sweep_lease_key
from tests.fakes.clock import FakeClock
from tests.fakes.resolver import ScriptedResolver, keep
from tests.fakes.store import InMemoryStore
from tests.fakes.transport import RecordingTransport
from tests.notify.fakes import FakeRecommendationSource, recommendation
from tests.worker.support import (
    RecordingSweep,
    context,
    scripted_runner,
    user_with_expiry_and_stranded_ripple,
)

# ---- nightly sweep -------------------------------------------------------------------


def test_nightly_sweep_runs_expiry_and_resume_for_each_active_user():
    store, clock = InMemoryStore(), FakeClock()
    temp_a, elig_a, event_a = user_with_expiry_and_stranded_ripple(store, clock, "u1")
    temp_b, elig_b, event_b = user_with_expiry_and_stranded_ripple(store, clock, "u2")
    runner = scripted_runner(store, ScriptedResolver({}, default=keep()), clock)
    ctx = context(store=store, clock=clock, runner=runner, sweep=NightlySweep(store, runner, clock))

    report = asyncio.run(nightly_sweep(ctx))

    assert report.events_by_user == {"u1": 2, "u2": 2}  # one resumed, one expiry each
    for temporary, eligibility, event in ((temp_a, elig_a, event_a), (temp_b, elig_b, event_b)):
        assert asyncio.run(store.get_memory(temporary.id)).status is Status.RETIRED
        assert asyncio.run(store.get_memory(eligibility.id)).status is Status.VALID
        assert asyncio.run(store.get_change_event(event.id)).completed_at is not None
    for user_id in ("u1", "u2"):
        assert asyncio.run(store.open_change_events(user_id)) == []  # nothing left open
    assert {e.trigger_kind for e in _all_events(store)} == {
        TriggerKind.USER_EDIT,
        TriggerKind.EXPIRY,
    }


def _all_events(store: InMemoryStore):
    return [
        e for user_id in ("u1", "u2") for e in asyncio.run(store.change_events_for_user(user_id))
    ]


def test_nightly_sweep_skips_a_user_whose_lease_is_held_and_sweeps_the_rest():
    clock = FakeClock()
    leases = InMemoryLease(clock)
    assert asyncio.run(leases.acquire(sweep_lease_key("u1"), timedelta(hours=1)))
    sweep = RecordingSweep()
    ctx = context(clock=clock, sweep=sweep, leases=leases)

    report = asyncio.run(nightly_sweep(ctx))

    assert sweep.runs == ["u2"]
    assert report.skipped_leased == ["u1"]
    assert report.events_by_user == {"u2": 1}


def test_nightly_sweep_releases_the_lease_after_the_run():
    clock = FakeClock()
    leases = InMemoryLease(clock)
    ctx = context(clock=clock, sweep=RecordingSweep(), leases=leases)
    asyncio.run(nightly_sweep(ctx))
    assert not leases.holds(sweep_lease_key("u1"))
    assert not leases.holds(sweep_lease_key("u2"))


def test_nightly_sweep_releases_the_lease_when_a_user_fails_and_raises_at_the_end():
    clock = FakeClock()
    leases = InMemoryLease(clock)
    sweep = RecordingSweep(fail_for={"u1"})
    ctx = context(clock=clock, sweep=sweep, leases=leases)

    with pytest.raises(JobFailedForUsersError) as info:
        asyncio.run(nightly_sweep(ctx))

    assert info.value.failed_user_ids == ["u1"]
    assert sweep.runs == ["u1", "u2"]  # the other user still ran
    assert not leases.holds(sweep_lease_key("u1"))
    cause = info.value.__cause__
    assert isinstance(cause, ExceptionGroup)
    assert [type(e) for e in cause.exceptions] == [ConnectionError]


def test_nightly_sweep_isolates_a_lease_backend_failure_too():
    class BrokenLease(InMemoryLease):
        async def acquire(self, key: str, ttl: timedelta) -> bool:
            if key == sweep_lease_key("u1"):
                raise OSError("redis unreachable")
            return await super().acquire(key, ttl)

    sweep = RecordingSweep()
    ctx = context(sweep=sweep, leases=BrokenLease(FakeClock()))
    with pytest.raises(JobFailedForUsersError) as info:
        asyncio.run(nightly_sweep(ctx))
    assert info.value.failed_user_ids == ["u1"]
    assert sweep.runs == ["u2"]


def test_nightly_sweep_lease_ttl_outlives_the_cron_timeout():
    # arq kills the job at its cron timeout; the lease must still be held until then,
    # or a second worker could start the same user's sweep before the first is dead.
    sweep_cron = next(j for j in settings.CRON_JOBS if j.name == "cron:nightly_sweep_job")
    assert sweep_cron.timeout_s is not None
    assert timedelta(seconds=sweep_cron.timeout_s) < SWEEP_LEASE_TTL


# ---- daily digest --------------------------------------------------------------------


def test_daily_digest_sends_to_every_active_user_with_a_chat_and_reports_skips():
    transport = RecordingTransport()
    source = FakeRecommendationSource({"u1": [recommendation()], "u2": [recommendation()]})
    ctx = context(users={"u1": "chat-1", "u2": None}, source=source, transport=transport)

    report = asyncio.run(daily_digest(ctx))

    assert report.sent == ["u1"]
    assert report.skipped == ["u2"]
    assert [m.chat_id for m in transport.sent] == ["chat-1"]


def test_daily_digest_rerun_the_same_day_sends_nothing():
    transport = RecordingTransport()
    source = FakeRecommendationSource({"u1": [recommendation()], "u2": [recommendation()]})
    ctx = context(source=source, transport=transport)
    asyncio.run(daily_digest(ctx))
    report = asyncio.run(daily_digest(ctx))
    assert report.sent == [] and report.skipped == ["u1", "u2"]
    assert len(transport.sent) == 2


def test_daily_digest_isolates_one_users_failure_and_raises_at_the_end():
    class FlakyTransport(RecordingTransport):
        async def send(self, chat_id: str, text: str):
            if chat_id == "chat-1":
                raise TelegramSendError(400, "Bad Request: chat not found", error_code=400)
            return await super().send(chat_id, text)

    transport = FlakyTransport()
    source = FakeRecommendationSource({"u1": [recommendation()], "u2": [recommendation()]})
    ctx = context(source=source, transport=transport)
    with pytest.raises(JobFailedForUsersError) as info:
        asyncio.run(daily_digest(ctx))
    assert info.value.failed_user_ids == ["u1"]
    assert [m.chat_id for m in transport.sent] == ["chat-2"]


# ---- hourly alerts -------------------------------------------------------------------


def test_hourly_alerts_sends_for_qualifying_users_only():
    clock = FakeClock()
    transport = RecordingTransport()
    source = FakeRecommendationSource(
        {
            "u1": [recommendation(fit_score=0.9, deadline=None)],
            "u2": [recommendation(fit_score=0.1, deadline=None)],
        }
    )
    ctx = context(clock=clock, source=source, transport=transport)
    report = asyncio.run(hourly_alerts(ctx))
    assert report.sent == ["u1"] and report.skipped == ["u2"]


def test_hourly_alerts_rerun_within_the_cooldown_sends_nothing():
    clock = FakeClock()
    transport = RecordingTransport()
    source = FakeRecommendationSource({"u1": [recommendation(fit_score=0.9, deadline=None)]})
    ctx = context(clock=clock, users={"u1": "chat-1"}, source=source, transport=transport)
    asyncio.run(hourly_alerts(ctx))
    clock.advance(timedelta(hours=1))
    report = asyncio.run(hourly_alerts(ctx))
    assert report.sent == []
    assert len(transport.sent) == 1


def test_hourly_alerts_cooldown_passes_since_as_now_minus_cooldown():
    clock = FakeClock()
    transport = RecordingTransport()
    source = FakeRecommendationSource({"u1": [recommendation(fit_score=0.9, deadline=None)]})
    ctx = context(clock=clock, users={"u1": "chat-1"}, source=source, transport=transport)
    asyncio.run(hourly_alerts(ctx, cooldown=timedelta(hours=2)))
    clock.advance(timedelta(hours=3))
    report = asyncio.run(hourly_alerts(ctx, cooldown=timedelta(hours=2)))
    assert report.sent == ["u1"]
    assert len(transport.sent) == 2


# ---- scout ---------------------------------------------------------------------------


def test_scout_run_with_the_default_registry_fetches_nothing(monkeypatch):
    # config/sources.yaml ships with every fetchable source disabled (ADR-0070), so the
    # cron body runs end to end without touching the network.
    repo = Path(__file__).resolve().parents[2]
    monkeypatch.setenv("RIPPLE_SOURCES_CONFIG", str(repo / "config" / "sources.yaml"))
    monkeypatch.setenv("RIPPLE_LLM_CONFIG", str(repo / "config" / "llm.default.toml"))
    report = asyncio.run(scout_run(context(users={"u1": "c1"})))
    assert report.by_user["u1"].per_source == {}
    assert report.failed == [] and report.skipped_leased == []
