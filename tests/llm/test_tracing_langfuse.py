"""LangfuseTracer over a fake client, and the env-driven factory (ADR-0028)."""

import logging

import pytest

from ripple.llm.tracing import (
    ENV_HOST,
    ENV_PUBLIC_KEY,
    ENV_SECRET_KEY,
    LangfuseTracer,
    LoggingTracer,
    tracer_from_env,
)


class FakeObservation:
    def __init__(self, name, kwargs):
        self.name = name
        self.kwargs = kwargs
        self.updates: list[dict] = []
        self.ended = False

    def update(self, **kwargs):
        self.updates.append(kwargs)

    def end(self, **kwargs):
        self.ended = True


class FakeLangfuse:
    def __init__(self):
        self.observations: list[FakeObservation] = []
        self.flushed = 0
        self.shutdowns = 0

    def start_observation(self, *, name, **kwargs):
        observation = FakeObservation(name, kwargs)
        self.observations.append(observation)
        return observation

    def flush(self):
        self.flushed += 1

    def shutdown(self):
        self.shutdowns += 1


def test_langfuse_tracer_sends_attributes_as_metadata_and_ends_the_observation():
    client = FakeLangfuse()
    tracer = LangfuseTracer(client)
    with tracer.span("llm.attempt", task="resolver", model="m") as span:
        span.set(input_tokens=12)
    [obs] = client.observations
    assert obs.name == "llm.attempt"
    assert obs.kwargs["metadata"] == {"task": "resolver", "model": "m"}
    assert obs.updates[-1]["metadata"]["input_tokens"] == 12
    assert "elapsed_ms" in obs.updates[-1]["metadata"]
    assert obs.ended


def test_langfuse_tracer_marks_errors_and_reraises():
    client = FakeLangfuse()
    with pytest.raises(ValueError), LangfuseTracer(client).span("llm.attempt"):
        raise ValueError("boom")
    [obs] = client.observations
    assert any(u.get("level") == "ERROR" for u in obs.updates)
    assert obs.updates[-1]["metadata"]["error_type"] == "ValueError"
    assert obs.ended


def test_langfuse_tracer_never_receives_content():
    client = FakeLangfuse()
    with LangfuseTracer(client).span("llm.attempt", task="resolver", output_tokens=3):
        pass
    serialised = str(client.observations[0].kwargs) + str(client.observations[0].updates)
    assert "Decide" not in serialised and "content" not in serialised


def test_langfuse_tracer_flush_and_shutdown_delegate():
    client = FakeLangfuse()
    tracer = LangfuseTracer(client)
    tracer.flush()
    tracer.shutdown()
    assert (client.flushed, client.shutdowns) == (1, 1)


def test_tracer_from_env_falls_back_to_logging_when_keys_are_missing(caplog):
    with caplog.at_level(logging.INFO, logger="ripple.llm.tracing"):
        tracer = tracer_from_env({ENV_PUBLIC_KEY: "pk", ENV_SECRET_KEY: "", ENV_HOST: "h"})
    assert isinstance(tracer, LoggingTracer)
    assert any("LoggingTracer" in r.getMessage() for r in caplog.records)
