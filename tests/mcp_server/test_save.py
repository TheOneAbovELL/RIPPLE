"""ripple_save: Intake with origin agent; change kinds; parked questions come back."""

import asyncio

from ripple.core.ids import new_id
from ripple.core.models import Status, TriggerKind
from tests.builders import derived, fact, link
from tests.fakes.resolver import ScriptedResolver, ask
from tests.mcp_server.harness import McpHarness, error, out

CGPA = {"subject": "student", "attribute": "cgpa", "value": 7.6}


def test_save_writes_a_new_agent_memory_and_ripples_it():
    h = McpHarness.build()

    async def run():
        user, token = await h.user()
        async with h.client() as c:
            saved = await h.call(
                c,
                "ripple_save",
                {"content": "CGPA is 7.6", "structured": CGPA, "source_ref": "chat:42"},
                token=token,
            )
            found = await h.call(c, "ripple_search", {"query": "cgpa"}, token=token)
        return user, saved, found

    user, saved, found = asyncio.run(run())
    body = out(saved)
    assert body["change_kind"] == "new"
    assert body["links_written"] == 0
    assert body["pending_questions"] == []
    stored = h.store.all_memories()
    assert [m.id for m in stored] == [body["memory_id"]]
    assert stored[0].user_id == user.id
    assert stored[0].created_by == "agent"
    assert stored[0].kind == "fact"
    assert stored[0].source_ref == "chat:42"
    [event] = h.store.change_events()
    assert event.id == body["event_id"]
    assert event.trigger_kind is TriggerKind.RIPPLE
    assert event.completed_at is not None
    assert [r["memory"]["id"] for r in out(found)["results"]] == [body["memory_id"]]


def test_save_of_a_changed_structured_value_is_a_new_version():
    h = McpHarness.build()

    async def run():
        user, token = await h.user()
        old = fact("student", "cgpa", 7.6, user_id=user.id)
        await h.seed(old)
        async with h.client() as c:
            updated = await h.call(
                c,
                "ripple_save",
                {"content": "CGPA is 8.0", "structured": {**CGPA, "value": 8.0}},
                token=token,
            )
            same = await h.call(
                c,
                "ripple_save",
                {"content": "CGPA is 8.0", "structured": {**CGPA, "value": 8.0}},
                token=token,
            )
        return old, updated, same

    old, updated, same = asyncio.run(run())
    body = out(updated)
    assert body["change_kind"] == "update"
    assert body["memory"]["version"] == 2
    assert body["memory"]["supersedes_id"] == old.id
    assert asyncio.run(h.store.get_memory(old.id)).status is Status.RETIRED
    unchanged = out(same)
    assert unchanged["change_kind"] == "unchanged"
    assert unchanged["event_id"] is None
    assert unchanged["memory_id"] == body["memory_id"]


def test_save_returns_the_questions_its_ripple_parked():
    belief_id = new_id()  # the scripted wave must name it before the harness exists
    h = McpHarness.build(
        waves=[(belief_id,)], resolver=ScriptedResolver({}, default=ask("Still eligible?"))
    )

    async def run():
        user, token = await h.user()
        cgpa = fact("student", "cgpa", 7.6, user_id=user.id)
        belief = derived("eligible for Acme", user_id=user.id, id=belief_id)
        await h.seed(cgpa, belief, link(cgpa, belief))
        async with h.client() as c:
            return await h.call(
                c,
                "ripple_save",
                {"content": "CGPA is 8.0", "structured": {**CGPA, "value": 8.0}},
                token=token,
            )

    body = out(asyncio.run(run()))
    [question] = body["pending_questions"]
    assert question["memory_id"] == belief_id
    assert question["question"] == "Still eligible?"
    assert question["event_id"] == body["event_id"]
    assert asyncio.run(h.store.get_memory(belief_id)).status is Status.PENDING_USER


def test_save_refuses_kinds_an_agent_may_not_write_raw():
    h = McpHarness.build()

    async def run():
        _, token = await h.user()
        async with h.client() as c:
            return await h.call(
                c, "ripple_save", {"content": "Intern at Acme", "kind": "opening"}, token=token
            )

    assert error(asyncio.run(run()))["error"] == "invalid_arguments"
    assert h.store.all_memories() == []
