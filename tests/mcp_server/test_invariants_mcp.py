"""Named invariant tests at the MCP boundary (CLAUDE.md I1, I4, I6, I7)."""

import asyncio

from ripple.core.models import Status
from ripple.core.retrieval_contract import RetrievalPath, RetrievedMemory
from ripple.llm.change_detector import LLMChangeDetector
from ripple.llm.config import ModelSpec, RouterConfig
from ripple.llm.router import Router
from ripple.mcp_server.server import SPECS, TOOL_NAMES
from tests.builders import derived, fact, link, memory
from tests.fakes.clock import FakeClock
from tests.fakes.llm import FakeLLM
from tests.fakes.store import InMemoryStore
from tests.mcp_server.harness import McpHarness, error, out


class LeakyRetriever:
    """A retriever that ignores the C2 contract and returns every row in the store,
    RETIRED ones included and the flag always off: the boundary must still hold."""

    def __init__(self) -> None:
        self.store: InMemoryStore | None = None

    async def search(
        self,
        user_id: str,
        query: str,
        *,
        k: int = 10,
        include_flagged: bool = False,
        expand_graph: bool = True,
    ) -> list[RetrievedMemory]:
        assert self.store is not None
        return [
            RetrievedMemory(memory=m, score=1.0, flagged=False, via=RetrievalPath.LEXICAL)
            for m in self.store.all_memories()
        ][:k]


def _rows(user_id: str):
    return [
        memory(content="python valid", user_id=user_id),
        memory(content="python suspect", status=Status.SUSPECT, user_id=user_id),
        memory(content="python pending", status=Status.PENDING_USER, user_id=user_id),
        memory(content="python retired", status=Status.RETIRED, user_id=user_id),
    ]


def test_invariant_I1_mcp_search_never_returns_retired():
    """With the real retriever and with one that leaks: RETIRED never appears, flagged
    rows appear only on request and always carry the flag."""
    leaky = LeakyRetriever()
    for h in (McpHarness.build(), McpHarness.build(retriever=leaky)):
        leaky.store = h.store

        async def run(h: McpHarness = h):
            user, token = await h.user()
            other, _ = await h.user("Bina")
            await h.seed(*_rows(user.id), memory(content="python theirs", user_id=other.id))
            async with h.client() as c:
                plain = await h.call(c, "ripple_search", {"query": "python"}, token=token)
                flagged = await h.call(
                    c, "ripple_search", {"query": "python", "include_flagged": True}, token=token
                )
            return plain, flagged

        plain, flagged = asyncio.run(run())
        assert {r["memory"]["status"] for r in out(plain)["results"]} == {"VALID"}
        statuses = {r["memory"]["status"]: r["flagged"] for r in out(flagged)["results"]}
        assert statuses == {"VALID": False, "SUSPECT": True, "PENDING_USER": True}
        assert all(r["memory"]["content"] != "python theirs" for r in out(flagged)["results"])


def test_invariant_I7_mcp_forget_cascades_and_logs():
    h = McpHarness.build()

    async def run():
        user, token = await h.user()
        v1 = fact("student", "cgpa", 7.6, user_id=user.id, status=Status.RETIRED)
        v2 = fact("student", "cgpa", 8.0, user_id=user.id, version=2, supersedes_id=v1.id)
        child = derived("eligible", user_id=user.id)
        grandchild = derived("apply to Acme", user_id=user.id)
        bystander = memory(content="unrelated", user_id=user.id)
        await h.seed(
            v1,
            v2,
            child,
            grandchild,
            bystander,
            link(v1, child),
            link(v2, child),
            link(child, grandchild),
        )
        async with h.client() as c:
            result = await h.call(c, "ripple_forget", {"memory_id": v2.id}, token=token)
        return v1, v2, child, grandchild, bystander, result

    v1, v2, child, grandchild, bystander, result = asyncio.run(run())
    body = out(result)
    assert body["deleted_ids"] == sorted([v1.id, v2.id, child.id, grandchild.id])
    assert [m.id for m in h.store.all_memories()] == [bystander.id]
    assert h.store.all_links() == []
    [event] = h.store.forget_events()
    assert event.root_memory_id == v2.id and event.deleted_ids == body["deleted_ids"]


def test_invariant_I4_mcp_save_with_invalid_llm_output_writes_nothing():
    """The change detector's model never returns valid JSON; the save fails whole."""
    llm = FakeLLM("not json", "still not json", "nope")
    config = RouterConfig(
        tasks={"change_detector": [ModelSpec(provider="fake", model="f")]}, max_retries=2
    )
    h = McpHarness.build(detector=LLMChangeDetector(Router(config, {"fake": llm}), FakeClock()))

    async def run():
        _, token = await h.user()
        async with h.client() as c:
            return await h.call(c, "ripple_save", {"content": "prose, no structure"}, token=token)

    failure = error(asyncio.run(run()))
    assert failure["error"] == "llm_output_invalid"
    assert failure["open_change_event_ids"] == []
    assert h.store.all_memories() == [] and h.store.change_events() == []
    assert len(llm.calls) == 3


# Every tool the server exposes. A new tool must be added here on purpose, which is the
# moment to ask whether it acts on an external site for the user (I6).
EXPECTED_TOOLS = (
    "ripple_search",
    "ripple_save",
    "ripple_update",
    "ripple_forget",
    "ripple_explain",
    "ripple_questions",
    "ripple_answer",
)
FORBIDDEN_TOOL_WORDS = ("apply", "submit", "application", "send", "portal", "browse")


def test_invariant_I6_mcp_exposes_no_apply_or_submit_tool():
    """From the published listing, what a client model would see: the exact tool set,
    and no name or description that offers to act on an external site."""
    h = McpHarness.build()

    async def run():
        async with h.client() as c:
            return (await c.list_tools()).tools

    listed = asyncio.run(run())
    assert tuple(t.name for t in listed) == EXPECTED_TOOLS == TOOL_NAMES
    offending = [t.name for t in listed if any(w in t.name for w in FORBIDDEN_TOOL_WORDS)]
    assert offending == []
    # Descriptions are read by the model too; the only acceptable mention of acting for
    # the user is the instruction not to.
    for spec in SPECS:
        words = spec.description.lower()
        assert "apply" not in words and "submit" not in words, spec.name
