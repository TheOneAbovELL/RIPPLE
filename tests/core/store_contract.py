"""Contract every Store implementation must satisfy.

Subclass, provide a `store` fixture, and every test here runs against it. The
in-memory store runs offline; the Postgres store runs under the slow marker.
"""

import asyncio
from datetime import timedelta

import pytest

from ripple.core.models import Status
from ripple.core.store import ChangeEventNotFoundError, MemoryNotFoundError, Store
from tests.builders import USER, change_event, derived, fact, link, memory
from tests.fakes.clock import DEFAULT_START


class StoreContract:
    async def _seed(self, store: Store):
        cgpa = fact("student", "cgpa", 7.6)
        eligibility = derived("not eligible for Acme (cutoff 7.8)")
        edge = link(cgpa, eligibility, link_type="depends_on_fact")
        async with store.transaction() as tx:
            await tx.add_memory(cgpa)
            await tx.add_memory(eligibility)
            await tx.add_link(edge)
        return cgpa, eligibility, edge

    def test_get_memory_returns_what_was_added(self, store: Store):
        cgpa, _, _ = asyncio.run(self._seed(store))
        assert asyncio.run(store.get_memory(cgpa.id)) == cgpa

    def test_get_memory_unknown_id_raises(self, store: Store):
        with pytest.raises(MemoryNotFoundError):
            asyncio.run(store.get_memory("nope"))

    def test_get_memories_preserves_order(self, store: Store):
        cgpa, eligibility, _ = asyncio.run(self._seed(store))
        found = asyncio.run(store.get_memories([eligibility.id, cgpa.id]))
        assert [m.id for m in found] == [eligibility.id, cgpa.id]

    def test_memories_for_user_filters_by_status(self, store: Store):
        cgpa, eligibility, _ = asyncio.run(self._seed(store))

        async def retire():
            async with store.transaction() as tx:
                await tx.replace_memory(eligibility.model_copy(update={"status": Status.RETIRED}))

        asyncio.run(retire())
        valid = asyncio.run(store.memories_for_user(USER, [Status.VALID]))
        assert [m.id for m in valid] == [cgpa.id]
        everything = asyncio.run(store.memories_for_user(USER))
        assert {m.id for m in everything} == {cgpa.id, eligibility.id}

    def test_dependents_and_parents_follow_link_direction(self, store: Store):
        cgpa, eligibility, edge = asyncio.run(self._seed(store))
        assert asyncio.run(store.dependents_of(cgpa.id)) == [edge]
        assert asyncio.run(store.parents_of(eligibility.id)) == [edge]
        assert asyncio.run(store.dependents_of(eligibility.id)) == []

    def test_links_for_user_returns_only_that_users_links(self, store: Store):
        _cgpa, _eligibility, edge = asyncio.run(self._seed(store))
        other = memory(user_id="student-2", content="other user's fact")
        other_derived = memory(user_id="student-2", content="other user's belief")

        async def write():
            async with store.transaction() as tx:
                await tx.add_memory(other)
                await tx.add_memory(other_derived)
                await tx.add_link(link(other, other_derived))

        asyncio.run(write())
        assert asyncio.run(store.links_for_user(USER)) == [edge]
        assert len(asyncio.run(store.links_for_user("student-2"))) == 1

    def test_add_link_requires_both_endpoints(self, store: Store):
        cgpa, _, _ = asyncio.run(self._seed(store))

        async def dangling():
            async with store.transaction() as tx:
                await tx.add_link(link(cgpa, "ghost"))

        with pytest.raises(MemoryNotFoundError):
            asyncio.run(dangling())

    def test_version_chain_and_latest_version(self, store: Store):
        cgpa, _, _ = asyncio.run(self._seed(store))
        day = timedelta(days=1)
        v2 = fact("student", "cgpa", 7.9, version=2, supersedes_id=cgpa.id, at=DEFAULT_START + day)
        v3 = fact(
            "student", "cgpa", 8.1, version=3, supersedes_id=v2.id, at=DEFAULT_START + 2 * day
        )

        async def add_versions():
            async with store.transaction() as tx:
                await tx.add_memory(v2)
                await tx.add_memory(v3)

        asyncio.run(add_versions())
        chain = asyncio.run(store.version_chain(v2.id))
        assert [m.version for m in chain] == [1, 2, 3]
        assert asyncio.run(store.latest_version(cgpa.id)).id == v3.id
        assert asyncio.run(store.latest_version(v3.id)).id == v3.id

    def test_transaction_rolls_back_every_write_on_error(self, store: Store):
        cgpa, _eligibility, edge = asyncio.run(self._seed(store))
        extra = derived("something new")

        async def failing():
            async with store.transaction() as tx:
                await tx.add_memory(extra)
                await tx.delete_links([edge.id])
                await tx.replace_memory(cgpa.model_copy(update={"status": Status.RETIRED}))
                raise RuntimeError("crash mid-update")

        with pytest.raises(RuntimeError):
            asyncio.run(failing())
        with pytest.raises(MemoryNotFoundError):
            asyncio.run(store.get_memory(extra.id))
        assert asyncio.run(store.dependents_of(cgpa.id)) == [edge]
        assert asyncio.run(store.get_memory(cgpa.id)).status is Status.VALID

    def test_change_events_open_and_completed(self, store: Store):
        cgpa, _, _ = asyncio.run(self._seed(store))
        event = change_event(cgpa)

        async def write():
            async with store.transaction() as tx:
                await tx.add_change_event(event)

        asyncio.run(write())
        assert asyncio.run(store.open_change_events(USER)) == [event]
        done = event.model_copy(update={"completed_at": DEFAULT_START + timedelta(minutes=1)})

        async def complete():
            async with store.transaction() as tx:
                await tx.replace_change_event(done)

        asyncio.run(complete())
        assert asyncio.run(store.open_change_events(USER)) == []
        assert asyncio.run(store.get_change_event(event.id)) == done

    def test_get_change_event_unknown_id_raises(self, store: Store):
        with pytest.raises(ChangeEventNotFoundError):
            asyncio.run(store.get_change_event("nope"))

    def test_memories_expiring_at_returns_only_valid_expired(self, store: Store):
        exam_busy = memory(content="busy with exams", valid_to=DEFAULT_START + timedelta(days=30))
        retired = memory(
            content="old", valid_to=DEFAULT_START + timedelta(days=1), status=Status.RETIRED
        )
        permanent = memory(content="likes Python")

        async def write():
            async with store.transaction() as tx:
                for m in (exam_busy, retired, permanent):
                    await tx.add_memory(m)

        asyncio.run(write())
        assert (
            asyncio.run(store.memories_expiring_at(USER, DEFAULT_START + timedelta(days=29))) == []
        )
        expired = asyncio.run(store.memories_expiring_at(USER, DEFAULT_START + timedelta(days=30)))
        assert [m.id for m in expired] == [exam_busy.id]

    def test_events_asking_finds_events_with_an_ask_decision(self, store: Store):
        from ripple.core.models import DecisionAction
        from tests.builders import decision

        cgpa, eligibility, _ = asyncio.run(self._seed(store))
        asked = change_event(cgpa, decisions=[decision(eligibility, DecisionAction.ASK)])
        kept = change_event(cgpa, decisions=[decision(eligibility, DecisionAction.KEEP)])

        async def write():
            async with store.transaction() as tx:
                await tx.add_change_event(asked)
                await tx.add_change_event(kept)

        asyncio.run(write())
        assert asyncio.run(store.events_asking(eligibility.id)) == [asked]
        assert asyncio.run(store.events_asking(cgpa.id)) == []

    def test_add_link_refuses_duplicate_edge(self, store: Store):
        cgpa, eligibility, _ = asyncio.run(self._seed(store))

        async def duplicate():
            async with store.transaction() as tx:
                await tx.add_link(link(cgpa, eligibility, link_type="depends_on_fact"))

        with pytest.raises(Exception, match=r"(?i)duplicate|unique"):
            asyncio.run(duplicate())

    def test_delete_memories_refuses_rows_that_still_have_links(self, store: Store):
        _cgpa, eligibility, _ = asyncio.run(self._seed(store))

        async def delete():
            async with store.transaction() as tx:
                await tx.delete_memories([eligibility.id])

        with pytest.raises(Exception):  # noqa: B017 - the driver's error type varies
            asyncio.run(delete())

    def test_events_for_user_are_scoped_and_erasable(self, store: Store):
        from ripple.core.models import ForgetEvent

        cgpa, _, _ = asyncio.run(self._seed(store))
        mine = change_event(cgpa)
        theirs = change_event(cgpa, user_id="student-2")
        forgotten = ForgetEvent(
            user_id=USER, root_memory_id=cgpa.id, deleted_ids=[cgpa.id], created_at=DEFAULT_START
        )

        async def write():
            async with store.transaction() as tx:
                await tx.add_change_event(mine)
                await tx.add_change_event(theirs)
                await tx.add_forget_event(forgotten)

        asyncio.run(write())
        assert asyncio.run(store.change_events_for_user(USER)) == [mine]
        assert asyncio.run(store.forget_events_for_user(USER)) == [forgotten]

        async def erase():
            async with store.transaction() as tx:
                return (
                    await tx.delete_change_events_for_user(USER),
                    await tx.delete_forget_events_for_user(USER),
                )

        assert asyncio.run(erase()) == (1, 1)
        assert asyncio.run(store.change_events_for_user(USER)) == []
        assert asyncio.run(store.change_events_for_user("student-2")) == [theirs]

    def test_delete_memories_and_links(self, store: Store):
        cgpa, eligibility, edge = asyncio.run(self._seed(store))

        async def delete():
            async with store.transaction() as tx:
                await tx.delete_links([edge.id])
                await tx.delete_memories([eligibility.id])

        asyncio.run(delete())
        with pytest.raises(MemoryNotFoundError):
            asyncio.run(store.get_memory(eligibility.id))
        assert asyncio.run(store.dependents_of(cgpa.id)) == []
