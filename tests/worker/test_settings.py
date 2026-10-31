"""The arq glue: cron shape and the ctx -> JobContext unpacking. No Redis is touched."""

import asyncio

import pytest
from arq.cron import CronJob

from ripple.core.errors import ConfigurationError
from ripple.worker import settings
from tests.fakes.transport import RecordingTransport
from tests.notify.fakes import FakeRecommendationSource, recommendation
from tests.worker.support import RecordingSweep, context


def _cron_by_name() -> dict[str, CronJob]:
    # arq prefixes cron job names with "cron:"; tests read the function name.
    return {job.name.removeprefix("cron:"): job for job in settings.WorkerSettings.cron_jobs}


def test_worker_settings_register_sweep_digest_alerts_and_scout_slots():
    assert set(_cron_by_name()) == {
        "nightly_sweep_job",
        "daily_digest_job",
        "hourly_alerts_job",
        "scout_run_job",
    }


def test_worker_settings_schedule_is_utc_and_ordered_scout_sweep_digest():
    jobs = _cron_by_name()
    assert (jobs["scout_run_job"].hour, jobs["scout_run_job"].minute) == (1, 0)
    assert (jobs["nightly_sweep_job"].hour, jobs["nightly_sweep_job"].minute) == (21, 0)
    assert (jobs["daily_digest_job"].hour, jobs["daily_digest_job"].minute) == (2, 30)
    assert jobs["hourly_alerts_job"].hour is None
    assert jobs["hourly_alerts_job"].minute == 15


def test_worker_settings_cron_jobs_are_unique_so_two_workers_do_not_double_run():
    # Pins arq's default (unique=True); ADR-0056 relies on it, so a future explicit
    # `unique=False` on any slot must fail here.
    assert all(job.unique for job in settings.WorkerSettings.cron_jobs)


def test_redis_settings_come_from_env_or_are_none():
    assert settings.redis_settings_from_env({}) is None
    configured = settings.redis_settings_from_env({"REDIS_URL": "redis://cache.internal:6380/2"})
    assert configured is not None
    assert (configured.host, configured.port, configured.database) == ("cache.internal", 6380, 2)


def test_job_context_is_read_from_arq_ctx_and_missing_context_is_a_configuration_error():
    ctx = context()
    assert settings.job_context({settings.CONTEXT_KEY: ctx}) is ctx
    with pytest.raises(ConfigurationError):
        settings.job_context({})


def test_arq_wrappers_delegate_to_the_plain_jobs_and_summarise():
    transport = RecordingTransport()
    source = FakeRecommendationSource({"u1": [recommendation(fit_score=0.9, deadline=None)]})
    sweep = RecordingSweep(events=3)
    ctx = {
        settings.CONTEXT_KEY: context(
            users={"u1": "chat-1", "u2": None}, sweep=sweep, source=source, transport=transport
        )
    }

    assert asyncio.run(settings.nightly_sweep_job(ctx)) == {
        "users": 2,
        "events": 6,
        "skipped_leased": 0,
    }
    assert asyncio.run(settings.daily_digest_job(ctx)) == {"sent": 1, "skipped": 1}
    assert asyncio.run(settings.hourly_alerts_job(ctx)) == {"sent": 1, "skipped": 1}
    assert [m.chat_id for m in transport.sent] == ["chat-1", "chat-1"]  # digest, then alert


def test_on_startup_refuses_to_run_without_redis_url(monkeypatch):
    monkeypatch.setattr(settings.WorkerSettings, "redis_settings", None)
    with pytest.raises(ConfigurationError, match="REDIS_URL"):
        asyncio.run(settings.on_startup({}))


def test_on_startup_builds_the_job_context_from_the_environment(monkeypatch):
    monkeypatch.setattr(
        settings.WorkerSettings,
        "redis_settings",
        settings.redis_settings_from_env({"REDIS_URL": "redis://localhost:6379/0"}),
    )
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://ripple:x@localhost:5432/ripple")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("RIPPLE_LLM_CONFIG", "config/llm.default.toml")
    ctx: dict[str, object] = {}
    asyncio.run(settings.on_startup(ctx))
    assert settings.CONTEXT_KEY in ctx


def test_on_startup_refuses_to_run_without_a_database_url(monkeypatch):
    monkeypatch.setattr(
        settings.WorkerSettings,
        "redis_settings",
        settings.redis_settings_from_env({"REDIS_URL": "redis://localhost:6379/0"}),
    )
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ConfigurationError, match="DATABASE_URL"):
        asyncio.run(settings.on_startup({}))
