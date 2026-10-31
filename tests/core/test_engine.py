"""Contract tests for the human-owned WaveEngine (ADR-0013).

The engine was implemented on 2026-10-31 (the author's request); the xfail markers that
waited for it were removed then.
"""

from ripple.core.engine import DependencyGraph, WaveEngine, WaveOutcome
from tests.builders import derived, fact, link, snapshot_link


def _chain():
    """offer -> availability -> eligibility -> recommendation, plus a snapshot edge."""
    offer = fact("student", "accepted_offer", "Acme summer")
    availability = derived("not available in summer")
    eligibility = derived("not eligible for summer roles")
    recommendation = derived("skip Globex summer internship")
    resume_v1 = fact("student", "resume", "v1")
    application = derived("applied to Initech with resume v1")
    links = [
        link(offer, availability),
        link(availability, eligibility),
        link(eligibility, recommendation),
        snapshot_link(resume_v1, application),
    ]
    graph = DependencyGraph.from_links(links)
    return graph, offer, availability, eligibility, recommendation, resume_v1, application


# ---- DependencyGraph (implemented) -----------------------------------------------


def test_graph_lists_direct_dependents_in_link_order():
    graph, offer, availability, *_ = _chain()
    assert graph.dependents(offer.id) == (availability.id,)


def test_graph_ignores_snapshot_links():
    graph, *_, resume_v1, _application = _chain()
    assert graph.dependents(resume_v1.id) == ()


def test_graph_dedupes_parallel_links_between_the_same_pair():
    a, b = fact("s", "x", 1), derived("y")
    graph = DependencyGraph.from_links([link(a, b), link(a, b, link_type="depends_on_time_period")])
    assert graph.dependents(a.id) == (b.id,)


def test_graph_descendants_is_breadth_first_and_cycle_safe():
    a, b, c = fact("s", "a", 1), derived("b"), derived("c")
    graph = DependencyGraph.from_links([link(a, b), link(b, c), link(c, a)])
    assert graph.descendants(a.id) == (b.id, c.id)


def test_graph_unknown_memory_has_no_dependents():
    assert DependencyGraph.from_links([]).dependents("ghost") == ()


# ---- WaveEngine -----------------------------------------------------------


def test_engine_first_wave_is_direct_dependents_of_seeds():
    graph, offer, availability, *_ = _chain()
    wave = WaveEngine().first_wave(graph, [offer.id])
    assert wave is not None
    assert wave.number == 1
    assert wave.memory_ids == (availability.id,)


def test_engine_first_wave_returns_none_when_seeds_have_no_dependents():
    graph, *_, recommendation, _resume, _application = _chain()
    assert WaveEngine().first_wave(graph, [recommendation.id]) is None


def test_engine_first_wave_never_includes_a_seed():
    a, b = fact("s", "a", 1), derived("b")
    graph = DependencyGraph.from_links([link(a, b), link(b, a)])
    wave = WaveEngine().first_wave(graph, [a.id, b.id])
    assert wave is None


def test_engine_changed_outcome_seeds_the_next_wave():
    graph, offer, availability, eligibility, recommendation, *_ = _chain()
    engine = WaveEngine()
    engine.first_wave(graph, [offer.id])
    wave2 = engine.next_wave(graph, [WaveOutcome(availability.id, changed=True)])
    assert wave2 is not None
    assert (wave2.number, wave2.memory_ids) == (2, (eligibility.id,))
    wave3 = engine.next_wave(graph, [WaveOutcome(eligibility.id, changed=True)])
    assert wave3 is not None
    assert wave3.memory_ids == (recommendation.id,)
    assert engine.next_wave(graph, [WaveOutcome(recommendation.id, changed=True)]) is None


def test_engine_keep_halts_the_branch():
    graph, offer, availability, *_ = _chain()
    engine = WaveEngine()
    engine.first_wave(graph, [offer.id])
    assert engine.next_wave(graph, [WaveOutcome(availability.id, changed=False)]) is None


def test_engine_update_follows_the_successor_version():
    offer = fact("student", "accepted_offer", "Acme")
    availability_v1 = derived("available")
    availability_v2 = derived("not available", version=2, supersedes_id=availability_v1.id)
    eligibility = derived("eligible")
    # After the update, links were copied to v2 (ADR-0014); v1's links are history.
    graph = DependencyGraph.from_links(
        [
            link(offer, availability_v1),
            link(availability_v1, eligibility),
            link(availability_v2, eligibility),
        ]
    )
    engine = WaveEngine()
    engine.first_wave(graph, [offer.id])
    wave2 = engine.next_wave(
        graph, [WaveOutcome(availability_v1.id, changed=True, successor_id=availability_v2.id)]
    )
    assert wave2 is not None
    assert wave2.memory_ids == (eligibility.id,)


def test_engine_never_revisits_a_memory_reached_twice():
    cgpa, skills = fact("s", "cgpa", 7.9), fact("s", "skills", "python")
    fit = derived("fit for Acme")
    graph = DependencyGraph.from_links([link(cgpa, fit), link(skills, fit)])
    wave = WaveEngine().first_wave(graph, [cgpa.id, skills.id])
    assert wave is not None
    assert wave.memory_ids == (fit.id,)


def test_engine_terminates_on_cycles():
    a, b, c = fact("s", "a", 1), derived("b"), derived("c")
    graph = DependencyGraph.from_links([link(a, b), link(b, c), link(c, b)])
    engine = WaveEngine()
    wave1 = engine.first_wave(graph, [a.id])
    assert wave1 is not None and wave1.memory_ids == (b.id,)
    wave2 = engine.next_wave(graph, [WaveOutcome(b.id, changed=True)])
    assert wave2 is not None and wave2.memory_ids == (c.id,)
    assert engine.next_wave(graph, [WaveOutcome(c.id, changed=True)]) is None


def test_engine_stops_at_max_depth_and_reports_truncation():
    graph, offer, availability, eligibility, *_ = _chain()
    engine = WaveEngine(max_depth=2)
    engine.first_wave(graph, [offer.id])
    wave2 = engine.next_wave(graph, [WaveOutcome(availability.id, changed=True)])
    assert wave2 is not None
    assert engine.next_wave(graph, [WaveOutcome(eligibility.id, changed=True)]) is None
    assert engine.truncated is True


def test_engine_is_deterministic_across_runs():
    graph, offer, *_ = _chain()
    first = WaveEngine().first_wave(graph, [offer.id])
    second = WaveEngine().first_wave(graph, [offer.id])
    assert first == second


def _shortcut():
    """cgpa -> eligibility -> recommendation, plus cgpa -> recommendation directly."""
    cgpa = fact("s", "cgpa", 7.9)
    eligibility = derived("eligible for Acme")
    recommendation = derived("recommend Acme")
    graph = DependencyGraph.from_links(
        [link(cgpa, eligibility), link(eligibility, recommendation), link(cgpa, recommendation)]
    )
    return graph, cgpa, eligibility, recommendation


def test_engine_resolves_a_memory_after_every_affected_parent_of_it():
    """ADR-0119: the recommendation rests on the eligibility too, so resolving it in
    wave 1 would read the eligibility before the eligibility is re-checked."""
    graph, cgpa, eligibility, recommendation = _shortcut()
    engine = WaveEngine()
    wave1 = engine.first_wave(graph, [cgpa.id])
    assert wave1 is not None and wave1.memory_ids == (eligibility.id,)
    wave2 = engine.next_wave(graph, [WaveOutcome(eligibility.id, changed=True)])
    assert wave2 is not None and (wave2.number, wave2.memory_ids) == (2, (recommendation.id,))
    assert engine.next_wave(graph, [WaveOutcome(recommendation.id, changed=True)]) is None


def test_engine_still_resolves_a_delayed_memory_when_its_middle_parent_is_kept():
    # The trigger changed and is a direct parent, so the keep halts only its own branch.
    graph, cgpa, eligibility, recommendation = _shortcut()
    engine = WaveEngine()
    engine.first_wave(graph, [cgpa.id])
    wave2 = engine.next_wave(graph, [WaveOutcome(eligibility.id, changed=False)])
    assert wave2 is not None and wave2.memory_ids == (recommendation.id,)


def test_engine_skips_a_level_with_nothing_due_and_numbers_waves_consecutively():
    a, b, c, d = fact("s", "a", 1), derived("b"), derived("c"), derived("d")
    graph = DependencyGraph.from_links([link(a, b), link(b, c), link(c, d), link(a, d)])
    engine = WaveEngine()
    assert engine.first_wave(graph, [a.id]).memory_ids == (b.id,)  # type: ignore[union-attr]
    # b kept: c (only below b) is not due; d is, through a.
    wave2 = engine.next_wave(graph, [WaveOutcome(b.id, changed=False)])
    assert wave2 is not None and (wave2.number, wave2.memory_ids) == (2, (d.id,))
