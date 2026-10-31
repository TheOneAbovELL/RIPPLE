"""IntentVerdict ties its payload to the intent (I4): the Router retries a half-formed
verdict instead of the agent guessing. Exercised through the agent where it matters."""

import asyncio

import pytest
from pydantic import ValidationError

from ripple.core.models import Status
from ripple.llm.schemas.conversation import IntentVerdict
from tests.agents.wiring import conversation_agent, intent, seed
from tests.builders import USER, derived
from tests.fakes.clock import FakeClock
from tests.fakes.llm import FakeLLM
from tests.fakes.store import InMemoryStore

CGPA = {"subject": "student", "attribute": "cgpa", "value": 7.8}


@pytest.mark.parametrize(
    "payload",
    [
        {"intent": "ask", "statement": "CGPA is 7.8"},
        {"intent": "ask", "structured": CGPA},
        {
            "intent": "answer_question",
            "memory_id": "m",
            "answer": "still_holds",
            "structured": CGPA,
        },
        {"intent": "answer_question", "memory_id": "m", "answer": "corrected"},
        {"intent": "tell", "statement": "x", "memory_id": "m"},
    ],
)
def test_intent_verdict_rejects_payload_that_does_not_match_the_intent(payload):
    with pytest.raises(ValidationError):
        IntentVerdict.model_validate({"reason": "r", **payload})


def test_intent_verdict_accepts_structured_on_a_corrected_answer():
    verdict = IntentVerdict.model_validate(
        {
            "intent": "answer_question",
            "reason": "r",
            "memory_id": "m",
            "answer": "corrected",
            "correction": "CGPA is 7.8",
            "structured": CGPA,
        }
    )
    assert verdict.structured is not None and verdict.structured.value == 7.8


def test_conversation_retries_an_answer_question_without_its_answer_kind():
    store, clock = InMemoryStore(), FakeClock()
    pending = derived("eligible for Acme", status=Status.PENDING_USER)
    asyncio.run(seed(store, pending))
    # First reply lacks the answer kind; the Router shows the error and the second is valid.
    llm = FakeLLM(
        f'{{"intent": "answer_question", "reason": "x", "memory_id": "{pending.id}"}}',
        intent("answer_question", memory_id=pending.id, answer="still_holds"),
    )
    agent = conversation_agent(store, clock, llm)

    reply = asyncio.run(agent.turn(USER, "yes"))

    assert reply.text.startswith("Thanks, kept")
    assert "answer_question needs memory_id and answer" in llm.calls[1].messages[-1].content
