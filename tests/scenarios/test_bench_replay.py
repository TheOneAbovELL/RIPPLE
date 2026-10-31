"""TTC replay harness (ADR-0062): snapshots, gold matching and the stub action layer."""

import asyncio
import json

from bench.replay import GoldState, StubActionLayer, VersionState
from bench.scenario import (
    EventSpec,
    Expectation,
    MemorySpec,
    ResolutionSpec,
    ScenarioRunner,
    ScenarioSpec,
)

from ripple.core.models import DecisionAction, Status
from tests.builders import derived, link, memory
from tests.fakes.clock import FakeClock
from tests.fakes.store import InMemoryStore


def _store_with(*memories, links=()):
    store = InMemoryStore()

    async def write():
        async with store.transaction() as tx:
            for m in memories:
                await tx.add_memory(m)
            for edge in links:
                await tx.add_link(edge)

    asyncio.run(write())
    return store


def _recommend(store, user_id):
    return asyncio.run(StubActionLayer(store).recommendations_for(user_id, now=FakeClock().now()))


# ---- gold matching --------------------------------------------------------------------


def test_gold_state_reports_each_mismatch_with_the_runner_wording():
    state = VersionState(id="x", status="VALID", version=1, content="old")
    gold = GoldState(status="RETIRED", content="new", version=2)
    assert gold.mismatches("e@latest", state) == [
        "e@latest: status VALID, expected RETIRED",
        "e@latest: content 'old', expected 'new'",
        "e@latest: version 1, expected 2",
    ]
    assert GoldState(deleted=True).mismatches("e", state) == ["e: expected deleted, found VALID"]
    assert GoldState(status="VALID").mismatches("e", None) == ["e: missing"]
    assert GoldState(deleted=True).matches(None)


# ---- stub action layer ----------------------------------------------------------------


def test_stub_recommends_valid_openings_and_skips_negative_eligibility():
    acme = memory(kind="opening", content="Acme SDE intern", id="acme")
    globex = memory(kind="opening", content="Globex SDE intern", id="globex")
    not_eligible = derived("not eligible for Acme", id="acme_elig")
    eligible = derived("eligible for Globex", id="globex_elig")
    store = _store_with(
        acme,
        globex,
        not_eligible,
        eligible,
        links=[
            link(acme, not_eligible, link_type="eligibility_of"),
            link(globex, eligible, link_type="eligibility_of"),
        ],
    )
    recommended = _recommend(store, acme.user_id)
    assert [r.opening_memory_id for r in recommended] == ["globex"]
    assert recommended[0].eligible and recommended[0].flagged is False


def test_stub_flags_a_recommendation_built_on_a_suspect_belief():
    globex = memory(kind="opening", content="Globex SDE intern", id="globex")
    fit = derived("strong fit for Globex", id="fit", status=Status.SUSPECT)
    store = _store_with(globex, fit, links=[link(globex, fit, link_type="fit_of")])
    (rec,) = _recommend(store, globex.user_id)
    assert rec.flagged is True


def test_stub_ignores_retired_openings_and_non_openings():
    old = memory(kind="opening", content="closed", id="old", status=Status.RETIRED)
    fact = memory(kind="fact", content="CGPA is 8", id="cgpa")
    store = _store_with(old, fact)
    assert _recommend(store, old.user_id) == []


# ---- trace -----------------------------------------------------------------------------


def _spec() -> ScenarioSpec:
    return ScenarioSpec(
        name="trace",
        memories={
            "acme": MemorySpec(kind="opening", content="Acme SDE intern"),
            "eligibility": MemorySpec(kind="derived", content="eligible for Acme"),
        },
        links=[["acme", "eligibility", "eligibility_of"]],
        events=[
            EventSpec(forget="acme", expect={"acme": Expectation(deleted=True)}),
        ],
    )


def test_trace_records_recommendations_with_the_beliefs_they_rest_on():
    outcome = ScenarioRunner(_spec(), strategy="newest_wins").run()
    assert outcome.trace is not None
    seeded, after_forget = outcome.trace.events
    (rec,) = seeded.recommendations
    assert rec.opening_alias == "acme" and rec.based_on == ("eligibility",)
    assert after_forget.recommendations == ()
    assert after_forget.memories["acme"].root is None
    assert after_forget.gold["acme"] == GoldState(deleted=True)


def test_trace_serialises_to_json():
    outcome = ScenarioRunner(_spec(), strategy="newest_wins").run()
    assert outcome.trace is not None
    text = json.dumps(outcome.trace.to_dict())
    loaded = json.loads(text)
    assert loaded["scenario"] == "trace" and loaded["strategy"] == "newest_wins"
    assert [e["action"] for e in loaded["events"]] == ["seed", "forget:acme"]
    assert loaded["events"][0]["simulated_day"] == 0.0


def test_trace_keeps_the_opening_alias_after_the_opening_gets_a_new_version():
    spec = ScenarioSpec(
        name="versioned-opening",
        memories={
            "acme": MemorySpec(kind="opening", content="Acme SDE intern"),
            "reminder": MemorySpec(kind="derived", content="remind about Acme"),
        },
        links=[["acme", "reminder", "reminder_for"]],
        events=[EventSpec(update="acme", content="Acme SDE intern, new deadline", expect={})],
    )
    outcome = ScenarioRunner(spec, strategy="newest_wins").run()
    assert outcome.trace is not None
    (rec,) = outcome.trace.events[1].recommendations
    assert rec.opening_alias == "acme" and rec.opening_id != "acme"


# ---- retrieval probe (ADR-0120) -----------------------------------------------------------


def _cgpa_rise() -> ScenarioSpec:
    return ScenarioSpec(
        name="probe",
        memories={
            "cgpa": MemorySpec(content="CGPA is 7.6"),
            "elig": MemorySpec(kind="derived", content="not eligible for Acme CGPA cutoff"),
        },
        links=[["cgpa", "elig", "eligibility_of"]],
        resolutions={
            "elig": ResolutionSpec(action=DecisionAction.UPDATE, new_content="eligible for Acme")
        },
        events=[
            EventSpec(
                update="cgpa",
                content="CGPA is 7.9",
                expect={
                    "cgpa": Expectation(status=Status.RETIRED),
                    "elig@latest": Expectation(content="eligible for Acme"),
                },
            )
        ],
    )


def test_probe_queries_each_gold_alias_after_an_event_and_never_after_the_seed():
    trace = ScenarioRunner(_cgpa_rise(), strategy="ripple").run().trace
    assert trace is not None
    seed, event = trace.events
    assert seed.retrieved == ()
    assert {r.query_alias for r in event.retrieved} == {"cgpa", "elig"}
    # I1 through the real retriever: the retired CGPA row is never shown.
    assert "cgpa" not in {r.memory_id for r in event.retrieved}


def test_probe_shows_append_only_the_old_statement_it_restored_unflagged():
    trace = ScenarioRunner(_cgpa_rise(), strategy="append_only").run().trace
    assert trace is not None
    shown = {(r.memory_id, r.flagged) for r in trace.events[1].retrieved}
    assert ("cgpa", False) in shown and ("elig", False) in shown


def test_probe_can_be_switched_off_and_the_trace_serialises_its_results():
    quiet = ScenarioRunner(_cgpa_rise(), strategy="ripple", probe_retrieval=False).run()
    assert quiet.trace is not None and quiet.trace.events[1].retrieved == ()
    loud = ScenarioRunner(_cgpa_rise(), strategy="ripple").run()
    assert loud.trace is not None
    events = json.loads(json.dumps(loud.trace.to_dict()))["events"]
    assert events[1]["retrieved"] and set(events[1]["retrieved"][0]) == {
        "query_alias",
        "memory_id",
        "flagged",
        "via",
    }


def test_probe_skips_an_event_without_gold():
    spec = _cgpa_rise()
    spec = spec.model_copy(update={"events": [*spec.events, EventSpec(advance_days=1)]})
    trace = ScenarioRunner(spec, strategy="ripple").run().trace
    assert trace is not None and trace.events[1].retrieved
    assert trace.events[2].gold == {} and trace.events[2].retrieved == ()


def test_probe_counts_do_not_depend_on_the_random_ids_of_new_versions():
    # New versions get uuid ids, which break retrieval ties; with a top-k cut the
    # counted set changed between runs (ADR-0120 point 4). Every match is returned now.
    from tests.scenarios.runner import load_scenario, scenario_paths

    for path in scenario_paths():
        spec = load_scenario(path)
        counts = set()
        for _ in range(3):
            metrics = ScenarioRunner(spec, strategy="append_only").run().metrics
            assert metrics is not None
            counts.add((metrics.retrieved, metrics.stale_retrieved))
        assert len(counts) == 1, path.name
