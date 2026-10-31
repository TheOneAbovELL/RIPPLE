"""bench.run writes a results/ folder per run with config, metrics, report and snapshots."""

import json

import pytest
from bench import run as bench_run
from bench.run import RunConfig, run_suite, write_results
from bench.seeds import SeedDriftError, generate_track, generator_seeds
from paper.registry import MEMORY_METRICS


@pytest.fixture
def results_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(bench_run, "RESULTS_DIR", tmp_path)
    monkeypatch.setattr(bench_run, "git_short_sha", lambda: "testsha")
    return tmp_path


def test_smoke_ripple_runs_every_scenario_and_passes_them(results_dir):
    config = RunConfig("smoke", "ripple", "all")
    outcomes = run_suite(config)
    run_dir = write_results(config, outcomes, started=0.0)
    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    assert run_dir.name.split("_", 1)[1] == "smoke_ripple_testsha" or run_dir.name.endswith(
        "smoke_testsha"
    )
    assert metrics["scenarios_not_runnable"] == 0
    assert metrics["scenarios_passed"] == metrics["scenarios"] == 11
    assert not any(o.errors or o.failures for o in outcomes)
    assert json.loads((run_dir / "config.json").read_text())["engine"] == (
        "ripple.core.engine.WaveEngine"
    )


def test_v0_baseline_run_writes_config_metrics_report_and_snapshots(results_dir):
    config = RunConfig("v0", "append_only", "strict_test")
    outcomes = run_suite(config)
    run_dir = write_results(config, outcomes, started=0.0)
    assert run_dir.name.endswith("_v0_append_only_testsha")
    config_json = json.loads((run_dir / "config.json").read_text(encoding="utf-8"))
    assert config_json["seeds"]["generator_seed"] == 20261019
    assert config_json["data"]["data_sha256"] and config_json["data"]["split"] == "strict_test"
    # No model and no prompt was used, and metrics.json counts the LLM calls to prove it.
    assert config_json["prompt_versions"] == {} and config_json["models"] == {}
    assert config_json["ablation"] is None and config_json["linker"] == "scenario"
    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["scenarios"] == len(outcomes) == 4
    assert metrics["scenarios_not_runnable"] == 0 and metrics["resolver_calls"] == 0
    assert 0 < metrics["checks_failed"] <= metrics["checks"]
    assert all(o["checks_failed"] <= o["checks"] for o in metrics["per_scenario"])
    assert set(metrics["memory_metrics"]) >= {key for key, _, _ in MEMORY_METRICS}
    assert metrics["llm_calls"] == 0 and "oracle" in metrics["llm_calls_note"]
    assert len(list((run_dir / "snapshots").glob("*.json"))) == 4
    report = (run_dir / "report.md").read_text(encoding="utf-8")
    assert "strategy append_only" in report and "| cgpa_rise__" in report


def test_main_exit_code_is_nonzero_when_a_scenario_fails_or_cannot_run(results_dir, capsys):
    assert (
        bench_run.main(["--suite", "v0", "--strategy", "newest_wins", "--split", "strict_test"])
        == 1
    )
    out = capsys.readouterr().out
    assert "v0/newest_wins:" in out and "FAIL" in out


def test_a_second_run_on_the_same_day_gets_its_own_folder(results_dir):
    config = RunConfig("v0", "append_only", "strict_test")
    first = write_results(config, run_suite(config), started=0.0)
    second = write_results(config, run_suite(config), started=0.0)
    assert first != second and second.name == f"{first.name}_2"


def test_an_invalid_scenario_is_reported_not_runnable_instead_of_crashing(monkeypatch, results_dir):
    from bench.scenario import EventSpec, MemorySpec, ScenarioSpec

    broken = ScenarioSpec(
        name="broken",
        memories={"cgpa": MemorySpec(content="CGPA is 7.6")},
        events=[EventSpec(update="cgpa_typo", content="x")],
    )
    monkeypatch.setattr(bench_run, "scenarios_for", lambda config: [("broken", broken)])
    (outcome,) = run_suite(RunConfig("smoke", "newest_wins", "all"))
    assert not outcome.runnable
    assert outcome.errors == [
        "not runnable: invalid scenario: event 1: update names an unknown alias 'cgpa_typo'"
    ]


def test_git_short_sha_marks_a_dirty_tree(monkeypatch):
    import subprocess

    class Done:
        def __init__(self, stdout: str) -> None:
            self.stdout = stdout

    answers = {"rev-parse": Done("abc1234\n"), "status": Done(" M bench/run.py\n")}
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: answers[cmd[1]])
    assert bench_run.git_short_sha() == "abc1234-dirty"
    answers["status"] = Done("")
    assert bench_run.git_short_sha() == "abc1234"


def _read(run_dir, name):
    return json.loads((run_dir / name).read_text(encoding="utf-8"))


def test_memory_metrics_of_a_v0_run_carry_every_registry_key_as_a_number_or_none(results_dir):
    config = RunConfig("v0", "check_everything", "strict_test")
    metrics = _read(write_results(config, run_suite(config), started=0.0), "metrics.json")
    memory = metrics["memory_metrics"]
    for key, _, _ in MEMORY_METRICS:
        assert memory[key] is None or isinstance(memory[key], int | float), key
    # The oracle spends no tokens: not measured, never a flattering 0.
    assert memory["tokens_per_ripple"] is None and memory["usd_per_ripple"] is None
    assert memory["cost_per_ripple"] > 0 and 0.0 <= memory["update_accuracy"] <= 1.0
    totals = metrics["memory_totals"]
    assert totals["resolver_calls"] == metrics["resolver_calls"]
    assert all("memory" in row for row in metrics["per_scenario"])


def test_generator_seeds_start_at_the_checked_in_default_and_count_up():
    assert generator_seeds("v0") == (20261019, 20261020, 20261021)
    assert len(generator_seeds("news_v1", 1)) == 1


def test_the_default_seed_reproduces_the_checked_in_data_and_others_differ():
    first, second = (generate_track("v0", seed) for seed in generator_seeds("v0", 2))
    assert first.data_sha256 == bench_run.load_manifest()["data_sha256"]
    assert second.data_sha256 != first.data_sha256
    assert len(second.scenarios) == len(first.scenarios) == 35


def test_a_drifted_default_seed_is_refused(monkeypatch):
    from bench import seeds

    monkeypatch.setattr(seeds, "load_manifest", lambda folder: {"data_sha256": "0" * 64})
    with pytest.raises(SeedDriftError):
        seeds.generate_track("v0", seeds.default_seed("v0"))


def test_runs_of_one_seed_group_differ_only_in_their_seed(results_dir):
    seed_set = generator_seeds("v0", 2)
    configs = [RunConfig("v0", "newest_wins", "strict_test", None, s, seed_set) for s in seed_set]
    dirs = [write_results(c, run_suite(c), started=0.0) for c in configs]
    assert [d.name.split("_", 1)[1] for d in dirs] == [
        f"v0_newest_wins_g{seed}_testsha" for seed in seed_set
    ]
    first, second = (_read(d, "config.json") for d in dirs)
    volatile = {"seeds", "run_at"}
    assert {k: v for k, v in first.items() if k not in volatile} == {
        k: v for k, v in second.items() if k not in volatile
    }
    assert first["seeds"]["kind"] == "generator" and first["seeds"]["run_seed"] is None
    by_seed = first["data"]["data_sha256_by_seed"]
    assert [first["seeds"]["data_sha256"], second["seeds"]["data_sha256"]] == [
        by_seed[str(seed)] for seed in seed_set
    ]


def test_an_ablation_run_is_labelled_in_its_folder_config_and_metrics(results_dir):
    config = RunConfig("v0", "ripple", "all", "no_ask_user")
    run_dir = write_results(config, run_suite(config), started=0.0)
    assert run_dir.name.endswith("_v0_ripple_no_ask_user_testsha")
    config_json, metrics = _read(run_dir, "config.json"), _read(run_dir, "metrics.json")
    assert config_json["ablation"] == metrics["ablation"] == "no_ask_user"
    assert "asks replaced by keeps" in config_json["resolver"]
    assert config_json["resolver"].startswith("scripted oracle")
    assert metrics["memory_metrics"]["questions_asked"] == 0.0
    # The same split without the ablation does ask, so the 0 above is the ablation's.
    unablated = RunConfig("v0", "ripple", "all")
    asked = _read(write_results(unablated, run_suite(unablated), started=0.0), "metrics.json")
    assert asked["memory_metrics"]["questions_asked"] > 0


def test_main_runs_one_folder_per_generator_seed(results_dir, capsys):
    argv = ["--suite", "finance_v1", "--strategy", "append_only", "--split", "strict_test"]
    bench_run.main([*argv, "--generator-seeds", "2"])
    folders = sorted(path.name for path in results_dir.iterdir())
    assert len(folders) == 2 and all("_finance_v1_append_only_g2026103" in f for f in folders)
    assert "seed 20261031" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("argv", "message"),
    [
        (["--strategy", "append_only", "--ablation", "no_graph"], "ripple only"),
        (["--suite", "smoke", "--generator-seeds", "3"], "generated tracks"),
    ],
)
def test_main_refuses_an_ablation_or_seeds_where_they_do_not_apply(
    results_dir, capsys, argv, message
):
    with pytest.raises(SystemExit):
        bench_run.main(["--suite", "v0", *argv] if argv[0] != "--suite" else argv)
    assert message in capsys.readouterr().err
    assert not list(results_dir.iterdir())


LOADED_BY_A_RUN = """
import json, sys
from bench import run as r
for strategy in ("ripple", "append_only", "newest_wins", "check_everything"):
    r.run_suite(r.RunConfig("smoke", strategy, "all"))
seed = 20261032
r.run_suite(r.RunConfig("finance_v1", "ripple", "strict_test", "no_ask_user", seed, (seed,)))
r.run_suite(r.RunConfig("news_v1", "ripple", "strict_test", "no_graph"))
files = [getattr(m, "__file__", None) for m in list(sys.modules.values())]
print(json.dumps(sorted(f for f in files if f)))
"""


def test_source_digest_covers_every_repository_module_a_run_loads():
    import subprocess
    import sys
    from pathlib import Path

    done = subprocess.run(
        [sys.executable, "-c", LOADED_BY_A_RUN],
        cwd=bench_run.REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    repo = bench_run.REPO_ROOT.resolve()
    loaded = [Path(f).resolve() for f in json.loads(done.stdout.strip().splitlines()[-1])]
    ours = [p for p in loaded if p.is_relative_to(repo) and ".venv" not in p.parts]
    roots = [root.resolve() for root in bench_run.DIGEST_ROOTS]
    uncovered = [p for p in ours if not any(p == root or p.is_relative_to(root) for root in roots)]
    assert ours and uncovered == []


def test_source_digest_leaves_out_the_grid_driver_and_the_summary():
    skipped = {path.name for path in bench_run.NOT_RUN_BY_A_BENCH_RUN}
    assert skipped == {"matrix.py", "summary.py"} and len(bench_run.source_digest()) == 64
