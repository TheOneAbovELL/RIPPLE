"""Named invariant tests at the API boundary (CLAUDE.md I1, I5, I6, I7)."""

import asyncio

from ripple.core.models import Status
from tests.api.fakes import ScriptedResumeParser, candidate_fact
from tests.api.harness import Harness, body
from tests.builders import derived, fact, link, memory

# Every route the API exposes. A new endpoint must be added here on purpose, which is
# the moment to ask whether it acts on an external site for the user (I6).
EXPECTED_ROUTES = {
    ("POST", "/statements"),
    ("GET", "/memories"),
    ("GET", "/memories/{memory_id}"),
    ("POST", "/memories/{memory_id}/edit"),
    ("POST", "/memories/{memory_id}/forget"),
    ("GET", "/questions"),
    ("POST", "/questions/{memory_id}/answer"),
    ("POST", "/resume"),
    ("GET", "/resume/candidates"),
    ("POST", "/resume/candidates/{candidate_id}/confirm"),
    ("POST", "/resume/candidates/{candidate_id}/reject"),
    ("POST", "/openings"),
    ("GET", "/recommendations"),
    ("GET", "/me"),
    ("POST", "/me/telegram/link"),
    ("GET", "/me/export"),
    ("DELETE", "/me"),
    ("GET", "/graph"),
    ("GET", "/vocabulary"),
    # Pilot feedback (ADR-0105): "applied" records the student's own statement only.
    ("POST", "/feedback"),
    ("GET", "/feedback"),
    # Recent ripples for the dashboard (ADR-0118): read-only.
    ("GET", "/events"),
}

FORBIDDEN_PATH_WORDS = ("apply", "submit", "application", "send", "portal")


def _routes(app):
    """From the OpenAPI document: what the dashboard's generated client will see."""
    return {
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        for method in operations
    }


def test_invariant_I6_api_has_no_apply_endpoint():
    app = Harness.build().app
    routes = _routes(app)
    assert routes == EXPECTED_ROUTES
    offending = [path for _, path in routes if any(w in path for w in FORBIDDEN_PATH_WORDS)]
    assert offending == []


def test_invariant_I1_api_never_returns_retired():
    """Across every memory-returning surface: list (with and without flagged), detail
    without history, questions. RETIRED rows are reachable only via history=true."""
    h = Harness.build()

    async def run():
        user, headers = await h.user()
        rows = [
            fact("student", "cgpa", 7.6, user_id=user.id),
            memory(content="suspect", status=Status.SUSPECT, user_id=user.id),
            memory(content="pending", status=Status.PENDING_USER, user_id=user.id),
            derived("retired belief", status=Status.RETIRED, user_id=user.id),
        ]
        await h.seed(*rows)
        retired = rows[-1]
        async with h.client() as c:
            listed = await c.get("/memories", headers=headers)
            plain = await c.get("/memories", params={"flagged": "false"}, headers=headers)
            by_kind = await c.get("/memories", params={"kind": "derived"}, headers=headers)
            detail = await c.get(f"/memories/{retired.id}", headers=headers)
            questions = await c.get("/questions", headers=headers)
            export = await c.get("/me/export", headers=headers)
        return retired, listed, plain, by_kind, detail, questions, export

    retired, listed, plain, by_kind, detail, questions, export = asyncio.run(run())
    for response in (listed, plain, by_kind):
        statuses = {m["memory"]["status"] for m in body(response)["memories"]}
        assert "RETIRED" not in statuses
    flagged = {m["memory"]["status"]: m["flagged"] for m in body(listed)["memories"]}
    assert flagged == {"VALID": False, "SUSPECT": True, "PENDING_USER": True}
    assert body(by_kind)["memories"] == []
    assert detail.status_code == 404
    # A seeded PENDING_USER row has no asking event, so the queue is empty here; the
    # point is that nothing RETIRED can appear (the queue reads PENDING_USER rows only).
    assert {q["memory"]["status"] for q in body(questions)["questions"]} <= {"PENDING_USER"}
    # The export is the user's own full record (FR-15), not retrieval: history belongs there.
    assert retired.id in {m["id"] for m in body(export)["memories"]}


def test_invariant_I1_graph_never_returns_retired_nodes_or_links_to_them():
    h = Harness.build()

    async def run():
        user, headers = await h.user()
        cgpa = fact("student", "cgpa", 7.6, user_id=user.id)
        live = derived("eligible for Acme", status=Status.SUSPECT, user_id=user.id)
        retired = derived("not eligible for Acme", status=Status.RETIRED, user_id=user.id)
        await h.seed(cgpa, live, retired, link(cgpa, live), link(cgpa, retired))
        async with h.client() as c:
            return cgpa, live, await c.get("/graph", headers=headers)

    cgpa, live, response = asyncio.run(run())
    out = body(response)
    assert {(n["memory"]["id"], n["flagged"]) for n in out["nodes"]} == {
        (cgpa.id, False),
        (live.id, True),
    }
    assert [(lk["parent_id"], lk["dependent_id"]) for lk in out["links"]] == [(cgpa.id, live.id)]


def test_invariant_I1_answer_receipt_never_carries_a_retired_memory():
    h = Harness.build()

    async def run():
        user, headers = await h.user()
        pending = derived("not eligible", status=Status.PENDING_USER, user_id=user.id)
        await h.seed(pending)
        async with h.client() as c:
            return await c.post(
                f"/questions/{pending.id}/answer",
                json={"answer": "no_longer_holds"},
                headers=headers,
            )

    out = body(asyncio.run(run()))
    assert out["status"] == "RETIRED" and out["memory"] is None


def test_invariant_I5_api_stores_no_resume_fact_before_confirmation():
    h = Harness.build(resume_parser=ScriptedResumeParser(candidate_fact("cgpa", 7.6, "CGPA 7.6")))

    async def run():
        _, headers = await h.user()
        async with h.client() as c:
            uploaded = await c.post(
                "/resume",
                files={"file": ("r.pdf", b"%PDF-1.4 x", "application/pdf")},
                headers=headers,
            )
            candidate_id = body(uploaded)["candidates"][0]["id"]
            before = list(h.store.all_memories())
            await c.post(f"/resume/candidates/{candidate_id}/confirm", headers=headers)
            return before

    before = asyncio.run(run())
    assert before == []
    assert [m.structured.value for m in h.store.all_memories() if m.structured] == [7.6]


def test_invariant_I7_api_deletes_only_through_forget_with_a_forget_event():
    h = Harness.build()

    async def run():
        user, headers = await h.user()
        cgpa = fact("student", "cgpa", 7.6, user_id=user.id)
        belief = derived("not eligible", user_id=user.id)
        await h.seed(cgpa, belief, link(cgpa, belief))
        async with h.client() as c:
            await c.post(f"/memories/{cgpa.id}/forget", headers=headers)
            await c.delete("/me", headers=headers)
        return cgpa, belief

    cgpa, belief = asyncio.run(run())
    deleted = sorted(i for e in h.store.forget_events() for i in e.deleted_ids)
    assert deleted == sorted([cgpa.id, belief.id])  # every deletion is accounted for
    assert h.store.all_memories() == []
