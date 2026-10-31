"""Named invariant tests added by the hardening workstream (CLAUDE.md I7)."""

import asyncio

from tests.api.fakes import ScriptedResumeParser, candidate_fact
from tests.api.harness import Harness
from tests.builders import fact

PDF = b"%PDF-1.4 test"


def test_invariant_I7_delete_me_removes_uploads_and_candidates():
    """Deleting the user leaves no resume text and no candidate behind, alongside the
    forget cascade over memories and the ChangeEvent erasure (ADR-0044, ADR-0097)."""
    h = Harness.build(
        resume_parser=ScriptedResumeParser(
            candidate_fact("cgpa", 7.6, "CGPA 7.6"), candidate_fact("branch", "CSE", "B.Tech CSE")
        )
    )

    async def run():
        user, headers = await h.user()
        other, _ = await h.user("Bina")
        await h.seed(fact("student", "batch", 2027, user_id=other.id))
        async with h.client() as c:
            uploaded = await c.post(
                "/resume", files={"file": ("r.pdf", PDF, "application/pdf")}, headers=headers
            )
            candidate_id = uploaded.json()["candidates"][0]["id"]
            await c.post(f"/resume/candidates/{candidate_id}/confirm", headers=headers)
            deleted = await c.delete("/me", headers=headers)
        return user, other, deleted

    user, other, deleted = asyncio.run(run())
    assert deleted.status_code == 204
    assert asyncio.run(h.services.upload_store.uploads_for_user(user.id)) == []
    assert asyncio.run(h.candidate_store.candidates_for_user(user.id)) == []
    assert [m for m in h.store.all_memories() if m.user_id == user.id] == []
    assert [e for e in h.store.change_events() if e.user_id == user.id] == []
    # The forget audit stays, and the other user's data is untouched.
    assert {e.user_id for e in h.store.forget_events()} == {user.id}
    assert [m.user_id for m in h.store.all_memories()] == [other.id]
