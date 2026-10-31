"""Transport retries with backoff, pricing from config, and tracing spans (ADR-0027, ADR-0018)."""

import asyncio

import pytest
from pydantic import BaseModel

from ripple.core.errors import LLMUnavailableError
from ripple.llm.client import Message
from ripple.llm.config import ModelPrice, ModelSpec, RouterConfig
from ripple.llm.router import Router
from ripple.llm.tracing import LoggingTracer
from tests.fakes.llm import FakeLLM


class Verdict(BaseModel):
    action: str


ASK = [Message(role="user", content="Decide.")]
GOOD = '{"action": "keep"}'


class RecordingSleeper:
    def __init__(self) -> None:
        self.delays: list[float] = []

    async def __call__(self, seconds: float) -> None:
        self.delays.append(seconds)


def _router(llm, *, transport_retries=2, prices=None, sleeper=None, tracer=None, fallback=None):
    specs = [ModelSpec(provider="p", model="m")]
    clients = {"p": llm}
    if fallback is not None:
        specs.append(ModelSpec(provider="f", model="fm"))
        clients["f"] = fallback
    config = RouterConfig(
        tasks={"t": specs},
        transport_retries=transport_retries,
        backoff_base_seconds=0.25,
        prices=prices or {},
    )
    return Router(config, clients, sleeper=sleeper, tracer=tracer)


def test_router_retries_transport_errors_with_exponential_backoff():
    llm = FakeLLM(ConnectionError("a"), TimeoutError("b"), GOOD)
    sleeper = RecordingSleeper()
    completion = asyncio.run(_router(llm, sleeper=sleeper).complete("t", ASK, Verdict))
    assert completion.output.action == "keep"
    assert sleeper.delays == [0.25, 0.5]
    assert completion.attempts == 3


def test_router_falls_back_after_transport_budget_is_spent():
    primary = FakeLLM(ConnectionError("a"), ConnectionError("b"), ConnectionError("c"))
    fallback = FakeLLM(GOOD)
    sleeper = RecordingSleeper()
    completion = asyncio.run(
        _router(primary, sleeper=sleeper, fallback=fallback).complete("t", ASK, Verdict)
    )
    assert completion.provider == "f"
    assert len(primary.calls) == 3 and len(sleeper.delays) == 2


def test_router_without_transport_retries_fails_over_immediately():
    primary = FakeLLM(ConnectionError("a"))
    with pytest.raises(LLMUnavailableError):
        asyncio.run(_router(primary, transport_retries=0).complete("t", ASK, Verdict))
    assert len(primary.calls) == 1


def test_router_prices_usage_from_config_only():
    llm = FakeLLM(GOOD)
    price = ModelPrice(input=1.0, output=10.0, source="test", recorded="2026-10-19")
    priced = asyncio.run(_router(llm, prices={"m": price}).complete("t", ASK, Verdict))
    expected = (priced.input_tokens * 1.0 + priced.output_tokens * 10.0) / 1_000_000
    assert priced.cost_usd == pytest.approx(expected)
    unpriced = asyncio.run(_router(FakeLLM(GOOD)).complete("t", ASK, Verdict))
    assert unpriced.cost_usd is None


def test_router_emits_a_span_per_attempt_and_per_completion(caplog):
    import logging

    llm = FakeLLM(ConnectionError("a"), GOOD)
    tracer = LoggingTracer(logging.getLogger("test.tracing"))
    with caplog.at_level(logging.INFO, logger="test.tracing"):
        asyncio.run(
            _router(llm, sleeper=RecordingSleeper(), tracer=tracer).complete("t", ASK, Verdict)
        )
    spans = [r.span for r in caplog.records if r.getMessage() == "span"]  # type: ignore[attr-defined]
    assert spans == ["llm.attempt", "llm.attempt", "llm.complete"]
    for record in caplog.records:
        assert "Decide." not in str(record.__dict__)


def test_config_loads_from_toml(tmp_path):
    path = tmp_path / "llm.toml"
    path.write_text(
        """
max_retries = 1
transport_retries = 3
[tasks]
resolver = [{ provider = "anthropic", model = "claude-sonnet-5-5" }]
[prices]
"claude-sonnet-5-5" = { input = 3.0, output = 15.0, source = "x", recorded = "2026-10-19" }
""",
        encoding="utf-8",
    )
    config = RouterConfig.from_toml(path)
    assert config.max_retries == 1 and config.transport_retries == 3
    assert config.models_for("resolver")[0].model == "claude-sonnet-5-5"
    assert config.cost_for("claude-sonnet-5-5", 1_000_000, 0) == pytest.approx(3.0)
    assert config.cost_for("unknown", 10, 10) is None


def test_default_config_file_parses_and_names_only_configured_providers():
    from pathlib import Path

    config = RouterConfig.from_toml(Path("config/llm.default.toml"))
    providers = {spec.provider for specs in config.tasks.values() for spec in specs}
    assert providers == {"anthropic"}
    assert config.prices == {}  # no invented prices (I8)
