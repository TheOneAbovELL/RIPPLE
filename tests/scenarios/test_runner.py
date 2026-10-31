"""The scenario runner itself, with a scripted engine so it does not wait on the human task.

Root rows get their alias as id, so a ScriptedEngine can plan waves by alias.
"""

from ripple.core.models import DecisionAction, Status
from tests.fakes.engine import ScriptedEngine
from tests.scenarios.runner import (
    EventSpec,
    Expectation,
    MemorySpec,
    ResolutionSpec,
    ScenarioRunner,
    ScenarioSpec,
)


def _spec(**events_kwargs):
    return ScenarioSpec(
        name="inline",
        memories={
            "cgpa": MemorySpec(content="CGPA is 7.6"),
            "eligibility": MemorySpec(kind="derived", content="not eligible"),
        },
        links=[["cgpa", "eligibility", "eligibility_of"]],
        resolutions={
            "eligibility": ResolutionSpec(action=DecisionAction.UPDATE, new_content="eligible")
        },
        events=[EventSpec(**events_kwargs)],
    )


def _scripted(*waves):
    class Factory(ScriptedEngine):
        def __init__(self, max_depth: int = 8) -> None:
            super().__init__(*(waves or (["eligibility"],)), max_depth=max_depth)

    return Factory


def test_runner_reports_passing_expectations():
    spec = _spec(
        update="cgpa",
        content="CGPA is 7.9",
        expect={
            "cgpa": Expectation(status=Status.RETIRED),
            "eligibility@latest": Expectation(status=Status.VALID, content="eligible", version=2),
        },
    )
    outcome = ScenarioRunner(spec, engine_factory=_scripted()).run()  # type: ignore[arg-type]
    assert outcome.passed and outcome.checks == 2 and outcome.resolver_calls == 1


def test_runner_reports_a_wrong_expectation_with_detail():
    spec = _spec(
        update="cgpa",
        content="CGPA is 7.9",
        expect={"eligibility@latest": Expectation(content="still not eligible")},
    )
    outcome = ScenarioRunner(spec, engine_factory=_scripted()).run()  # type: ignore[arg-type]
    assert not outcome.passed
    assert outcome.failures == [
        "eligibility@latest: content 'eligible', expected 'still not eligible'"
    ]


def test_runner_forget_and_deleted_expectation():
    spec = _spec(
        forget="cgpa",
        expect={"cgpa": Expectation(deleted=True), "eligibility": Expectation(deleted=True)},
    )
    outcome = ScenarioRunner(spec).run()
    assert outcome.passed


def test_runner_records_a_snapshot_after_seeding_and_after_every_event():
    spec = _spec(update="cgpa", content="CGPA is 7.9", expect={})
    outcome = ScenarioRunner(spec, engine_factory=_scripted()).run()  # type: ignore[arg-type]
    assert outcome.trace is not None
    assert [e.action for e in outcome.trace.events] == ["seed", "update:cgpa"]
    seeded, after = outcome.trace.events
    before_state, after_state, cgpa_root = (
        seeded.state_of("eligibility@latest"),
        after.state_of("eligibility@latest"),
        after.state_of("cgpa"),
    )
    assert before_state is not None and before_state.version == 1
    assert after_state is not None and after_state.content == "eligible"
    assert cgpa_root is not None and cgpa_root.status == "RETIRED"
    assert after.resolver_calls == 1


def test_runner_rejects_an_unknown_strategy():
    import pytest

    with pytest.raises(ValueError, match="unknown strategy"):
        ScenarioRunner(_spec(forget="cgpa"), strategy="mem0")


def test_update_carries_over_structured_and_valid_to_when_the_event_omits_them():
    import asyncio
    from datetime import timedelta

    from ripple.core.models import StructuredFact

    spec = ScenarioSpec(
        name="carry",
        memories={
            "exams": MemorySpec(
                content="busy with exams",
                structured=StructuredFact(
                    subject="student", attribute="availability", value="exams"
                ),
                valid_to_days=10,
            )
        },
        events=[EventSpec(update="exams", content="busy with exams and labs", expect={})],
    )
    runner = ScenarioRunner(spec, strategy="newest_wins")
    runner.run()
    latest = asyncio.run(runner.store.latest_version("exams"))
    assert latest.structured is not None and latest.structured.value == "exams"
    assert latest.valid_to == runner.started_at + timedelta(days=10)


def test_validate_scenario_rejects_unknown_action_aliases_and_double_actions():
    from tests.scenarios.runner import validate_scenario

    spec = ScenarioSpec(
        name="bad",
        memories={"cgpa": MemorySpec(content="CGPA is 7.6")},
        events=[
            EventSpec(forget="nope"),
            EventSpec(update="cgpa", content="x", advance_days=1),
            EventSpec(new="cgpa", content="dup"),
        ],
    )
    assert validate_scenario(spec) == [
        "event 1: forget names an unknown alias 'nope'",
        "event 2 must carry exactly one action, has ['update', 'advance_days']",
        "event 3: alias 'cgpa' already exists",
    ]
