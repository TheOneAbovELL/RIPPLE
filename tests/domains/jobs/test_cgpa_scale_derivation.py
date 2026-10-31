"""Derivation reads the CGPA scale (ADR-0034): beliefs and criteria never compare a
4-point CGPA with a 10-point cutoff, and they link the scale fact so a change ripples."""

from ripple.domains.jobs.derive import derive_criteria, derive_for_opening
from ripple.domains.jobs.openings import record_opening
from ripple.domains.jobs.profile import record_profile_fact
from ripple.domains.jobs.vocabulary import ProfileAttribute
from tests.domains.jobs.helpers import USER, make_runner, parsed_acme, run
from tests.fakes.clock import FakeClock
from tests.fakes.store import InMemoryStore


def _profile(store, clock, runner, *, cgpa, scale=None):
    run(record_profile_fact(store, clock, runner, USER, ProfileAttribute.CGPA, cgpa))
    run(record_profile_fact(store, clock, runner, USER, ProfileAttribute.BATCH, 2027))
    if scale is None:
        return None
    fact, _ = run(
        record_profile_fact(store, clock, runner, USER, ProfileAttribute.CGPA_SCALE, scale)
    )
    return fact


def _derive_acme(store, clock, runner):
    recorded = run(record_opening(store, clock, USER, parsed_acme(), runner))
    return run(derive_for_opening(store, clock, runner, recorded.anchor.id))


def test_derive_for_opening_derives_no_eligibility_for_a_4_point_cgpa_against_a_cutoff():
    store, clock = InMemoryStore(), FakeClock()
    runner = make_runner(store, clock)
    _profile(store, clock, runner, cgpa=3.6, scale=4)

    derived = _derive_acme(store, clock, runner)

    # 3.6 < 7.8 on raw numbers would read "not eligible"; that verdict is never written.
    assert derived.eligibility is None


def test_derive_for_opening_links_an_explicit_10_point_scale_to_eligibility():
    store, clock = InMemoryStore(), FakeClock()
    runner = make_runner(store, clock)
    scale = _profile(store, clock, runner, cgpa=8.1, scale=10)
    assert scale is not None

    derived = _derive_acme(store, clock, runner)

    assert derived.eligibility is not None
    assert derived.eligibility.content.startswith("eligible")
    parents = {link.parent_id for link in run(store.parents_of(derived.eligibility.id))}
    assert scale.id in parents


def test_derive_criteria_drops_the_cgpa_gate_off_the_cutoff_scale_but_reads_the_scale():
    store, clock = InMemoryStore(), FakeClock()
    runner = make_runner(store, clock)
    scale = _profile(store, clock, runner, cgpa=3.6, scale=4)
    assert scale is not None

    criteria = run(derive_criteria(store, clock, runner, USER))

    assert criteria is not None
    assert "cgpa_cutoff" not in criteria.content and "batch 2027" in criteria.content
    parents = {link.parent_id for link in run(store.parents_of(criteria.id))}
    assert scale.id in parents


def test_derive_criteria_keeps_the_cgpa_gate_on_the_default_scale():
    store, clock = InMemoryStore(), FakeClock()
    runner = make_runner(store, clock)
    _profile(store, clock, runner, cgpa=8.1)

    criteria = run(derive_criteria(store, clock, runner, USER))

    assert criteria is not None and "cgpa_cutoff <= 8.1" in criteria.content


def test_correcting_the_scale_to_10_brings_the_cgpa_gate_back_into_the_criteria():
    from ripple.core.resolver import ResolverChain
    from ripple.domains.jobs.rules import jobs_rules
    from tests.domains.jobs.helpers import RefusingResolver

    store, clock = InMemoryStore(), FakeClock()
    setup = make_runner(store, clock)
    _profile(store, clock, setup, cgpa=8.1, scale=4)
    criteria = run(derive_criteria(store, clock, setup, USER))
    assert criteria is not None and "cgpa_cutoff" not in criteria.content
    rules = ResolverChain(jobs_rules(), fallback=RefusingResolver())
    runner = make_runner(store, clock, resolver=rules, runs=[[[criteria.id]]])

    run(record_profile_fact(store, clock, runner, USER, ProfileAttribute.CGPA_SCALE, 10))

    latest = run(store.latest_version(criteria.id))
    assert "cgpa_cutoff <= 8.1" in latest.content
