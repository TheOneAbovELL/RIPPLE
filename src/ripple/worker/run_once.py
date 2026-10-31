"""Run one worker job once against DATABASE_URL, without Redis (ADR-0134).

    uv run python -m ripple.worker.run_once nightly_sweep|daily_digest|hourly_alerts|scout_run

One process, so leases are in memory: they exclude only this process's own work (a
local API on the same database holds no event lease, ADR-0132). The context is built by
`job_context_from_env` itself, leaving out two things a local run must not do: enqueue
scout_user_job (there is no queue), and, without TELEGRAM_BOT_TOKEN, send anything.
Then a PrintingTransport writes each message that would go out, and the delivery log
is in memory, so a preview never marks a digest as sent in the database. Jobs still
write their ripples (the sweep, the Scout) for real. The job's summary is the same dict
the arq wrappers return, printed as one JSON line.

Exit codes: 0 done, 1 some users failed (named), 2 configuration error.
"""

import argparse
import asyncio
import json
import os
import sys
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal, TextIO

from sqlalchemy.ext.asyncio import AsyncEngine

from ripple.core.clock import Clock, SystemClock
from ripple.core.errors import ConfigurationError
from ripple.llm.providers.anthropic import ENV_API_KEY
from ripple.notify.contracts import DeliveryLog, MessageReceipt, Transport
from ripple.notify.delivery_log import InMemoryDeliveryLog, PostgresDeliveryLog
from ripple.notify.telegram import ENV_TOKEN as TELEGRAM_TOKEN_VAR
from ripple.notify.telegram import TelegramTransport
from ripple.storage.engine import ENV_VAR as DATABASE_URL_VAR
from ripple.storage.engine import engine_from_url
from ripple.storage.loop import use_selector_event_loop
from ripple.worker import settings
from ripple.worker.context import JobContext
from ripple.worker.jobs import JobFailedForUsersError
from ripple.worker.wiring import job_context_from_env, shutdown_tracer

# The arq wrappers already turn each report into a summary dict; reusing them keeps the
# local output identical to what the scheduler records.
JOBS: Mapping[str, Callable[[dict[str, Any]], Awaitable[dict[str, int]]]] = {
    "nightly_sweep": settings.nightly_sweep_job,
    "daily_digest": settings.daily_digest_job,
    "hourly_alerts": settings.hourly_alerts_job,
    "scout_run": settings.scout_run_job,
}
# Jobs whose every run reaches the model (the Scout parses each JD with it).
NEEDS_MODEL = frozenset({"scout_run"})


class PrintingTransport:
    """A Transport that prints the message instead of sending it (no bot token)."""

    def __init__(self, clock: Clock, out: TextIO) -> None:
        self._clock = clock
        self._out = out
        self.sent = 0

    async def send(self, chat_id: str, text: str) -> MessageReceipt:
        self.sent += 1
        print(f"----- would send to Telegram chat {chat_id} -----", file=self._out)
        print(text, file=self._out)
        print("----- end of message -----", file=self._out, flush=True)
        return MessageReceipt(chat_id=chat_id, message_id=None, sent_at=self._clock.now())


Messages = Literal["printed", "sent"]


@dataclass(frozen=True)
class LocalJob:
    context: JobContext
    # "printed": no bot token, so messages are printed and not recorded in Postgres.
    messages: Messages
    # Disposed after the run; None when a test injects a context without a database.
    engine: AsyncEngine | None = None
    transport: Transport | None = None
    delivery_log: DeliveryLog | None = None


ContextFactory = Callable[[Mapping[str, str], TextIO], LocalJob]


def local_job(env: Mapping[str, str], out: TextIO) -> LocalJob:
    """The JobContext for one local run; raises ConfigurationError before any job runs."""
    database_url = env.get(DATABASE_URL_VAR, "").strip()
    if not database_url:
        raise ConfigurationError(f"{DATABASE_URL_VAR} is not set")
    engine = engine_from_url(database_url)
    clock = SystemClock()
    messages: Messages = "sent" if env.get(TELEGRAM_TOKEN_VAR, "").strip() else "printed"
    transport: Transport
    delivery_log: DeliveryLog
    if messages == "printed":
        transport, delivery_log = PrintingTransport(clock, out), InMemoryDeliveryLog()
    else:
        transport = TelegramTransport.from_env(clock, env=env)
        delivery_log = PostgresDeliveryLog(engine)  # a real send is recorded (ADR-0095)
    # The worker's own wiring, minus the queue: no enqueue_scout, in-memory leases.
    context = job_context_from_env(
        env, engine=engine, transport=transport, delivery_log=delivery_log
    )
    return LocalJob(
        context=context,
        messages=messages,
        engine=engine,
        transport=transport,
        delivery_log=delivery_log,
    )


async def run_job(name: str, job: LocalJob) -> dict[str, int]:
    try:
        return await JOBS[name]({settings.CONTEXT_KEY: job.context})
    finally:
        if job.engine is not None:
            await job.engine.dispose()


def main(
    argv: Sequence[str] | None = None,
    *,
    env: Mapping[str, str] | None = None,
    out: TextIO = sys.stdout,
    context_factory: ContextFactory = local_job,
) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m ripple.worker.run_once",
        description="Run one worker job once against DATABASE_URL, without Redis.",
    )
    parser.add_argument("job", choices=sorted(JOBS))
    args = parser.parse_args(argv)
    env = os.environ if env is None else env
    use_selector_event_loop()  # psycopg async on Windows (ADR-0115)

    try:
        job = context_factory(env, out)
    except ConfigurationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if job.messages == "printed":
        print(
            f"{TELEGRAM_TOKEN_VAR} is not set: nothing is sent; each message is printed "
            "instead and not recorded as delivered.",
            file=out,
        )
    if args.job in NEEDS_MODEL and not env.get(ENV_API_KEY, "").strip():
        print(f"{ENV_API_KEY} is not set: {args.job} needs the model and will fail.", file=out)
    print(
        "Criteria changes found during this run are not queued for a Scout run (no Redis).",
        file=out,
        flush=True,
    )

    try:
        summary = asyncio.run(run_job(args.job, job))
    except JobFailedForUsersError as exc:
        print(json.dumps({"job": args.job, "failed_user_ids": exc.failed_user_ids}), file=out)
        return 1
    finally:
        shutdown_tracer()
    print(json.dumps({"job": args.job, "messages": job.messages, "result": summary}), file=out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
