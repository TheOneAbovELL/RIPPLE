"""Named invariant tests for the jobs adapter (CLAUDE.md): I1, I3 and I5 as the adapter
can enforce them. I5: no derived content holds a number or a quoted phrase that does not
come from a parent memory."""

import re

from ripple.core.engine import DependencyGraph
from ripple.core.models import Memory, Status, TriggerKind
from ripple.core.writes import update_memory
from ripple.domains.jobs.derive import derive_criteria, derive_for_opening
from ripple.domains.jobs.openings import record_opening
from ripple.domains.jobs.profile import profile_fact, record_profile_fact
from ripple.domains.jobs.ranking import JobsRecommender
from ripple.domains.jobs.vocabulary import Kind, ProfileAttribute
from tests.domains.jobs.helpers import USER, make_runner, parsed_acme, rules_runner, run
from tests.fakes.clock import FakeClock
from tests.fakes.store import InMemoryStore

NUMBER = re.compile(r"\d+(?:\.\d+)?")
QUOTED = re.compile(r'"([^"]*)"')


def _parents(store: InMemoryStore, memory: Memory) -> list[Memory]:
    return [run(store.latest_version(link.parent_id)) for link in run(store.parents_of(memory.id))]


def _assert_only_parent_values(store: InMemoryStore, belief: Memory) -> None:
    parents = _parents(store, belief)
    assert parents, f"{belief.content!r} has no parents to cite"
    allowed_numbers: set[str] = set()
    allowed_text: list[str] = []
    for parent in parents:
        allowed_text.append(parent.content)
        allowed_numbers |= set(NUMBER.findall(parent.content))
        if parent.structured is not None:
            value = parent.structured.value
            allowed_numbers |= set(NUMBER.findall(str(value)))
            if isinstance(value, float):
                allowed_numbers.add(f"{value:g}")
    # I5 is about inputs, not arithmetic: a wrong remind_at would still pass here; the
    # rule and derive tests pin the computed values.
    # A belief may also state its own computed value (score, remind-at), counts of its
    # parents, and the fixed 48-hour lead; everything else must be a parent's value.
    if belief.structured is not None:
        own = belief.structured.value
        allowed_numbers |= set(NUMBER.findall(str(own)))
        if isinstance(own, float):
            allowed_numbers |= {f"{own:g}", f"{own:.2f}"}
    allowed_numbers |= {str(n) for n in range(len(parents) + 1)} | {"48"}
    for quoted in QUOTED.findall(belief.content):
        assert quoted in allowed_text, f"{quoted!r} is not a parent's content"
    for number in NUMBER.findall(belief.content):
        assert number in allowed_numbers, f"{number} in {belief.content!r} is not a parent value"


def _seed():
    store, clock = InMemoryStore(), FakeClock()
    runner = make_runner(store, clock)
    cgpa, _ = run(record_profile_fact(store, clock, runner, USER, ProfileAttribute.CGPA, 7.6))
    run(record_profile_fact(store, clock, runner, USER, ProfileAttribute.BATCH, 2027))
    run(record_profile_fact(store, clock, runner, USER, ProfileAttribute.SKILL, "Python"))
    recorded = run(record_opening(store, clock, USER, parsed_acme(), runner))
    beliefs = run(derive_for_opening(store, clock, runner, recorded.anchor.id))
    criteria = run(derive_criteria(store, clock, runner, USER))
    return store, clock, cgpa, recorded, beliefs, criteria


def test_invariant_I5_derived_beliefs_cite_only_values_held_by_their_parents():
    store, _, _, _, beliefs, criteria = _seed()
    for belief in (beliefs.eligibility, beliefs.fit, beliefs.reminder, criteria):
        assert belief is not None
        _assert_only_parent_values(store, belief)


def test_invariant_I5_rule_updates_cite_only_values_held_by_their_parents():
    store, clock, cgpa, _, beliefs, criteria = _seed()
    assert beliefs.eligibility is not None and criteria is not None
    runner, fallback = rules_runner(store, clock, runs=[[[beliefs.eligibility.id, criteria.id]]])
    _, event = run(
        update_memory(
            store,
            clock,
            cgpa.id,
            content="CGPA is 8.2",
            structured=profile_fact(ProfileAttribute.CGPA, 8.2),
            valid_to=None,
            created_by="user",
            kind=TriggerKind.USER_EDIT,
        )
    )
    run(runner.run(event))
    assert fallback.contexts == []
    for original in (beliefs.eligibility, criteria):
        latest = run(store.latest_version(original.id))
        assert latest.version == 2
        assert "8.2" in latest.content and "7.6" not in latest.content
        _assert_only_parent_values(store, latest)


def test_invariant_I5_the_adapter_never_writes_a_profile_fact_on_its_own():
    store, _, _, _, _, _ = _seed()
    profile_facts = [
        m
        for m in store.all_memories()
        if m.kind == Kind.FACT and m.structured and m.structured.subject == "student"
    ]
    assert {m.created_by for m in profile_facts} == {"user"}
    opening_rows = [
        m
        for m in store.all_memories()
        if m.kind == Kind.OPENING or (m.structured and m.structured.subject.startswith("opening:"))
    ]
    assert {m.created_by for m in opening_rows if m.kind != Kind.DERIVED} == {"scout"}
    assert {
        m.created_by for m in store.all_memories() if m.kind in (Kind.DERIVED, Kind.CRITERIA)
    } == {"curator"}


def test_invariant_I1_recommender_never_returns_retired_and_flags_suspect_or_pending():
    store, clock, _, recorded, beliefs, _ = _seed()
    assert beliefs.fit is not None
    now = clock.now()
    assert [r.flagged for r in run(JobsRecommender(store).recommendations_for(USER, now=now))] == [
        False
    ]

    async def flip(memory_id: str, status: Status):
        async with store.transaction() as tx:
            await tx.replace_memory(
                (await tx.get_memory(memory_id)).model_copy(update={"status": status})
            )

    run(flip(beliefs.fit.id, Status.SUSPECT))
    assert [r.flagged for r in run(JobsRecommender(store).recommendations_for(USER, now=now))] == [
        True
    ]
    run(flip(beliefs.fit.id, Status.PENDING_USER))
    assert [r.flagged for r in run(JobsRecommender(store).recommendations_for(USER, now=now))] == [
        True
    ]
    run(flip(recorded.anchor.id, Status.RETIRED))
    assert run(JobsRecommender(store).recommendations_for(USER, now=now)) == []


def test_jobs_rules_cgpa_change_never_calls_the_fallback():
    store, clock, cgpa, _, beliefs, criteria = _seed()
    assert beliefs.eligibility is not None and criteria is not None
    graph = DependencyGraph.from_links(run(store.links_for_user(USER)))
    wave = list(graph.dependents(cgpa.id))
    runner, fallback = rules_runner(store, clock, runs=[[wave]])
    _, event = run(
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
    event = run(runner.run(event))
    assert fallback.contexts == []
    assert len(event.decisions) == len(wave) == 2
