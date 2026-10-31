"""bench.run v1 suites, the domain-aware runner and check_everything's order (ADR-0101, 0104)."""

import asyncio
import json

import pytest
import yaml
from bench import generate_finance, generate_news
from bench import run as bench_run
from bench.domains import domain_of, registry_for
from bench.generate import scenario_yaml
from bench.run import RunConfig, run_suite, write_results
from bench.scenario import ScenarioRunner, ScenarioSpec, validate_scenario
from bench.strategies import parents_first
from bench.tracks import load_track

from ripple.core.engine import DependencyGraph
from ripple.core.errors import ConfigurationError
from tests.builders import link


@pytest.fixture
def results_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(bench_run, "RESULTS_DIR", tmp_path)
    monkeypatch.setattr(bench_run, "git_short_sha", lambda: "testsha")
    return tmp_path


def first(module, template: str) -> ScenarioSpec:
    return next(spec for entry, spec in load_track(module.DATA_DIR) if entry.template == template)


# ---- domain-aware runner --------------------------------------------------------------------


def test_domain_of_defaults_to_jobs_and_refuses_an_unknown_domain():
    assert domain_of({}) == "jobs" and domain_of({"domain": "news"}) == "news"
    with pytest.raises(ConfigurationError, match="no adapter"):
        domain_of({"domain": "weather"})
    assert "summarises" in registry_for("news").known_types()


def test_a_news_scenario_writes_news_memories():
    runner = ScenarioRunner(first(generate_news, "figure_revised"), strategy="check_everything")
    outcome = runner.run()
    assert outcome.passed
    rows = asyncio.run(runner.store.memories_for_user("scenario-user"))
    assert rows and {m.domain for m in rows} == {"news"}


def test_validate_scenario_reports_a_link_type_the_domain_does_not_know():
    spec = first(generate_news, "figure_revised")
    broken = spec.model_copy(update={"links": [[*spec.links[0][:2], "eligibility_of"]]})
    assert any("is not a link type of the domain" in p for p in validate_scenario(broken))
    jobs_meta = spec.model_copy(update={"meta": {**spec.meta, "domain": "jobs"}})
    assert any("'summarises' is not a link type" in p for p in validate_scenario(jobs_meta))


def test_validate_scenario_reports_an_unknown_domain_instead_of_raising():
    spec = first(generate_news, "figure_revised")
    unknown = spec.model_copy(update={"meta": {**spec.meta, "domain": "weather"}})
    assert any("no adapter" in p for p in validate_scenario(unknown))


# ---- check_everything order (ADR-0104) ------------------------------------------------------


def rename_alias(spec: ScenarioSpec, old: str, new: str) -> ScenarioSpec:
    """The same scenario with one alias spelled differently: keys and link ends only."""

    def alias(name: str) -> str:
        base, at, selector = name.partition("@")
        return f"{new if base == old else base}{at}{selector}"

    raw = yaml.safe_load(scenario_yaml(spec))
    raw["memories"] = {alias(k): v for k, v in raw["memories"].items()}
    raw["links"] = [[alias(p), alias(d), t] for p, d, t in raw["links"]]
    raw["resolutions"] = {alias(k): v for k, v in raw["resolutions"].items()}
    for entries in raw["resolutions"].values():
        for entry in entries if isinstance(entries, list) else [entries]:
            if "trigger" in entry:
                entry["trigger"] = alias(entry["trigger"])
    for event in raw["events"]:
        for action in ("update", "new", "answer", "forget"):
            if action in event:
                event[action] = alias(event[action])
        event["links"] = [[alias(p), alias(d), t] for p, d, t in event.get("links", [])]
        event["expect"] = {alias(k): v for k, v in event.get("expect", {}).items()}
    return ScenarioSpec.model_validate(raw)


def test_parents_first_puts_ancestors_before_dependents_and_is_otherwise_stable():
    graph = DependencyGraph.from_links([link("a", "b"), link("b", "c")])
    assert parents_first(["c", "x", "b", "a"], graph) == ["x", "a", "b", "c"]
    assert parents_first(["x", "y"], graph) == ["x", "y"]


def test_parents_first_keeps_a_cycle_in_its_given_order():
    graph = DependencyGraph.from_links([link("a", "b"), link("b", "a")])
    assert parents_first(["b", "a", "z"], graph) == ["b", "a", "z"]


def test_parents_first_places_a_member_below_a_cycle_after_the_whole_cycle():
    graph = DependencyGraph.from_links([link("x", "y"), link("y", "x"), link("x", "a")])
    assert parents_first(["a", "x", "y"], graph) == ["x", "y", "a"]


def test_check_everything_outcome_does_not_depend_on_alias_spelling():
    # conflicting_reports: summary asks, its dependent briefing is kept by the oracle.
    # Before ADR-0104, "briefing" sorting before "summary" let the ask re-park the kept
    # briefing and the baseline matched the gold by accident of spelling.
    spec = first(generate_news, "conflicting_reports")
    renamed = rename_alias(spec, "briefing", "zz_briefing")
    outcomes = [ScenarioRunner(s, strategy="check_everything").run() for s in (spec, renamed)]
    assert [o.checks_failed for o in outcomes] == [1, 1]
    assert not any(o.passed for o in outcomes)


# ---- bench.run --------------------------------------------------------------------------------


@pytest.mark.parametrize("module", [generate_news, generate_finance])
def test_a_v1_baseline_run_writes_config_metrics_report_and_snapshots(results_dir, module):
    config = RunConfig(module.TRACK, "append_only", "strict_test")
    outcomes = run_suite(config)
    run_dir = write_results(config, outcomes, started=0.0)
    assert run_dir.name.endswith(f"_{module.TRACK}_append_only_testsha")
    config_json = json.loads((run_dir / "config.json").read_text(encoding="utf-8"))
    data = config_json["data"]
    assert data["track"] == module.TRACK and data["domain"] == module.DOMAIN
    assert data["content"] == "synthetic" and data["curated"] == {"count": 0, "sha256": None}
    assert config_json["seeds"]["generator_seed"] == module.DEFAULT_SEED
    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["split"] == "strict_test" and metrics["scenarios"] == len(outcomes) > 0
    assert metrics["scenarios_not_runnable"] == 0 and metrics["llm_calls"] == 0
    assert len(list((run_dir / "snapshots").glob("*.json"))) == len(outcomes)


def test_finance_ripple_runs_every_scenario_now_that_the_engine_exists(results_dir):
    outcomes = run_suite(RunConfig(generate_finance.TRACK, "ripple", "all"))
    assert len(outcomes) == 35 and all(o.runnable for o in outcomes)
    assert not any(o.errors for o in outcomes)


def test_finance_train_split_is_refused(results_dir, capsys):
    with pytest.raises(SystemExit):
        bench_run.main(["--suite", "finance_v1", "--strategy", "append_only", "--split", "train"])
    assert "test only (H4)" in capsys.readouterr().err


def test_curated_split_is_refused_outside_the_v1_tracks(results_dir):
    with pytest.raises(SystemExit):
        bench_run.main(["--suite", "v0", "--strategy", "append_only", "--split", "curated"])


def test_an_empty_selection_is_refused_without_writing_results(results_dir):
    # No curated stories exist yet; an empty run must not leave a folder behind.
    with pytest.raises(SystemExit):
        bench_run.main(["--suite", "news_v1", "--strategy", "append_only", "--split", "curated"])
    assert not list(results_dir.iterdir())
