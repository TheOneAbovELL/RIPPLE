import pytest

from ripple.core.errors import ConfigurationError
from ripple.storage.engine import ENV_VAR, database_url, engine_from_url


def test_database_url_is_none_when_unset(monkeypatch):
    monkeypatch.delenv(ENV_VAR, raising=False)
    assert database_url() is None


def test_database_url_is_none_when_blank(monkeypatch):
    monkeypatch.setenv(ENV_VAR, "")
    assert database_url() is None


def test_engine_from_url_rejects_non_psycopg_driver():
    with pytest.raises(ConfigurationError, match="postgresql\\+psycopg"):
        engine_from_url("postgresql+asyncpg://u:p@localhost/db")


def test_engine_from_url_builds_async_engine_without_connecting():
    engine = engine_from_url("postgresql+psycopg://u:p@localhost:5432/db")
    assert engine.url.drivername == "postgresql+psycopg"
