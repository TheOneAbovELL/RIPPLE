"""Production wiring reads the environment and refuses to guess (ADR-0041)."""

import asyncio
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from ripple.api.app import create_app, create_production_app
from ripple.api.wiring import DomainAdapters, Settings, app_from_env, build_services
from ripple.core.errors import ConfigurationError
from tests.api.fakes import (
    RecordingOpeningRecorder,
    ScriptedOpeningParser,
    ScriptedRecommendations,
    ScriptedResumeParser,
    SimpleCandidateStatements,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
ENV = {
    "DATABASE_URL": "postgresql+psycopg://ripple:change-me@localhost:5432/ripple",
    "RIPPLE_LLM_CONFIG": str(REPO_ROOT / "config" / "llm.default.toml"),
}


def _adapters() -> DomainAdapters:
    return DomainAdapters(
        resume_parser=ScriptedResumeParser(),
        candidate_statements=SimpleCandidateStatements(),
        opening_parser=ScriptedOpeningParser(),
        opening_recorder=RecordingOpeningRecorder(),
        recommendations=ScriptedRecommendations(),
    )


def test_missing_database_url_names_the_variable():
    with pytest.raises(ConfigurationError, match="DATABASE_URL"):
        Settings.from_env({k: v for k, v in ENV.items() if k != "DATABASE_URL"})


def test_llm_config_defaults_to_the_repo_file_and_bad_values_are_configuration_errors():
    assert Settings.from_env({"DATABASE_URL": ENV["DATABASE_URL"]}).llm_config == Path(
        "config/llm.default.toml"
    )
    with pytest.raises(ConfigurationError, match="does not exist"):
        build_services(
            Settings.from_env({**ENV, "RIPPLE_LLM_CONFIG": "nope/llm.toml"}), _adapters()
        )
    with pytest.raises(ConfigurationError, match="postgresql\\+psycopg"):
        build_services(Settings.from_env({**ENV, "DATABASE_URL": "sqlite:///x.db"}), _adapters())


def test_build_services_wires_an_app_without_touching_the_database():
    """Engine creation is lazy; an unauthenticated request never reaches Postgres."""
    services = build_services(Settings.from_env(ENV), _adapters())
    app = create_app(services)

    async def run():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            return await c.get("/me")

    assert asyncio.run(run()).status_code == 401


def test_production_factory_builds_the_app_with_the_real_adapters(monkeypatch):
    """After integration checkpoint C2 the factory wires WS-1/WS-2 adapters itself."""
    from ripple.api.adapters import OpeningRecorderAdapter, ResumeParserAdapter
    from ripple.domains.jobs.ranking import JobsRecommender

    for key, value in ENV.items():
        monkeypatch.setenv(key, value)
    app = create_production_app()
    services = app.state.services
    assert isinstance(services.resume_parser, ResumeParserAdapter)
    assert isinstance(services.opening_recorder, OpeningRecorderAdapter)
    assert isinstance(services.recommendations, JobsRecommender)
    assert app_from_env(ENV).state.services.domain == services.domain
