"""/me: identity, Telegram linking, export and delete (FR-15, ADR-0044)."""

import asyncio
from datetime import timedelta

from ripple.core.models import Status
from ripple.storage.users import link_telegram
from tests.api.fakes import ScriptedResumeParser, candidate_fact
from tests.api.harness import Harness, body
from tests.builders import derived, fact, link

PDF = b"%PDF-1.4 test"


def test_telegram_link_code_is_one_time_and_expires():
    h = Harness.build()

    async def run():
        user, headers = await h.user()
        async with h.client() as c:
            before = await c.get("/me", headers=headers)
            issued = await c.post("/me/telegram/link", headers=headers)
            code = body(issued)["code"]
            # The worker side (WS-6) consumes the code with the chat id it saw.
            linked = await link_telegram(h.user_store, code, 123456, h.clock.now())
            reused = await link_telegram(h.user_store, code, 999, h.clock.now())
            after = await c.get("/me", headers=headers)
            stale = body(await c.post("/me/telegram/link", headers=headers))["code"]
            h.clock.advance(timedelta(minutes=16))
            expired = await link_telegram(h.user_store, stale, 999, h.clock.now())
        return user, before, issued, linked, reused, after, expired

    user, before, issued, linked, reused, after, expired = asyncio.run(run())
    assert body(before)["telegram_linked"] is False
    assert issued.status_code == 201
    assert len(body(issued)["code"]) == 12
    assert linked is not None and linked.id == user.id and linked.telegram_chat_id == 123456
    assert reused is None
    assert body(after)["telegram_linked"] is True
    assert expired is None


def test_export_contains_everything_including_history_and_candidates():
    h = Harness.build(resume_parser=ScriptedResumeParser(candidate_fact("cgpa", 7.6, "CGPA 7.6")))

    async def run():
        user, headers = await h.user()
        other, _ = await h.user("Bina")
        retired = fact("student", "batch", 2026, user_id=user.id, status=Status.RETIRED)
        theirs = fact("student", "batch", 2027, user_id=other.id)
        await h.seed(retired, theirs)
        async with h.client() as c:
            await c.post(
                "/resume", files={"file": ("r.pdf", PDF, "application/pdf")}, headers=headers
            )
            cgpa = body(
                await c.post(
                    "/statements",
                    json={
                        "content": "CGPA is 7.6",
                        "kind": "fact",
                        "structured": {"subject": "student", "attribute": "cgpa", "value": 7.6},
                    },
                    headers=headers,
                )
            )["memory"]
            belief = body(
                await c.post(
                    "/statements",
                    json={"content": "eligible since cgpa above cutoff", "kind": "derived"},
                    headers=headers,
                )
            )["memory"]
            await c.post(f"/memories/{belief['id']}/forget", headers=headers)
            export = await c.get("/me/export", headers=headers)
        return user, retired, cgpa, export

    user, retired, cgpa, export = asyncio.run(run())
    assert export.status_code == 200, export.text
    out = body(export)
    assert out["user"]["id"] == user.id
    assert sorted(m["id"] for m in out["memories"]) == sorted([retired.id, cgpa["id"]])
    assert len(out["change_events"]) == 2
    assert len(out["forget_events"]) == 1
    assert len(out["resume_candidates"]) == 1
    assert out["links"] == []  # the linked belief was forgotten with its link
    assert all(m["user_id"] == user.id for m in out["memories"])


def test_delete_me_forgets_everything_and_revokes_the_token():
    h = Harness.build(resume_parser=ScriptedResumeParser(candidate_fact("cgpa", 7.6, "CGPA 7.6")))

    async def run():
        user, headers = await h.user()
        other, other_h = await h.user("Bina")
        cgpa = fact("student", "cgpa", 7.6, user_id=user.id)
        belief = derived("not eligible", user_id=user.id)
        lonely = fact("student", "batch", 2027, user_id=user.id)
        theirs = fact("student", "batch", 2027, user_id=other.id)
        await h.seed(cgpa, belief, lonely, theirs, link(cgpa, belief))
        async with h.client() as c:
            await c.post(
                "/resume", files={"file": ("r.pdf", PDF, "application/pdf")}, headers=headers
            )
            await c.post("/me/telegram/link", headers=headers)
            deleted = await c.delete("/me", headers=headers)
            afterwards = await c.get("/me", headers=headers)
            other_still = await c.get("/memories", headers=other_h)
        return user, deleted, afterwards, other_still

    user, deleted, afterwards, other_still = asyncio.run(run())
    assert deleted.status_code == 204
    assert afterwards.status_code == 401
    assert [m for m in h.store.all_memories() if m.user_id == user.id] == []
    assert h.store.all_links() == []
    assert len(body(other_still)["memories"]) == 1
    assert h.user_store.users.get(user.id) is None
    assert all(t.user_id != user.id for t in h.user_store.tokens.values())
    assert all(code.user_id != user.id for code in h.user_store.codes.values())
    assert asyncio.run(h.candidate_store.candidates_for_user(user.id)) == []
    # The audit of the deletion stays: ids and timestamps, no content.
    assert {e.user_id for e in h.store.forget_events()} == {user.id}
    deleted_ids = sorted(i for e in h.store.forget_events() for i in e.deleted_ids)
    assert len(deleted_ids) == 3
    # FR-15: the user's ChangeEvents are erased with the data; ForgetEvents stay as audit.
    assert [e for e in h.store.change_events() if e.user_id == user.id] == []


def test_delete_me_erases_the_users_delivery_records():
    import dataclasses

    from ripple.api.app import create_app
    from ripple.notify.contracts import AlertKind
    from ripple.notify.delivery_log import InMemoryDeliveryLog

    h = Harness.build()
    log = InMemoryDeliveryLog()
    h.services = dataclasses.replace(h.services, delivery_log=log)
    h.app = create_app(h.services)

    async def run():
        user, headers = await h.user()
        await log.record_digest(user.id, h.clock.now().date())
        await log.record_alert(user.id, "o1", AlertKind.HIGH_FIT, h.clock.now())
        async with h.client() as c:
            deleted = await c.delete("/me", headers=headers)
        return user, deleted

    user, deleted = asyncio.run(run())
    assert deleted.status_code == 204
    assert asyncio.run(log.last_digest_day(user.id)) is None
    assert asyncio.run(log.last_alert_at(user.id, "o1", AlertKind.HIGH_FIT)) is None
