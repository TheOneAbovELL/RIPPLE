"""ripple_questions and ripple_answer: the ask-user queue over MCP (FR-7)."""

import asyncio

from ripple.core.models import Decision, DecisionAction, Status, TriggerKind
from tests.builders import change_event, derived, memory
from tests.mcp_server.harness import McpHarness, error, out


async def _pending(h: McpHarness, user_id: str, question: str = "Still true?"):
    asked = derived("eligible for Acme", user_id=user_id, status=Status.PENDING_USER)
    event = change_event(
        memory(content="trigger", user_id=user_id),
        user_id=user_id,
        affected_ids=[asked.id],
        decisions=[
            Decision(
                memory_id=asked.id,
                wave=1,
                action=DecisionAction.ASK,
                reason="parent changed",
                question=question,
            )
        ],
    )
    await h.seed(asked)
    async with h.store.transaction() as tx:
        await tx.add_change_event(event)
    return asked, event


def test_questions_lists_pending_memories_with_their_question():
    h = McpHarness.build()

    async def run():
        user, token = await h.user()
        other, _ = await h.user("Bina")
        asked, event = await _pending(h, user.id)
        await _pending(h, other.id, "Theirs?")
        async with h.client() as c:
            return asked, event, await h.call(c, "ripple_questions", token=token)

    asked, event, result = asyncio.run(run())
    [question] = out(result)["questions"]
    assert question["memory_id"] == asked.id
    assert question["memory"]["id"] == asked.id
    assert question["question"] == "Still true?"
    assert question["reason"] == "parent changed"
    assert question["event_id"] == event.id


def test_answer_still_holds_restores_the_memory():
    h = McpHarness.build()

    async def run():
        user, token = await h.user()
        asked, _ = await _pending(h, user.id)
        async with h.client() as c:
            return asked, await h.call(
                c, "ripple_answer", {"memory_id": asked.id, "reply": "still_holds"}, token=token
            )

    asked, result = asyncio.run(run())
    body = out(result)
    assert body["memory_id"] == asked.id and body["status"] == "VALID"
    assert body["memory"]["id"] == asked.id
    event = asyncio.run(h.store.get_change_event(body["event_id"]))
    assert event.trigger_kind is TriggerKind.USER_ANSWER


def test_answer_no_longer_holds_retires_and_returns_no_memory():
    h = McpHarness.build()

    async def run():
        user, token = await h.user()
        asked, _ = await _pending(h, user.id)
        async with h.client() as c:
            return asked, await h.call(
                c,
                "ripple_answer",
                {"memory_id": asked.id, "reply": "no_longer_holds"},
                token=token,
            )

    asked, result = asyncio.run(run())
    body = out(result)
    assert body["status"] == "RETIRED" and body["memory"] is None
    assert asyncio.run(h.store.get_memory(asked.id)).status is Status.RETIRED


def test_answer_with_a_correction_writes_a_new_version():
    h = McpHarness.build()

    async def run():
        user, token = await h.user()
        asked, _ = await _pending(h, user.id)
        async with h.client() as c:
            missing = await h.call(
                c, "ripple_answer", {"memory_id": asked.id, "reply": "correction"}, token=token
            )
            corrected = await h.call(
                c,
                "ripple_answer",
                {"memory_id": asked.id, "reply": "correction", "content": "eligible for Beta"},
                token=token,
            )
        return asked, missing, corrected

    asked, missing, corrected = asyncio.run(run())
    assert error(missing)["error"] == "invalid_arguments"
    body = out(corrected)
    assert body["memory_id"] != asked.id
    assert body["status"] == "VALID"
    assert body["memory"]["content"] == "eligible for Beta"
    assert body["memory"]["supersedes_id"] == asked.id


def test_answer_refuses_memories_that_are_not_pending_or_not_the_callers():
    h = McpHarness.build()

    async def run():
        user, token = await h.user()
        other, _ = await h.user("Bina")
        plain = memory(content="valid", user_id=user.id)
        theirs, _ = await _pending(h, other.id)
        await h.seed(plain)
        async with h.client() as c:
            not_pending = await h.call(
                c, "ripple_answer", {"memory_id": plain.id, "reply": "still_holds"}, token=token
            )
            foreign = await h.call(
                c, "ripple_answer", {"memory_id": theirs.id, "reply": "still_holds"}, token=token
            )
        return not_pending, foreign, theirs

    not_pending, foreign, theirs = asyncio.run(run())
    assert error(not_pending)["error"] == "conflict"
    assert error(foreign)["error"] == "not_found"
    assert asyncio.run(h.store.get_memory(theirs.id)).status is Status.PENDING_USER
