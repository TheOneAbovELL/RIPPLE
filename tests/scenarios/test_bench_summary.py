"""bench.summary: seed means, H1/H2 readings and refusal rules over real run folders."""

import json

import pytest
from bench import run as bench_run
from bench import summary
from bench.matrix import grid
from bench.run import RunConfig, run_suite, write_results
from bench.seeds import generator_seeds


@pytest.fixture
def results_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(bench_run, "RESULTS_DIR", tmp_path)
    monkeypatch.setattr(bench_run, "git_short_sha", lambda: "testsha")
    return tmp_path


def _seeded_runs(strategies, seeds=2):
    seed_set = generator_seeds("finance_v1", seeds)
    for strategy in strategies:
        for seed in seed_set:
            config = RunConfig("finance_v1", strategy, "strict_test", None, seed, seed_set)
            write_results(config, run_suite(config), started=0.0)


def test_summary_means_each_metric_over_seeds_and_reads_h1_and_h2(results_dir):
    _seeded_runs(("ripple", "check_everything", "append_only"))
    assert summary.main(["--results", str(results_dir)]) == 0
    (out,) = results_dir.glob("*_benchsummary_testsha")
    document = json.loads((out / "metrics.json").read_text(encoding="utf-8"))
    rows = {row["strategy"]: row for row in document["rows"]}
    accuracy = rows["ripple"]["cells"]["update_accuracy"]
    assert len(accuracy["values"]) == 2
    assert accuracy["mean"] == pytest.approx(sum(accuracy["values"]) / 2)
    (h1,) = document["h1"]
    ceiling = rows["check_everything"]["cells"]
    assert h1["cost_ratio"] == pytest.approx(
        rows["ripple"]["cells"]["cost_per_ripple"]["mean"] / ceiling["cost_per_ripple"]["mean"]
    )
    (h2,) = document["h2"]
    assert h2["gap_points"] == pytest.approx(
        (h2["append_only_stale_retrieval"] - h2["ripple_stale_retrieval"]) * 100
    )
    text = (out / "report.md").read_text(encoding="utf-8")
    assert all(f"results/{folder}" in text for row in document["rows"] for folder in row["folders"])


def test_summary_ignores_runs_of_other_code(results_dir, monkeypatch):
    _seeded_runs(("append_only",), seeds=1)
    monkeypatch.setattr(bench_run, "source_digest", lambda: "f" * 64)
    assert summary.main(["--results", str(results_dir)]) == 1
    assert not list(results_dir.glob("*_benchsummary_*"))


def test_summary_refuses_reruns_of_one_seed_that_disagree(results_dir):
    _seeded_runs(("append_only",), seeds=1)
    (first,) = results_dir.iterdir()
    copy = results_dir / f"{first.name}_2"
    copy.mkdir()
    config = json.loads((first / "config.json").read_text(encoding="utf-8"))
    config["run_at"] = "2999-01-01T00:00:00+00:00"
    metrics = json.loads((first / "metrics.json").read_text(encoding="utf-8"))
    metrics["memory_metrics"]["update_accuracy"] = 0.123
    (copy / "config.json").write_text(json.dumps(config), encoding="utf-8")
    (copy / "metrics.json").write_text(json.dumps(metrics), encoding="utf-8")
    runs, _ = summary.load_runs(results_dir, bench_run.source_digest())
    with pytest.raises(summary.SummaryError, match="reruns disagree"):
        summary.summarise(runs)


def test_matrix_grid_covers_every_track_strategy_seed_and_offline_ablation():
    runs = list(grid())
    assert len(runs) == 4 + (2 + 2 + 1) * 4 + 3 * 2
    seeded = [argv for argv in runs if "--generator-seeds" in argv]
    assert all(argv[argv.index("--generator-seeds") + 1] == "3" for argv in seeded)
    ablations = {argv[argv.index("--ablation") + 1] for argv in runs if "--ablation" in argv}
    assert ablations == {"no_graph", "no_ask_user"}


def test_summary_leaves_out_a_run_with_scenarios_that_did_not_run(results_dir):
    _seeded_runs(("append_only",), seeds=1)
    (folder,) = results_dir.iterdir()
    metrics = json.loads((folder / "metrics.json").read_text(encoding="utf-8"))
    metrics["scenarios_not_runnable"] = 1
    (folder / "metrics.json").write_text(json.dumps(metrics), encoding="utf-8")
    runs, incomplete = summary.load_runs(results_dir, bench_run.source_digest())
    assert runs == [] and incomplete == [folder.name]


def test_summary_refuses_to_average_runs_that_differ_beyond_their_seed(results_dir):
    _seeded_runs(("append_only",), seeds=2)
    folder = sorted(results_dir.iterdir())[1]
    config = json.loads((folder / "config.json").read_text(encoding="utf-8"))
    config["resolver"] = "llm resolver"
    (folder / "config.json").write_text(json.dumps(config), encoding="utf-8")
    runs, _ = summary.load_runs(results_dir, bench_run.source_digest())
    with pytest.raises(summary.SummaryError, match="differ in configuration"):
        summary.summarise(runs)


def test_matrix_stops_before_summarising_a_grid_with_a_refused_run(monkeypatch, capsys):
    from bench import matrix

    def refuse(argv):
        raise SystemExit(2)

    monkeypatch.setattr(matrix.bench_run, "main", refuse)
    monkeypatch.setattr(matrix.summary, "main", lambda argv: pytest.fail("summarised"))
    assert matrix.main([]) == 2
    assert "REFUSED bench.run --suite smoke" in capsys.readouterr().out


def test_summary_refuses_a_ratio_over_strategies_that_ran_different_seeds(results_dir):
    _seeded_runs(("ripple",), seeds=2)
    _seeded_runs(("check_everything",), seeds=1)
    runs, _ = summary.load_runs(results_dir, bench_run.source_digest())
    with pytest.raises(summary.SummaryError, match="ran different seeds"):
        summary.summarise(runs)


def test_summary_reports_the_seed_range_of_passed_scenarios_and_the_counts():
    cells = {
        "scenarios_passed": {"mean": 17.0, "low": 15.0, "high": 18.0},
        "scenarios": {"mean": 20.0, "low": 20.0, "high": 20.0},
    }
    assert summary._passed(cells) == "17.0/20 [15 to 18]"  # pyright: ignore[reportPrivateUsage]
    assert summary._count({"mean": 24.0, "low": 24.0, "high": 24.0}) == "24"  # pyright: ignore[reportPrivateUsage]
    assert summary._count({"mean": 25.0, "low": 24.0, "high": 27.0}) == "25 [24 to 27]"  # pyright: ignore[reportPrivateUsage]
