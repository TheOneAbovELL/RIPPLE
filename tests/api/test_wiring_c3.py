"""Production wiring added at checkpoint C3: Telegram in the API, CORS, retriever, tracer flush."""

import asyncio
from pathlib import Path

import pytest
from fastapi import FastAPI

from ripple.api.wiring import (
    Settings,
    api_lifespan,
    app_from_env,
    build_services,
    flush_tracer,
    psycopg_dsn,
    redis_factory,
)
from ripple.core.errors import ConfigurationError
from ripple.llm.tracing import LangfuseTracer, LoggingTracer

REPO_ROOT = Path(__file__).resolve().parents[2]
ENV = {
    "DATABASE_URL": "postgresql+psycopg://ripple:change-me@localhost:5432/ripple",
    "RIPPLE_LLM_CONFIG": str(REPO_ROOT / "config" / "llm.default.toml"),
}


def test_settings_read_cors_origins_and_whether_telegram_is_on():
    plain = Settings.from_env(ENV)
    assert (plain.cors_origins, plain.telegram) == ((), False)
    dev = Settings.from_env(
        {
            **ENV,
            "RIPPLE_CORS_ORIGINS": "http://localhost:3000, http://127.0.0.1:3000,",
            "TELEGRAM_BOT_TOKEN": "123:abc",
        }
    )
    assert dev.cors_origins == ("http://localhost:3000", "http://127.0.0.1:3000")
    assert dev.telegram is True


def test_build_services_carries_one_retriever_and_the_router():
    services = build_services(Settings.from_env(ENV))
    assert services.retriever is not None and services.router is not None


def test_build_services_gives_delete_me_the_postgres_delivery_log():
    from ripple.notify.delivery_log import PostgresDeliveryLog

    assert isinstance(build_services(Settings.from_env(ENV)).delivery_log, PostgresDeliveryLog)


def test_telegram_without_a_webhook_secret_refuses_to_start():
    with pytest.raises(ConfigurationError, match="TELEGRAM_WEBHOOK_SECRET"):
        app_from_env({**ENV, "TELEGRAM_BOT_TOKEN": "123:abc"})


def test_telegram_on_mounts_the_webhook_route_and_off_does_not():
    on = app_from_env({**ENV, "TELEGRAM_BOT_TOKEN": "123:abc", "TELEGRAM_WEBHOOK_SECRET": "s" * 32})
    off = app_from_env(ENV)
    assert getattr(on.state, "telegram_webhook_mounted", False) is True
    assert getattr(off.state, "telegram_webhook_mounted", False) is False


def test_psycopg_dsn_drops_the_sqlalchemy_driver_only():
    assert psycopg_dsn(ENV["DATABASE_URL"]) == "postgresql://ripple:change-me@localhost:5432/ripple"


class _RecordingLangfuse:
    def __init__(self) -> None:
        self.shutdowns = 0

    def start_observation(self, *, name, **kwargs):
        raise AssertionError("no span expected")

    def flush(self) -> None:
        pass

    def shutdown(self) -> None:
        self.shutdowns += 1


def test_flush_tracer_shuts_langfuse_down_and_ignores_the_logging_tracer():
    client = _RecordingLangfuse()
    flush_tracer(LangfuseTracer(client))
    flush_tracer(LoggingTracer())
    assert client.shutdowns == 1


def test_lifespan_without_telegram_opens_nothing_and_flushes_the_tracer_on_exit():
    client = _RecordingLangfuse()
    services = build_services(Settings.from_env(ENV))
    services.router._tracer = LangfuseTracer(client)  # type: ignore[union-attr]
    lifespan = api_lifespan(Settings.from_env(ENV), services, ENV, webhook_secret=None)

    async def run():
        async with lifespan(FastAPI()):
            assert client.shutdowns == 0

    asyncio.run(run())
    assert client.shutdowns == 1


def test_redis_factory_returns_one_pool_per_url_per_process():
    assert redis_factory("redis://localhost:6379/0") is redis_factory("redis://localhost:6379/0")
    assert redis_factory("redis://localhost:6379/0") is not redis_factory(
        "redis://localhost:6379/1"
    )


def test_api_runner_shares_the_event_lease_and_scout_trigger_only_with_redis():
    from ripple.agents.scout import CriteriaChangeObserver
    from ripple.domains.jobs.derive import ProfileDerivationObserver
    from ripple.worker.lease import ChangeEventLease

    plain = build_services(Settings.from_env(ENV)).runner
    assert plain._event_lease is None
    assert [type(o) for o in plain._observers] == [ProfileDerivationObserver]
    shared = build_services(Settings.from_env({**ENV, "REDIS_URL": "redis://localhost:6379/0"}))
    assert isinstance(shared.runner._event_lease, ChangeEventLease)
    assert [type(o) for o in shared.runner._observers] == [
        ProfileDerivationObserver,
        CriteriaChangeObserver,
    ]


def test_lifespan_closes_the_redis_pools_it_opened():
    pool = redis_factory("redis://localhost:6379/9")
    closed: list[bool] = []

    class FakeArq:
        async def aclose(self) -> None:
            closed.append(True)

    pool._pool = FakeArq()  # type: ignore[assignment]  # as if a request had opened it
    services = build_services(Settings.from_env(ENV))
    lifespan = api_lifespan(Settings.from_env(ENV), services, ENV, webhook_secret=None)

    async def run():
        async with lifespan(FastAPI()):
            assert closed == []

    asyncio.run(run())
    assert closed == [True] and pool._pool is None


def test_build_services_refuses_a_trained_linker_without_a_model_folder():
    # ADR-0128: RIPPLE_LINKER picks the write-path prose linker; a bad choice fails at
    # start-up, not on the first free-text statement.
    with pytest.raises(ConfigurationError, match="RIPPLE_TRAINED_LINKER_MODEL"):
        build_services(Settings.from_env({**ENV, "RIPPLE_LINKER": "trained"}))
    with pytest.raises(ConfigurationError, match="RIPPLE_LINKER"):
        build_services(Settings.from_env({**ENV, "RIPPLE_LINKER": "bert"}))


def test_build_services_keeps_the_llm_linker_for_prose_by_default():
    from ripple.linking.llm import LLMLinker

    intake = build_services(Settings.from_env(ENV)).intake
    assert isinstance(intake._linker._prose, LLMLinker)  # type: ignore[attr-defined]


def test_a_blank_linker_setting_means_the_default():
    # compose writes `RIPPLE_LINKER=${RIPPLE_LINKER:-}`: empty must not stop the API.
    from ripple.linking.llm import LLMLinker

    settings = Settings.from_env({**ENV, "RIPPLE_LINKER": " ", "RIPPLE_TRAINED_LINKER_MODEL": ""})
    intake = build_services(settings).intake
    assert isinstance(intake._linker._prose, LLMLinker)  # type: ignore[attr-defined]
