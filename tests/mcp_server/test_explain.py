"""ripple_explain: why (live parents), history (version chain), events, visibility."""

import asyncio

from ripple.core.models import Decision, DecisionAction, Status
from tests.builders import change_event, derived, fact, link, memory, snapshot_link
from tests.mcp_server.harness import McpHarness, error, out


def test_explain_shows_live_parents_history_and_decisions_with_questions():
    h = McpHarness.build()

    async def run():
        user, token = await h.user()
        cgpa_v1 = fact("student", "cgpa", 7.6, user_id=user.id, status=Status.RETIRED)
        cgpa_v2 = fact("student", "cgpa", 8.0, user_id=user.id, version=2, supersedes_id=cgpa_v1.id)
        resume = memory(content="resume v1", kind="fact", user_id=user.id)
        belief_v1 = derived("eligible", user_id=user.id, status=Status.RETIRED)
        belief_v2 = derived(
            "still eligible",
            user_id=user.id,
            status=Status.PENDING_USER,
            version=2,
            supersedes_id=belief_v1.id,
        )
        asked = change_event(
            cgpa_v2,
            user_id=user.id,
            affected_ids=[belief_v2.id],
            decisions=[
                Decision(
                    memory_id=belief_v2.id,
                    wave=1,
                    action=DecisionAction.ASK,
                    reason="cgpa moved",
                    evidence_refs=["resume.pdf#1-9"],
                    question="Are you still eligible?",
                )
            ],
        )
        unrelated = change_event(resume, user_id=user.id)
        await h.seed(
            cgpa_v1,
            cgpa_v2,
            resume,
            belief_v1,
            belief_v2,
            link(cgpa_v1, belief_v2),  # history link: parent superseded, skipped in why
            link(cgpa_v2, belief_v2),
            snapshot_link(resume, belief_v2),
        )
        async with h.store.transaction() as tx:
            await tx.add_change_event(asked)
            await tx.add_change_event(unrelated)
        async with h.client() as c:
            result = await h.call(c, "ripple_explain", {"memory_id": belief_v2.id}, token=token)
        return cgpa_v2, resume, belief_v1, belief_v2, asked, result

    cgpa_v2, resume, belief_v1, belief_v2, asked, result = asyncio.run(run())
    body = out(result)
    assert body["memory"]["id"] == belief_v2.id
    assert body["visibility"] == "flagged"
    assert body["status"] == "PENDING_USER"
    # Link order is not part of the contract (the store orders ties by random id).
    assert {(p["parent"]["id"], p["link_class"]) for p in body["why"]} == {
        (cgpa_v2.id, "depends_on"),
        (resume.id, "snapshot_of"),
    }
    assert len(body["why"]) == 2
    assert [v["id"] for v in body["history"]] == [belief_v1.id, belief_v2.id]
    [event] = body["events"]
    assert event["id"] == asked.id
    assert event["trigger_memory_id"] == cgpa_v2.id
    [decision] = event["decisions"]
    assert decision["action"] == "ask"
    assert decision["reason"] == "cgpa moved"
    assert decision["question"] == "Are you still eligible?"
    assert decision["evidence_refs"] == ["resume.pdf#1-9"]


def test_explain_reports_visibility_for_valid_and_retired_memories():
    h = McpHarness.build()

    async def run():
        user, token = await h.user()
        valid = memory(content="valid", user_id=user.id)
        retired = memory(content="retired", status=Status.RETIRED, user_id=user.id)
        await h.seed(valid, retired)
        async with h.client() as c:
            shown = await h.call(c, "ripple_explain", {"memory_id": valid.id}, token=token)
            past = await h.call(c, "ripple_explain", {"memory_id": retired.id}, token=token)
        return shown, past

    shown, past = asyncio.run(run())
    assert out(shown)["visibility"] == "visible" and out(shown)["why"] == []
    assert out(past)["visibility"] == "hidden" and out(past)["status"] == "RETIRED"


def test_explain_of_another_users_memory_is_not_found():
    h = McpHarness.build()

    async def run():
        _, token = await h.user()
        other, _ = await h.user("Bina")
        theirs = memory(content="theirs", user_id=other.id)
        await h.seed(theirs)
        async with h.client() as c:
            return await h.call(c, "ripple_explain", {"memory_id": theirs.id}, token=token)

    assert error(asyncio.run(run()))["error"] == "not_found"
