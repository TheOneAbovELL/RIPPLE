"""RippleRunner behaviour with a scripted engine and resolver (ADR-0013, ADR-0015).

The engine is human-owned, so these tests feed waves by hand and check what the runner
commits: statuses, versions, link copies, ChangeEvent contents, and crash recovery.
"""

import asyncio
from datetime import timedelta

import pytest

from ripple.core.models import DecisionAction, Status, TriggerKind
from ripple.core.ripple import RippleRunner
from ripple.core.writes import record_memory, update_memory
from tests.builders import USER, derived, fact, link
from tests.fakes.clock import FakeClock
from tests.fakes.engine import ScriptedEngine
from tests.fakes.resolver import ExplodingResolver, ScriptedResolver, ask, keep, retire, update
from tests.fakes.store import InMemoryStore


def _seed(store: InMemoryStore, clock: FakeClock):
    """cgpa -> eligibility -> recommendation; cgpa -> criteria."""
    cgpa = fact("student", "cgpa", 7.6)
    eligibility = derived("not eligible for Acme (cutoff 7.8)")
    recommendation = derived("do not apply to Acme")
    criteria = derived("search cgpa cutoff <= 7.6", kind="criteria")

    async def write():
        async with store.transaction() as tx:
            for m in (cgpa, eligibility, recommendation, criteria):
                await tx.add_memory(m)
            await tx.add_link(link(cgpa, eligibility, link_type="depends_on_fact"))
            await tx.add_link(link(eligibility, recommendation))
            await tx.add_link(link(cgpa, criteria))

    asyncio.run(write())
    return cgpa, eligibility, recommendation, criteria


def _runner(store, resolver, clock, *waves):
    engines = []

    class Factory(ScriptedEngine):
        def __init__(self, max_depth: int = 8) -> None:
            super().__init__(*waves, max_depth=max_depth)
            engines.append(self)

    runner = RippleRunner(store, resolver, clock, engine_factory=Factory)  # type: ignore[arg-type]
    return runner, engines


def test_runner_marks_wave_suspect_then_applies_keep_and_completes():
    store, clock = InMemoryStore(), FakeClock()
    cgpa, eligibility, _, criteria = _seed(store, clock)
    new, event = asyncio.run(
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
    resolver = ScriptedResolver({}, default=keep())
    runner, _ = _runner(store, resolver, clock, [eligibility.id, criteria.id])
    done = asyncio.run(runner.run(event))

    assert done.completed_at is not None
    assert done.affected_ids == [eligibility.id, criteria.id]
    assert [d.action for d in done.decisions] == [DecisionAction.KEEP, DecisionAction.KEEP]
    assert all(d.wave == 1 for d in done.decisions)
    assert asyncio.run(store.get_memory(eligibility.id)).status is Status.VALID
    # The resolver saw the new cgpa version as the parent, not the retired one.
    assert resolver.contexts[0].parents[0].id == new.id
    assert resolver.contexts[0].trigger.id == new.id


def test_runner_update_creates_new_version_and_feeds_successor_to_engine():
    store, clock = InMemoryStore(), FakeClock()
    cgpa, eligibility, recommendation, criteria = _seed(store, clock)
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
    resolver = ScriptedResolver(
        {eligibility.id: update("eligible for Acme"), criteria.id: keep()},
        default=update("apply to Acme"),
    )
    runner, engines = _runner(
        store, resolver, clock, [eligibility.id, criteria.id], [recommendation.id]
    )
    done = asyncio.run(runner.run(event))

    first_outcomes = engines[0].outcomes[0]
    assert [(o.memory_id, o.changed) for o in first_outcomes] == [
        (eligibility.id, True),
        (criteria.id, False),
    ]
    successor = first_outcomes[0].successor_id
    assert successor is not None
    new_eligibility = asyncio.run(store.get_memory(successor))
    assert (new_eligibility.version, new_eligibility.content) == (2, "eligible for Acme")
    assert asyncio.run(store.get_memory(eligibility.id)).status is Status.RETIRED
    # Links were copied: every dependent of the new version is a version of the
    # recommendation (v1 as history, v2 written in wave 2), and cgpa v2 is its only parent.
    dependents = asyncio.run(store.dependents_of(successor))
    latest_recommendation = asyncio.run(store.latest_version(recommendation.id))
    assert {asyncio.run(store.latest_version(edge.dependent_id)).id for edge in dependents} == {
        latest_recommendation.id
    }
    assert latest_recommendation.version == 2
    assert len(asyncio.run(store.parents_of(successor))) == 1
    assert [d.wave for d in done.decisions] == [1, 1, 2]
    assert done.decisions[0].new_version_id == successor


def test_runner_retire_sets_status_and_counts_as_changed():
    store, clock = InMemoryStore(), FakeClock()
    cgpa, eligibility, _, criteria = _seed(store, clock)
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
    runner, engines = _runner(
        store,
        ScriptedResolver({eligibility.id: retire()}, default=keep()),
        clock,
        [eligibility.id, criteria.id],
    )
    asyncio.run(runner.run(event))
    assert asyncio.run(store.get_memory(eligibility.id)).status is Status.RETIRED
    assert engines[0].outcomes[0][0].changed is True


def test_runner_ask_parks_memory_and_marks_its_subtree_suspect():
    store, clock = InMemoryStore(), FakeClock()
    cgpa, eligibility, recommendation, criteria = _seed(store, clock)
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
    resolver = ScriptedResolver(
        {eligibility.id: ask("Is Acme's cutoff still 7.8?")}, default=keep()
    )
    runner, engines = _runner(store, resolver, clock, [eligibility.id, criteria.id])
    done = asyncio.run(runner.run(event))

    assert asyncio.run(store.get_memory(eligibility.id)).status is Status.PENDING_USER
    assert asyncio.run(store.get_memory(recommendation.id)).status is Status.SUSPECT
    assert engines[0].outcomes[0][0].changed is False
    assert done.decisions[0].action is DecisionAction.ASK
    # Nothing below the ask was resolved.
    assert {c.memory.id for c in resolver.contexts} == {eligibility.id, criteria.id}


def test_runner_crash_between_commits_leaves_open_event_and_suspect_wave():
    store, clock = InMemoryStore(), FakeClock()
    cgpa, eligibility, _, criteria = _seed(store, clock)
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
    exploding = ExplodingResolver(ScriptedResolver({}, default=keep()), explode_on_call=2)
    runner, _ = _runner(store, exploding, clock, [eligibility.id, criteria.id])
    with pytest.raises(ConnectionError):
        asyncio.run(runner.run(event))

    reopened = asyncio.run(store.get_change_event(event.id))
    assert reopened.is_open
    assert reopened.affected_ids == [eligibility.id, criteria.id]
    assert reopened.decisions == []
    assert asyncio.run(store.get_memory(eligibility.id)).status is Status.SUSPECT
    assert asyncio.run(store.get_memory(criteria.id)).status is Status.SUSPECT


def test_runner_resume_finishes_the_pending_wave_and_continues():
    store, clock = InMemoryStore(), FakeClock()
    cgpa, eligibility, recommendation, criteria = _seed(store, clock)
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
    exploding = ExplodingResolver(ScriptedResolver({}, default=keep()), explode_on_call=1)
    runner, _ = _runner(store, exploding, clock, [eligibility.id, criteria.id])
    with pytest.raises(ConnectionError):
        asyncio.run(runner.run(event))

    clock.advance(timedelta(hours=6))
    resolver = ScriptedResolver({eligibility.id: update("eligible for Acme")}, default=keep())
    # On resume the scripted engine replays wave 1, then yields wave 2 for the recommendation.
    resumer, engines = _runner(
        store, resolver, clock, [eligibility.id, criteria.id], [recommendation.id]
    )
    done = asyncio.run(resumer.resume(asyncio.run(store.get_change_event(event.id))))

    assert done.completed_at is not None
    assert [d.wave for d in done.decisions] == [1, 1, 2]
    assert asyncio.run(store.get_memory(criteria.id)).status is Status.VALID
    assert asyncio.run(store.get_memory(recommendation.id)).status is Status.VALID
    assert engines[0].seeds == [done.trigger_memory_id]


def test_runner_resume_on_completed_event_is_a_no_op():
    store, clock = InMemoryStore(), FakeClock()
    cgpa, *_ = _seed(store, clock)
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
    runner, _ = _runner(store, ScriptedResolver({}), clock)
    done = asyncio.run(runner.run(event))
    assert asyncio.run(runner.resume(done)) == done


def test_record_memory_opens_event_and_runner_with_no_dependents_completes_immediately():
    store, clock = InMemoryStore(), FakeClock()
    new_fact = fact("student", "skills", "pytorch")
    event = asyncio.run(record_memory(store, clock, new_fact, []))
    assert event.trigger_kind is TriggerKind.RIPPLE
    assert event.is_open
    runner, _ = _runner(store, ScriptedResolver({}), clock)
    done = asyncio.run(runner.run(event))
    assert done.completed_at == clock.now()
    assert done.affected_ids == [] and done.decisions == []
    assert asyncio.run(store.memories_for_user(USER)) == [new_fact]


def test_runner_skips_memory_retired_between_commits():
    store, clock = InMemoryStore(), FakeClock()
    cgpa, eligibility, _, criteria = _seed(store, clock)
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

    class RetiringResolver(ScriptedResolver):
        async def resolve(self, context):
            # Simulate a concurrent forget retiring criteria before it is resolved.
            if context.memory.id == eligibility.id:
                async with store.transaction() as tx:
                    retired = (await tx.get_memory(criteria.id)).model_copy(
                        update={"status": Status.RETIRED}
                    )
                    await tx.replace_memory(retired)
            return await super().resolve(context)

    runner, _ = _runner(
        store, RetiringResolver({}, default=keep()), clock, [eligibility.id, criteria.id]
    )
    done = asyncio.run(runner.run(event))
    assert [d.memory_id for d in done.decisions] == [eligibility.id]
