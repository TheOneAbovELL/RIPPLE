"""RippleBench v0 generator (ADR-0061): determinism, validity, split hygiene, baselines run."""

import json
from pathlib import Path

import pytest
from bench.generate import (
    DATA_DIR,
    TEMPLATES,
    Generated,
    check_data,
    generate,
    load_jobs_v0,
    load_manifest,
    make_personas,
    scenario_yaml,
    write_data,
)
from bench.scenario import ScenarioRunner, load_scenario, validate_scenario

FAMILIES = {"changed", "unchanged", "temporary", "chain", "ask", "snapshot", "forget"}


@pytest.fixture(scope="module")
def generated() -> Generated:
    return generate(seed=7, personas=5)


def test_generate_is_deterministic_for_the_same_seed(generated):
    again = generate(seed=7, personas=5)
    assert [scenario_yaml(s) for _, s in again.scenarios] == [
        scenario_yaml(s) for _, s in generated.scenarios
    ]
    assert again.manifest == generated.manifest


def test_generate_changes_with_the_seed():
    assert (
        generate(seed=1, personas=3).manifest["data_sha256"]
        != (generate(seed=2, personas=3).manifest["data_sha256"])
    )


def test_adding_a_persona_leaves_earlier_personas_scenarios_unchanged():
    four, five = generate(seed=7, personas=4), generate(seed=7, personas=5)
    first_four = {e.name: scenario_yaml(s) for e, s in five.scenarios if e.persona in make_ids(4)}
    assert {e.name: scenario_yaml(s) for e, s in four.scenarios} == first_four


def make_ids(count: int) -> set[str]:
    return {p.id for p in make_personas(7, count)}


def test_every_generated_scenario_is_valid_and_covers_every_family(generated):
    assert len(generated.scenarios) == 5 * len(TEMPLATES) == 35
    assert {e.family for e, _ in generated.scenarios} == FAMILIES
    for entry, spec in generated.scenarios:
        assert validate_scenario(spec) == [], entry.name
        assert spec.name == entry.name == Path(entry.file).stem
        assert spec.meta["persona"] == entry.persona and spec.meta["template"] == entry.template
        assert any(event.expect for event in spec.events), entry.name


def test_split_is_by_persona_and_template_never_by_item(generated):
    manifest = generated.manifest
    test_personas, test_templates = (
        set(manifest["personas"]["test"]),
        set(manifest["templates"]["test"]),
    )
    assert test_personas and test_templates
    for raw in manifest["scenarios"]:
        unseen = (raw["persona"] in test_personas, raw["template"] in test_templates)
        expected = {
            (False, False): ("train", "none"),
            (True, False): ("test", "persona"),
            (False, True): ("test", "template"),
            (True, True): ("test", "both"),
        }[unseen]
        assert (raw["split"], raw["held_out"]) == expected, raw["name"]
    train = [r for r in manifest["scenarios"] if r["split"] == "train"]
    strict = [r for r in manifest["scenarios"] if r["held_out"] == "both"]
    assert not {r["persona"] for r in train} & {r["persona"] for r in strict}
    assert not {r["template"] for r in train} & {r["template"] for r in strict}


def test_written_files_round_trip_through_the_loader(generated, tmp_path):
    write_data(generated, tmp_path)
    assert check_data(generated, tmp_path) == []
    loaded = load_jobs_v0("all", tmp_path)
    assert [e for e, _ in loaded] == [e for e, _ in generated.scenarios]
    assert [s for _, s in loaded] == [s for _, s in generated.scenarios]
    assert len(load_jobs_v0("train", tmp_path)) + len(load_jobs_v0("test", tmp_path)) == 35
    assert all(e.held_out == "both" for e, _ in load_jobs_v0("strict_test", tmp_path))
    with pytest.raises(ValueError, match="unknown split"):
        load_jobs_v0("dev", tmp_path)


def test_check_data_reports_drift(generated, tmp_path):
    write_data(generated, tmp_path)
    (tmp_path / "manifest.json").write_text("{}", encoding="utf-8")
    first = next(iter(tmp_path.glob("*.yaml")))
    first.write_text(first.read_text(encoding="utf-8") + "# edited\n", encoding="utf-8")
    problems = check_data(generated, tmp_path)
    assert "manifest.json differs from a fresh generation" in problems
    assert f"{first.name} differs from a fresh generation" in problems


def test_checked_in_data_matches_a_fresh_default_generation():
    """The committed bench/data/jobs_v0 is exactly what `python -m bench.generate` writes."""
    assert check_data(generate(), DATA_DIR) == []
    manifest = load_manifest()
    assert manifest["track"] == "jobs_v0" and len(manifest["scenarios"]) == 35
    assert manifest["data_sha256"] == generate().manifest["data_sha256"]


V0 = load_jobs_v0()


@pytest.mark.parametrize("strategy", ["append_only", "newest_wins", "check_everything"])
@pytest.mark.parametrize("item", V0, ids=lambda item: item[0].name)
def test_baselines_run_every_v0_scenario_to_completion(strategy, item):
    _, spec = item
    outcome = ScenarioRunner(spec, strategy=strategy).run()
    assert outcome.runnable, outcome.errors
    assert outcome.events_run == len(spec.events)


@pytest.mark.parametrize("item", V0, ids=lambda item: item[0].name)
def test_the_oracle_resolver_lets_check_everything_match_gold_except_where_the_graph_matters(
    item,
):
    """check_everything re-checks everything with the gold oracle, so it matches gold
    everywhere except the ask family, where the subtree flag needs the graph."""
    entry, spec = item
    outcome = ScenarioRunner(spec, strategy="check_everything").run()
    if entry.family == "ask":
        assert outcome.failures == ["recommendation: status VALID, expected SUSPECT"]
    else:
        assert outcome.passed, outcome.problems


@pytest.mark.parametrize("item", V0, ids=lambda item: item[0].name)
def test_append_only_fails_gold_in_every_v0_scenario(item):
    _, spec = item
    assert not ScenarioRunner(spec, strategy="append_only").run().passed


def test_write_data_refuses_a_directory_of_hand_written_scenarios(generated, tmp_path):
    (tmp_path / "cgpa_change.yaml").write_text("name: cgpa_change\n", encoding="utf-8")
    with pytest.raises(FileExistsError, match=r"no manifest\.json"):
        write_data(generated, tmp_path)
    assert (tmp_path / "cgpa_change.yaml").exists()


def test_write_data_replaces_only_files_its_previous_manifest_listed(generated, tmp_path):
    write_data(generated, tmp_path)
    (tmp_path / "unrelated.yaml").write_text("name: unrelated\n", encoding="utf-8")
    write_data(generate(seed=8, personas=2), tmp_path)
    names = {p.name for p in tmp_path.glob("*.yaml")}
    assert "unrelated.yaml" in names and len(names) == 2 * len(TEMPLATES) + 1


def test_make_personas_refuses_more_personas_than_names():
    with pytest.raises(ValueError, match="at most"):
        make_personas(1, 11)


def test_scenario_files_on_disk_load_with_the_shared_loader():
    for path in sorted(DATA_DIR.glob("*.yaml")):
        spec = load_scenario(path)
        assert spec.name == path.stem
        assert json.loads(json.dumps(spec.meta))["track"] == "jobs_v0"
