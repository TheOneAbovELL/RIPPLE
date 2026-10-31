import asyncio
from datetime import timedelta

import pytest

from ripple.core.answers import (
    NotPendingError,
    answer_no_longer_holds,
    answer_with_correction,
    confirm_still_holds,
)
from ripple.core.models import DecisionAction, Status, TriggerKind
from ripple.core.ripple import RippleRunner
from ripple.core.sweep import NightlySweep
from ripple.core.writes import record_memory, update_memory
from tests.builders import USER, derived, fact, link
from tests.fakes.clock import DEFAULT_START, FakeClock
from tests.fakes.engine import ScriptedEngine
from tests.fakes.resolver import ExplodingResolver, ScriptedResolver, ask, keep, update
from tests.fakes.store import InMemoryStore


def _runner(store, resolver, clock, *waves):
    class Factory(ScriptedEngine):
        def __init__(self, max_depth: int = 8) -> None:
            super().__init__(*waves, max_depth=max_depth)

    return RippleRunner(store, resolver, clock, engine_factory=Factory)  # type: ignore[arg-type]


def _availability_graph(store: InMemoryStore):
    """exam_busy (temporary) -> availability -> recommendation."""
    exam_busy = fact(
        "student", "availability", "busy with exams", valid_to=DEFAULT_START + timedelta(days=30)
    )
    availability = derived("not available this month")
    recommendation = derived("defer applications with October interviews")

    async def write():
        async with store.transaction() as tx:
            for m in (exam_busy, availability, recommendation):
                await tx.add_memory(m)
            await tx.add_link(link(exam_busy, availability, link_type="depends_on_time_period"))
            await tx.add_link(link(availability, recommendation))

    asyncio.run(write())
    return exam_busy, availability, recommendation


# ---- expiry ------------------------------------------------------------------------


def test_sweep_retires_expired_memory_and_ripples_with_expiry_trigger():
    store, clock = InMemoryStore(), FakeClock()
    exam_busy, availability, recommendation = _availability_graph(store)
    resolver = ScriptedResolver(
        {availability.id: update("available again")}, default=update("resume applications")
    )
    sweep = NightlySweep(
        store, _runner(store, resolver, clock, [availability.id], [recommendation.id]), clock
    )

    assert asyncio.run(sweep.expire(USER)) == []  # nothing has expired yet
    clock.advance(timedelta(days=30))
    events = asyncio.run(sweep.expire(USER))

    assert len(events) == 1
    event = events[0]
    assert event.trigger_kind is TriggerKind.EXPIRY
    assert event.trigger_memory_id == exam_busy.id
    assert event.completed_at is not None
    assert asyncio.run(store.get_memory(exam_busy.id)).status is Status.RETIRED
    assert asyncio.run(store.latest_version(availability.id)).content == "available again"
    assert [d.wave for d in event.decisions] == [1, 2]


def test_sweep_expiry_is_idempotent():
    store, clock = InMemoryStore(), FakeClock()
    _availability_graph(store)
    sweep = NightlySweep(store, _runner(store, ScriptedResolver({}), clock), clock)
    clock.advance(timedelta(days=31))
    assert len(asyncio.run(sweep.expire(USER))) == 1
    assert asyncio.run(sweep.expire(USER)) == []


# ---- resume of open events ---------------------------------------------------------


def test_sweep_resumes_only_open_events_older_than_stale_after():
    store, clock = InMemoryStore(), FakeClock()
    cgpa = fact("student", "cgpa", 7.6)
    eligibility = derived("not eligible")

    async def write():
        async with store.transaction() as tx:
            await tx.add_memory(cgpa)
            await tx.add_memory(eligibility)
            await tx.add_link(link(cgpa, eligibility))

    asyncio.run(write())
    _, event = asyncio.run(
        update_memory(
            store,
            clock,
            cgpa.id,
            content="CGPA is 7.9",
            structured=None,
            valid_to=None,
            created_by="user",
            kind=TriggerKind.USER_EDIT,
        )
    )
    exploding = ExplodingResolver(ScriptedResolver({}), explode_on_call=1)
    with pytest.raises(ConnectionError):
        asyncio.run(_runner(store, exploding, clock, [eligibility.id]).run(event))

    sweep = NightlySweep(
        store,
        _runner(store, ScriptedResolver({}, default=keep()), clock, [eligibility.id]),
        clock,
        stale_after=timedelta(hours=1),
    )
    clock.advance(timedelta(minutes=30))
    assert asyncio.run(sweep.resume_open(USER)) == []  # too fresh: the runner may still be on it
    clock.advance(timedelta(hours=1))
    resumed = asyncio.run(sweep.resume_open(USER))
    assert len(resumed) == 1 and resumed[0].completed_at is not None
    assert asyncio.run(store.get_memory(eligibility.id)).status is Status.VALID
    assert asyncio.run(store.open_change_events(USER)) == []


# ---- user answers ------------------------------------------------------------------


def _pending_graph(store: InMemoryStore, clock: FakeClock):
    """cgpa -> eligibility(asked) -> recommendation(subtree suspect)."""
    cgpa = fact("student", "cgpa", 7.6)
    eligibility = derived("not eligible for Acme")
    recommendation = derived("skip Acme")

    async def write():
        async with store.transaction() as tx:
            for m in (cgpa, eligibility, recommendation):
                await tx.add_memory(m)
            await tx.add_link(link(cgpa, eligibility))
            await tx.add_link(link(eligibility, recommendation))

    asyncio.run(write())
    _, event = asyncio.run(
        update_memory(
            store,
            clock,
            cgpa.id,
            content="CGPA is 7.9",
            structured=None,
            valid_to=None,
            created_by="user",
            kind=TriggerKind.USER_EDIT,
        )
    )
    runner = _runner(store, ScriptedResolver({eligibility.id: ask()}), clock, [eligibility.id])
    asyncio.run(runner.run(event))
    assert asyncio.run(store.get_memory(eligibility.id)).status is Status.PENDING_USER
    assert asyncio.run(store.get_memory(recommendation.id)).status is Status.SUSPECT
    return cgpa, eligibility, recommendation


def test_confirm_still_holds_restores_memory_and_subtree_with_change_event():
    store, clock = InMemoryStore(), FakeClock()
    _, eligibility, recommendation = _pending_graph(store, clock)
    event = asyncio.run(confirm_still_holds(store, clock, eligibility.id))
    assert event.trigger_kind is TriggerKind.USER_ANSWER
    assert event.completed_at is not None
    assert [d.memory_id for d in event.decisions] == [eligibility.id, recommendation.id]
    assert all(d.action is DecisionAction.KEEP for d in event.decisions)
    assert asyncio.run(store.get_memory(eligibility.id)).status is Status.VALID
    assert asyncio.run(store.get_memory(recommendation.id)).status is Status.VALID


def test_answer_no_longer_holds_retires_and_ripples():
    store, clock = InMemoryStore(), FakeClock()
    _, eligibility, recommendation = _pending_graph(store, clock)
    runner = _runner(
        store,
        ScriptedResolver({recommendation.id: update("apply to Acme")}),
        clock,
        [recommendation.id],
    )
    event = asyncio.run(answer_no_longer_holds(store, clock, runner, eligibility.id))
    assert asyncio.run(store.get_memory(eligibility.id)).status is Status.RETIRED
    assert asyncio.run(store.latest_version(recommendation.id)).content == "apply to Acme"
    assert event.trigger_kind is TriggerKind.USER_ANSWER and event.completed_at is not None


def test_answer_with_correction_writes_new_version_and_ripples():
    store, clock = InMemoryStore(), FakeClock()
    _, eligibility, recommendation = _pending_graph(store, clock)
    runner = _runner(store, ScriptedResolver({}, default=keep()), clock, [recommendation.id])
    event = asyncio.run(
        answer_with_correction(store, clock, runner, eligibility.id, content="eligible for Acme")
    )
    latest = asyncio.run(store.latest_version(eligibility.id))
    assert (latest.version, latest.content, latest.created_by) == (2, "eligible for Acme", "user")
    assert event.trigger_memory_id == latest.id
    assert asyncio.run(store.get_memory(recommendation.id)).status is Status.VALID


def test_answers_refuse_memories_that_are_not_pending():
    store, clock = InMemoryStore(), FakeClock()
    plain = fact("student", "skills", "python")
    asyncio.run(record_memory(store, clock, plain, []))
    with pytest.raises(NotPendingError):
        asyncio.run(confirm_still_holds(store, clock, plain.id))
    assert asyncio.run(store.get_memory(plain.id)).status is Status.VALID
