"""Named invariant tests for the agents (CLAUDE.md I4, I5, I6)."""

import ast
import asyncio
from pathlib import Path

import pytest

import ripple.agents
from ripple.agents.capabilities import Capability
from ripple.core.errors import LLMOutputInvalidError
from tests.agents.wiring import claims, conversation_agent, highlights, intent, seed, tailor_agent
from tests.builders import USER, fact, memory
from tests.fakes.clock import FakeClock
from tests.fakes.llm import FakeLLM
from tests.fakes.retriever import ScriptedRetriever, hit
from tests.fakes.store import InMemoryStore

AGENTS_DIR = Path(ripple.agents.__file__).parent

# An explicit allowlist: the stdlib modules the agents need, pydantic, LangGraph and
# ripple. Anything else (smtplib, socket, urllib, httpx, a browser driver) is a breach
# without anyone having to list it. langgraph.checkpoint.postgres does talk to the
# network, by design: it is the checkpoint database (ADR-0023), not an external site.
ALLOWED_TOP_LEVEL = {
    "collections",
    "contextlib",
    "dataclasses",
    "enum",
    "json",
    "logging",
    "re",
    "typing",
    "pydantic",
    "langgraph",
    "ripple",
}
# Delivery packages may reach users and external services; agents must not import them.
FORBIDDEN_RIPPLE = ("ripple.api", "ripple.mcp_server", "ripple.notify", "ripple.worker")
# A capability named like an outward action would fail even if someone added it to the enum.
FORBIDDEN_WORDS = ("submit", "browser", "http", "apply", "click", "navigate", "fetch", "send")


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def _forbidden(module: str) -> bool:
    top = module.split(".", 1)[0]
    return top not in ALLOWED_TOP_LEVEL or any(
        module == f or module.startswith(f + ".") for f in FORBIDDEN_RIPPLE
    )


# ---- I5 ----------------------------------------------------------------------------


def test_invariant_I5_tailor_cites_only_existing_memories():
    store = InMemoryStore()
    opening = memory(content="ML intern at Acme", kind="opening")
    real = fact("student", "project", "CNN for crop disease")
    someone_elses = fact("student", "project", "trading bot", user_id="someone-else")
    asyncio.run(seed(store, opening, real, someone_elses))
    llm = FakeLLM(
        highlights(
            (real.id, "real project", []),
            (someone_elses.id, "exists, but not this student's", []),
            ("invented-id", "never existed", []),
        )
    )

    result = asyncio.run(tailor_agent(store, llm).suggest(USER, opening.id))

    assert [s.memory_id for s in result.suggestions] == [real.id]
    assert result.dropped == 2
    assert {m.id for m in store.all_memories()} == {opening.id, real.id, someone_elses.id}


def test_invariant_I5_conversation_marks_unsupported_claims():
    """Design (ADR-0045): a claim with no retrieved evidence behind it is dropped from
    the reply and the reply discloses the count; it is never shown as fact. The name is
    the one the workstream brief fixed; the behaviour is drop-and-disclose."""
    store, clock = InMemoryStore(), FakeClock()
    cgpa = fact("student", "cgpa", 7.6)
    llm = FakeLLM(
        intent("ask"),
        claims(
            ("Your CGPA is 7.6.", [cgpa.id]),
            ("You have two years of experience at Google.", []),
            ("You won a hackathon.", ["not-retrieved"]),
        ),
    )
    agent = conversation_agent(store, clock, llm, ScriptedRetriever(hit(cgpa)))

    reply = asyncio.run(agent.turn(USER, "what do you know about me?"))

    assert "Google" not in reply.text and "hackathon" not in reply.text
    assert reply.text.splitlines() == [
        "Your CGPA is 7.6.",
        "I left out 2 statement(s) I could not support from your recorded memory.",
    ]
    assert reply.dropped_claims == 2
    assert [c.memory_id for c in reply.citations] == [cgpa.id]


# ---- I6 ----------------------------------------------------------------------------


def test_invariant_I6_agents_expose_no_submit_or_browser_tool():
    store, clock = InMemoryStore(), FakeClock()
    conversation = conversation_agent(store, clock, FakeLLM())
    tailor = tailor_agent(store, FakeLLM())

    for agent in (conversation, tailor):
        assert agent.capabilities <= set(Capability)
    for capability in Capability:
        assert not any(word in capability.value for word in FORBIDDEN_WORDS), capability
    # The graphs hold exactly the nodes the ADRs describe; no tool node exists.
    assert set(conversation.graph.get_graph().nodes) == {
        "__start__",
        "classify",
        "tell",
        "answer",
        "answer_question",
        "__end__",
    }
    assert set(tailor.graph.get_graph().nodes) == {"__start__", "gather", "suggest", "__end__"}
    # And nothing in the package can reach a browser, a socket or a delivery package.
    breaches = [
        f"{path.name} imports {name}"
        for path in sorted(AGENTS_DIR.rglob("*.py"))
        for name in sorted(_imports(path))
        if _forbidden(name)
    ]
    assert breaches == []


def test_invariant_I6_import_check_detects_a_breach():
    for module in ("httpx", "urllib.request", "smtplib", "socket", "ripple.notify.telegram"):
        assert _forbidden(module), module
    assert not _forbidden("ripple.core.intake") and not _forbidden("langgraph.graph")


# ---- I4 ----------------------------------------------------------------------------


def test_invariant_I4_agent_rejects_invalid_llm_output():
    store, clock = InMemoryStore(), FakeClock()
    cgpa = fact("student", "cgpa", 7.6)
    asyncio.run(seed(store, cgpa))
    before = (store.all_memories(), store.change_events())
    # Intent never valid: a tell without a statement, prose, an unknown intent.
    llm = FakeLLM(
        '{"intent": "tell", "reason": "x"}',
        "Sure! I think the student is telling us a fact.",
        '{"intent": "browse", "reason": "x"}',
    )
    agent = conversation_agent(store, clock, llm, ScriptedRetriever(hit(cgpa)))

    with pytest.raises(LLMOutputInvalidError):
        asyncio.run(agent.turn(USER, "my cgpa is 7.9"))

    assert (store.all_memories(), store.change_events()) == before
    assert len(llm.calls) == 3


def test_invariant_I4_conversation_rejects_invalid_answer_output():
    store, clock = InMemoryStore(), FakeClock()
    cgpa = fact("student", "cgpa", 7.6)
    asyncio.run(seed(store, cgpa))
    before = (store.all_memories(), store.change_events())
    llm = FakeLLM(intent("ask"), '{"answer": "free text"}', "[]", '{"claims": [{"text": ""}]}')
    agent = conversation_agent(store, clock, llm, ScriptedRetriever(hit(cgpa)))

    with pytest.raises(LLMOutputInvalidError):
        asyncio.run(agent.turn(USER, "what is my cgpa?"))

    assert (store.all_memories(), store.change_events()) == before


def test_invariant_I4_tailor_rejects_invalid_output():
    store = InMemoryStore()
    opening = memory(content="ML intern at Acme", kind="opening")
    asyncio.run(seed(store, opening, fact("student", "project", "CNN for crop disease")))
    llm = FakeLLM('{"highlights": "none"}', "no", '{"highlights": [{"reason": "r"}]}')

    with pytest.raises(LLMOutputInvalidError):
        asyncio.run(tailor_agent(store, llm).suggest(USER, opening.id))

    assert store.change_events() == []
