"""FR-8's second trigger (ADR-0079): a ripple that changes the criteria queues a Scout run."""

import asyncio

from ripple.agents.scout import CriteriaChangeObserver
from ripple.core.models import Decision, DecisionAction
from ripple.domains.jobs.derive import derive_criteria
from ripple.domains.jobs.profile import record_profile_fact
from ripple.domains.jobs.vocabulary import ProfileAttribute
from tests.builders import USER, change_event, derived, fact
from tests.domains.jobs.helpers import make_runner, run
from tests.fakes.clock import FakeClock
from tests.fakes.store import InMemoryStore


class RecordingTrigger:
    def __init__(self) -> None:
        self.users: list[str] = []

    async def on_criteria_changed(self, user_id: str) -> None:
        self.users.append(user_id)


def _seed(store, *memories):
    async def write():
        async with store.transaction() as tx:
            for memory in memories:
                await tx.add_memory(memory)

    asyncio.run(write())


def test_observer_triggers_when_the_event_was_triggered_by_a_criteria_memory():
    store, trigger = InMemoryStore(), RecordingTrigger()
    criteria = derived("search openings with batch 2027", kind="criteria")
    _seed(store, criteria)

    run(CriteriaChangeObserver(store, trigger).event_completed(change_event(criteria)))

    assert trigger.users == [USER]


def test_observer_triggers_when_the_event_updated_a_criteria_memory():
    store, trigger = InMemoryStore(), RecordingTrigger()
    cgpa = fact("student", "cgpa", 8.1)
    criteria = derived("search openings with cgpa_cutoff <= 7.6", kind="criteria")
    _seed(store, cgpa, criteria)
    update = Decision(
        memory_id=criteria.id,
        action=DecisionAction.UPDATE,
        reason="cgpa rose",
        wave=1,
        new_version_id="v2",
    )

    run(
        CriteriaChangeObserver(store, trigger).event_completed(
            change_event(cgpa, decisions=[update])
        )
    )

    assert trigger.users == [USER]


def test_observer_stays_quiet_for_an_event_that_left_the_criteria_alone():
    store, trigger = InMemoryStore(), RecordingTrigger()
    cgpa = fact("student", "cgpa", 8.1)
    eligibility = derived("eligible for Acme")
    _seed(store, cgpa, eligibility)
    update = Decision(
        memory_id=eligibility.id,
        action=DecisionAction.UPDATE,
        reason="cgpa rose",
        wave=1,
        new_version_id="v2",
    )

    run(
        CriteriaChangeObserver(store, trigger).event_completed(
            change_event(cgpa, decisions=[update])
        )
    )

    assert trigger.users == []


def test_deriving_criteria_through_a_runner_with_the_observer_queues_one_scout_run():
    store, clock, trigger = InMemoryStore(), FakeClock(), RecordingTrigger()
    plain = make_runner(store, clock)
    run(record_profile_fact(store, clock, plain, USER, ProfileAttribute.CGPA, 8.1))
    observed = make_runner(store, clock, observers=[CriteriaChangeObserver(store, trigger)])

    run(derive_criteria(store, clock, observed, USER))

    assert trigger.users == [USER]
