"""scout_user_job (ADR-0079) and the worker wiring that feeds it."""

import asyncio
from datetime import timedelta

from ripple.agents.scout import CriteriaChangeObserver
from ripple.domains.jobs.sources.report import SCOUT_LEASE_TTL, ScoutReport, scout_lease_key
from ripple.notify.delivery_log import PostgresDeliveryLog
from ripple.worker import settings
from ripple.worker.jobs import scout_user
from ripple.worker.lease import InMemoryLease
from ripple.worker.wiring import build_job_context, job_context_from_env
from tests.fakes.clock import FakeClock
from tests.worker.support import context
from tests.worker.test_wiring import ENV


class RecordingScout:
    def __init__(self, clock: FakeClock) -> None:
        self.clock = clock
        self.users: list[str] = []
        self.caches: list[object] = []

    async def run_for_user(self, user_id: str, *, cache: object = None) -> ScoutReport:
        self.users.append(user_id)
        self.caches.append(cache)
        return ScoutReport(user_id=user_id, started_at=self.clock.now())


def test_scout_user_runs_the_scout_for_that_user_only():
    clock = FakeClock()
    scout = RecordingScout(clock)
    report = asyncio.run(
        scout_user(context(clock=clock, users={"u1": "c1", "u2": "c2"}), "u2", scout=scout)  # type: ignore[arg-type]
    )
    assert scout.users == ["u2"] and list(report.by_user) == ["u2"]


def test_scout_user_skips_while_the_daily_run_holds_that_users_lease():
    clock = FakeClock()
    leases = InMemoryLease(clock)
    asyncio.run(leases.acquire(scout_lease_key("u1"), SCOUT_LEASE_TTL))
    scout = RecordingScout(clock)

    report = asyncio.run(scout_user(context(clock=clock, leases=leases), "u1", scout=scout))  # type: ignore[arg-type]

    assert scout.users == [] and report.skipped_leased == ["u1"]
    clock.advance(SCOUT_LEASE_TTL + timedelta(seconds=1))
    asyncio.run(scout_user(context(clock=clock, leases=leases), "u1", scout=scout))  # type: ignore[arg-type]
    assert scout.users == ["u1"]


def test_scout_user_skips_a_user_deleted_after_the_enqueue():
    clock = FakeClock()
    scout = RecordingScout(clock)
    report = asyncio.run(
        scout_user(context(clock=clock, users={"u1": "c1"}), "gone", scout=scout)  # type: ignore[arg-type]
    )
    assert scout.users == [] and report.by_user == {}


def test_scout_run_shares_one_parse_cache_across_the_users_of_a_run():
    from ripple.worker.jobs import scout_run

    clock = FakeClock()
    scout = RecordingScout(clock)
    asyncio.run(scout_run(context(clock=clock), scout=scout))  # type: ignore[arg-type]
    first, second = scout.caches
    assert first is not None and first is second


def test_scout_user_job_is_registered_with_arq_with_the_cron_slots_timeout():
    (registered,) = [
        f for f in settings.WorkerSettings.functions if getattr(f, "name", "") == "scout_user_job"
    ]
    assert registered.timeout_s == settings.SCOUT_USER_TIMEOUT.total_seconds()
    assert settings.SCOUT_USER_TIMEOUT <= SCOUT_LEASE_TTL


def test_enqueue_scout_user_merges_a_burst_into_one_job_per_user():
    from ripple.worker.wiring import SCOUT_USER_DEFER, enqueue_scout_user

    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    class Redis:
        async def enqueue_job(self, *args: object, **kwargs: object) -> None:
            calls.append((args, kwargs))

    asyncio.run(enqueue_scout_user(Redis(), "u1"))  # type: ignore[arg-type]
    assert calls == [
        (("scout_user_job", "u1"), {"_job_id": "scout_user:u1", "_defer_by": SCOUT_USER_DEFER})
    ]


def test_worker_digest_uses_the_postgres_delivery_log():
    context_ = job_context_from_env(ENV)
    assert isinstance(context_.digest._log, PostgresDeliveryLog)


def test_worker_runner_gets_the_criteria_observer_only_with_a_queue():
    from ripple.domains.jobs.derive import ProfileDerivationObserver

    plain = job_context_from_env(ENV)
    assert [type(o) for o in plain.runner._observers] == [ProfileDerivationObserver]

    async def enqueue(user_id: str) -> None:
        pass

    queued = job_context_from_env(ENV, enqueue_scout=enqueue)
    assert [type(o) for o in queued.runner._observers] == [
        ProfileDerivationObserver,
        CriteriaChangeObserver,
    ]


class FakeArqRedis:
    def __init__(self) -> None:
        self.jobs: list[tuple[str, tuple[object, ...]]] = []

    async def enqueue_job(self, name: str, *args: object, **kwargs: object) -> None:
        self.jobs.append((name, args))

    async def set(self, *args: object, **kwargs: object) -> bool:
        return True


def test_build_job_context_enqueues_scout_user_job_on_arqs_connection(monkeypatch):
    for key, value in ENV.items():
        monkeypatch.setenv(key, value)
    redis = FakeArqRedis()
    built = asyncio.run(build_job_context({"redis": redis}))
    (_derivation, observer) = built.runner._observers
    assert isinstance(observer, CriteriaChangeObserver)

    asyncio.run(observer._trigger.on_criteria_changed("u7"))

    assert redis.jobs == [("scout_user_job", ("u7",))]


def test_lazy_redis_lease_opens_the_pool_on_first_acquire_and_releases_without_one():
    from ripple.worker.lease import LazyRedisLease

    opened: list[FakeArqRedis] = []

    async def factory() -> FakeArqRedis:
        opened.append(FakeArqRedis())
        return opened[-1]

    lease = LazyRedisLease(factory)  # type: ignore[arg-type]
    asyncio.run(lease.release("never-acquired"))  # no pool, nothing to free
    assert opened == []
    assert asyncio.run(lease.acquire("k", timedelta(seconds=5))) is True
    assert asyncio.run(lease.acquire("k2", timedelta(seconds=5))) is True
    assert len(opened) == 1


def test_event_lease_release_failure_is_logged_not_raised(caplog):
    import logging

    from ripple.worker.lease import ChangeEventLease

    class BrokenLease:
        async def acquire(self, key: str, ttl: timedelta) -> bool:
            return True

        async def release(self, key: str) -> None:
            raise ConnectionError("redis went away")

    lease = ChangeEventLease(BrokenLease())
    with caplog.at_level(logging.ERROR, logger="ripple.worker.lease"):
        asyncio.run(lease.release("e1"))
    assert any(r.getMessage() == "event lease release failed" for r in caplog.records)
