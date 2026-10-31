"""GET /events: the user's recent ChangeEvents with labels for the memories they name."""

import asyncio
from datetime import timedelta

from ripple.core.models import Decision, DecisionAction, Status, TriggerKind
from tests.api.harness import Harness, body
from tests.builders import change_event, derived, fact


def _decision(memory_id: str, action: DecisionAction = DecisionAction.KEEP) -> Decision:
    return Decision(memory_id=memory_id, wave=1, action=action, reason="recomputed")


def _seed_three_events(h: Harness, user_id: str):
    cgpa = fact("student", "cgpa", 8.1, user_id=user_id)
    old = derived("eligible for Acme", user_id=user_id, status=Status.RETIRED)
    belief = derived("not eligible for Acme", user_id=user_id)
    start = h.clock.now()
    quiet = change_event(cgpa, user_id=user_id, at=start)  # nothing depended on it
    rippled = change_event(
        cgpa,
        user_id=user_id,
        at=start + timedelta(minutes=1),
        trigger_kind=TriggerKind.USER_EDIT,
        decisions=[_decision(old.id), _decision(belief.id)],
    )
    newest = change_event(
        belief,
        user_id=user_id,
        at=start + timedelta(minutes=2),
        decisions=[_decision(belief.id)],
    )
    return (cgpa, old, belief), (quiet, rippled, newest)


async def _seed_events(h: Harness, *events) -> None:
    async with h.store.transaction() as tx:
        for event in events:
            await tx.add_change_event(event)


def test_events_are_newest_first_and_rippled_only_by_default_with_labels():
    h = Harness.build()

    async def run():
        user, headers = await h.user()
        memories, events = _seed_three_events(h, user.id)
        await h.seed(*memories)
        await _seed_events(h, *events)
        async with h.client() as c:
            return memories, events, await c.get("/events", headers=headers)

    (cgpa, old, belief), (_, rippled, newest), response = asyncio.run(run())
    out = body(response)
    assert [e["id"] for e in out["events"]] == [newest.id, rippled.id]
    assert out["total"] == 3
    labels = out["memories"]
    assert labels[cgpa.id] == {"content": cgpa.content, "status": "VALID"}
    # The audit names the version a decision retired, marked as such (history view).
    assert labels[old.id] == {"content": "eligible for Acme", "status": "RETIRED"}
    assert set(labels) == {cgpa.id, old.id, belief.id}


def test_events_limit_and_all_include_quiet_writes():
    h = Harness.build()

    async def run():
        user, headers = await h.user()
        memories, events = _seed_three_events(h, user.id)
        await h.seed(*memories)
        await _seed_events(h, *events)
        async with h.client() as c:
            one = await c.get("/events?limit=1", headers=headers)
            every = await c.get("/events?rippled_only=false", headers=headers)
            too_many = await c.get("/events?limit=500", headers=headers)
        return events, one, every, too_many

    (quiet, rippled, newest), one, every, too_many = asyncio.run(run())
    assert [e["id"] for e in body(one)["events"]] == [newest.id]
    assert [e["id"] for e in body(every)["events"]] == [newest.id, rippled.id, quiet.id]
    assert too_many.status_code == 422


def test_events_never_show_another_users_events_or_memories():
    h = Harness.build()

    async def run():
        _, asha_headers = await h.user("Asha")
        ravi, _ravi_headers = await h.user("Ravi")
        memories, events = _seed_three_events(h, ravi.id)
        await h.seed(*memories)
        await _seed_events(h, *events)
        async with h.client() as c:
            return await c.get("/events", headers=asha_headers)

    out = body(asyncio.run(run()))
    assert (out["events"], out["memories"], out["total"]) == ([], {}, 0)


def test_events_need_a_token():
    h = Harness.build()

    async def run():
        async with h.client() as c:
            return await c.get("/events")

    assert asyncio.run(run()).status_code == 401


def test_an_open_ripple_that_decided_nothing_yet_is_still_a_recent_ripple():
    """A model outage leaves beliefs SUSPECT with no decision yet (ADR-0118 point 7): the
    dashboard must show that event, flagged labels included."""
    h = Harness.build()

    async def run():
        user, headers = await h.user()
        cgpa = fact("student", "cgpa", 8.1, user_id=user.id)
        waiting = derived("eligible for Acme", user_id=user.id, status=Status.SUSPECT)
        stalled = change_event(cgpa, user_id=user.id, affected_ids=[waiting.id])
        await h.seed(cgpa, waiting)
        await _seed_events(h, stalled)
        async with h.client() as c:
            return waiting, stalled, await c.get("/events", headers=headers)

    waiting, stalled, response = asyncio.run(run())
    out = body(response)
    assert [e["id"] for e in out["events"]] == [stalled.id]
    assert out["memories"][waiting.id]["status"] == "SUSPECT"


def test_events_redact_decision_text_about_forgotten_memories():
    """I7: forgetting the CGPA removes it from memory; a reason quoting it must not keep
    showing the number on the home page."""
    from ripple.core.models import ForgetEvent

    h = Harness.build()

    async def run():
        user, headers = await h.user()
        cgpa = fact("student", "cgpa", 7.9, user_id=user.id)
        belief = derived("not eligible for Acme", user_id=user.id)
        quoted = Decision(
            memory_id=belief.id,
            wave=1,
            action=DecisionAction.KEEP,
            reason="CGPA 7.9 < cutoff 8.0",
            evidence_refs=[cgpa.id],
        )
        event = change_event(cgpa, user_id=user.id, decisions=[quoted])
        await h.seed(belief)  # the CGPA itself was forgotten: only the belief is left
        await _seed_events(h, event)
        async with h.store.transaction() as tx:
            await tx.add_forget_event(
                ForgetEvent(
                    user_id=user.id,
                    root_memory_id=cgpa.id,
                    deleted_ids=[cgpa.id],
                    created_at=h.clock.now(),
                )
            )
        async with h.client() as c:
            return cgpa, belief, await c.get("/events", headers=headers)

    cgpa, belief, response = asyncio.run(run())
    out = body(response)
    [decision] = out["events"][0]["decisions"]
    assert "7.9" not in response.text
    assert decision["reason"] == "forgotten at the user's request"
    assert cgpa.id not in out["memories"] and belief.id in out["memories"]
