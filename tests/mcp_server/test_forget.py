"""ripple_forget: the whole chain and its depends_on subtree leave; snapshots stay (I7)."""

import asyncio

from tests.builders import derived, fact, link, memory, snapshot_link
from tests.mcp_server.harness import McpHarness, error, out


def test_forget_deletes_the_subtree_logs_it_and_hides_it_from_search():
    h = McpHarness.build()

    async def run():
        user, token = await h.user()
        cgpa = fact("student", "cgpa", 7.6, user_id=user.id, content="cgpa python")
        belief = derived("eligible python", user_id=user.id)
        application = memory(content="applied python", kind="application", user_id=user.id)
        await h.seed(
            cgpa, belief, application, link(cgpa, belief), snapshot_link(cgpa, application)
        )
        async with h.client() as c:
            forgotten = await h.call(c, "ripple_forget", {"memory_id": cgpa.id}, token=token)
            after = await h.call(c, "ripple_search", {"query": "python"}, token=token)
        return cgpa, belief, application, forgotten, after

    cgpa, belief, application, forgotten, after = asyncio.run(run())
    body = out(forgotten)
    assert body["root_memory_id"] == cgpa.id
    assert body["deleted_ids"] == sorted([cgpa.id, belief.id])
    assert {m.id for m in h.store.all_memories()} == {application.id}
    assert h.store.all_links() == []
    [event] = h.store.forget_events()
    assert event.id == body["event_id"] and event.deleted_ids == body["deleted_ids"]
    assert [r["memory"]["id"] for r in out(after)["results"]] == [application.id]


def test_forget_of_another_users_memory_is_not_found_and_deletes_nothing():
    h = McpHarness.build()

    async def run():
        _, token = await h.user()
        other, _ = await h.user("Bina")
        theirs = fact("student", "cgpa", 7.6, user_id=other.id)
        await h.seed(theirs)
        async with h.client() as c:
            foreign = await h.call(c, "ripple_forget", {"memory_id": theirs.id}, token=token)
            unknown = await h.call(c, "ripple_forget", {"memory_id": "nope"}, token=token)
        return theirs, foreign, unknown

    theirs, foreign, unknown = asyncio.run(run())
    assert error(foreign)["error"] == "not_found"
    assert error(unknown)["error"] == "not_found"
    assert [m.id for m in h.store.all_memories()] == [theirs.id]
    assert h.store.forget_events() == []
