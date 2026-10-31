"""Bearer identity over MCP (ADR-0081): no token, wrong token, revoked token, cross-user."""

import asyncio

import pytest
from mcp.shared.exceptions import MCPError

from tests.builders import fact
from tests.mcp_server.harness import McpHarness, error, out


def test_tool_calls_without_a_resolvable_token_are_refused():
    h = McpHarness.build()

    async def run():
        async with h.client() as c:
            listing = await c.list_tools()  # discovery needs no identity
            with pytest.raises(MCPError) as missing:
                await h.call(c, "ripple_questions", token=None)
            with pytest.raises(MCPError) as wrong:
                await h.call(c, "ripple_questions", token="not-a-token")
        return listing, missing.value, wrong.value

    listing, missing, wrong = asyncio.run(run())
    assert len(listing.tools) == 7
    assert "unauthorized" in missing.message
    assert "unauthorized" in wrong.message
    assert "not-a-token" not in wrong.message


def test_a_revoked_token_stops_working_on_the_next_call():
    h = McpHarness.build()

    async def run():
        _, token = await h.user()
        async with h.client() as c:
            before = await h.call(c, "ripple_questions", token=token)
            h.user_store.tokens.clear()  # ADR-0040 revocation: the row is deleted
            with pytest.raises(MCPError) as after:
                await h.call(c, "ripple_questions", token=token)
        return before, after.value

    before, after = asyncio.run(run())
    assert out(before)["questions"] == []
    assert "unauthorized" in after.message


def test_users_cannot_see_or_touch_each_others_memories():
    h = McpHarness.build()

    async def run():
        asha, asha_token = await h.user("Asha")
        _, bina_token = await h.user("Bina")
        theirs = fact("student", "cgpa", 7.6, user_id=asha.id, content="cgpa python")
        await h.seed(theirs)
        by_id = {"memory_id": theirs.id}
        async with h.client() as c:
            own = await h.call(c, "ripple_search", {"query": "python"}, token=asha_token)
            other = await h.call(c, "ripple_search", {"query": "python"}, token=bina_token)
            explain = await h.call(c, "ripple_explain", by_id, token=bina_token)
            update = await h.call(
                c, "ripple_update", {**by_id, "content": "mine now"}, token=bina_token
            )
            answer = await h.call(
                c, "ripple_answer", {**by_id, "reply": "still_holds"}, token=bina_token
            )
            forget = await h.call(c, "ripple_forget", by_id, token=bina_token)
        return theirs, own, other, explain, update, answer, forget

    theirs, own, other, explain, update, answer, forget = asyncio.run(run())
    assert [r["memory"]["id"] for r in out(own)["results"]] == [theirs.id]
    assert out(other)["results"] == []
    for result in (explain, update, answer, forget):
        assert error(result)["error"] == "not_found"
    assert asyncio.run(h.store.get_memory(theirs.id)).content == "cgpa python"
    assert h.store.change_events() == [] and h.store.forget_events() == []
