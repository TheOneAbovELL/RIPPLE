"""Worker wiring builds a complete JobContext from the environment without connecting."""

import pytest

from ripple.core.errors import ConfigurationError
from ripple.core.sweep import NightlySweep
from ripple.domains.jobs.ranking import JobsRecommender
from ripple.notify.digest import DigestService
from ripple.worker.lease import InMemoryLease
from ripple.worker.wiring import job_context_from_env

ENV = {
    "DATABASE_URL": "postgresql+psycopg://ripple:x@localhost:5432/ripple",
    "TELEGRAM_BOT_TOKEN": "123:abc",
    "RIPPLE_LLM_CONFIG": "config/llm.default.toml",
}


def test_job_context_from_env_wires_every_collaborator():
    context = job_context_from_env(ENV)
    assert isinstance(context.sweep, NightlySweep)
    assert isinstance(context.digest, DigestService)
    assert isinstance(context.leases, InMemoryLease)
    # The ranking source is the jobs adapter's recommender.
    assert isinstance(context.digest._recommendations, JobsRecommender)


def test_job_context_requires_database_url():
    with pytest.raises(ConfigurationError, match="DATABASE_URL"):
        job_context_from_env({k: v for k, v in ENV.items() if k != "DATABASE_URL"})


def test_job_context_requires_telegram_token():
    with pytest.raises(ConfigurationError, match="TELEGRAM_BOT_TOKEN"):
        job_context_from_env({k: v for k, v in ENV.items() if k != "TELEGRAM_BOT_TOKEN"})


def test_job_context_refuses_missing_llm_config():
    with pytest.raises(ConfigurationError, match="does not exist"):
        job_context_from_env({**ENV, "RIPPLE_LLM_CONFIG": "config/nope.toml"})
