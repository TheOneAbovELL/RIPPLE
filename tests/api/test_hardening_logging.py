"""Request ids and JSON logs (ADR-0098): one trace id from the header to the event."""

import asyncio
import json
import logging
import logging.config

import pytest

from ripple.api.logging import (
    TRACE_ID_HEADER,
    JsonFormatter,
    TraceIdFilter,
    accept_trace_id,
    bind_trace_id,
    current_trace_id,
    logging_config,
    reset_trace_id,
)
from tests.api.fakes import ScriptedResumeParser, candidate_fact
from tests.api.harness import Harness, body

PDF = b"%PDF-1.4 test"


def _record(message: str = "hello", **extra) -> logging.LogRecord:
    record = logging.LogRecord("ripple.test", logging.INFO, __file__, 1, message, None, None)
    for key, value in extra.items():
        setattr(record, key, value)
    return record


# ---- records --------------------------------------------------------------------------


def test_filter_stamps_the_bound_trace_id_on_records_without_one():
    token = bind_trace_id("abc123")
    try:
        record = _record()
        assert TraceIdFilter().filter(record) is True
        assert record.trace_id == "abc123"  # type: ignore[attr-defined]
    finally:
        reset_trace_id(token)


def test_filter_keeps_a_trace_id_the_caller_set_and_replaces_an_explicit_none():
    token = bind_trace_id("from-request")
    try:
        theirs = _record(trace_id="their-own")
        router_style = _record(trace_id=None)  # the Router passes trace_id=None through extra
        TraceIdFilter().filter(theirs)
        TraceIdFilter().filter(router_style)
        assert theirs.trace_id == "their-own"  # type: ignore[attr-defined]
        assert router_style.trace_id == "from-request"  # type: ignore[attr-defined]
    finally:
        reset_trace_id(token)


def test_outside_a_request_the_trace_id_is_none():
    assert current_trace_id() is None
    record = _record()
    TraceIdFilter().filter(record)
    assert record.trace_id is None  # type: ignore[attr-defined]


def test_json_formatter_emits_one_object_with_extras_and_no_standard_noise():
    record = _record("llm attempt", trace_id="t1", task="resolver", latency_ms=12)
    out = json.loads(JsonFormatter().format(record))
    assert out["message"] == "llm attempt"
    assert out["level"] == "INFO"
    assert out["logger"] == "ripple.test"
    assert out["trace_id"] == "t1"
    assert out["task"] == "resolver" and out["latency_ms"] == 12
    assert out["ts"].endswith("+00:00")
    assert "args" not in out and "pathname" not in out and "exception" not in out


def test_json_formatter_serialises_odd_values_and_tracebacks():
    try:
        raise ValueError("boom")
    except ValueError:
        import sys

        record = _record("failed", memory_id=object())
        record.exc_info = sys.exc_info()
    out = json.loads(JsonFormatter().format(record))
    assert "ValueError: boom" in out["exception"]
    assert isinstance(out["memory_id"], str)


def test_logging_config_loads_and_routes_root_records_through_the_json_handler(capsys):
    logging.config.dictConfig(logging_config("INFO"))
    try:
        token = bind_trace_id("cfg-1")
        logging.getLogger("ripple.anything").info("configured", extra={"memory_id": "m1"})
        reset_trace_id(token)
    finally:
        logging.config.dictConfig({"version": 1, "disable_existing_loggers": False})
    line = capsys.readouterr().err.strip().splitlines()[-1]
    out = json.loads(line)
    assert (out["message"], out["trace_id"], out["memory_id"]) == ("configured", "cfg-1", "m1")


def test_plain_format_is_available_for_development():
    config = logging_config("DEBUG", json_lines=False)
    assert config["handlers"]["stderr"]["formatter"] == "plain"
    assert config["root"]["level"] == "DEBUG"


# ---- header handling ------------------------------------------------------------------


@pytest.mark.parametrize("candidate", ["abc-123", "req_1.2:3", "A" * 128])
def test_accept_trace_id_keeps_plain_tokens(candidate):
    assert accept_trace_id(candidate) == candidate


@pytest.mark.parametrize("candidate", [None, "", "has space", "x" * 129, "bad\nline", "é"])
def test_accept_trace_id_mints_a_fresh_id_for_anything_else(candidate):
    minted = accept_trace_id(candidate)
    assert minted != candidate and len(minted) == 32


# ---- middleware -----------------------------------------------------------------------


def test_response_echoes_the_clients_request_id_or_mints_one():
    h = Harness.build()

    async def run():
        async with h.client() as c:
            echoed = await c.get("/healthz", headers={"X-Request-ID": "dash-42"})
            minted = await c.get("/healthz")
        return echoed, minted

    echoed, minted = asyncio.run(run())
    assert echoed.headers[TRACE_ID_HEADER] == "dash-42"
    assert len(minted.headers[TRACE_ID_HEADER]) == 32


def test_error_responses_carry_the_request_id_too():
    h = Harness.build()

    async def run():
        async with h.client() as c:
            return await c.get("/me", headers={"X-Request-ID": "dash-43"})

    response = asyncio.run(run())
    assert response.status_code == 401
    assert response.headers[TRACE_ID_HEADER] == "dash-43"


def test_log_records_during_a_request_carry_its_id(caplog):
    h = Harness.build()
    logger = logging.getLogger("ripple.api.access")
    logger.addFilter(TraceIdFilter())
    try:
        with caplog.at_level(logging.INFO, logger="ripple.api.access"):

            async def run():
                async with h.client() as c:
                    await c.get("/healthz", headers={"X-Request-ID": "dash-44"})

            asyncio.run(run())
    finally:
        logger.filters.clear()
    access = [r for r in caplog.records if r.getMessage() == "request"]
    assert access and all(r.trace_id == "dash-44" for r in access)  # type: ignore[attr-defined]
    assert access[-1].path == "/healthz" and access[-1].status == 200  # type: ignore[attr-defined]
    assert current_trace_id() is None  # reset after the request


def test_the_request_id_reaches_the_change_event_written_by_a_confirm():
    h = Harness.build(resume_parser=ScriptedResumeParser(candidate_fact("cgpa", 7.6, "CGPA 7.6")))

    async def run():
        _, headers = await h.user()
        async with h.client() as c:
            uploaded = body(
                await c.post(
                    "/resume", files={"file": ("r.pdf", PDF, "application/pdf")}, headers=headers
                )
            )
            candidate_id = uploaded["candidates"][0]["id"]
            return await c.post(
                f"/resume/candidates/{candidate_id}/confirm",
                headers={**headers, "X-Request-ID": "confirm-7"},
            )

    response = asyncio.run(run())
    assert response.status_code == 200, response.text
    assert body(response)["intake"]["event"]["trace_id"] == "confirm-7"
    assert [e.trace_id for e in h.store.change_events()] == ["confirm-7"]
