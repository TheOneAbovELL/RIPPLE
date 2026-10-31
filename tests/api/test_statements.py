"""POST /statements: the write flow over HTTP."""

import asyncio
import json

from ripple.core.models import Status, TriggerKind
from ripple.llm.change_detector import LLMChangeDetector
from ripple.llm.config import ModelSpec, RouterConfig
from ripple.llm.router import Router
from tests.api.fakes import FailingResolver
from tests.api.harness import Harness, body
from tests.builders import derived, fact, link
from tests.fakes.clock import FakeClock
from tests.fakes.llm import FakeLLM

CGPA = {"subject": "student", "attribute": "cgpa", "value": 7.6}


def test_new_structured_fact_is_recorded_with_a_completed_event():
    h = Harness.build()

    async def run():
        user, headers = await h.user()
        async with h.client() as c:
            return user, await c.post(
                "/statements",
                json={"content": "CGPA is 7.6", "kind": "fact", "structured": CGPA},
                headers=headers,
            )

    user, response = asyncio.run(run())
    assert response.status_code == 201, response.text
    out = body(response)
    assert out["change_kind"] == "new"
    assert out["memory"]["user_id"] == user.id
    assert out["memory"]["domain"] == "jobs"
    assert out["memory"]["status"] == "VALID"
    assert out["memory"]["created_by"] == "user"
    assert out["event"]["trigger_kind"] == "ripple"
    assert out["event"]["completed_at"] is not None


def test_same_attribute_new_value_writes_version_two_and_retires_version_one():
    h = Harness.build()

    async def run():
        _, headers = await h.user()
        async with h.client() as c:
            first = await c.post(
                "/statements",
                json={"content": "CGPA is 7.6", "kind": "fact", "structured": CGPA},
                headers=headers,
            )
            second = await c.post(
                "/statements",
                json={
                    "content": "CGPA is 7.9",
                    "kind": "fact",
                    "structured": {**CGPA, "value": 7.9},
                },
                headers=headers,
            )
            unchanged = await c.post(
                "/statements",
                json={
                    "content": "CGPA is 7.9",
                    "kind": "fact",
                    "structured": {**CGPA, "value": 7.9},
                },
                headers=headers,
            )
        return first, second, unchanged

    first, second, unchanged = asyncio.run(run())
    v1 = body(first)["memory"]
    v2 = body(second)["memory"]
    assert body(second)["change_kind"] == "update"
    assert (v2["version"], v2["supersedes_id"]) == (2, v1["id"])
    assert asyncio.run(h.store.get_memory(v1["id"])).status is Status.RETIRED
    assert body(unchanged)["change_kind"] == "unchanged"
    assert body(unchanged)["event"] is None
    assert body(unchanged)["memory"]["id"] == v2["id"]


def test_inspector_origin_becomes_a_user_edit_trigger():
    h = Harness.build()

    async def run():
        _, headers = await h.user()
        async with h.client() as c:
            return await c.post(
                "/statements",
                json={
                    "content": "CGPA is 7.6",
                    "kind": "fact",
                    "structured": CGPA,
                    "origin": "inspector",
                },
                headers=headers,
            )

    response = asyncio.run(run())
    assert body(response)["event"]["trigger_kind"] == TriggerKind.USER_EDIT.value


def test_agent_written_kinds_are_not_accepted_from_a_client():
    h = Harness.build()

    async def run():
        _, headers = await h.user()
        async with h.client() as c:
            return await c.post(
                "/statements",
                json={"content": "Acme hiring", "kind": "opening"},
                headers=headers,
            )

    assert asyncio.run(run()).status_code == 422
    assert h.store.all_memories() == []


def test_agent_origin_is_not_accepted_from_a_client():
    h = Harness.build()

    async def run():
        _, headers = await h.user()
        async with h.client() as c:
            return await c.post(
                "/statements",
                json={"content": "x", "kind": "fact", "origin": "agent"},
                headers=headers,
            )

    assert asyncio.run(run()).status_code == 422


def test_prose_statement_goes_through_the_llm_change_detector_with_fake_llm():
    llm = FakeLLM(json.dumps({"kind": "new", "reason": "nothing like it recorded"}))
    config = RouterConfig(tasks={"change_detector": [ModelSpec(provider="fake", model="f")]})
    detector = LLMChangeDetector(Router(config, {"fake": llm}), FakeClock())
    h = Harness.build(detector=detector)

    async def run():
        _, headers = await h.user()
        async with h.client() as c:
            return await c.post(
                "/statements",
                json={"content": "I prefer remote roles", "kind": "fact"},
                headers=headers,
            )

    response = asyncio.run(run())
    assert response.status_code == 201, response.text
    assert body(response)["change_kind"] == "new"
    assert len(llm.calls) == 1


def test_resolver_failure_after_the_write_reports_the_open_event():
    """The memory and its SUSPECT wave are committed before the resolver runs; the 503
    names the open event so the client knows the sweep will finish it (ADR-0013)."""
    cgpa = fact("student", "cgpa", 7.6)
    belief = derived("not eligible for Acme")
    h = Harness.build(waves=[[belief.id]], resolver=FailingResolver())

    async def run():
        user, headers = await h.user()
        await h.seed(
            cgpa.model_copy(update={"user_id": user.id}),
            belief.model_copy(update={"user_id": user.id}),
            link(cgpa, belief),
        )
        async with h.client() as c:
            return await c.post(
                "/statements",
                json={
                    "content": "CGPA is 7.9",
                    "kind": "fact",
                    "structured": {**CGPA, "value": 7.9},
                },
                headers=headers,
            )

    response = asyncio.run(run())
    assert response.status_code == 503
    out = body(response)
    assert out["error"] == "LLMUnavailableError"
    assert "down" not in out["detail"]  # provider text never reaches the client
    open_events = h.store.change_events()
    assert [e.id for e in open_events if e.is_open] == out["open_change_event_ids"]
    assert len(out["open_change_event_ids"]) == 1
    assert asyncio.run(h.store.get_memory(belief.id)).status is Status.SUSPECT
    versions = [m for m in h.store.all_memories() if m.structured and m.structured.value == 7.9]
    assert len(versions) == 1  # the write itself is committed, not rolled back


def test_invalid_llm_output_is_a_503_not_a_partial_write():
    """I4 at the boundary: the router gave up, nothing was written."""
    llm = FakeLLM("not json", "still not json", "nope")
    config = RouterConfig(
        tasks={"change_detector": [ModelSpec(provider="fake", model="f")]}, max_retries=2
    )
    detector = LLMChangeDetector(Router(config, {"fake": llm}), FakeClock())
    h = Harness.build(detector=detector)

    async def run():
        _, headers = await h.user()
        async with h.client() as c:
            return await c.post(
                "/statements", json={"content": "prose", "kind": "fact"}, headers=headers
            )

    response = asyncio.run(run())
    assert response.status_code == 503
    assert body(response)["error"] == "LLMOutputInvalidError"
    assert h.store.all_memories() == []
