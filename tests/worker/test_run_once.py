"""ripple.worker.run_once: one job, no Redis, nothing sent without a bot token (ADR-0134)."""

import asyncio
import io
import json
from dataclasses import replace

import pytest

from ripple.notify.delivery_log import InMemoryDeliveryLog
from ripple.notify.digest import DigestService
from ripple.worker.run_once import JOBS, LocalJob, PrintingTransport, local_job, main
from tests.fakes.clock import FakeClock
from tests.notify.fakes import FakeRecommendationSource, FakeUserDirectory, recommendation
from tests.worker.support import RecordingSweep, context


def _factory(job: LocalJob):
    return lambda env, out: job


def _last_json(text: str) -> dict:
    return json.loads(text.strip().splitlines()[-1])


def test_printing_transport_prints_the_chat_and_text_and_returns_a_receipt():
    clock, out = FakeClock(), io.StringIO()
    transport = PrintingTransport(clock, out)

    receipt = asyncio.run(transport.send("chat-7", "Your digest"))

    assert "would send to Telegram chat chat-7" in out.getvalue()
    assert "Your digest" in out.getvalue()
    assert receipt.chat_id == "chat-7" and receipt.message_id is None
    assert receipt.sent_at == clock.now()


def test_run_once_daily_digest_without_token_prints_the_message_instead_of_sending():
    clock, out = FakeClock(), io.StringIO()
    directory = FakeUserDirectory({"u1": "chat-1"})
    transport = PrintingTransport(clock, out)
    ctx = replace(
        context(clock=clock, users={"u1": "chat-1"}),
        digest=DigestService(
            FakeRecommendationSource({"u1": [recommendation(title="SDE intern")]}),
            directory,
            transport,
            clock,
            delivery_log=InMemoryDeliveryLog(),
        ),
    )

    code = main(
        ["daily_digest"], env={}, out=out, context_factory=_factory(LocalJob(ctx, "printed"))
    )

    assert code == 0
    assert transport.sent == 1
    assert "would send to Telegram chat chat-1" in out.getvalue()
    assert "SDE intern" in out.getvalue()
    assert "TELEGRAM_BOT_TOKEN is not set" in out.getvalue()
    assert _last_json(out.getvalue()) == {
        "job": "daily_digest",
        "messages": "printed",
        "result": {"sent": 1, "skipped": 0},
    }


def test_run_once_nightly_sweep_reports_the_arq_summary_for_every_active_user():
    out = io.StringIO()
    sweep = RecordingSweep(events=2)
    ctx = context(sweep=sweep, users={"u1": None, "u2": None})

    code = main(
        ["nightly_sweep"], env={}, out=out, context_factory=_factory(LocalJob(ctx, "printed"))
    )

    assert code == 0
    assert sweep.runs == ["u1", "u2"]
    assert _last_json(out.getvalue())["result"] == {"users": 2, "events": 4, "skipped_leased": 0}


def test_run_once_exits_1_and_names_the_users_whose_work_failed():
    out = io.StringIO()
    ctx = context(sweep=RecordingSweep(fail_for={"u2"}), users={"u1": None, "u2": None})

    code = main(
        ["nightly_sweep"], env={}, out=out, context_factory=_factory(LocalJob(ctx, "printed"))
    )

    assert code == 1
    assert _last_json(out.getvalue()) == {"job": "nightly_sweep", "failed_user_ids": ["u2"]}


def test_run_once_exits_2_without_database_url(capsys):
    code = main(["nightly_sweep"], env={}, out=io.StringIO())

    assert code == 2
    assert "DATABASE_URL is not set" in capsys.readouterr().err


def test_run_once_warns_that_scout_run_needs_the_model_key():
    out = io.StringIO()
    ctx = context(users={})

    code = main(["scout_run"], env={}, out=out, context_factory=_factory(LocalJob(ctx, "printed")))

    # No active users: nothing is fetched or parsed, so the run completes; the warning stands.
    assert code == 0
    assert "ANTHROPIC_API_KEY is not set: scout_run needs the model" in out.getvalue()


def test_run_once_rejects_an_unknown_job():
    with pytest.raises(SystemExit) as exit_info:
        main(["weekly_report"], env={}, out=io.StringIO())
    assert exit_info.value.code == 2


def test_local_job_without_token_is_a_dry_run_that_records_nothing_in_postgres():
    # The engine is lazy: building the context opens no connection.
    job = local_job({"DATABASE_URL": "postgresql+psycopg://u:p@127.0.0.1:1/none"}, io.StringIO())

    assert job.messages == "printed"
    # What the digest inside the context uses, not only what LocalJob reports: a dry run
    # that recorded deliveries in Postgres would mark tomorrow's real digest as sent.
    digest = job.context.digest
    assert isinstance(digest.transport, PrintingTransport) and digest.transport is job.transport
    assert isinstance(digest.delivery_log, InMemoryDeliveryLog)
    assert digest.delivery_log is job.delivery_log
    assert job.engine is not None
    asyncio.run(job.engine.dispose())


def test_local_job_with_token_sends_for_real_and_records_deliveries():
    from ripple.notify.delivery_log import PostgresDeliveryLog
    from ripple.notify.telegram import TelegramTransport

    job = local_job(
        {"DATABASE_URL": "postgresql+psycopg://u:p@127.0.0.1:1/none", "TELEGRAM_BOT_TOKEN": "t"},
        io.StringIO(),
    )

    assert job.messages == "sent"
    assert isinstance(job.context.digest.transport, TelegramTransport)
    assert isinstance(job.context.digest.delivery_log, PostgresDeliveryLog)
    assert job.engine is not None
    asyncio.run(job.engine.dispose())


def test_run_once_offers_exactly_the_scheduled_jobs():
    assert set(JOBS) == {"nightly_sweep", "daily_digest", "hourly_alerts", "scout_run"}


def test_local_job_runner_has_the_same_observers_as_the_worker_without_a_queue():
    # Parity with job_context_from_env (ADR-0116): a sweep run here re-derives exactly
    # what the scheduled one would. The worker adds the criteria trigger only with a queue.
    from ripple.worker.wiring import job_context_from_env

    env = {"DATABASE_URL": "postgresql+psycopg://u:p@127.0.0.1:1/none", "TELEGRAM_BOT_TOKEN": "t"}
    local = local_job(env, io.StringIO())
    worker = job_context_from_env(env)

    def observer_types(runner) -> list[str]:
        return [type(o).__name__ for o in runner._observers]

    assert observer_types(local.context.runner) == observer_types(worker.runner)
    assert observer_types(local.context.runner) == ["ProfileDerivationObserver"]
    assert local.engine is not None
    asyncio.run(local.engine.dispose())
