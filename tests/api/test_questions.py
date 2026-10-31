"""The ask-user queue and the three answers (FR-7)."""

import asyncio

from ripple.core.models import Status, TriggerKind
from tests.api.harness import Harness, body
from tests.builders import derived, fact, link
from tests.fakes.resolver import ScriptedResolver, ask


def _with_a_question():
    """A ripple whose resolver asks about the belief, parking the memory below it.

    The engine replays the same wave on every run; after the ask, `belief` is
    PENDING_USER or RETIRED, which the runner skips, so later answers ripple nothing."""
    cgpa = fact("student", "cgpa", 7.6)
    belief = derived("not eligible for Acme")
    below = derived("skip Acme this week")
    h = Harness.build(
        waves=[[belief.id]],
        resolver=ScriptedResolver(
            {belief.id: ask("Is the Acme cutoff still 7.8?", reason="cutoff may have moved")}
        ),
    )

    async def run():
        user, headers = await h.user()
        owned = [m.model_copy(update={"user_id": user.id}) for m in (cgpa, belief, below)]
        await h.seed(*owned, link(cgpa, belief), link(belief, below))
        async with h.client() as c:
            await c.post(
                f"/memories/{cgpa.id}/edit",
                json={
                    "content": "CGPA is 7.9",
                    "structured": {"subject": "student", "attribute": "cgpa", "value": 7.9},
                },
                headers=headers,
            )
        return headers, belief, below

    headers, belief, below = asyncio.run(run())
    return h, headers, belief, below


def test_questions_list_pending_memories_with_the_ask_question_and_reason():
    h, headers, belief, below = _with_a_question()

    async def run():
        async with h.client() as c:
            return await c.get("/questions", headers=headers)

    response = asyncio.run(run())
    questions = body(response)["questions"]
    assert [q["memory"]["id"] for q in questions] == [belief.id]
    assert questions[0]["question"] == "Is the Acme cutoff still 7.8?"
    assert questions[0]["reason"] == "cutoff may have moved"
    assert questions[0]["event_id"] is not None
    assert asyncio.run(h.store.get_memory(below.id)).status is Status.SUSPECT


def test_still_holds_restores_the_memory_and_what_it_parked():
    h, headers, belief, below = _with_a_question()

    async def run():
        async with h.client() as c:
            answered = await c.post(
                f"/questions/{belief.id}/answer", json={"answer": "still_holds"}, headers=headers
            )
            questions = await c.get("/questions", headers=headers)
        return answered, questions

    answered, questions = asyncio.run(run())
    assert answered.status_code == 200, answered.text
    assert body(answered)["memory"]["status"] == "VALID"
    assert body(answered)["event"]["trigger_kind"] == TriggerKind.USER_ANSWER.value
    assert body(questions)["questions"] == []
    assert asyncio.run(h.store.get_memory(below.id)).status is Status.VALID


def test_no_longer_holds_retires_the_memory():
    h, headers, belief, _ = _with_a_question()

    async def run():
        async with h.client() as c:
            answered = await c.post(
                f"/questions/{belief.id}/answer",
                json={"answer": "no_longer_holds"},
                headers=headers,
            )
            gone = await c.get(f"/memories/{belief.id}", headers=headers)
        return answered, gone

    answered, gone = asyncio.run(run())
    out = body(answered)
    assert (out["memory_id"], out["status"], out["memory"]) == (belief.id, "RETIRED", None)
    assert gone.status_code == 404


def test_correction_writes_a_new_version():
    h, headers, belief, _ = _with_a_question()

    async def run():
        async with h.client() as c:
            missing = await c.post(
                f"/questions/{belief.id}/answer", json={"answer": "correction"}, headers=headers
            )
            answered = await c.post(
                f"/questions/{belief.id}/answer",
                json={"answer": "correction", "content": "eligible for Acme (cutoff 7.5)"},
                headers=headers,
            )
        return missing, answered

    missing, answered = asyncio.run(run())
    assert missing.status_code == 422
    out = body(answered)["memory"]
    assert (out["version"], out["supersedes_id"], out["status"]) == (2, belief.id, "VALID")
    assert out["content"] == "eligible for Acme (cutoff 7.5)"


def test_answering_a_memory_without_a_question_is_a_conflict():
    h = Harness.build()

    async def run():
        user, headers = await h.user()
        plain = fact("student", "cgpa", 7.6, user_id=user.id)
        await h.seed(plain)
        async with h.client() as c:
            return await c.post(
                f"/questions/{plain.id}/answer", json={"answer": "still_holds"}, headers=headers
            )

    response = asyncio.run(run())
    assert response.status_code == 409
    assert body(response)["error"] == "NotPendingError"
