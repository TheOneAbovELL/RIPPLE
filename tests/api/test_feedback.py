"""POST /feedback and GET /feedback (ADR-0105).

`create_app` mounts the router with the rate-limit dependency and `Services` carries the
in-memory store (checkpoint C4 applied the ws-16 contract requests).
"""

import asyncio
from datetime import timedelta
from typing import Any

import pytest

from ripple.core.models import ChangeEvent, DecisionAction, Status
from ripple.domains.jobs.vocabulary import Kind
from ripple.storage.feedback import FeedbackKind, InMemoryFeedbackStore
from tests.api.harness import Harness, body
from tests.builders import change_event, decision, fact, memory

OPENING_CONTENT = "SDE intern at Acme, CGPA >= 7.5, apply by 30 Nov"


def feedback_harness() -> tuple[Harness, InMemoryFeedbackStore]:
    h = Harness.build()
    store = h.services.feedback_store
    assert isinstance(store, InMemoryFeedbackStore)
    return h, store


def opening(user_id: str, **overrides: Any):
    return memory(content=OPENING_CONTENT, kind=Kind.OPENING, user_id=user_id, **overrides)


def asking(asked_id: str, user_id: str) -> ChangeEvent:
    return change_event(
        "trigger-1",
        user_id=user_id,
        decisions=[decision(asked_id, DecisionAction.ASK)],
    )


async def seed_event(h: Harness, event: ChangeEvent) -> None:
    async with h.store.transaction() as tx:
        await tx.add_change_event(event)


def test_post_feedback_records_saved_opening_with_201():
    h, store = feedback_harness()

    async def run():
        user, headers = await h.user()
        job = opening(user.id)
        await h.seed(job)
        async with h.client() as c:
            response = await c.post(
                "/feedback",
                json={"target_memory_id": job.id, "kind": "saved", "note": "good stipend"},
                headers=headers,
            )
        return user, job, response

    user, job, response = asyncio.run(run())
    assert response.status_code == 201
    payload = body(response)
    assert (payload["target_memory_id"], payload["kind"], payload["note"]) == (
        job.id,
        "saved",
        "good stipend",
    )
    assert payload["created_at"].startswith(h.clock.now().isoformat()[:19])
    [row] = asyncio.run(store.feedback_for_user(user.id))
    assert row.id == payload["id"]


def test_post_feedback_returns_first_row_with_200_when_repeated():
    h, store = feedback_harness()

    async def run():
        user, headers = await h.user()
        job = opening(user.id)
        await h.seed(job)
        async with h.client() as c:
            first = await c.post(
                "/feedback", json={"target_memory_id": job.id, "kind": "applied"}, headers=headers
            )
            h.clock.advance(timedelta(minutes=5))
            again = await c.post(
                "/feedback", json={"target_memory_id": job.id, "kind": "applied"}, headers=headers
            )
        return user, first, again

    user, first, again = asyncio.run(run())
    assert (first.status_code, again.status_code) == (201, 200)
    assert body(again)["id"] == body(first)["id"]
    assert len(asyncio.run(store.feedback_for_user(user.id))) == 1


def test_post_feedback_applied_changes_no_memory():
    """I6: "applied" is the student's statement; nothing in memory or elsewhere moves."""
    h, _ = feedback_harness()

    async def run():
        user, headers = await h.user()
        job = opening(user.id)
        await h.seed(job)
        before = h.store.all_memories()
        async with h.client() as c:
            await c.post(
                "/feedback", json={"target_memory_id": job.id, "kind": "applied"}, headers=headers
            )
        return user, before

    user, before = asyncio.run(run())
    assert h.store.all_memories() == before
    assert asyncio.run(h.store.change_events_for_user(user.id)) == []


def test_post_feedback_question_useful_on_asked_memory():
    h, store = feedback_harness()

    async def run():
        user, headers = await h.user()
        asked = fact("student", "cgpa", 7.6, user_id=user.id, status=Status.PENDING_USER)
        await h.seed(asked)
        await seed_event(h, asking(asked.id, user.id))
        async with h.client() as c:
            response = await c.post(
                "/feedback",
                json={"target_memory_id": asked.id, "kind": "question_useful"},
                headers=headers,
            )
        return user, response

    user, response = asyncio.run(run())
    assert response.status_code == 201
    [row] = asyncio.run(store.feedback_for_user(user.id))
    assert row.kind is FeedbackKind.QUESTION_USEFUL


def test_post_feedback_third_tap_on_a_question_returns_the_first_row():
    """useful → not useful → useful: the third tap is the first row again (first wins),
    which is why the report rates a question by its first rating (ADR-0106)."""
    h, store = feedback_harness()

    async def run():
        user, headers = await h.user()
        asked = fact("student", "cgpa", 7.6, user_id=user.id, status=Status.PENDING_USER)
        await h.seed(asked)
        await seed_event(h, asking(asked.id, user.id))
        statuses = []
        async with h.client() as c:
            for kind in ("question_useful", "question_not_useful", "question_useful"):
                h.clock.advance(timedelta(minutes=1))
                response = await c.post(
                    "/feedback", json={"target_memory_id": asked.id, "kind": kind}, headers=headers
                )
                statuses.append(response.status_code)
        return user, statuses

    user, statuses = asyncio.run(run())
    assert statuses == [201, 201, 200]
    kinds = [f.kind for f in asyncio.run(store.feedback_for_user(user.id))]
    assert kinds == [FeedbackKind.QUESTION_USEFUL, FeedbackKind.QUESTION_NOT_USEFUL]


@pytest.mark.parametrize("kind", ["saved", "applied", "dismissed"])
def test_post_feedback_rejects_recommendation_kind_when_target_is_not_an_opening(kind: str):
    h, store = feedback_harness()

    async def run():
        user, headers = await h.user()
        cgpa = fact("student", "cgpa", 7.6, user_id=user.id)
        await h.seed(cgpa)
        async with h.client() as c:
            response = await c.post(
                "/feedback", json={"target_memory_id": cgpa.id, "kind": kind}, headers=headers
            )
        return user, response

    user, response = asyncio.run(run())
    assert response.status_code == 422
    assert asyncio.run(store.feedback_for_user(user.id)) == []


@pytest.mark.parametrize("kind", ["question_useful", "question_not_useful"])
def test_post_feedback_rejects_question_kind_when_nothing_was_asked(kind: str):
    h, store = feedback_harness()

    async def run():
        user, headers = await h.user()
        job = opening(user.id)
        await h.seed(job)
        async with h.client() as c:
            response = await c.post(
                "/feedback", json={"target_memory_id": job.id, "kind": kind}, headers=headers
            )
        return user, response

    user, response = asyncio.run(run())
    assert response.status_code == 422
    assert asyncio.run(store.feedback_for_user(user.id)) == []


def test_post_feedback_404_for_another_users_memory():
    h, store = feedback_harness()

    async def run():
        _, headers = await h.user()
        other, _ = await h.user("Bina")
        theirs = opening(other.id)
        await h.seed(theirs)
        async with h.client() as c:
            response = await c.post(
                "/feedback", json={"target_memory_id": theirs.id, "kind": "saved"}, headers=headers
            )
        return response

    response = asyncio.run(run())
    assert response.status_code == 404
    assert store.rows == {}


def test_post_feedback_404_for_unknown_memory():
    h, _ = feedback_harness()

    async def run():
        _, headers = await h.user()
        async with h.client() as c:
            return await c.post(
                "/feedback", json={"target_memory_id": "nope", "kind": "saved"}, headers=headers
            )

    assert asyncio.run(run()).status_code == 404


def test_post_feedback_401_without_token():
    h, _ = feedback_harness()

    async def run():
        async with h.client() as c:
            return await c.post("/feedback", json={"target_memory_id": "x", "kind": "saved"})

    assert asyncio.run(run()).status_code == 401


@pytest.mark.parametrize(
    "payload",
    [
        {"target_memory_id": "x", "kind": "liked"},
        {"target_memory_id": "x", "kind": "saved", "note": "n" * 281},
        {"target_memory_id": "x", "kind": "saved", "user_id": "someone-else"},
        {"kind": "saved"},
    ],
    ids=["unknown-kind", "long-note", "extra-field", "no-target"],
)
def test_post_feedback_422_for_invalid_body(payload: dict[str, Any]):
    h, _ = feedback_harness()

    async def run():
        _, headers = await h.user()
        async with h.client() as c:
            return await c.post("/feedback", json=payload, headers=headers)

    assert asyncio.run(run()).status_code == 422


def test_post_feedback_does_not_return_retired_opening_content():
    """I1: the row is ids and kinds; a RETIRED target's content never comes back."""
    h, _ = feedback_harness()

    async def run():
        user, headers = await h.user()
        job = opening(user.id, status=Status.RETIRED)
        await h.seed(job)
        async with h.client() as c:
            return await c.post(
                "/feedback", json={"target_memory_id": job.id, "kind": "dismissed"}, headers=headers
            )

    response = asyncio.run(run())
    assert response.status_code == 201
    assert OPENING_CONTENT not in response.text


def test_get_feedback_lists_only_own_rows_oldest_first():
    h, _ = feedback_harness()

    async def run():
        user, headers = await h.user()
        other, other_h = await h.user("Bina")
        first, second, theirs = opening(user.id), opening(user.id), opening(other.id)
        await h.seed(first, second, theirs)
        async with h.client() as c:
            await c.post(
                "/feedback", json={"target_memory_id": first.id, "kind": "saved"}, headers=headers
            )
            h.clock.advance(timedelta(minutes=1))
            await c.post(
                "/feedback",
                json={"target_memory_id": second.id, "kind": "dismissed"},
                headers=headers,
            )
            await c.post(
                "/feedback", json={"target_memory_id": theirs.id, "kind": "saved"}, headers=other_h
            )
            listed = await c.get("/feedback", headers=headers)
        return first, second, listed

    first, second, listed = asyncio.run(run())
    assert listed.status_code == 200
    rows = body(listed)["feedback"]
    assert [(r["target_memory_id"], r["kind"]) for r in rows] == [
        (first.id, "saved"),
        (second.id, "dismissed"),
    ]


def test_get_feedback_filters_by_target():
    h, _ = feedback_harness()

    async def run():
        user, headers = await h.user()
        first, second = opening(user.id), opening(user.id)
        await h.seed(first, second)
        async with h.client() as c:
            for job in (first, second):
                await c.post(
                    "/feedback", json={"target_memory_id": job.id, "kind": "saved"}, headers=headers
                )
            listed = await c.get(
                "/feedback", params={"target_memory_id": second.id}, headers=headers
            )
        return second, listed

    second, listed = asyncio.run(run())
    assert [r["target_memory_id"] for r in body(listed)["feedback"]] == [second.id]


def test_get_feedback_401_without_token():
    h, _ = feedback_harness()

    async def run():
        async with h.client() as c:
            return await c.get("/feedback")

    assert asyncio.run(run()).status_code == 401


def test_create_app_serves_feedback():
    h = Harness.build()

    async def run():
        _, headers = await h.user()
        async with h.client() as c:
            return await c.get("/feedback", headers=headers)

    assert asyncio.run(run()).status_code == 200


def test_delete_me_erases_feedback():
    h, store = feedback_harness()

    async def run():
        user, headers = await h.user()
        job = opening(user.id)
        await h.seed(job)
        async with h.client() as c:
            await c.post(
                "/feedback", json={"target_memory_id": job.id, "kind": "saved"}, headers=headers
            )
            deleted = await c.delete("/me", headers=headers)
        return user, deleted

    user, deleted = asyncio.run(run())
    assert deleted.status_code == 204
    assert asyncio.run(store.feedback_for_user(user.id)) == []


def test_feedback_on_a_question_is_accepted_after_it_was_answered():
    """The dashboard asks "was this useful?" right after the answer (WS-12 C4)."""
    h, _ = feedback_harness()

    async def run():
        user, headers = await h.user()
        asked = fact("student", "cgpa", 7.6, user_id=user.id, status=Status.PENDING_USER)
        await h.seed(asked)
        await seed_event(h, asking(asked.id, user.id))
        async with h.client() as c:
            answered = await c.post(
                f"/questions/{asked.id}/answer", json={"answer": "still_holds"}, headers=headers
            )
            rated = await c.post(
                "/feedback",
                json={"target_memory_id": asked.id, "kind": "question_useful"},
                headers=headers,
            )
        return answered, rated

    answered, rated = asyncio.run(run())
    assert answered.status_code == 200, answered.text
    assert rated.status_code == 201, rated.text


def test_export_includes_the_users_feedback():
    h, _ = feedback_harness()

    async def run():
        user, headers = await h.user()
        job = opening(user.id)
        await h.seed(job)
        async with h.client() as c:
            await c.post(
                "/feedback", json={"target_memory_id": job.id, "kind": "saved"}, headers=headers
            )
            return job, await c.get("/me/export", headers=headers)

    job, exported = asyncio.run(run())
    assert [(r["target_memory_id"], r["kind"]) for r in body(exported)["feedback"]] == [
        (job.id, "saved")
    ]
