"""I4: LLM output is validated before use; invalid output is retried or rejected, never
partially applied. Exercised through the runner with the real LLMResolver and FakeLLM."""

import asyncio

import pytest

from ripple.core.errors import LLMOutputInvalidError
from ripple.core.models import Status, TriggerKind
from ripple.core.ripple import RippleRunner
from ripple.core.writes import update_memory
from ripple.llm.config import ModelSpec, RouterConfig
from ripple.llm.resolver import LLMResolver
from ripple.llm.router import Router
from tests.builders import derived, fact, link
from tests.fakes.clock import FakeClock
from tests.fakes.engine import ScriptedEngine
from tests.fakes.llm import FakeLLM
from tests.fakes.store import InMemoryStore


def test_invariant_I4_invalid_llm_output_is_never_applied():
    store, clock = InMemoryStore(), FakeClock()
    cgpa = fact("student", "cgpa", 7.6)
    eligibility = derived("not eligible")

    async def write():
        async with store.transaction() as tx:
            await tx.add_memory(cgpa)
            await tx.add_memory(eligibility)
            await tx.add_link(link(cgpa, eligibility))

    asyncio.run(write())
    _, event = asyncio.run(
        update_memory(
            store,
            clock,
            cgpa.id,
            content="CGPA is 7.9",
            structured=None,
            valid_to=None,
            created_by="user",
            kind=TriggerKind.USER_EDIT,
        )
    )
    # Three replies, none valid: a half-formed update, prose, and a wrong enum.
    llm = FakeLLM(
        '{"action": "update", "reason": "changed"}',
        "I think it should be updated to eligible.",
        '{"action": "promote", "reason": "x"}',
    )
    config = RouterConfig(
        tasks={"resolver": [ModelSpec(provider="fake", model="f")]}, max_retries=2
    )
    resolver = LLMResolver(Router(config, {"fake": llm}))

    class Factory(ScriptedEngine):
        def __init__(self, max_depth: int = 8) -> None:
            super().__init__([eligibility.id], max_depth=max_depth)

    runner = RippleRunner(store, resolver, clock, engine_factory=Factory)  # type: ignore[arg-type]
    with pytest.raises(LLMOutputInvalidError):
        asyncio.run(runner.run(event))

    assert len(llm.calls) == 3
    # Nothing was applied: no decision, no new version, the belief is still SUSPECT and
    # the event is open for the sweep to resume once the model behaves.
    reopened = asyncio.run(store.get_change_event(event.id))
    assert reopened.decisions == [] and reopened.is_open
    assert asyncio.run(store.latest_version(eligibility.id)).id == eligibility.id
    assert asyncio.run(store.get_memory(eligibility.id)).status is Status.SUSPECT
