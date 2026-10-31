"""Conversation agent: intents, writes through Intake, evidence-only answers, checkpoints."""

import asyncio
import json
from collections.abc import Iterable
from datetime import timedelta

from ripple.agents.checkpoints import memory_saver
from ripple.agents.conversation import (
    NOTHING_KNOWN,
    NOTHING_SUPPORTED,
    RECENT_TURNS,
    UNCLEAR_QUESTION,
    ConversationAgent,
)
from ripple.core.change_detection import ChangeClassification, ChangeKind
from ripple.core.models import Memory, Status, TriggerKind
from tests.agents.wiring import ScriptedDetector, claims, conversation_agent, intent, seed, tell
from tests.builders import USER, derived, fact, link
from tests.fakes.clock import DEFAULT_START, FakeClock
from tests.fakes.llm import FakeLLM
from tests.fakes.resolver import ScriptedResolver, ask, retire
from tests.fakes.retriever import ScriptedRetriever, hit
from tests.fakes.store import InMemoryStore

CGPA = {"subject": "student", "attribute": "cgpa", "value": 7.6}


def _turn(agent: ConversationAgent, message: str, *, message_id: str | None = "msg-7"):
    return asyncio.run(agent.turn(USER, message, message_id=message_id))


# ---- tell ----------------------------------------------------------------------


def test_tell_records_fact_through_intake_and_replies_with_it():
    store, clock = InMemoryStore(), FakeClock()
    llm = FakeLLM(tell("CGPA is 7.6", CGPA))
    agent = conversation_agent(store, clock, llm)

    reply = _turn(agent, "my cgpa is 7.6")

    assert reply.intent == "tell"
    assert reply.text == "Recorded: CGPA is 7.6."
    [memory] = store.all_memories()
    assert reply.recorded_memory_id == memory.id
    assert memory.structured is not None and memory.structured.value == 7.6
    assert memory.source_ref == "msg-7" and memory.created_by == "user"
    [event] = store.change_events()
    # A conversation statement is an ordinary ripple, not an inspector edit.
    assert event.trigger_kind is TriggerKind.RIPPLE and event.completed_at is not None


def test_tell_of_a_recorded_value_writes_nothing_and_says_so():
    store, clock = InMemoryStore(), FakeClock()
    cgpa = fact("student", "cgpa", 7.6)
    asyncio.run(seed(store, cgpa))
    agent = conversation_agent(store, clock, FakeLLM(tell("CGPA is 7.6", CGPA)))

    reply = _turn(agent, "cgpa 7.6")

    assert reply.text.startswith("That is already recorded")
    assert reply.recorded_memory_id == cgpa.id
    assert store.change_events() == []


def test_tell_with_a_number_the_student_did_not_write_records_the_message():
    store, clock = InMemoryStore(), FakeClock()
    # The model "helpfully" turns a vague message into a number (I5 exposure).
    llm = FakeLLM(tell("CGPA is 8.0", {**CGPA, "value": 8.0}))
    agent = conversation_agent(store, clock, llm)

    reply = _turn(agent, "my cgpa went up this semester")

    [memory] = store.all_memories()
    assert memory.content == "my cgpa went up this semester"
    assert memory.structured is None
    assert "8.0" not in reply.text


def test_tell_keeps_a_restatement_whose_numbers_the_student_wrote():
    store, clock = InMemoryStore(), FakeClock()
    llm = FakeLLM(tell("CGPA is 7.90", {**CGPA, "value": 7.9}))
    agent = conversation_agent(store, clock, llm)

    _turn(agent, "cgpa is now 7.9!")

    [memory] = store.all_memories()
    assert memory.content == "CGPA is 7.90"
    assert memory.structured is not None and memory.structured.value == 7.9


def test_tell_of_a_temporary_fact_says_until_when():
    store, clock = InMemoryStore(), FakeClock()
    until = DEFAULT_START + timedelta(days=30)
    detector = ScriptedDetector(
        ChangeClassification(kind=ChangeKind.TEMPORARY, reason="exams", valid_to=until)
    )
    llm = FakeLLM(tell("busy with exams this month"))
    agent = conversation_agent(store, clock, llm, detector=detector)

    reply = _turn(agent, "busy with exams this month")

    assert reply.text == f"Recorded until {until.date().isoformat()}: busy with exams this month."
    [memory] = store.all_memories()
    assert memory.valid_to == until


def test_tell_that_parks_a_belief_surfaces_the_pending_question():
    store, clock = InMemoryStore(), FakeClock()
    cgpa = fact("student", "cgpa", 7.6)
    eligibility = derived("not eligible for Acme (cutoff 7.8)")
    asyncio.run(seed(store, cgpa, eligibility, links=[link(cgpa, eligibility)]))
    resolver = ScriptedResolver(
        {eligibility.id: ask("Still not eligible?", reason="cutoff may differ")}
    )
    llm = FakeLLM(tell("CGPA is 7.9", {**CGPA, "value": 7.9}))
    agent = conversation_agent(store, clock, llm, waves=[[eligibility.id]], resolver=resolver)

    reply = _turn(agent, "cgpa went up to 7.9")

    assert reply.text.startswith("Updated: CGPA is 7.9")
    [question] = reply.questions
    assert question.memory_id == eligibility.id
    assert question.reason == "cutoff may differ"
    assert "Does this still hold? not eligible for Acme" in reply.text
    assert asyncio.run(store.get_memory(eligibility.id)).status is Status.PENDING_USER


# ---- ask / plan ------------------------------------------------------------------


def test_ask_answers_from_retrieved_evidence_with_citations():
    store, clock = InMemoryStore(), FakeClock()
    cgpa = fact("student", "cgpa", 7.6, source_ref="msg-1")
    retriever = ScriptedRetriever(hit(cgpa))
    llm = FakeLLM(intent("ask"), claims(("Your CGPA is 7.6.", [cgpa.id])))
    agent = conversation_agent(store, clock, llm, retriever)

    reply = _turn(agent, "what is my cgpa?")

    assert reply.intent == "ask"
    assert reply.text == "Your CGPA is 7.6."
    [citation] = reply.citations
    assert citation.memory_id == cgpa.id and citation.source_refs == ("msg-1",)
    assert citation.flagged is False and reply.dropped_claims == 0
    [call] = retriever.calls
    assert call.user_id == USER and call.include_flagged and call.expand_graph
    # Prompt in the system message, evidence in the user message only (prompts.md).
    system, user = llm.calls[1].messages
    assert system.role == "system" and "ONLY the EVIDENCE" in system.content
    assert cgpa.content in user.content and cgpa.content not in system.content
    assert "MODE: ask" in user.content


def test_ask_renders_flagged_evidence_as_unconfirmed():
    store, clock = InMemoryStore(), FakeClock()
    eligibility = derived("eligible for Acme", status=Status.SUSPECT)
    llm = FakeLLM(intent("ask"), claims(("You are eligible for Acme.", [eligibility.id])))
    agent = conversation_agent(store, clock, llm, ScriptedRetriever(hit(eligibility)))

    reply = _turn(agent, "am I eligible for Acme?")

    assert reply.text == "You are eligible for Acme. (unconfirmed)"
    assert reply.citations[0].flagged is True
    # The model was told it is unconfirmed too.
    evidence = json.loads(llm.calls[1].messages[1].content.split("```json\n")[1].split("\n```")[0])
    assert evidence[0]["flagged"] is True


def test_ask_where_every_claim_is_unsupported_says_it_cannot_answer():
    store, clock = InMemoryStore(), FakeClock()
    cgpa = fact("student", "cgpa", 7.6)
    llm = FakeLLM(intent("ask"), claims(("You interned at Google.", [])))
    agent = conversation_agent(store, clock, llm, ScriptedRetriever(hit(cgpa)))

    reply = _turn(agent, "where did I intern?")

    assert reply.text.splitlines() == [
        NOTHING_SUPPORTED,
        "I left out 1 statement(s) I could not support from your recorded memory.",
    ]
    assert reply.citations == ()


def test_ask_with_no_hits_answers_honestly_without_calling_the_model():
    store, clock = InMemoryStore(), FakeClock()
    llm = FakeLLM(intent("ask"))
    agent = conversation_agent(store, clock, llm, ScriptedRetriever())

    reply = _turn(agent, "what openings fit me?")

    assert reply.text == NOTHING_KNOWN
    assert reply.citations == () and reply.dropped_claims == 0
    assert len(llm.calls) == 1  # intent only; no answer call without evidence


def test_plan_uses_the_answer_path_in_plan_mode():
    store, clock = InMemoryStore(), FakeClock()
    deadline = derived("Acme deadline is 2026-10-30")
    llm = FakeLLM(intent("plan"), claims(("Apply to Acme before 2026-10-30.", [deadline.id])))
    agent = conversation_agent(store, clock, llm, ScriptedRetriever(hit(deadline)))

    reply = _turn(agent, "what should I do this week?")

    assert reply.intent == "plan"
    assert "MODE: plan" in llm.calls[1].messages[1].content
    assert reply.text == "Apply to Acme before 2026-10-30."


# ---- answer_question ----------------------------------------------------------------


def test_answer_question_still_holds_restores_the_memory():
    store, clock = InMemoryStore(), FakeClock()
    pending = derived("eligible for Acme", status=Status.PENDING_USER)
    asyncio.run(seed(store, pending))
    llm = FakeLLM(intent("answer_question", memory_id=pending.id, answer="still_holds"))
    agent = conversation_agent(store, clock, llm)

    reply = _turn(agent, "yes that still holds")

    assert reply.intent == "answer_question"
    assert reply.text == "Thanks, kept: eligible for Acme."
    assert asyncio.run(store.get_memory(pending.id)).status is Status.VALID
    [event] = store.change_events()
    assert event.trigger_kind is TriggerKind.USER_ANSWER
    # The classifier was shown the pending question so it could name its id.
    assert pending.id in llm.calls[0].messages[1].content


def test_answer_question_no_longer_holds_retires_and_ripples():
    store, clock = InMemoryStore(), FakeClock()
    pending = derived("available for internships in December", status=Status.PENDING_USER)
    reminder = derived("apply to Acme before the December break")
    asyncio.run(seed(store, pending, reminder, links=[link(pending, reminder)]))
    llm = FakeLLM(intent("answer_question", memory_id=pending.id, answer="no_longer_holds"))
    resolver = ScriptedResolver({reminder.id: retire()})
    agent = conversation_agent(store, clock, llm, waves=[[reminder.id]], resolver=resolver)

    reply = _turn(agent, "no, I am not available then")

    assert reply.text == "Retired: available for internships in December."
    assert asyncio.run(store.get_memory(pending.id)).status is Status.RETIRED
    assert asyncio.run(store.get_memory(reminder.id)).status is Status.RETIRED
    [event] = store.change_events()
    assert event.trigger_kind is TriggerKind.USER_ANSWER and event.completed_at is not None


def test_answer_question_corrected_writes_a_new_version_and_ripples():
    store, clock = InMemoryStore(), FakeClock()
    pending = derived("eligible for Acme", status=Status.PENDING_USER)
    asyncio.run(seed(store, pending))
    correction = "eligible for Acme only for the internship track"
    llm = FakeLLM(
        intent("answer_question", memory_id=pending.id, answer="corrected", correction=correction)
    )
    agent = conversation_agent(store, clock, llm)

    reply = _turn(agent, "eligible for Acme only for the internship track actually")

    latest = asyncio.run(store.latest_version(pending.id))
    assert latest.version == 2 and latest.content == correction
    assert reply.recorded_memory_id == latest.id
    assert asyncio.run(store.get_memory(pending.id)).status is Status.RETIRED


def test_answer_question_corrected_updates_the_structured_value():
    store, clock = InMemoryStore(), FakeClock()
    pending = fact("student", "cgpa", 7.6, status=Status.PENDING_USER)
    asyncio.run(seed(store, pending))
    llm = FakeLLM(
        intent(
            "answer_question",
            memory_id=pending.id,
            answer="corrected",
            correction="CGPA is 7.8",
            structured={**CGPA, "value": 7.8},
        )
    )
    agent = conversation_agent(store, clock, llm)

    _turn(agent, "no, it is 7.8 now")

    latest = asyncio.run(store.latest_version(pending.id))
    assert latest.content == "CGPA is 7.8"
    assert latest.structured is not None and latest.structured.value == 7.8


def test_answer_question_for_an_unknown_question_writes_nothing():
    store, clock = InMemoryStore(), FakeClock()
    other = derived("eligible for Acme", status=Status.PENDING_USER, user_id="someone-else")
    asyncio.run(seed(store, other))
    llm = FakeLLM(intent("answer_question", memory_id=other.id, answer="no_longer_holds"))
    agent = conversation_agent(store, clock, llm)

    reply = _turn(agent, "no, that is wrong")

    assert reply.text == UNCLEAR_QUESTION
    assert asyncio.run(store.get_memory(other.id)).status is Status.PENDING_USER
    assert store.change_events() == []


class StalePendingStore(InMemoryStore):
    """Lists a memory as pending after it was answered elsewhere: the read/write race."""

    async def memories_for_user(self, user_id: str, statuses: Iterable[Status] | None = None):
        found = await super().memories_for_user(user_id, None)
        if statuses is not None and Status.PENDING_USER in set(statuses):
            return [m.model_copy(update={"status": Status.PENDING_USER}) for m in found]
        return await super().memories_for_user(user_id, statuses)


def test_answer_question_answered_meanwhile_replies_instead_of_raising():
    store, clock = StalePendingStore(), FakeClock()
    answered: Memory = derived("eligible for Acme")  # VALID in the store already
    asyncio.run(seed(store, answered))
    llm = FakeLLM(intent("answer_question", memory_id=answered.id, answer="still_holds"))
    agent = conversation_agent(store, clock, llm)

    reply = _turn(agent, "yes")

    assert reply.text == UNCLEAR_QUESTION
    assert store.change_events() == []


# ---- checkpoints ----------------------------------------------------------------


def test_checkpoint_keeps_turn_history_across_two_turns():
    store, clock = InMemoryStore(), FakeClock()
    saver = memory_saver()
    llm = FakeLLM(tell("CGPA is 7.6", CGPA), intent("ask"))
    agent = conversation_agent(store, clock, llm, ScriptedRetriever(), checkpointer=saver)

    first = _turn(agent, "my cgpa is 7.6")
    _turn(agent, "what do you know about me?")

    # The second classification saw the first turn.
    second_intent_message = llm.calls[1].messages[1].content
    assert "student: my cgpa is 7.6" in second_intent_message
    assert f"assistant: {first.text}" in second_intent_message
    config = ConversationAgent.thread_config(USER)
    state = asyncio.run(agent.graph.aget_state(config))
    assert [t.message for t in state.values["turns"]] == [
        "my cgpa is 7.6",
        "what do you know about me?",
    ]

    # A fresh agent on the same saver resumes the same thread.
    again = conversation_agent(store, clock, FakeLLM(), ScriptedRetriever(), checkpointer=saver)
    resumed = asyncio.run(again.graph.aget_state(config))
    assert len(resumed.values["turns"]) == 2


def test_checkpoint_keeps_only_the_recent_turns():
    store, clock = InMemoryStore(), FakeClock()
    messages = [f"question {n}" for n in range(RECENT_TURNS + 1)]
    llm = FakeLLM(*(intent("ask") for _ in messages))
    agent = conversation_agent(store, clock, llm, ScriptedRetriever())

    for message in messages:
        _turn(agent, message)

    state = asyncio.run(agent.graph.aget_state(ConversationAgent.thread_config(USER)))
    assert [t.message for t in state.values["turns"]] == messages[1:]


def test_threads_are_per_user():
    store, clock = InMemoryStore(), FakeClock()
    saver = memory_saver()
    llm = FakeLLM(intent("ask"), intent("ask"))
    agent = conversation_agent(store, clock, llm, ScriptedRetriever(), checkpointer=saver)

    asyncio.run(agent.turn("student-a", "hello"))
    asyncio.run(agent.turn("student-b", "hi"))

    assert "student: hello" not in llm.calls[1].messages[1].content
    state_b = asyncio.run(agent.graph.aget_state(ConversationAgent.thread_config("student-b")))
    assert [t.message for t in state_b.values["turns"]] == ["hi"]
