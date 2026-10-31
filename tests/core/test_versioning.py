import asyncio
from datetime import timedelta

import pytest

from ripple.core.models import LinkClass, Status, StructuredFact
from ripple.core.versioning import write_new_version
from tests.builders import derived, fact, link, snapshot_link
from tests.fakes.clock import DEFAULT_START
from tests.fakes.store import InMemoryStore

LATER = DEFAULT_START + timedelta(days=1)


def _graph(store: InMemoryStore):
    """resume_v1 <- application (snapshot); cgpa -> eligibility -> recommendation."""
    cgpa = fact("student", "cgpa", 7.6)
    eligibility = derived("not eligible")
    recommendation = derived("skip Acme")
    resume = fact("student", "resume", "v1")
    application = derived("applied to Acme with resume v1", kind="application")

    async def write():
        async with store.transaction() as tx:
            for m in (cgpa, eligibility, recommendation, resume, application):
                await tx.add_memory(m)
            await tx.add_link(link(cgpa, eligibility))
            await tx.add_link(link(eligibility, recommendation))
            await tx.add_link(snapshot_link(resume, application))

    asyncio.run(write())
    return cgpa, eligibility, recommendation, resume, application


def _update(store: InMemoryStore, old, content: str, structured=None):
    async def go():
        async with store.transaction() as tx:
            return await write_new_version(
                tx,
                old,
                content=content,
                structured=structured,
                valid_to=None,
                created_by="user",
                now=LATER,
            )

    return asyncio.run(go())


def test_new_version_increments_and_retires_the_old_row():
    store = InMemoryStore()
    cgpa, *_ = _graph(store)
    v2 = _update(
        store, cgpa, "CGPA is 7.9", StructuredFact(subject="student", attribute="cgpa", value=7.9)
    )
    assert (v2.version, v2.supersedes_id, v2.status) == (2, cgpa.id, Status.VALID)
    assert v2.valid_from == LATER
    assert asyncio.run(store.get_memory(cgpa.id)).status is Status.RETIRED
    assert asyncio.run(store.latest_version(cgpa.id)).id == v2.id


def test_new_version_copies_incoming_depends_on_links():
    store = InMemoryStore()
    cgpa, eligibility, *_ = _graph(store)
    v2 = _update(store, cgpa, "CGPA is 7.9")
    copied = asyncio.run(store.dependents_of(v2.id))
    assert [edge.dependent_id for edge in copied] == [eligibility.id]
    assert copied[0].link_class is LinkClass.DEPENDS_ON
    # The old row keeps its link as history.
    assert [edge.dependent_id for edge in asyncio.run(store.dependents_of(cgpa.id))] == [
        eligibility.id
    ]


def test_new_version_copies_outgoing_links_repointed_at_latest_parent():
    store = InMemoryStore()
    cgpa, eligibility, *_ = _graph(store)
    cgpa_v2 = _update(store, cgpa, "CGPA is 7.9")
    eligibility_v2 = _update(store, eligibility, "eligible")
    parents = asyncio.run(store.parents_of(eligibility_v2.id))
    assert [p.parent_id for p in parents] == [cgpa_v2.id]


def test_second_change_to_parent_reaches_the_updated_dependent():
    store = InMemoryStore()
    cgpa, eligibility, *_ = _graph(store)
    cgpa_v2 = _update(store, cgpa, "CGPA is 7.9")
    eligibility_v2 = _update(store, eligibility, "eligible")
    cgpa_v3 = _update(store, cgpa_v2, "CGPA is 8.1")
    dependents = asyncio.run(store.dependents_of(cgpa_v3.id))
    assert [d.dependent_id for d in dependents] == [eligibility_v2.id]


def test_snapshot_links_stay_on_the_old_version():
    store = InMemoryStore()
    *_, resume, application = _graph(store)
    resume_v2 = _update(store, resume, "resume v2")
    assert asyncio.run(store.dependents_of(resume_v2.id)) == []
    old_links = asyncio.run(store.dependents_of(resume.id))
    assert [edge.dependent_id for edge in old_links] == [application.id]
    assert asyncio.run(store.get_memory(application.id)).status is Status.VALID


def test_new_version_inherits_sensitivity_confidence_and_source():
    store = InMemoryStore()
    cgpa, *_ = _graph(store)
    v2 = _update(store, cgpa, "CGPA is 7.9")
    assert (v2.sensitivity, v2.confidence, v2.source_ref) == (
        cgpa.sensitivity,
        cgpa.confidence,
        cgpa.source_ref,
    )


def test_failed_update_leaves_old_version_and_links_untouched():
    store = InMemoryStore()
    cgpa, eligibility, *_ = _graph(store)

    async def go():
        async with store.transaction() as tx:
            await write_new_version(
                tx,
                cgpa,
                content="CGPA is 7.9",
                structured=None,
                valid_to=None,
                created_by="user",
                now=LATER,
            )
            raise RuntimeError("crash")

    with pytest.raises(RuntimeError):
        asyncio.run(go())
    assert asyncio.run(store.get_memory(cgpa.id)).status is Status.VALID
    assert asyncio.run(store.latest_version(cgpa.id)).id == cgpa.id
    assert len(asyncio.run(store.parents_of(eligibility.id))) == 1
