from pathlib import Path

import pytest
from bench.scenario import ScenarioSpec, load_scenario
from training.replay import ReplayError, Snapshot, scenario_snapshots

from ripple.core.models import Status
from ripple.domains.jobs.vocabulary import jobs_registry

V0 = sorted(Path("bench/data/jobs_v0").glob("*.yaml"))
LIVE = (Status.VALID, Status.SUSPECT, Status.PENDING_USER)


def _check_expectations(spec: ScenarioSpec, snapshots: list[Snapshot]) -> list[str]:
    """Compare the replay with what the scenario itself says the real runner leaves:
    alias@latest is the live version (content, version, gone when RETIRED), a bare
    alias is the root row (RETIRED = superseded or gone), deleted = gone."""
    problems: list[str] = []
    for step, event in enumerate(spec.events, start=1):
        snap = snapshots[step]
        for key, expected in event.expect.items():
            alias, _, latest = key.partition("@")
            live = alias in snap.memories
            where = f"{spec.name} event {step} {key}"
            if expected.deleted:
                if live:
                    problems.append(f"{where}: expected deleted, still live")
                continue
            if latest:
                if expected.status is Status.RETIRED:
                    if live:
                        problems.append(f"{where}: expected retired, still live")
                    continue
                if not live:
                    problems.append(f"{where}: expected live, gone")
                    continue
                if expected.version is not None and snap.versions[alias] != expected.version:
                    problems.append(
                        f"{where}: version {snap.versions[alias]} != {expected.version}"
                    )
                if (
                    expected.content is not None
                    and snap.memories[alias].content != expected.content
                ):
                    problems.append(f"{where}: content {snap.memories[alias].content!r}")
            elif expected.status is Status.RETIRED:
                if live and snap.versions[alias] == 1:
                    problems.append(f"{where}: expected superseded or gone, still version 1")
            elif expected.status in LIVE:
                if not live or snap.versions[alias] != 1:
                    problems.append(f"{where}: expected the root row live and unchanged")
                elif (
                    expected.content is not None
                    and snap.memories[alias].content != expected.content
                ):
                    problems.append(f"{where}: content {snap.memories[alias].content!r}")
    return problems


@pytest.mark.parametrize("path", V0, ids=[p.stem for p in V0])
def test_replay_agrees_with_every_v0_scenario_expectation(path: Path):
    spec = load_scenario(path)
    assert _check_expectations(spec, scenario_snapshots(spec, jobs_registry())) == []


def _cutoff_unknown(**changes) -> ScenarioSpec:
    data = load_scenario(Path("bench/data/jobs_v0/cutoff_unknown__p0_jay.yaml")).model_dump()
    data.update(changes)
    return ScenarioSpec.model_validate(data)


def test_replay_stops_a_branch_at_ask_as_the_engine_does():
    # recommendation would update on any trigger, but eligibility asks first
    spec = _cutoff_unknown(
        resolutions={
            "eligibility": {"action": "ask", "question": "still eligible?"},
            "recommendation": {"action": "update", "new_content": "apply to umbrella"},
        },
        events=[_cutoff_unknown().events[0].model_dump(exclude={"expect"})],
    )
    after = scenario_snapshots(spec, jobs_registry())[1]
    assert after.memories["recommendation"].content == "skip umbrella"
    assert after.versions["recommendation"] == 1


def test_replay_carries_structure_over_an_update_that_does_not_restate_it():
    event = _cutoff_unknown().events[0].model_dump(exclude={"expect", "structured"})
    spec = _cutoff_unknown(events=[event])
    after = scenario_snapshots(spec, jobs_registry())[1]
    structured = after.memories["cgpa"].structured
    assert structured is not None and structured.attribute == "cgpa"


def test_replay_refuses_two_links_on_one_pair():
    spec = _cutoff_unknown(links=[["cgpa", "eligibility", "eligibility_of"]] * 2)
    with pytest.raises(ReplayError, match="two links"):
        scenario_snapshots(spec, jobs_registry())


def test_replay_refuses_an_event_on_a_forgotten_memory():
    first = {"forget": "eligibility"}
    second = {"answer": "eligibility", "reply": "still_holds"}
    spec = _cutoff_unknown(events=[first, second])
    with pytest.raises(ReplayError, match="event 2"):
        scenario_snapshots(spec, jobs_registry())
