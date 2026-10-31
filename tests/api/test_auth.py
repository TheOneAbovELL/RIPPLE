"""Bearer auth and per-user isolation (ADR-0040)."""

import asyncio

from ripple.core.models import StructuredFact
from tests.api.harness import Harness, body
from tests.builders import fact


def test_requests_without_a_token_are_401():
    h = Harness.build()

    async def run():
        async with h.client() as c:
            missing = await c.get("/me")
            wrong_scheme = await c.get("/me", headers={"Authorization": "Basic abc"})
            bad = await c.get("/me", headers={"Authorization": "Bearer not-a-token"})
            return missing, wrong_scheme, bad

    missing, wrong_scheme, bad = asyncio.run(run())
    assert (missing.status_code, wrong_scheme.status_code, bad.status_code) == (401, 401, 401)
    assert missing.headers["www-authenticate"] == "Bearer"


def test_a_valid_token_identifies_its_user():
    h = Harness.build()

    async def run():
        user, headers = await h.user("Asha")
        async with h.client() as c:
            return user, await c.get("/me", headers=headers)

    user, response = asyncio.run(run())
    assert response.status_code == 200
    assert body(response)["id"] == user.id
    assert body(response)["display_name"] == "Asha"


def test_users_cannot_see_or_touch_each_others_memories():
    """Isolation: every id-addressed route answers 404 across users, and lists are scoped."""
    h = Harness.build()

    async def run():
        asha, asha_h = await h.user("Asha")
        _bina, bina_h = await h.user("Bina")
        theirs = fact("student", "cgpa", 7.6, user_id=asha.id)
        await h.seed(theirs)
        async with h.client() as c:
            own_list = await c.get("/memories", headers=asha_h)
            other_list = await c.get("/memories", headers=bina_h)
            own_get = await c.get(f"/memories/{theirs.id}", headers=asha_h)
            other_get = await c.get(f"/memories/{theirs.id}", headers=bina_h)
            other_history = await c.get(
                f"/memories/{theirs.id}", params={"history": "true"}, headers=bina_h
            )
            other_edit = await c.post(
                f"/memories/{theirs.id}/edit", json={"content": "mine now"}, headers=bina_h
            )
            other_answer = await c.post(
                f"/questions/{theirs.id}/answer", json={"answer": "still_holds"}, headers=bina_h
            )
            other_forget = await c.post(f"/memories/{theirs.id}/forget", headers=bina_h)
            still_there = await c.get(f"/memories/{theirs.id}", headers=asha_h)
        return (
            own_list,
            other_list,
            own_get,
            other_get,
            other_history,
            other_edit,
            other_answer,
            other_forget,
            still_there,
        )

    (
        own_list,
        other_list,
        own_get,
        other_get,
        other_history,
        other_edit,
        other_answer,
        other_forget,
        still_there,
    ) = asyncio.run(run())
    assert len(body(own_list)["memories"]) == 1
    assert body(other_list)["memories"] == []
    assert own_get.status_code == 200
    assert {
        other_get.status_code,
        other_history.status_code,
        other_edit.status_code,
        other_answer.status_code,
        other_forget.status_code,
    } == {404}
    assert still_there.status_code == 200


def test_statements_are_written_under_the_token_holder_not_a_body_field():
    h = Harness.build()

    async def run():
        asha, asha_h = await h.user("Asha")
        async with h.client() as c:
            response = await c.post(
                "/statements",
                json={
                    "content": "CGPA is 7.6",
                    "kind": "fact",
                    "structured": StructuredFact(
                        subject="student", attribute="cgpa", value=7.6
                    ).model_dump(),
                    "user_id": "someone-else",
                },
                headers=asha_h,
            )
        return asha, response

    asha, response = asyncio.run(run())
    # extra="forbid": a client cannot name a user; the token decides.
    assert response.status_code == 422
    assert h.store.all_memories() == []
    assert asha.id  # the user exists; nothing was written for anyone
