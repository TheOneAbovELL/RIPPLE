"""Eligibility honours the student's CGPA scale (IDEAS 9; ADR-0034).

JD cutoffs are parsed on a ten-point scale only. A student on a 4-point scale cannot be
compared with them without a conversion nobody agrees on, so the rule declines and the
resolver chain falls back (the LLM resolver, which can ask the student).
"""

from ripple.core.engine import DependencyGraph
from ripple.core.models import DecisionAction, Memory, Status
from ripple.core.resolver import ResolverChain
from ripple.domains.jobs.beliefs import compute_eligibility
from ripple.domains.jobs.derive import derive_for_opening
from ripple.domains.jobs.openings import record_opening
from ripple.domains.jobs.parsers.numbers import CGPA_SCALE_MAX
from ripple.domains.jobs.profile import record_profile_fact
from ripple.domains.jobs.rules import (
    DEFAULT_CGPA_SCALE,
    JD_CGPA_SCALE,
    EligibilityRule,
    jobs_rules,
)
from ripple.domains.jobs.schemas import ProfileView
from ripple.domains.jobs.vocabulary import ProfileAttribute
from tests.domains.jobs.helpers import USER, make_runner, parsed_acme, rules_runner, run
from tests.domains.jobs.test_rules import (
    ANCHOR,
    BATCH_2027,
    CGPA_79,
    CUTOFF,
    REQ_BATCH,
    belief_memory,
    context,
    profile,
)
from tests.fakes.clock import FakeClock
from tests.fakes.resolver import ScriptedResolver, ask
from tests.fakes.store import InMemoryStore

SCALE_4 = profile(ProfileAttribute.CGPA_SCALE, 4)
SCALE_10 = profile(ProfileAttribute.CGPA_SCALE, 10)


def _eligibility_parents(*extra: Memory) -> list[Memory]:
    return [ANCHOR, CGPA_79, CUTOFF, BATCH_2027, REQ_BATCH, *extra]


# ---- the rule -------------------------------------------------------------------------


def test_eligibility_rule_declines_when_the_student_is_on_a_4_point_scale():
    parents = _eligibility_parents(SCALE_4)
    belief = belief_memory(_eligibility_parents(), compute_eligibility)
    assert EligibilityRule().resolve(context(belief, parents)) is None


def test_eligibility_rule_compares_as_before_on_an_explicit_10_point_scale():
    parents = _eligibility_parents(SCALE_10)
    belief = belief_memory(_eligibility_parents(), compute_eligibility)
    resolution = EligibilityRule().resolve(context(belief, parents))
    assert resolution is not None and resolution.action is DecisionAction.KEEP


def test_eligibility_rule_ignores_the_scale_when_the_opening_states_no_cutoff():
    parents = [ANCHOR, BATCH_2027, REQ_BATCH, SCALE_4]
    belief = belief_memory([ANCHOR, BATCH_2027, REQ_BATCH], compute_eligibility)
    resolution = EligibilityRule().resolve(context(belief, parents))
    assert resolution is not None and resolution.action is DecisionAction.KEEP


def test_eligibility_rule_treats_a_retired_scale_as_the_default_10_point_scale():
    retired = SCALE_4.model_copy(update={"status": Status.RETIRED})
    belief = belief_memory(_eligibility_parents(), compute_eligibility)
    resolution = EligibilityRule().resolve(context(belief, _eligibility_parents(retired)))
    assert resolution is not None and resolution.action is DecisionAction.KEEP


def test_eligibility_rule_on_a_4_point_scale_falls_back_through_the_chain():
    fallback = ScriptedResolver({}, default=ask("Is your CGPA on a 10-point scale?"))
    chain = ResolverChain(jobs_rules(), fallback=fallback)
    belief = belief_memory(_eligibility_parents(), compute_eligibility)
    resolution = run(chain.resolve(context(belief, _eligibility_parents(SCALE_4))))
    assert resolution.action is DecisionAction.ASK
    assert [c.memory.id for c in fallback.contexts] == [belief.id]


def test_jd_cutoff_scale_is_the_parsers_ten_point_scale():
    assert JD_CGPA_SCALE == CGPA_SCALE_MAX == DEFAULT_CGPA_SCALE


def test_profile_view_scale_is_the_latest_live_scale_fact_or_the_default():
    assert ProfileView.from_memories([CGPA_79]).cgpa_scale_value == DEFAULT_CGPA_SCALE
    assert ProfileView.from_memories([CGPA_79, SCALE_4]).cgpa_scale_value == 4
    later_10 = SCALE_10.model_copy(update={"recorded_at": SCALE_4.recorded_at.replace(year=2030)})
    assert ProfileView.from_memories([SCALE_4, later_10]).cgpa_scale_value == 10


# ---- rule links: the scale fact reaches the eligibility beliefs -------------------------


def _student_with_acme(
    store: InMemoryStore, clock: FakeClock, setup, *, cutoff: float | None = 7.8
):
    run(record_profile_fact(store, clock, setup, USER, ProfileAttribute.CGPA, 3.6))
    run(record_profile_fact(store, clock, setup, USER, ProfileAttribute.BATCH, 2027))
    recorded = run(record_opening(store, clock, USER, parsed_acme(cutoff=cutoff), setup))
    beliefs = run(derive_for_opening(store, clock, setup, recorded.anchor.id))
    assert beliefs.eligibility is not None
    return beliefs.eligibility


def test_recording_a_4_point_scale_links_it_to_eligibility_and_the_rule_defers():
    store, clock = InMemoryStore(), FakeClock()
    setup = make_runner(store, clock)
    eligibility = _student_with_acme(store, clock, setup)
    fallback = ScriptedResolver({}, default=ask("Is your 3.6 on a 4-point scale?"))
    chain = ResolverChain(jobs_rules(), fallback=fallback)
    runner = make_runner(store, clock, resolver=chain, runs=[[[eligibility.id]]])

    scale, event = run(
        record_profile_fact(store, clock, runner, USER, ProfileAttribute.CGPA_SCALE, 4)
    )

    graph = DependencyGraph.from_links(run(store.links_for_user(USER)))
    assert eligibility.id in graph.dependents(scale.id)
    assert [c.memory.id for c in fallback.contexts] == [eligibility.id]
    assert scale.id in [p.id for p in fallback.contexts[0].parents]
    assert event is not None and [d.action for d in event.decisions] == [DecisionAction.ASK]
    assert run(store.get_memory(eligibility.id)).status is Status.PENDING_USER


def test_changing_the_scale_links_beliefs_derived_after_it_was_first_recorded():
    store, clock = InMemoryStore(), FakeClock()
    setup = make_runner(store, clock)
    first, _ = run(record_profile_fact(store, clock, setup, USER, ProfileAttribute.CGPA_SCALE, 10))
    # An opening with no cutoff: its eligibility never reads the scale, so derivation
    # writes no scale link; only the scale change's rule link can reach it.
    eligibility = _student_with_acme(store, clock, setup, cutoff=None)
    assert eligibility.id not in DependencyGraph.from_links(
        run(store.links_for_user(USER))
    ).dependents(first.id)
    runner, fallback = rules_runner(store, clock, runs=[[[eligibility.id]]])

    scale, _ = run(record_profile_fact(store, clock, runner, USER, ProfileAttribute.CGPA_SCALE, 4))

    graph = DependencyGraph.from_links(run(store.links_for_user(USER)))
    assert eligibility.id in graph.dependents(scale.id)
    assert fallback.contexts == []  # no cutoff: the rule still decides on a 4-point scale


def test_recording_the_default_10_point_scale_is_kept_by_the_rules_alone():
    store, clock = InMemoryStore(), FakeClock()
    setup = make_runner(store, clock)
    eligibility = _student_with_acme(store, clock, setup)
    runner, fallback = rules_runner(store, clock, runs=[[[eligibility.id]]])

    _, event = run(record_profile_fact(store, clock, runner, USER, ProfileAttribute.CGPA_SCALE, 10))

    assert fallback.contexts == []
    assert event is not None and [d.action for d in event.decisions] == [DecisionAction.KEEP]
