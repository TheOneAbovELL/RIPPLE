"""Resume upload and the confirmation flow (FR-1, ADR-0024, I5)."""

import asyncio

from tests.api.fakes import ScriptedResumeParser, candidate_fact, unparseable_resume
from tests.api.harness import Harness, body

PDF = b"%PDF-1.4\n%fake resume for tests\n"


def _upload(c, headers, content: bytes = PDF, name: str = "resume.pdf"):
    return c.post("/resume", files={"file": (name, content, "application/pdf")}, headers=headers)


def test_upload_stores_candidates_as_pending_and_writes_no_memory():
    parser = ScriptedResumeParser(
        candidate_fact("cgpa", 7.6, "CGPA 7.6"), candidate_fact("branch", "CSE", "B.Tech CSE")
    )
    h = Harness.build(resume_parser=parser)

    async def run():
        user, headers = await h.user()
        async with h.client() as c:
            uploaded = await _upload(c, headers)
            listed = await c.get("/resume/candidates", headers=headers)
            memories = await c.get("/memories", headers=headers)
        return user, uploaded, listed, memories

    user, uploaded, listed, memories = asyncio.run(run())
    assert uploaded.status_code == 201, uploaded.text
    out = body(uploaded)
    assert [c["attribute"] for c in out["candidates"]] == ["cgpa", "branch"]
    assert {c["status"] for c in out["candidates"]} == {"pending"}
    assert {c["user_id"] for c in out["candidates"]} == {user.id}
    assert parser.calls[0][1] == f"resume:{out['upload_id']}"
    assert len(body(listed)["candidates"]) == 2
    assert body(memories)["memories"] == []  # I5: nothing stored before confirmation


def test_non_pdf_and_oversized_uploads_are_refused_before_parsing():
    parser = ScriptedResumeParser(candidate_fact("cgpa", 7.6, "CGPA 7.6"))
    h = Harness.build(resume_parser=parser)

    async def run():
        _, headers = await h.user()
        async with h.client() as c:
            text = await _upload(c, headers, b"just text", "resume.txt")
            big = await _upload(c, headers, PDF + b"x" * 2048)
        return text, big

    text, big = asyncio.run(run())
    assert (text.status_code, big.status_code) == (415, 413)
    assert parser.calls == []


def test_unparseable_pdf_is_a_422():
    h = Harness.build(resume_parser=ScriptedResumeParser(error=unparseable_resume()))

    async def run():
        _, headers = await h.user()
        async with h.client() as c:
            return await _upload(c, headers)

    response = asyncio.run(run())
    assert response.status_code == 422
    assert body(response)["error"] == "ResumeUnparseableError"


def test_confirm_turns_the_candidate_into_a_memory_through_intake():
    h = Harness.build(resume_parser=ScriptedResumeParser(candidate_fact("cgpa", 7.6, "CGPA 7.6")))

    async def run():
        user, headers = await h.user()
        async with h.client() as c:
            uploaded = body(await _upload(c, headers))
            candidate_id = uploaded["candidates"][0]["id"]
            confirmed = await c.post(f"/resume/candidates/{candidate_id}/confirm", headers=headers)
            again = await c.post(f"/resume/candidates/{candidate_id}/confirm", headers=headers)
            pending = await c.get("/resume/candidates", headers=headers)
            done = await c.get(
                "/resume/candidates", params={"status": "confirmed"}, headers=headers
            )
            memories = await c.get("/memories", headers=headers)
        return user, uploaded, confirmed, again, pending, done, memories

    user, uploaded, confirmed, again, pending, done, memories = asyncio.run(run())
    assert confirmed.status_code == 200, confirmed.text
    out = body(confirmed)
    memory = out["intake"]["memory"]
    assert out["candidate"]["status"] == "confirmed"
    assert out["candidate"]["memory_id"] == memory["id"]
    assert memory["user_id"] == user.id
    assert memory["structured"] == {"subject": "student", "attribute": "cgpa", "value": 7.6}
    assert memory["source_ref"] == f"resume:{uploaded['upload_id']}#0-8"
    assert out["intake"]["event"]["completed_at"] is not None
    assert again.status_code == 409
    assert body(pending)["candidates"] == []
    assert [c["id"] for c in body(done)["candidates"]] == [out["candidate"]["id"]]
    assert [m["memory"]["id"] for m in body(memories)["memories"]] == [memory["id"]]


def test_reject_keeps_the_candidate_as_declined_and_writes_nothing():
    h = Harness.build(resume_parser=ScriptedResumeParser(candidate_fact("cgpa", 7.6, "CGPA 7.6")))

    async def run():
        _, headers = await h.user()
        async with h.client() as c:
            candidate_id = body(await _upload(c, headers))["candidates"][0]["id"]
            rejected = await c.post(f"/resume/candidates/{candidate_id}/reject", headers=headers)
            confirm_after = await c.post(
                f"/resume/candidates/{candidate_id}/confirm", headers=headers
            )
        return rejected, confirm_after

    rejected, confirm_after = asyncio.run(run())
    assert body(rejected)["candidate"]["status"] == "rejected"
    assert confirm_after.status_code == 409
    assert h.store.all_memories() == []


def test_candidates_are_scoped_to_their_owner():
    h = Harness.build(resume_parser=ScriptedResumeParser(candidate_fact("cgpa", 7.6, "CGPA 7.6")))

    async def run():
        _, asha_h = await h.user("Asha")
        _, bina_h = await h.user("Bina")
        async with h.client() as c:
            candidate_id = body(await _upload(c, asha_h))["candidates"][0]["id"]
            other_list = await c.get("/resume/candidates", headers=bina_h)
            other_confirm = await c.post(
                f"/resume/candidates/{candidate_id}/confirm", headers=bina_h
            )
            other_reject = await c.post(f"/resume/candidates/{candidate_id}/reject", headers=bina_h)
        return other_list, other_confirm, other_reject

    other_list, other_confirm, other_reject = asyncio.run(run())
    assert body(other_list)["candidates"] == []
    assert (other_confirm.status_code, other_reject.status_code) == (404, 404)
