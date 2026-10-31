"""Crash-recovery and concurrency edge cases the first review asked for (ADR-0013, NFR-4)."""

import asyncio
from datetime import timedelta

import pytest

from ripple.core.answers import answer_no_longer_holds, confirm_still_holds
from ripple.core.models import Status, TriggerKind
from ripple.core.ripple import RippleRunner
from ripple.core.sweep import NightlySweep
from ripple.core.writes import update_memory
from tests.builders import USER, derived, fact, link, memory
from tests.fakes.clock import DEFAULT_START, FakeClock
from tests.fakes.engine import ScriptedEngine
from tests.fakes.resolver import ExplodingResolver, ScriptedResolver, ask, keep, update
from tests.fakes.store import InMemoryStore


def _runner(store, resolver, clock, *waves):
    class Factory(ScriptedEngine):
        def __init__(self, max_depth: int = 8) -> None:
            super().__init__(*waves, max_depth=max_depth)

    return RippleRunner(store, resolver, clock, engine_factory=Factory)  # type: ignore[arg-type]


def _update(store, clock, memory_id, content="CGPA is 7.9"):
    return asyncio.run(
        update_memory(
            store,
            clock,
            memory_id,
            content=content,
            structured=None,
            valid_to=None,
            created_by="user",
            kind=TriggerKind.USER_EDIT,
        )
    )


def _seed(store, *memories, links=()):
    async def write():
        async with store.transaction() as tx:
            for m in memories:
                await tx.add_memory(m)
            for edge in links:
                await tx.add_link(edge)

    asyncio.run(write())


# ---- B1: resume after a crash in wave 2, with a history member in wave 1 -----------


def test_resume_after_crash_in_wave_two_resolves_wave_two_not_history():
    store, clock = InMemoryStore(), FakeClock()
    cgpa = fact("student", "cgpa", 7.6)
    eligibility = derived("not eligible")
    recommendation = derived("skip Acme")
    _seed(
        store,
        cgpa,
        eligibility,
        recommendation,
        links=[link(cgpa, eligibility), link(eligibility, recommendation)],
    )
    # Make eligibility v1 history with a live v2, so wave 1 contains a RETIRED member.
    eligibility_v2, first_event = _update(store, clock, eligibility.id, "eligibility v2")
    asyncio.run(
        _runner(store, ScriptedResolver({}, default=keep()), clock, [recommendation.id]).run(
            first_event
        )
    )

    _, event = _update(store, clock, cgpa.id)
    exploding = ExplodingResolver(
        ScriptedResolver({}, default=update("changed")), explode_on_call=2
    )
    with pytest.raises(ConnectionError):
        asyncio.run(
            _runner(
                store, exploding, clock, [eligibility.id, eligibility_v2.id], [recommendation.id]
            ).run(event)
        )

    crashed = asyncio.run(store.get_change_event(event.id))
    assert crashed.affected_ids == [eligibility_v2.id, recommendation.id]  # history never affected
    assert [d.wave for d in crashed.decisions] == [1]
    assert asyncio.run(store.get_memory(recommendation.id)).status is Status.SUSPECT

    resumer = _runner(
        store,
        ScriptedResolver({}, default=update("changed again")),
        clock,
        [eligibility.id, eligibility_v2.id],
        [recommendation.id],
    )
    done = asyncio.run(resumer.resume(crashed))
    assert done.completed_at is not None
    assert [d.wave for d in done.decisions] == [1, 2]
    assert done.decisions[1].memory_id == recommendation.id
    assert asyncio.run(store.latest_version(recommendation.id)).content == "changed again"


# ---- T2: a failure inside commit two rolls back to the SUSPECT state ---------------


class FailingSecondCommitStore(InMemoryStore):
    """replace_change_event raises once a decision is being appended (commit two)."""

    def __init__(self) -> None:
        super().__init__()
        self.exploded = False

    async def replace_change_event(self, event):
        if event.decisions and not self.exploded and event.completed_at is None:
            self.exploded = True
            raise RuntimeError("disk full during commit two")
        await super().replace_change_event(event)


def test_failed_commit_two_leaves_wave_suspect_and_no_new_version():
    store, clock = FailingSecondCommitStore(), FakeClock()
    cgpa = fact("student", "cgpa", 7.6)
    eligibility = derived("not eligible")
    _seed(store, cgpa, eligibility, links=[link(cgpa, eligibility)])
    _, event = _update(store, clock, cgpa.id)
    runner = _runner(
        store, ScriptedResolver({eligibility.id: update("eligible")}), clock, [eligibility.id]
    )
    with pytest.raises(RuntimeError, match="commit two"):
        asyncio.run(runner.run(event))
    assert asyncio.run(store.get_memory(eligibility.id)).status is Status.SUSPECT
    assert asyncio.run(store.latest_version(eligibility.id)).id == eligibility.id
    reopened = asyncio.run(store.get_change_event(event.id))
    assert reopened.decisions == [] and reopened.is_open


# ---- M5: rows are re-read inside commit two -----------------------------------------


def test_member_answered_between_commits_is_skipped_not_overwritten():
    store, clock = InMemoryStore(), FakeClock()
    cgpa = fact("student", "cgpa", 7.6)
    eligibility = derived("not eligible")
    _seed(store, cgpa, eligibility, links=[link(cgpa, eligibility)])
    _, event = _update(store, clock, cgpa.id)

    class ForgetsDuringResolve(ScriptedResolver):
        async def resolve(self, context):
            async with store.transaction() as tx:
                retired = (await tx.get_memory(eligibility.id)).model_copy(
                    update={"status": Status.RETIRED}
                )
                await tx.replace_memory(retired)
            return await super().resolve(context)

    runner = _runner(
        store, ForgetsDuringResolve({}, default=update("eligible")), clock, [eligibility.id]
    )
    done = asyncio.run(runner.run(event))
    assert done.decisions == []
    assert asyncio.run(store.get_memory(eligibility.id)).status is Status.RETIRED
    assert asyncio.run(store.latest_version(eligibility.id)).id == eligibility.id


# ---- M1/M2: parked subtrees are recorded and restored exactly ----------------------


def _two_asks_sharing_a_child(store, clock):
    """cgpa -> a(ask), cgpa -> b(ask); a -> child, b -> child."""
    cgpa = fact("student", "cgpa", 7.6)
    a = derived("belief A")
    b = derived("belief B")
    child = derived("depends on A and B")
    _seed(
        store,
        cgpa,
        a,
        b,
        child,
        links=[link(cgpa, a), link(cgpa, b), link(a, child), link(b, child)],
    )
    _, event = _update(store, clock, cgpa.id)
    runner = _runner(
        store, ScriptedResolver({a.id: ask("A?"), b.id: ask("B?")}), clock, [a.id, b.id]
    )
    done = asyncio.run(runner.run(event))
    assert asyncio.run(store.get_memory(child.id)).status is Status.SUSPECT
    return cgpa, a, b, child, done


def test_ask_records_parked_ids_on_the_event():
    store, clock = InMemoryStore(), FakeClock()
    _, a, _b, child, done = _two_asks_sharing_a_child(store, clock)
    # The first ask parked the child; the second found it already SUSPECT and parked nothing.
    assert done.parked == {a.id: [child.id]}


def test_confirming_one_ask_does_not_restore_a_child_still_parked_by_another_question():
    store, clock = InMemoryStore(), FakeClock()
    _, a, b, child, _ = _two_asks_sharing_a_child(store, clock)  # b parked nothing
    asyncio.run(confirm_still_holds(store, clock, b.id))  # b parked nothing
    assert asyncio.run(store.get_memory(child.id)).status is Status.SUSPECT
    asyncio.run(confirm_still_holds(store, clock, a.id))
    assert asyncio.run(store.get_memory(child.id)).status is Status.VALID


def test_no_longer_holds_with_keep_in_wave_one_does_not_strand_grandchildren():
    store, clock = InMemoryStore(), FakeClock()
    cgpa = fact("student", "cgpa", 7.6)
    eligibility = derived("not eligible")
    recommendation = derived("skip Acme")
    deeper = derived("do not prepare for Acme")
    _seed(
        store,
        cgpa,
        eligibility,
        recommendation,
        deeper,
        links=[
            link(cgpa, eligibility),
            link(eligibility, recommendation),
            link(recommendation, deeper),
        ],
    )
    _, event = _update(store, clock, cgpa.id)
    asyncio.run(
        _runner(store, ScriptedResolver({eligibility.id: ask()}), clock, [eligibility.id]).run(
            event
        )
    )
    assert asyncio.run(store.get_memory(deeper.id)).status is Status.SUSPECT

    runner = _runner(
        store, ScriptedResolver({recommendation.id: keep()}), clock, [recommendation.id]
    )
    answered = asyncio.run(answer_no_longer_holds(store, clock, runner, eligibility.id))
    assert asyncio.run(store.get_memory(deeper.id)).status is Status.VALID
    assert asyncio.run(store.get_memory(recommendation.id)).status is Status.VALID
    # The answer event records the retirement and both restorations before wave 1.
    assert [d.wave for d in answered.decisions] == [0, 0, 0, 1]


# ---- M3: a resolver update keeps valid_to and structured fields --------------------


def test_resolver_update_carries_valid_to_and_structured_forward():
    store, clock = InMemoryStore(), FakeClock()
    cgpa = fact("student", "cgpa", 7.6)
    until = DEFAULT_START + timedelta(days=10)
    temp_belief = fact("student", "availability", "limited", valid_to=until)
    _seed(store, cgpa, temp_belief, links=[link(cgpa, temp_belief)])
    _, event = _update(store, clock, cgpa.id)
    runner = _runner(
        store,
        ScriptedResolver({temp_belief.id: update("still limited, different reason")}),
        clock,
        [temp_belief.id],
    )
    asyncio.run(runner.run(event))
    latest = asyncio.run(store.latest_version(temp_belief.id))
    assert latest.valid_to == until
    assert latest.structured == temp_belief.structured


# ---- sweep re-reads before retiring ---------------------------------------------------


def test_sweep_skips_a_memory_an_earlier_ripple_already_retired():
    store, clock = InMemoryStore(), FakeClock()
    first = memory(content="temp A", valid_to=DEFAULT_START + timedelta(days=1))
    # Recorded a minute later so the sweep visits A first (order is by recorded_at, id).
    second = memory(
        content="temp B",
        valid_to=DEFAULT_START + timedelta(days=1),
        at=DEFAULT_START + timedelta(minutes=1),
    )
    _seed(store, first, second, links=[link(first, second)])
    clock.advance(timedelta(days=2))
    # Expiring A retires B through the ripple; the sweep must not then expire B again.
    from tests.fakes.resolver import retire

    runner = _runner(store, ScriptedResolver({second.id: retire()}), clock, [second.id])
    events = asyncio.run(NightlySweep(store, runner, clock).expire(USER))
    assert [e.trigger_memory_id for e in events] == [first.id]
    assert asyncio.run(store.get_memory(second.id)).status is Status.RETIRED
