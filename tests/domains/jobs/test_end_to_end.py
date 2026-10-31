"""Profile -> opening -> derived beliefs -> CGPA change rippled by the rules alone.

The engine is scripted (the real WaveEngine is the author's task), but the wave it
replays is exactly what `DependencyGraph` says the new CGPA's dependents are, which
the test asserts first.
"""

import pytest

from ripple.core.engine import DependencyGraph
from ripple.core.models import DecisionAction, Status, TriggerKind
from ripple.core.writes import update_memory
from ripple.domains.jobs.derive import derive_criteria, derive_for_opening
from ripple.domains.jobs.openings import record_opening
from ripple.domains.jobs.profile import profile_fact, record_profile_fact
from ripple.domains.jobs.ranking import JobsRecommender
from ripple.domains.jobs.vocabulary import ProfileAttribute
from tests.domains.jobs.helpers import USER, make_runner, parsed_acme, rules_runner, run
from tests.fakes.clock import FakeClock
from tests.fakes.store import InMemoryStore


def test_cgpa_rise_updates_eligibility_and_criteria_through_the_rules_without_an_llm():
    store, clock = InMemoryStore(), FakeClock()
    setup = make_runner(store, clock)
    cgpa, _ = run(record_profile_fact(store, clock, setup, USER, ProfileAttribute.CGPA, 7.6))
    run(record_profile_fact(store, clock, setup, USER, ProfileAttribute.BATCH, 2027))
    run(record_profile_fact(store, clock, setup, USER, ProfileAttribute.SKILL, "Python"))
    recorded = run(record_opening(store, clock, USER, parsed_acme(), setup))
    beliefs = run(derive_for_opening(store, clock, setup, recorded.anchor.id))
    criteria = run(derive_criteria(store, clock, setup, USER))
    assert beliefs.eligibility is not None and beliefs.fit is not None and criteria is not None
    assert beliefs.eligibility.structured is not None
    assert beliefs.eligibility.structured.value is False
    not_eligible_before = run(JobsRecommender(store).recommendations_for(USER, now=clock.now()))
    assert [r.eligible for r in not_eligible_before] == [False]

    # The graph (not the scripted engine) says what wave 1 must be.
    graph = DependencyGraph.from_links(run(store.links_for_user(USER)))
    assert set(graph.dependents(cgpa.id)) == {beliefs.eligibility.id, criteria.id}
    assert beliefs.fit.id not in graph.dependents(cgpa.id)

    runner, fallback = rules_runner(store, clock, runs=[[[beliefs.eligibility.id, criteria.id]]])
    new_cgpa, event = run(
        update_memory(
            store,
            clock,
            cgpa.id,
            content="CGPA is 7.9",
            structured=profile_fact(ProfileAttribute.CGPA, 7.9),
            valid_to=None,
            created_by="user",
            kind=TriggerKind.USER_EDIT,
        )
    )
    # ADR-0014: the copied link now points the beliefs at the new CGPA version.
    graph = DependencyGraph.from_links(run(store.links_for_user(USER)))
    assert set(graph.dependents(new_cgpa.id)) == {beliefs.eligibility.id, criteria.id}

    event = run(runner.run(event))

    assert fallback.contexts == []
    assert event.completed_at is not None
    assert {(d.memory_id, d.action) for d in event.decisions} == {
        (beliefs.eligibility.id, DecisionAction.UPDATE),
        (criteria.id, DecisionAction.UPDATE),
    }
    eligibility_v2 = run(store.latest_version(beliefs.eligibility.id))
    assert eligibility_v2.version == 2 and eligibility_v2.status is Status.VALID
    assert eligibility_v2.structured is not None and eligibility_v2.structured.value is True
    assert eligibility_v2.content == (
        "eligible for Software Development Engineer Intern at Acme: "
        "CGPA 7.9 >= cutoff 7.8; batch 2027 matches required batch 2027"
    )
    assert run(store.get_memory(beliefs.eligibility.id)).status is Status.RETIRED
    criteria_v2 = run(store.latest_version(criteria.id))
    assert criteria_v2.content == (
        "search openings with cgpa_cutoff <= 7.9; batch 2027; skills python"
    )
    decision = next(d for d in event.decisions if d.memory_id == beliefs.eligibility.id)
    assert new_cgpa.id in decision.evidence_refs and cgpa.id not in decision.evidence_refs
    # The fit belief was not in the wave and is untouched.
    assert run(store.get_memory(beliefs.fit.id)).status is Status.VALID
    # And the recommendation now reads the updated belief, not a recomputation.
    after = run(JobsRecommender(store).recommendations_for(USER, now=clock.now()))
    assert [r.eligible for r in after] == [True]
    assert after[0].flagged is False


def test_deadline_extension_updates_the_reminder_and_leaves_eligibility_alone():
    store, clock = InMemoryStore(), FakeClock()
    setup = make_runner(store, clock)
    run(record_profile_fact(store, clock, setup, USER, ProfileAttribute.CGPA, 7.9))
    recorded = run(record_opening(store, clock, USER, parsed_acme(batch=None), setup))
    beliefs = run(derive_for_opening(store, clock, setup, recorded.anchor.id))
    assert beliefs.reminder is not None and beliefs.eligibility is not None
    deadline = recorded.field("deadline")
    assert deadline is not None and deadline.structured is not None

    graph = DependencyGraph.from_links(run(store.links_for_user(USER)))
    assert set(graph.dependents(deadline.id)) == {beliefs.reminder.id}

    runner, fallback = rules_runner(store, clock, runs=[[[beliefs.reminder.id]]])
    _, event = run(
        update_memory(
            store,
            clock,
            deadline.id,
            content="Apply by 2026-11-19T09:00:00+00:00",
            structured=deadline.structured.model_copy(
                update={"value": "2026-11-19T09:00:00+00:00"}
            ),
            valid_to=None,
            created_by="scout",
            kind=TriggerKind.RIPPLE,
        )
    )
    event = run(runner.run(event))
    assert fallback.contexts == []
    reminder_v2 = run(store.latest_version(beliefs.reminder.id))
    assert reminder_v2.version == 2
    assert reminder_v2.content.startswith("remind at 2026-11-17T09:00:00+00:00 about ")
    assert run(store.get_memory(beliefs.eligibility.id)).status is Status.VALID
    assert run(store.get_memory(beliefs.eligibility.id)).version == 1


def test_deadline_changed_to_prose_makes_the_reminder_rule_decline_instead_of_crashing():
    """A non-ISO deadline is unknown, never an error (vocabulary.py, ADR-0035)."""
    store, clock = InMemoryStore(), FakeClock()
    setup = make_runner(store, clock)
    run(record_profile_fact(store, clock, setup, USER, ProfileAttribute.CGPA, 7.9))
    recorded = run(record_opening(store, clock, USER, parsed_acme(batch=None), setup))
    beliefs = run(derive_for_opening(store, clock, setup, recorded.anchor.id))
    deadline = recorded.field("deadline")
    assert beliefs.reminder is not None and deadline is not None
    assert deadline.structured is not None

    runner, _ = rules_runner(store, clock, runs=[[[beliefs.reminder.id]]])
    _, event = run(
        update_memory(
            store,
            clock,
            deadline.id,
            content="Apply by: to be announced",
            structured=deadline.structured.model_copy(update={"value": "to be announced"}),
            valid_to=None,
            created_by="user",
            kind=TriggerKind.USER_EDIT,
        )
    )
    # The rule has nothing to compute from, so the decision goes to the fallback (the
    # LLM in production; here a resolver that fails loudly when reached).
    with pytest.raises(AssertionError, match="LLM fallback called for 'remind at"):
        run(runner.run(event))
