"""ripple_search: visible memories with flags, scores and evidence (I1 at the boundary)."""

import asyncio

from ripple.core.models import Status
from tests.builders import memory
from tests.mcp_server.harness import McpHarness, error, out


def test_search_returns_visible_memories_with_flags_scores_and_evidence():
    h = McpHarness.build()

    async def run():
        user, token = await h.user()
        other, _ = await h.user("Bina")
        valid = memory(content="knows python well", user_id=user.id, source_ref="resume.pdf#1-9")
        suspect = memory(content="python eligibility", status=Status.SUSPECT, user_id=user.id)
        theirs = memory(content="python too", user_id=other.id)
        await h.seed(valid, suspect, theirs)
        async with h.client() as c:
            plain = await h.call(c, "ripple_search", {"query": "python"}, token=token)
            flagged = await h.call(
                c, "ripple_search", {"query": "python", "include_flagged": True}, token=token
            )
            one = await h.call(
                c,
                "ripple_search",
                {"query": "python", "include_flagged": True, "k": 1},
                token=token,
            )
        return valid, suspect, plain, flagged, one

    valid, suspect, plain, flagged, one = asyncio.run(run())
    hits = out(plain)["results"]
    assert [r["memory"]["id"] for r in hits] == [valid.id]
    assert hits[0]["flagged"] is False
    assert hits[0]["score"] > 0
    assert hits[0]["via"] == "lexical"
    assert hits[0]["evidence"] == ["resume.pdf#1-9"]
    by_id = {r["memory"]["id"]: r["flagged"] for r in out(flagged)["results"]}
    assert by_id == {valid.id: False, suspect.id: True}
    assert len(out(one)["results"]) == 1


def test_search_rejects_an_empty_query_and_an_out_of_range_k():
    h = McpHarness.build()

    async def run():
        _, token = await h.user()
        async with h.client() as c:
            blank = await h.call(c, "ripple_search", {"query": "   "}, token=token)
            zero = await h.call(c, "ripple_search", {"query": "x", "k": 0}, token=token)
            huge = await h.call(c, "ripple_search", {"query": "x", "k": 51}, token=token)
        return blank, zero, huge

    for result in asyncio.run(run()):
        assert error(result)["error"] == "invalid_arguments"
