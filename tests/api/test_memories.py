"""The inspector: list, explain (why), history, edit, forget (FR-12)."""

import asyncio

from ripple.core.models import Status, TriggerKind
from tests.api.harness import Harness, body
from tests.builders import derived, fact, link, memory, snapshot_link
from tests.fakes.resolver import ScriptedResolver, update


def _ids(response):
    return [m["memory"]["id"] for m in body(response)["memories"]]


def test_list_hides_retired_and_flags_suspect_and_pending():
    h = Harness.build()

    async def run():
        user, headers = await h.user()
        rows = [
            memory(content="valid", user_id=user.id),
            memory(content="suspect", status=Status.SUSPECT, user_id=user.id),
            memory(content="pending", status=Status.PENDING_USER, user_id=user.id),
            memory(content="retired", status=Status.RETIRED, user_id=user.id),
        ]
        await h.seed(*rows)
        async with h.client() as c:
            everything = await c.get("/memories", headers=headers)
            plain = await c.get("/memories", params={"flagged": "false"}, headers=headers)
            retired_filter = await c.get("/memories", params={"status": "RETIRED"}, headers=headers)
        return everything, plain, retired_filter

    everything, plain, retired_filter = asyncio.run(run())
    listed = {(m["memory"]["content"], m["flagged"]) for m in body(everything)["memories"]}
    assert listed == {("valid", False), ("suspect", True), ("pending", True)}
    assert [m["memory"]["content"] for m in body(plain)["memories"]] == ["valid"]
    assert retired_filter.status_code == 422  # RETIRED is not a listable status


def test_list_filters_by_kind_and_status():
    h = Harness.build()

    async def run():
        user, headers = await h.user()
        cgpa = fact("student", "cgpa", 7.6, user_id=user.id)
        belief = derived("not eligible", user_id=user.id, status=Status.SUSPECT)
        await h.seed(cgpa, belief)
        async with h.client() as c:
            facts = await c.get("/memories", params={"kind": "fact"}, headers=headers)
            suspect = await c.get("/memories", params={"status": "SUSPECT"}, headers=headers)
        return cgpa, belief, facts, suspect

    cgpa, belief, facts, suspect = asyncio.run(run())
    assert _ids(facts) == [cgpa.id]
    assert _ids(suspect) == [belief.id]


def test_detail_explains_why_skipping_history_links_and_keeping_snapshots():
    h = Harness.build()

    async def run():
        user, headers = await h.user()
        cgpa_v1 = fact("student", "cgpa", 7.6, user_id=user.id)
        cgpa_v2 = fact("student", "cgpa", 7.9, user_id=user.id, version=2, supersedes_id=cgpa_v1.id)
        cgpa_v1 = cgpa_v1.model_copy(update={"status": Status.RETIRED})
        resume_v1 = memory(content="resume v1", user_id=user.id, status=Status.RETIRED)
        belief = derived("eligible for Acme", user_id=user.id)
        application = memory(content="applied to Acme", kind="application", user_id=user.id)
        await h.seed(
            cgpa_v1,
            cgpa_v2,
            resume_v1,
            belief,
            application,
            link(cgpa_v1, belief),  # history: parent superseded
            link(cgpa_v2, belief),  # live
            snapshot_link(resume_v1, application),  # snapshot: shown although parent retired
        )
        async with h.client() as c:
            belief_out = await c.get(f"/memories/{belief.id}", headers=headers)
            app_out = await c.get(f"/memories/{application.id}", headers=headers)
        return cgpa_v2, resume_v1, belief_out, app_out

    cgpa_v2, resume_v1, belief_out, app_out = asyncio.run(run())
    why = body(belief_out)["why"]
    assert [p["parent"]["id"] for p in why] == [cgpa_v2.id]
    assert why[0]["link_class"] == "depends_on"
    assert body(belief_out)["history"] is None
    assert body(belief_out)["flagged"] is False
    snapshot_why = body(app_out)["why"]
    assert [p["parent"]["id"] for p in snapshot_why] == [resume_v1.id]
    assert snapshot_why[0]["link_class"] == "snapshot_of"


def test_history_shows_the_version_chain_and_the_events_that_mention_it():
    h = Harness.build()

    async def run():
        _, headers = await h.user()
        cgpa = {"subject": "student", "attribute": "cgpa", "value": 7.6}
        async with h.client() as c:
            v1 = body(
                await c.post(
                    "/statements",
                    json={"content": "CGPA is 7.6", "kind": "fact", "structured": cgpa},
                    headers=headers,
                )
            )["memory"]
            v2 = body(
                await c.post(
                    "/statements",
                    json={
                        "content": "CGPA is 7.9",
                        "kind": "fact",
                        "structured": {**cgpa, "value": 7.9},
                    },
                    headers=headers,
                )
            )["memory"]
            retired_plain = await c.get(f"/memories/{v1['id']}", headers=headers)
            retired_history = await c.get(
                f"/memories/{v1['id']}", params={"history": "true"}, headers=headers
            )
            latest_history = await c.get(
                f"/memories/{v2['id']}", params={"history": "true"}, headers=headers
            )
        return v1, v2, retired_plain, retired_history, latest_history

    v1, v2, retired_plain, retired_history, latest_history = asyncio.run(run())
    assert retired_plain.status_code == 404  # I1: a retired row is not a visible belief
    assert retired_history.status_code == 200
    history = body(latest_history)["history"]
    assert [m["id"] for m in history["versions"]] == [v1["id"], v2["id"]]
    # Both events share the FakeClock instant, so their order is by id: compare as a set.
    assert {e["trigger_memory_id"] for e in history["events"]} == {v1["id"], v2["id"]}
    assert body(retired_history)["history"]["versions"] == history["versions"]


def test_edit_writes_a_user_edit_version_that_ripples():
    cgpa = fact("student", "cgpa", 7.6)
    belief = derived("not eligible for Acme (cutoff 7.8)")
    h = Harness.build(
        waves=[[belief.id]], resolver=ScriptedResolver({belief.id: update("eligible for Acme")})
    )

    async def run():
        user, headers = await h.user()
        await h.seed(
            cgpa.model_copy(update={"user_id": user.id}),
            belief.model_copy(update={"user_id": user.id}),
            link(cgpa, belief),
        )
        async with h.client() as c:
            edited = await c.post(
                f"/memories/{cgpa.id}/edit",
                json={
                    "content": "CGPA is 7.9",
                    "structured": {"subject": "student", "attribute": "cgpa", "value": 7.9},
                },
                headers=headers,
            )
            listed = await c.get("/memories", headers=headers)
        return cgpa, belief, edited, listed

    cgpa, belief, edited, listed = asyncio.run(run())
    assert edited.status_code == 200, edited.text
    out = body(edited)
    assert (out["memory"]["version"], out["memory"]["supersedes_id"]) == (2, cgpa.id)
    assert out["memory"]["created_by"] == "user"
    assert out["event"]["trigger_kind"] == TriggerKind.USER_EDIT.value
    assert [d["action"] for d in out["event"]["decisions"]] == ["update"]
    contents = sorted(m["memory"]["content"] for m in body(listed)["memories"])
    assert contents == ["CGPA is 7.9", "eligible for Acme"]
    assert asyncio.run(h.store.get_memory(belief.id)).status is Status.RETIRED


def test_edit_of_a_pending_memory_is_refused_and_points_at_answers():
    h = Harness.build()

    async def run():
        user, headers = await h.user()
        pending = fact("student", "cgpa", 7.6, user_id=user.id, status=Status.PENDING_USER)
        await h.seed(pending)
        async with h.client() as c:
            return await c.post(
                f"/memories/{pending.id}/edit", json={"content": "CGPA is 8"}, headers=headers
            )

    response = asyncio.run(run())
    assert response.status_code == 409
    assert "/questions" in body(response)["detail"]


def test_forget_cascades_and_is_the_only_deletion_path():
    h = Harness.build()

    async def run():
        user, headers = await h.user()
        cgpa = fact("student", "cgpa", 7.6, user_id=user.id)
        belief = derived("not eligible", user_id=user.id)
        unrelated = fact("student", "batch", 2027, user_id=user.id)
        await h.seed(cgpa, belief, unrelated, link(cgpa, belief))
        async with h.client() as c:
            forgotten = await c.post(f"/memories/{cgpa.id}/forget", headers=headers)
            after = await c.get(f"/memories/{cgpa.id}", headers=headers)
            remaining = await c.get("/memories", headers=headers)
        return cgpa, belief, unrelated, forgotten, after, remaining

    cgpa, belief, unrelated, forgotten, after, remaining = asyncio.run(run())
    assert forgotten.status_code == 200
    event = body(forgotten)["event"]
    assert sorted(event["deleted_ids"]) == sorted([cgpa.id, belief.id])
    assert after.status_code == 404
    assert _ids(remaining) == [unrelated.id]
    assert len(h.store.forget_events()) == 1
