"""The scheduled jobs as plain async functions (ADR-0017, ADR-0056).

Each job loops over the active users, isolates one user's failure from the others,
and raises at the end if any user failed so the scheduler records a failed run. A
retried run is safe: expiry is idempotent, resume only touches still-open events, the
digest and alerts are deduplicated by the DeliveryLog, and the per-user lease keeps two
sweeps of one user apart.
"""

import logging
import os
from collections.abc import Sequence
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from datetime import timedelta

from ripple.agents.scout import (
    SCOUT_LEASE_TTL,
    ScoutAgent,
    ScoutRunCache,
    ScoutRunReport,
    open_scout,
    scout_lease_key,
)
from ripple.core.errors import RippleError
from ripple.domains.jobs.sources.registry import registry_from_env
from ripple.worker.context import JobContext
from ripple.worker.lease import leased, sweep_lease_key
from ripple.worker.wiring import router_from_env

log = logging.getLogger("ripple.worker.jobs")

SWEEP_LEASE_TTL = timedelta(hours=2)  # longer than any sweep is allowed to take


class JobFailedForUsersError(RippleError):
    """Some users' work failed; the rest completed.

    Carries who failed so a rerun can be targeted, and the original exceptions as an
    ExceptionGroup in `__cause__` so the scheduler's run record keeps the tracebacks.
    """

    def __init__(self, job: str, failures: dict[str, Exception]) -> None:
        self.job = job
        self.failed_user_ids = list(failures)
        super().__init__(f"job {job!r} failed for {len(failures)} user(s)")
        self.__cause__ = ExceptionGroup(
            f"{job} per-user failures", [failures[user_id] for user_id in self.failed_user_ids]
        )


@dataclass
class SweepReport:
    events_by_user: dict[str, int] = field(default_factory=dict)
    skipped_leased: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)


@dataclass
class DeliveryReport:
    sent: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)


async def nightly_sweep(context: JobContext) -> SweepReport:
    """NightlySweep.run for every active user, one lease per user."""
    report = SweepReport()
    failures: dict[str, Exception] = {}
    for user_id in await context.users.active_user_ids():
        try:
            async with leased(context.leases, sweep_lease_key(user_id), SWEEP_LEASE_TTL) as held:
                if not held:
                    report.skipped_leased.append(user_id)
                    log.info("sweep skipped: lease held elsewhere", extra={"user_id": user_id})
                    continue
                events = await context.sweep.run(user_id)
                report.events_by_user[user_id] = len(events)
                log.info("sweep done", extra={"user_id": user_id, "events": len(events)})
        except Exception as exc:  # the lease itself may fail (Redis), not only the sweep
            failures[user_id] = exc
            report.failed.append(user_id)
            log.exception("sweep failed", extra={"user_id": user_id})
    if failures:
        raise JobFailedForUsersError("nightly_sweep", failures)
    return report


async def daily_digest(context: JobContext) -> DeliveryReport:
    """One digest per active user; DigestService enforces once per day."""
    report = DeliveryReport()
    failures: dict[str, Exception] = {}
    for user_id in await context.users.active_user_ids():
        try:
            receipt = await context.digest.send_daily(user_id)
        except Exception as exc:
            failures[user_id] = exc
            report.failed.append(user_id)
            log.exception("digest failed", extra={"user_id": user_id})
            continue
        if receipt is not None:
            report.sent.append(user_id)
        else:
            report.skipped.append(user_id)
    if failures:
        raise JobFailedForUsersError("daily_digest", failures)
    return report


async def hourly_alerts(
    context: JobContext, *, cooldown: timedelta | None = None
) -> DeliveryReport:
    """Alerts for every active user; `since` is now minus the cooldown (ADR-0055)."""
    window = cooldown if cooldown is not None else context.digest.thresholds.alert_cooldown
    since = context.clock.now() - window
    report = DeliveryReport()
    failures: dict[str, Exception] = {}
    for user_id in await context.users.active_user_ids():
        try:
            receipt = await context.digest.send_alerts(user_id, since)
        except Exception as exc:
            failures[user_id] = exc
            report.failed.append(user_id)
            log.exception("alerts failed", extra={"user_id": user_id})
            continue
        if receipt is not None:
            report.sent.append(user_id)
        else:
            report.skipped.append(user_id)
    if failures:
        raise JobFailedForUsersError("hourly_alerts", failures)
    return report


async def scout_run(context: JobContext, *, scout: ScoutAgent | None = None) -> ScoutRunReport:
    """The Scout for every active user, one lease per user (FR-8, ADR-0072).

    Tests inject `scout`; the cron slot builds one for the run from the environment
    (config/sources.yaml via RIPPLE_SOURCES_CONFIG, the Router config) and closes its
    HTTP client afterwards. A user's failure is isolated like the sweep's.
    """
    return await _scout(context, await context.users.active_user_ids(), scout, "scout_run")


async def scout_user(
    context: JobContext, user_id: str, *, scout: ScoutAgent | None = None
) -> ScoutRunReport:
    """One user's Scout run, enqueued when a ripple changed their criteria (ADR-0079).

    Same lease as the daily run, so the two never scout one user at once. The id came
    through a queue, so it is checked against the active users first: an account
    deleted after the enqueue must not get openings written under its id (FR-15).
    """
    if user_id not in await context.users.active_user_ids():
        log.info("scout skipped: user no longer active", extra={"user_id": user_id})
        return ScoutRunReport()
    return await _scout(context, [user_id], scout, "scout_user")


async def _scout(
    context: JobContext, user_ids: Sequence[str], scout: ScoutAgent | None, job: str
) -> ScoutRunReport:
    report = ScoutRunReport()
    failures: dict[str, Exception] = {}
    async with AsyncExitStack() as stack:
        agent = scout
        if agent is None:
            agent = await stack.enter_async_context(
                open_scout(
                    store=context.store,
                    clock=context.clock,
                    runner=context.runner,
                    router=context.router or router_from_env(os.environ),
                    registry=registry_from_env(),
                )
            )
        # One cache for every user of this run: a listing and a JD parse are the same
        # for everyone (ADR-0072 point 4), so the model sees each JD once per run.
        cache = ScoutRunCache()
        for user_id in user_ids:
            try:
                async with leased(
                    context.leases, scout_lease_key(user_id), SCOUT_LEASE_TTL
                ) as held:
                    if not held:
                        report.skipped_leased.append(user_id)
                        log.info("scout skipped: lease held elsewhere", extra={"user_id": user_id})
                        continue
                    user_report = await agent.run_for_user(user_id, cache=cache)
                    report.by_user[user_id] = user_report
                    log.info(
                        "scout done",
                        extra={
                            "user_id": user_id,
                            "new": user_report.new,
                            "duplicates": user_report.duplicates,
                            "errors": len(user_report.errors),
                        },
                    )
            except Exception as exc:
                failures[user_id] = exc
                report.failed.append(user_id)
                log.exception("scout failed", extra={"user_id": user_id})
    if failures:
        raise JobFailedForUsersError(job, failures)
    return report
