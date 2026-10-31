"""Baseline strategies (ADR-0060): same store, same resolver, different propagation.

The ripple strategy needs the human-owned engine, so it is driven here with a
ScriptedEngine; the three baselines need no engine at all and run as they will in
the bench.
"""

import asyncio

import pytest
from bench.scenario import (
    EventSpec,
    Expectation,
    MemorySpec,
    ResolutionSpec,
    ScenarioRunner,
    ScenarioSpec,
)
from bench.strategies import (
    ABLATIONS,
    STRATEGY_NAMES,
    NoAskResolver,
    build_strategy,
    one_shot_engine,
)

from ripple.core.engine import DependencyGraph, WaveOutcome
from ripple.core.models import DecisionAction, Status
from tests.fakes.clock import FakeClock
from tests.fakes.engine import ScriptedEngine
from tests.fakes.resolver import ScriptedResolver
from tests.fakes.store import InMemoryStore
from tests.scenarios.runner import SCENARIO_DIR, load_scenario, scenario_paths

BASELINES = ("append_only", "newest_wins", "check_everything")


def _cgpa_spec(resolution: ResolutionSpec | list[ResolutionSpec] | None = None) -> ScenarioSpec:
    """cgpa -> eligibility (eligibility_of), plus an unlinked opening and a criteria."""
    return ScenarioSpec(
        name="inline",
        memories={
            "cgpa": MemorySpec(content="CGPA is 7.6"),
            "eligibility": MemorySpec(kind="derived", content="not eligible for Acme"),
            "criteria": MemorySpec(kind="criteria", content="cutoff <= 7.6"),
            "globex": MemorySpec(kind="opening", content="Globex SDE intern"),
        },
        links=[["cgpa", "eligibility", "eligibility_of"], ["cgpa", "criteria", "criteria_from"]],
        resolutions={
            "eligibility": resolution
            if resolution is not None
            else ResolutionSpec(action=DecisionAction.UPDATE, new_content="eligible for Acme"),
            "criteria": ResolutionSpec(action=DecisionAction.UPDATE, new_content="cutoff <= 7.9"),
        },
        events=[
            EventSpec(
                update="cgpa",
                content="CGPA is 7.9",
                expect={
                    "cgpa": Expectation(status=Status.RETIRED),
                    "eligibility@latest": Expectation(version=2, content="eligible for Acme"),
                    "criteria@latest": Expectation(version=2),
                    "globex": Expectation(status=Status.VALID, version=1),
                },
            )
        ],
    )


def _scripted(*waves):
    class Factory(ScriptedEngine):
        def __init__(self, max_depth: int = 8) -> None:
            super().__init__(*waves, max_depth=max_depth)

    return Factory


# ---- append_only -----------------------------------------------------------------------


def test_append_only_keeps_the_superseded_version_valid_and_touches_no_dependent():
    runner = ScenarioRunner(_cgpa_spec(), strategy="append_only")
    outcome = runner.run()
    store = runner.store
    assert asyncio.run(store.get_memory("cgpa")).status is Status.VALID
    assert asyncio.run(store.latest_version("cgpa")).version == 2
    assert asyncio.run(store.get_memory("eligibility")).version == 1
    assert outcome.resolver_calls == 0
    # Gold is unchanged, so the baseline fails it honestly.
    assert outcome.failures == [
        "cgpa: status VALID, expected RETIRED",
        "eligibility@latest: content 'not eligible for Acme', expected 'eligible for Acme'",
        "eligibility@latest: version 1, expected 2",
        "criteria@latest: version 1, expected 2",
    ]


def test_append_only_records_the_restoration_as_a_wave_zero_decision():
    runner = ScenarioRunner(_cgpa_spec(), strategy="append_only")
    runner.run()
    (event,) = runner.store.change_events()  # type: ignore[attr-defined]
    assert event.completed_at is not None
    assert [(d.memory_id, d.wave, d.action) for d in event.decisions] == [
        ("cgpa", 0, DecisionAction.KEEP)
    ]


# ---- newest_wins ----------------------------------------------------------------------


def test_newest_wins_retires_only_the_superseded_version():
    runner = ScenarioRunner(_cgpa_spec(), strategy="newest_wins")
    outcome = runner.run()
    store = runner.store
    assert asyncio.run(store.get_memory("cgpa")).status is Status.RETIRED
    assert asyncio.run(store.get_memory("eligibility")).status is Status.VALID
    assert asyncio.run(store.get_memory("eligibility")).version == 1
    assert outcome.resolver_calls == 0
    assert not any(f.startswith("cgpa:") for f in outcome.failures)
    assert any(f.startswith("eligibility@latest") for f in outcome.failures)


def test_newest_wins_completes_the_event_without_decisions():
    runner = ScenarioRunner(_cgpa_spec(), strategy="newest_wins")
    runner.run()
    (event,) = runner.store.change_events()  # type: ignore[attr-defined]
    assert event.completed_at is not None and event.decisions == []


# ---- check_everything ---------------------------------------------------------------


def test_check_everything_resolves_every_valid_memory_including_unlinked_ones():
    runner = ScenarioRunner(_cgpa_spec(), strategy="check_everything")
    outcome = runner.run()
    # eligibility, criteria and the unlinked globex opening; never the trigger itself.
    assert outcome.resolver_calls == 3
    assert outcome.passed, outcome.failures
    (event,) = runner.store.change_events()  # type: ignore[attr-defined]
    assert sorted(event.affected_ids) == ["criteria", "eligibility", "globex"]
    assert all(d.wave == 1 for d in event.decisions)


def test_check_everything_ignores_a_resolution_scoped_to_another_trigger():
    scoped = [
        ResolutionSpec(
            trigger="cutoff", action=DecisionAction.UPDATE, new_content="eligible for Acme"
        )
    ]
    outcome = ScenarioRunner(_cgpa_spec(scoped), strategy="check_everything").run()
    assert outcome.resolver_calls == 3
    assert "eligibility@latest: version 1, expected 2" in outcome.failures
    assert outcome.checks_failed == 1  # one target (two mismatch lines), not two


def test_one_shot_engine_emits_one_wave_without_the_seeds_and_then_stops():
    engine = one_shot_engine(["a", "b", "trigger"])()
    graph = DependencyGraph.from_links([])
    wave = engine.first_wave(graph, ["trigger"])
    assert wave is not None and wave.memory_ids == ("a", "b") and wave.number == 1
    assert engine.next_wave(graph, [WaveOutcome("a", changed=True)]) is None
    assert engine.truncated is False
    assert one_shot_engine(["trigger"])().first_wave(graph, ["trigger"]) is None


# ---- ripple ----------------------------------------------------------------------------


def test_ripple_strategy_counts_resolver_calls_through_the_shared_resolver():
    runner = ScenarioRunner(
        _cgpa_spec(),
        strategy="ripple",
        engine_factory=_scripted(["eligibility", "criteria"]),  # type: ignore[arg-type]
    )
    outcome = runner.run()
    assert outcome.passed, outcome.failures
    assert outcome.resolver_calls == runner.resolver.calls == 2


# ---- shared behaviour ------------------------------------------------------------------


@pytest.mark.parametrize("name", BASELINES)
@pytest.mark.parametrize("path", scenario_paths(), ids=lambda p: p.stem)
def test_baselines_run_every_smoke_scenario_without_the_engine(name, path):
    spec = load_scenario(path)
    outcome = ScenarioRunner(spec, strategy=name).run()
    assert outcome.runnable, outcome.errors
    assert outcome.events_run == len(spec.events)


def test_an_answer_to_a_question_a_baseline_never_asked_is_a_recorded_error():
    spec = load_scenario(SCENARIO_DIR / "ask_confirmed.yaml")
    outcome = ScenarioRunner(spec, strategy="newest_wins").run()
    assert outcome.events_run == 2
    assert outcome.errors == ["answer:eligibility: memory 'eligibility' is VALID, not PENDING_USER"]
    assert not outcome.passed


def test_append_only_restoration_and_completion_commit_together():
    """A crash after the restore but before the event completes must roll both back."""
    from bench.strategies import AppendOnlyStrategy

    from ripple.core.models import TriggerKind
    from ripple.core.writes import update_memory

    store, clock = InMemoryStore(), FakeClock()
    runner = ScenarioRunner(_cgpa_spec(), store=store, clock=clock, strategy="newest_wins")
    asyncio.run(runner._seed())
    _, event = asyncio.run(
        update_memory(
            store,
            clock,
            "cgpa",
            content="CGPA is 7.9",
            structured=None,
            valid_to=None,
            created_by="user",
            kind=TriggerKind.USER_EDIT,
        )
    )
    strategy = AppendOnlyStrategy(store, ScriptedResolver({}), clock)

    async def explode(*args, **kwargs):
        raise ConnectionError("db down")

    store.replace_change_event = explode  # type: ignore[method-assign]
    with pytest.raises(ConnectionError):
        asyncio.run(strategy.run(event))
    assert asyncio.run(store.get_memory("cgpa")).status is Status.RETIRED


def test_baselines_disagree_with_gold_where_propagation_is_the_point():
    spec = load_scenario(SCENARIO_DIR / "accepted_offer_chain.yaml")
    append_only = ScenarioRunner(spec, strategy="append_only").run()
    newest_wins = ScenarioRunner(spec, strategy="newest_wins").run()
    check_everything = ScenarioRunner(spec, strategy="check_everything").run()
    assert not append_only.passed and not newest_wins.passed
    assert check_everything.passed, check_everything.failures
    assert check_everything.resolver_calls == 5  # every VALID memory but the trigger


def test_expiry_retires_the_temporary_fact_under_every_strategy_but_ripples_only_with_a_resolver():
    spec = load_scenario(SCENARIO_DIR / "temporary_unavailability.yaml")
    for name in BASELINES:
        runner = ScenarioRunner(spec, strategy=name)
        runner.run()
        assert asyncio.run(runner.store.get_memory("exams")).status is Status.RETIRED, name
        availability = asyncio.run(runner.store.latest_version("availability"))
        assert availability.version == (3 if name == "check_everything" else 1), name


def test_build_strategy_covers_every_name_and_rejects_others():
    store, clock = InMemoryStore(), FakeClock()
    for name in STRATEGY_NAMES:
        assert build_strategy(name, store=store, resolver=ScriptedResolver({}), clock=clock).name
    with pytest.raises(ValueError, match="unknown strategy"):
        build_strategy("mem0", store=store, resolver=ScriptedResolver({}), clock=clock)


# ---- ablations (ADR-0122) -----------------------------------------------------------------


def test_no_ask_resolver_keeps_what_the_inner_resolver_would_have_asked_about():
    from ripple.core.resolver import Resolution

    class Asking:
        async def resolve(self, context):
            return Resolution(action=DecisionAction.ASK, reason="unsure", question="Still true?")

    resolution = asyncio.run(NoAskResolver(Asking()).resolve(None))  # type: ignore[arg-type]
    assert resolution.action is DecisionAction.KEEP and resolution.question is None
    assert "no_ask_user" in resolution.reason


def test_no_ask_user_ablation_never_parks_a_memory_the_oracle_asks_about():
    spec = load_scenario(SCENARIO_DIR / "ask_confirmed.yaml")
    outcome = ScenarioRunner(spec, strategy="ripple", ablation="no_ask_user").run()
    assert outcome.metrics is not None and outcome.metrics.questions_asked == 0
    assert outcome.metrics.questions_needed > 0 and not outcome.passed


def test_no_graph_ablation_scores_exactly_as_check_everything_on_every_smoke_scenario():
    for path in scenario_paths():
        spec = load_scenario(path)
        ablated = ScenarioRunner(spec, strategy="ripple", ablation="no_graph").run()
        baseline = ScenarioRunner(spec, strategy="check_everything").run()
        assert ablated.strategy == "ripple"
        assert (ablated.failures, ablated.resolver_calls) == (
            baseline.failures,
            baseline.resolver_calls,
        ), path.name


def test_build_strategy_refuses_an_ablation_of_a_baseline_or_an_unknown_one():
    store, clock = InMemoryStore(), FakeClock()
    resolver = ScriptedResolver({})
    for name, ablation in (("append_only", "no_graph"), ("ripple", "no_curator")):
        with pytest.raises(ValueError, match="ablation"):
            build_strategy(name, store=store, resolver=resolver, clock=clock, ablation=ablation)
    assert ABLATIONS == ("no_graph", "no_ask_user")
