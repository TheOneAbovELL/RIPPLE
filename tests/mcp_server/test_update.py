"""ripple_update: Intake.edit as an agent, under the inspector's rules (ADR-0042)."""

import asyncio
from datetime import UTC, datetime

from ripple.core.models import Status, TriggerKind
from tests.builders import fact, memory
from tests.mcp_server.harness import McpHarness, error, out


def test_update_writes_a_user_edit_version_created_by_agent():
    h = McpHarness.build()

    async def run():
        user, token = await h.user()
        old = fact("student", "cgpa", 7.6, user_id=user.id)
        await h.seed(old)
        async with h.client() as c:
            return old, await h.call(
                c,
                "ripple_update",
                {
                    "memory_id": old.id,
                    "content": "CGPA is 8.1",
                    "structured": {"subject": "student", "attribute": "cgpa", "value": 8.1},
                },
                token=token,
            )

    old, result = asyncio.run(run())
    body = out(result)
    assert body["change_kind"] == "update"
    new = body["memory"]
    assert new["version"] == 2 and new["supersedes_id"] == old.id
    assert new["created_by"] == "agent"
    assert new["structured"]["value"] == 8.1
    assert asyncio.run(h.store.get_memory(old.id)).status is Status.RETIRED
    [event] = h.store.change_events()
    assert event.id == body["event_id"]
    assert event.trigger_kind is TriggerKind.USER_EDIT


def test_update_keeps_valid_to_unless_given_and_rejects_a_naive_one():
    h = McpHarness.build()
    expiry = datetime(2027, 6, 1, tzinfo=UTC)

    async def run():
        user, token = await h.user()
        temp = memory(content="interning at Acme", user_id=user.id, valid_to=expiry)
        await h.seed(temp)
        async with h.client() as c:
            kept = await h.call(
                c, "ripple_update", {"memory_id": temp.id, "content": "intern at Acme"}, token=token
            )
            moved = await h.call(
                c,
                "ripple_update",
                {
                    "memory_id": out(kept)["memory_id"],
                    "content": "intern at Acme till July",
                    "valid_to": "2027-07-01T00:00:00+00:00",
                },
                token=token,
            )
            naive = await h.call(
                c,
                "ripple_update",
                {
                    "memory_id": out(moved)["memory_id"],
                    "content": "x",
                    "valid_to": "2027-07-01T00:00:00",
                },
                token=token,
            )
        return kept, moved, naive

    kept, moved, naive = asyncio.run(run())
    assert out(kept)["memory"]["valid_to"] == "2027-06-01T00:00:00Z"
    assert out(moved)["memory"]["valid_to"] == "2027-07-01T00:00:00Z"
    assert error(naive)["error"] == "invalid_arguments"


def test_update_refuses_unknown_retired_foreign_and_pending_memories():
    h = McpHarness.build()

    async def run():
        user, token = await h.user()
        other, _ = await h.user("Bina")
        retired = memory(content="old", status=Status.RETIRED, user_id=user.id)
        pending = memory(content="asked", status=Status.PENDING_USER, user_id=user.id)
        theirs = memory(content="theirs", user_id=other.id)
        await h.seed(retired, pending, theirs)
        edit = {"content": "mine now"}
        async with h.client() as c:
            unknown = await h.call(c, "ripple_update", {"memory_id": "nope", **edit}, token=token)
            gone = await h.call(c, "ripple_update", {"memory_id": retired.id, **edit}, token=token)
            foreign = await h.call(
                c, "ripple_update", {"memory_id": theirs.id, **edit}, token=token
            )
            asked = await h.call(c, "ripple_update", {"memory_id": pending.id, **edit}, token=token)
        return unknown, gone, foreign, asked, theirs

    unknown, gone, foreign, asked, theirs = asyncio.run(run())
    assert error(unknown)["error"] == "not_found"
    assert error(gone)["error"] == "not_found"
    assert error(foreign)["error"] == "not_found"
    assert error(asked)["error"] == "conflict"
    assert "ripple_answer" in error(asked)["detail"]
    assert asyncio.run(h.store.get_memory(theirs.id)).content == "theirs"
    assert h.store.change_events() == []
