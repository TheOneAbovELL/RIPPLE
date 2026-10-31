import asyncio
import logging

import pytest
from pydantic import BaseModel

from ripple.core.errors import ConfigurationError, LLMOutputInvalidError, LLMUnavailableError
from ripple.llm.client import Message
from ripple.llm.config import ModelSpec, RouterConfig
from ripple.llm.router import Router
from tests.fakes.llm import FakeLLM


class Verdict(BaseModel):
    action: str
    reason: str


ASK = [Message(role="user", content="Decide.")]
GOOD = '{"action": "keep", "reason": "unchanged"}'
MISSING_FIELD = '{"action": "keep"}'
NOT_JSON = "Sure! The answer is keep."


def _router(primary: FakeLLM, fallback: FakeLLM | None = None, max_retries: int = 2) -> Router:
    specs = [ModelSpec(provider="primary", model="p-1")]
    clients = {"primary": primary}
    if fallback is not None:
        specs.append(ModelSpec(provider="fallback", model="f-1"))
        clients["fallback"] = fallback
    # Transport retries are covered in test_router_transport.py; here a raise fails over at once.
    config = RouterConfig(tasks={"resolver": specs}, max_retries=max_retries, transport_retries=0)
    return Router(config, clients)


def test_router_validates_output_into_schema():
    llm = FakeLLM(GOOD)
    completion = asyncio.run(_router(llm).complete("resolver", ASK, Verdict))
    assert completion.output == Verdict(action="keep", reason="unchanged")
    assert completion.attempts == 1
    assert completion.model == "p-1"


def test_router_retries_invalid_output_then_returns_valid():
    llm = FakeLLM(MISSING_FIELD, NOT_JSON, GOOD)
    completion = asyncio.run(_router(llm).complete("resolver", ASK, Verdict))
    assert completion.attempts == 3
    assert completion.output.action == "keep"
    # The retry shows the model its own answer and the validation error.
    retry_messages = llm.calls[1].messages
    assert retry_messages[-2].content == MISSING_FIELD
    assert "reason" in retry_messages[-1].content
    # Non-JSON is reported at the root, not as an empty field name.
    assert "<root>" in llm.calls[2].messages[-1].content


def test_router_rejects_invalid_output_after_n_retries():
    llm = FakeLLM(MISSING_FIELD, MISSING_FIELD, MISSING_FIELD)
    with pytest.raises(LLMOutputInvalidError) as excinfo:
        asyncio.run(_router(llm, max_retries=2).complete("resolver", ASK, Verdict))
    assert excinfo.value.attempts == 3
    assert len(llm.calls) == 3


def test_router_with_zero_retries_makes_exactly_one_attempt():
    primary = FakeLLM(NOT_JSON)
    fallback = FakeLLM(GOOD)
    with pytest.raises(LLMOutputInvalidError) as excinfo:
        asyncio.run(_router(primary, fallback, max_retries=0).complete("resolver", ASK, Verdict))
    assert len(primary.calls) == 1
    assert excinfo.value.attempts == 1
    # Invalid output never escalates to another provider.
    assert fallback.calls == []


def test_router_falls_back_when_provider_raises():
    primary = FakeLLM(ConnectionError("boom"))
    fallback = FakeLLM(GOOD)
    completion = asyncio.run(_router(primary, fallback).complete("resolver", ASK, Verdict))
    assert completion.provider == "fallback"
    assert completion.output.action == "keep"


def test_router_counts_tokens_from_failed_provider_before_fallback():
    primary = FakeLLM(MISSING_FIELD, ConnectionError("rate limited"))
    fallback = FakeLLM(GOOD)
    completion = asyncio.run(_router(primary, fallback).complete("resolver", ASK, Verdict))
    assert completion.attempts == 3
    assert completion.output_tokens == len(MISSING_FIELD.split()) + len(GOOD.split())


def test_router_raises_unavailable_when_every_provider_fails():
    primary = FakeLLM(ConnectionError("down"))
    fallback = FakeLLM(TimeoutError("slow"))
    with pytest.raises(LLMUnavailableError) as excinfo:
        asyncio.run(_router(primary, fallback).complete("resolver", ASK, Verdict))
    assert len(excinfo.value.failures) == 2


def test_router_sends_schema_to_the_client():
    llm = FakeLLM(GOOD)
    asyncio.run(_router(llm).complete("resolver", ASK, Verdict))
    assert llm.calls[0].json_schema["title"] == "Verdict"
    assert llm.calls[0].model == "p-1"


def test_router_accumulates_tokens_across_attempts():
    llm = FakeLLM(MISSING_FIELD, GOOD)
    completion = asyncio.run(_router(llm).complete("resolver", ASK, Verdict))
    assert completion.output_tokens == len(MISSING_FIELD.split()) + len(GOOD.split())


def test_router_refuses_config_with_unknown_provider():
    with pytest.raises(ConfigurationError, match="ghost"):
        Router(
            RouterConfig(tasks={"resolver": [ModelSpec(provider="ghost", model="x")]}),
            {"primary": FakeLLM()},
        )


def test_router_logs_every_attempt_without_content(caplog):
    llm = FakeLLM(MISSING_FIELD, GOOD)
    with caplog.at_level(logging.INFO, logger="ripple.llm.router"):
        asyncio.run(_router(llm).complete("resolver", ASK, Verdict))
    attempts = [r for r in caplog.records if r.getMessage() == "llm attempt"]
    assert [r.valid for r in attempts] == [False, True]  # type: ignore[attr-defined]
    for record in caplog.records:
        serialised = str(record.__dict__)
        assert GOOD not in serialised
        assert MISSING_FIELD not in serialised
        assert "Decide." not in serialised


def test_fake_llm_records_calls():
    llm = FakeLLM(GOOD)
    asyncio.run(_router(llm).complete("resolver", ASK, Verdict))
    assert [m.content for m in llm.calls[0].messages] == ["Decide."]
