"""The scenario runner lives in bench/scenario.py; this module keeps the test-side
names and knows where the hand-written smoke scenarios are."""

from pathlib import Path

from bench.scenario import (
    USER,
    AliasResolver,
    EventSpec,
    Expectation,
    MemorySpec,
    ResolutionSpec,
    ScenarioOutcome,
    ScenarioRunner,
    ScenarioSpec,
    load_scenario,
    validate_scenario,
)

SCENARIO_DIR = Path(__file__).parent

__all__ = [
    "SCENARIO_DIR",
    "USER",
    "AliasResolver",
    "EventSpec",
    "Expectation",
    "MemorySpec",
    "ResolutionSpec",
    "ScenarioOutcome",
    "ScenarioRunner",
    "ScenarioSpec",
    "load_scenario",
    "scenario_paths",
    "validate_scenario",
]


def scenario_paths() -> list[Path]:
    return sorted(SCENARIO_DIR.glob("*.yaml"))
