"""arq WorkerSettings (ADR-0017): the only file that knows about Redis and cron.

Schedule (UTC; the pilot's users are in IST, UTC+5:30):
- scout_run      01:00  every active user (ADR-0072); scout_user_job is enqueued per
                       user when a ripple changes their criteria (ADR-0079)
- nightly_sweep  21:00  (02:30 IST) expiry and resume of open ripples
- daily_digest   02:30  (08:00 IST) after the Scout and the sweep have run
- hourly_alerts  every hour at :15
The arq wrappers below only unpack the JobContext from arq's ctx; the jobs themselves
are in jobs.py and are tested directly. arq opens its Redis connection before calling
on_startup, so an unset REDIS_URL is caught only after one connection attempt against
arq's localhost default; no job runs before the check.
"""

import os
from collections.abc import Mapping
from datetime import timedelta
from typing import Any, ClassVar

from arq import cron, func
from arq.connections import RedisSettings

from ripple.core.errors import ConfigurationError
from ripple.worker import jobs
from ripple.worker.context import JobContext
from ripple.worker.wiring import build_job_context

ENV_REDIS_URL = "REDIS_URL"
CONTEXT_KEY = "job_context"


def redis_settings_from_env(env: Mapping[str, str] | None = None) -> RedisSettings | None:
    """RedisSettings from REDIS_URL, or None when it is unset (checked again at startup)."""
    url = (env if env is not None else os.environ).get(ENV_REDIS_URL)
    return RedisSettings.from_dsn(url) if url else None


def job_context(ctx: Mapping[str, Any]) -> JobContext:
    context = ctx.get(CONTEXT_KEY)
    if not isinstance(context, JobContext):
        raise ConfigurationError("worker started without a JobContext; on_startup did not run")
    return context


async def on_startup(ctx: dict[str, Any]) -> None:
    if WorkerSettings.redis_settings is None:
        raise ConfigurationError(f"{ENV_REDIS_URL} is not set; refusing to start on defaults")
    ctx[CONTEXT_KEY] = await build_job_context(ctx)


async def on_shutdown(ctx: dict[str, Any]) -> None:
    from ripple.worker.wiring import shutdown_tracer

    shutdown_tracer()
    ctx.pop(CONTEXT_KEY, None)


async def nightly_sweep_job(ctx: dict[str, Any]) -> dict[str, int]:
    report = await jobs.nightly_sweep(job_context(ctx))
    return {
        "users": len(report.events_by_user),
        "events": sum(report.events_by_user.values()),
        "skipped_leased": len(report.skipped_leased),
    }


async def daily_digest_job(ctx: dict[str, Any]) -> dict[str, int]:
    report = await jobs.daily_digest(job_context(ctx))
    return {"sent": len(report.sent), "skipped": len(report.skipped)}


async def hourly_alerts_job(ctx: dict[str, Any]) -> dict[str, int]:
    report = await jobs.hourly_alerts(job_context(ctx))
    return {"sent": len(report.sent), "skipped": len(report.skipped)}


async def scout_run_job(ctx: dict[str, Any]) -> dict[str, int]:
    report = await jobs.scout_run(job_context(ctx))
    return {
        "users": len(report.by_user),
        "new": sum(user.new for user in report.by_user.values()),
        "skipped_leased": len(report.skipped_leased),
    }


SCOUT_USER_TIMEOUT = timedelta(minutes=30)


async def scout_user_job(ctx: dict[str, Any], user_id: str) -> dict[str, int]:
    """Enqueued by EnqueueingScoutTrigger when a ripple changed the criteria (ADR-0079)."""
    report = await jobs.scout_user(job_context(ctx), user_id)
    return {
        "new": sum(user.new for user in report.by_user.values()),
        "skipped_leased": len(report.skipped_leased),
    }


CRON_JOBS = [
    cron(scout_run_job, hour=1, minute=0, timeout=timedelta(minutes=30)),
    cron(nightly_sweep_job, hour=21, minute=0, timeout=timedelta(hours=1)),
    cron(daily_digest_job, hour=2, minute=30, timeout=timedelta(minutes=10)),
    cron(hourly_alerts_job, minute=15, timeout=timedelta(minutes=10)),
]


class WorkerSettings:
    """What `arq ripple.worker.settings.WorkerSettings` reads."""

    # arq registers the cron jobs itself; listing the same functions here also lets an
    # operator enqueue one by hand (`enqueue_job("daily_digest_job")`) outside the schedule.
    functions: ClassVar = [
        nightly_sweep_job,
        daily_digest_job,
        hourly_alerts_job,
        scout_run_job,
        # A full scout of one user can outlast arq's 5-minute default; same bound as the
        # cron slot so a cancelled job never strands a ripple (ADR-0079).
        func(scout_user_job, timeout=SCOUT_USER_TIMEOUT),
    ]
    cron_jobs: ClassVar = CRON_JOBS
    on_startup = on_startup
    on_shutdown = on_shutdown
    max_jobs = 4
    # None when REDIS_URL is unset: arq would then fall back to localhost, so on_startup
    # refuses to run instead (secrets and addresses come from the environment only).
    redis_settings = redis_settings_from_env()
