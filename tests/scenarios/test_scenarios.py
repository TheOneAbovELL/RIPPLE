"""Every YAML scenario runs against the real WaveEngine.

The loader and the runner's own logic are tested separately.
"""

import pytest

from tests.scenarios.runner import ScenarioRunner, load_scenario, scenario_paths


@pytest.mark.parametrize("path", scenario_paths(), ids=lambda p: p.stem)
def test_scenario(path):
    outcome = ScenarioRunner(load_scenario(path)).run()
    assert outcome.failures == []
    assert outcome.checks > 0


def test_every_scenario_file_loads_and_declares_expectations():
    paths = scenario_paths()
    assert len(paths) >= 10, "the smoke suite needs at least ten scenarios"
    for path in paths:
        spec = load_scenario(path)
        assert spec.name == path.stem
        assert spec.events, path
        assert any(event.expect for event in spec.events), path
        for link in spec.links:
            assert link[0] in spec.memories and link[1] in spec.memories, path
