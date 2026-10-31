import asyncio
import json

import pytest

from ripple.core.errors import LLMOutputInvalidError
from ripple.core.models import DecisionAction
from ripple.core.resolver import ResolutionContext
from ripple.llm.config import ModelSpec, RouterConfig
from ripple.llm.resolver import LLMResolver
from ripple.llm.router import Router
from tests.builders import derived, fact
from tests.fakes.llm import FakeLLM


def _resolver(llm: FakeLLM, max_retries: int = 2) -> LLMResolver:
    config = RouterConfig(
        tasks={"resolver": [ModelSpec(provider="fake", model="f")]}, max_retries=max_retries
    )
    return LLMResolver(Router(config, {"fake": llm}))


def _context():
    trigger = fact("student", "cgpa", 7.9, version=2, supersedes_id="old")
    belief = derived("not eligible for Acme (cutoff 7.8)")
    return ResolutionContext(trigger=trigger, memory=belief, parents=[trigger], wave=1)


def test_llm_resolver_returns_update_resolution():
    context = _context()
    llm = FakeLLM(
        json.dumps(
            {
                "action": "update",
                "reason": "7.9 clears the 7.8 cutoff",
                "new_content": "eligible for Acme",
                "evidence_refs": [context.parents[0].id, "not-shown"],
            }
        )
    )
    resolution = asyncio.run(_resolver(llm).resolve(context))
    assert resolution.action is DecisionAction.UPDATE
    assert resolution.new_content == "eligible for Acme"
    # Evidence outside what the model was shown is dropped (I2 refs must resolve).
    assert resolution.evidence_refs == (context.parents[0].id,)


def test_llm_resolver_returns_ask_with_question():
    llm = FakeLLM(
        json.dumps({"action": "ask", "reason": "cutoff unknown", "question": "Is the cutoff 7.8?"})
    )
    resolution = asyncio.run(_resolver(llm).resolve(_context()))
    assert resolution.action is DecisionAction.ASK and resolution.question == "Is the cutoff 7.8?"


def test_llm_resolver_retries_update_without_content_then_accepts():
    llm = FakeLLM(
        json.dumps({"action": "update", "reason": "changed"}),
        json.dumps({"action": "update", "reason": "changed", "new_content": "eligible"}),
    )
    resolution = asyncio.run(_resolver(llm).resolve(_context()))
    assert resolution.new_content == "eligible"
    assert len(llm.calls) == 2
    assert "new_content" in llm.calls[1].messages[-1].content


def test_llm_resolver_rejects_after_retry_budget():
    llm = FakeLLM("nonsense", "still nonsense")
    with pytest.raises(LLMOutputInvalidError):
        asyncio.run(_resolver(llm, max_retries=1).resolve(_context()))


def test_llm_resolver_puts_prompt_in_system_and_evidence_in_user_message():
    llm = FakeLLM(json.dumps({"action": "keep", "reason": "fine"}))
    context = _context()
    asyncio.run(_resolver(llm).resolve(context))
    [request] = llm.calls
    system, user = request.messages
    assert system.role == "system" and "Curator" in system.content
    assert context.memory.content in user.content and context.trigger.content in user.content
    assert context.memory.content not in system.content
