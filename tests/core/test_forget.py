import asyncio

import pytest

from ripple.core.forget import forget
from ripple.core.store import MemoryNotFoundError
from ripple.core.versioning import write_new_version
from tests.builders import derived, fact, link, snapshot_link
from tests.fakes.clock import FakeClock
from tests.fakes.store import InMemoryStore


def _seed(store: InMemoryStore):
    """cgpa(v1,v2) -> eligibility -> recommendation; resume <-snapshot- application; skills."""
    cgpa = fact("student", "cgpa", 7.6)
    eligibility = derived("not eligible for Acme")
    recommendation = derived("skip Acme")
    resume = fact("student", "resume", "v1")
    application = derived("applied with resume v1", kind="application")
    skills = fact("student", "skills", "python")

    async def write():
        async with store.transaction() as tx:
            for m in (cgpa, eligibility, recommendation, resume, application, skills):
                await tx.add_memory(m)
            await tx.add_link(link(cgpa, eligibility))
            await tx.add_link(link(eligibility, recommendation))
            await tx.add_link(snapshot_link(resume, application))
            cgpa_v2 = await write_new_version(
                tx,
                cgpa,
                content="CGPA is 7.9",
                structured=None,
                valid_to=None,
                created_by="user",
                now=FakeClock().now(),
            )
        return cgpa_v2

    cgpa_v2 = asyncio.run(write())
    return cgpa, cgpa_v2, eligibility, recommendation, resume, application, skills


def test_forget_deletes_whole_version_chain_and_depends_on_cascade():
    store = InMemoryStore()
    cgpa, cgpa_v2, eligibility, recommendation, *_ = _seed(store)
    event = asyncio.run(forget(store, FakeClock(), cgpa.id))
    assert set(event.deleted_ids) == {cgpa.id, cgpa_v2.id, eligibility.id, recommendation.id}
    for gone in event.deleted_ids:
        with pytest.raises(MemoryNotFoundError):
            asyncio.run(store.get_memory(gone))
    assert store.forget_events() == [event]


def test_forget_from_a_newer_version_deletes_the_older_ones_too():
    store = InMemoryStore()
    cgpa, cgpa_v2, *_ = _seed(store)
    event = asyncio.run(forget(store, FakeClock(), cgpa_v2.id))
    assert cgpa.id in event.deleted_ids and cgpa_v2.id in event.deleted_ids


def test_forget_removes_snapshot_link_but_keeps_the_dependent():
    store = InMemoryStore()
    *_, resume, application, _skills = _seed(store)
    event = asyncio.run(forget(store, FakeClock(), resume.id))
    assert event.deleted_ids == [resume.id]
    assert asyncio.run(store.get_memory(application.id)).content.startswith("applied")
    assert asyncio.run(store.parents_of(application.id)) == []


def test_forget_leaves_unrelated_memories_and_links_alone():
    store = InMemoryStore()
    cgpa, _, _, _, resume, application, skills = _seed(store)
    asyncio.run(forget(store, FakeClock(), cgpa.id))
    assert asyncio.run(store.get_memory(skills.id)) == skills
    assert [edge.dependent_id for edge in asyncio.run(store.dependents_of(resume.id))] == [
        application.id
    ]


def test_forget_leaves_no_dangling_links():
    store = InMemoryStore()
    cgpa, *_ = _seed(store)
    asyncio.run(forget(store, FakeClock(), cgpa.id))
    remaining = {m.id for m in store.all_memories()}
    for edge in store.all_links():
        assert edge.parent_id in remaining and edge.dependent_id in remaining


def test_forget_unknown_memory_raises_and_writes_nothing():
    store = InMemoryStore()
    _seed(store)
    with pytest.raises(MemoryNotFoundError):
        asyncio.run(forget(store, FakeClock(), "ghost"))
    assert store.forget_events() == []
