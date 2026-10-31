"""Cross-run summary of the benchmark grid: means over generator seeds, H1 and H2 readings.

    uv run python -m bench.summary [--results <dir>]

Reads every bench run folder under results/ whose config.json `source_sha256` equals
the digest of the code as it is now (so a summary never mixes runs of different code),
groups them by (suite, split, strategy, ablation), keeps one folder per generator seed
(the newest; two runs of one seed must agree on every memory metric, or the summary
refuses), and writes results/<date>_benchsummary_<sha>/ with metrics.json (the whole
summary document) and report.md (its tables and the source folders): the two files
paper/i8.py reads when a document cites a results folder, so docs/results/benchmark.md
can cite this folder for every number it copies from report.md (I8). Runs labelled
alike must agree on their whole configuration but the volatile fields, and runs with
scenarios that did not run are left out (and listed).

Means are the plain mean of the per-seed values, as paper/numbers.py's MEAN aggregate
computes them; the H1 ratios are ratios of those means (ripple / check_everything), as
the registry's derived macros compute them. Min and max over seeds are reported beside
every mean. Nothing here re-runs a scenario or changes a definition.
"""

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from bench import run as bench_run

KEY_METRICS = (
    "update_accuracy",
    "dependent_update_accuracy",
    "stale_kept",
    "wrongful_changes",
    "questions_asked",
    "questions_needed",
    "stale_retrieval_rate",
    "stale_recommendation_rate",
    "ttc_share_never_converged",
    "cost_per_ripple",
    "resolver_calls_per_scenario",
)
# Counts behind the rates, per run (mean and range over seeds): top-level metrics.json
# keys first, then memory_totals keys.
COUNT_KEYS = ("scenarios", "scenarios_passed", "errors", "resolver_calls")
TOTAL_KEYS = ("should_change", "change_events", "recommendations_shown", "retrieved")
SHARES = frozenset(
    {
        "update_accuracy",
        "dependent_update_accuracy",
        "stale_retrieval_rate",
        "stale_recommendation_rate",
        "ttc_share_never_converged",
    }
)


# As paper/numbers.py VOLATILE_CONFIG: the fields runs of one configuration may differ in.
VOLATILE_CONFIG = frozenset({"seeds", "run_at", "platform", "python"})


class SummaryError(ValueError):
    """The selected runs cannot be summarised honestly (disagreeing reruns, say)."""


@dataclass(frozen=True)
class Run:
    folder: str
    config: Mapping[str, Any]
    metrics: Mapping[str, Any]

    @property
    def seed(self) -> int | None:
        seeds = self.config.get("seeds")
        return seeds.get("generator_seed") if isinstance(seeds, Mapping) else None

    @property
    def group(self) -> tuple[str, str, str, str]:
        return (
            str(self.config["suite"]),
            str(self.config.get("split")),
            str(self.config["strategy"]),
            str(self.config.get("ablation")),
        )

    @property
    def configuration(self) -> str:
        """Everything but the volatile fields, as paper/numbers.py `comparable` reads it:
        runs averaged together must agree on all of it (resolver, linker, data, probe)."""
        kept = {k: v for k, v in self.config.items() if k not in VOLATILE_CONFIG}
        return json.dumps(kept, sort_keys=True, default=str).replace("\\\\", "/")


@dataclass(frozen=True)
class Cell:
    mean: float | None
    low: float | None
    high: float | None
    values: tuple[float | None, ...]


def load_runs(results_dir: Path, digest: str) -> tuple[list[Run], list[str]]:
    """Runs of the current code, and the folders of such runs left out because some
    scenario did not run (paper/numbers.py refuses those too)."""
    runs: list[Run] = []
    incomplete: list[str] = []
    for folder in sorted(results_dir.iterdir()):
        config_path, metrics_path = folder / "config.json", folder / "metrics.json"
        if not (config_path.is_file() and metrics_path.is_file()):
            continue
        config = json.loads(config_path.read_text(encoding="utf-8"))
        if config.get("source_sha256") != digest or "strategy" not in config:
            continue
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        if not isinstance(metrics.get("memory_metrics"), Mapping):
            continue
        if metrics.get("scenarios_not_runnable") != 0:
            incomplete.append(folder.name)
            continue
        runs.append(Run(folder.name, config, metrics))
    return runs, incomplete


def one_per_seed(runs: Sequence[Run]) -> list[Run]:
    """The newest run per seed; reruns of one seed must agree (the bench is deterministic)."""
    by_seed: dict[object, Run] = {}
    for run in sorted(runs, key=lambda r: str(r.config.get("run_at"))):
        earlier = by_seed.get(run.seed)
        if (
            earlier is not None
            and earlier.metrics["memory_metrics"] != run.metrics["memory_metrics"]
        ):
            raise SummaryError(f"reruns disagree: {earlier.folder} and {run.folder}")
        by_seed[run.seed] = run
    return [by_seed[seed] for seed in sorted(by_seed, key=str)]


def cell(runs: Sequence[Run], key: str) -> Cell:
    values: list[float | None] = []
    for run in runs:
        raw = run.metrics["memory_metrics"].get(key)
        values.append(float(raw) if isinstance(raw, int | float) else None)
    numbers = [v for v in values if v is not None]
    if not numbers or len(numbers) != len(values):
        return Cell(None, None, None, tuple(values))
    return Cell(sum(numbers) / len(numbers), min(numbers), max(numbers), tuple(values))


def count_cell(runs: Sequence[Run], key: str) -> Cell:
    values = [float(run.metrics[key]) for run in runs]
    return Cell(sum(values) / len(values), min(values), max(values), tuple(values))


def total_cell(runs: Sequence[Run], key: str) -> Cell:
    values = [float(run.metrics["memory_totals"][key]) for run in runs]
    return Cell(sum(values) / len(values), min(values), max(values), tuple(values))


def summarise(runs: Sequence[Run]) -> dict[str, Any]:
    groups: dict[tuple[str, str, str, str], list[Run]] = {}
    for run in runs:
        groups.setdefault(run.group, []).append(run)
    rows: list[dict[str, Any]] = []
    for (suite, split, strategy, ablation), members in sorted(groups.items()):
        if len({run.configuration for run in members}) > 1:
            folders = ", ".join(run.folder for run in members)
            raise SummaryError(f"runs labelled alike differ in configuration: {folders}")
        chosen = one_per_seed(members)
        cells = {key: cell(chosen, key) for key in KEY_METRICS}
        for key in (*COUNT_KEYS, "llm_calls"):
            cells[key] = count_cell(chosen, key)
        for key in TOTAL_KEYS:
            cells[key] = total_cell(chosen, key)
        rows.append(
            {
                "suite": suite,
                "split": None if split == "None" else split,
                "strategy": strategy,
                "ablation": None if ablation == "None" else ablation,
                "seeds": [r.seed for r in chosen],
                "folders": [r.folder for r in chosen],
                "cells": {k: c.__dict__ | {"values": list(c.values)} for k, c in cells.items()},
            }
        )
    return {"rows": rows, "h1": _h1(rows), "h2": _h2(rows)}


def _find(
    rows: Sequence[Mapping[str, Any]], suite: str, split: str | None, strategy: str
) -> Mapping[str, Any] | None:
    for row in rows:
        if (row["suite"], row["split"], row["strategy"], row["ablation"]) == (
            suite,
            split,
            strategy,
            None,
        ):
            return row
    return None


def _mean(row: Mapping[str, Any] | None, key: str) -> float | None:
    return None if row is None else row["cells"][key]["mean"]


def _pairs(rows: Sequence[Mapping[str, Any]]) -> list[tuple[str, str | None]]:
    seen: list[tuple[str, str | None]] = []
    for row in rows:
        pair = (row["suite"], row["split"])
        if row["suite"] != "smoke" and pair not in seen:
            seen.append(pair)
    return seen


def _h1(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """ADR-0063 accuracy and ADR-0110 point 8 cost: ripple / check_everything."""
    readings: list[dict[str, Any]] = []
    for suite, split in _pairs(rows):
        ripple, ceiling = (
            _find(rows, suite, split, "ripple"),
            _find(rows, suite, split, "check_everything"),
        )
        if ripple is None or ceiling is None:
            continue
        _same_seeds(ripple, ceiling)
        readings.append(
            {
                "suite": suite,
                "split": split,
                "accuracy_ratio": _ratio(
                    _mean(ripple, "update_accuracy"), _mean(ceiling, "update_accuracy")
                ),
                "cost_ratio": _ratio(
                    _mean(ripple, "cost_per_ripple"), _mean(ceiling, "cost_per_ripple")
                ),
                "accuracy_ratio_by_seed": _by_seed(ripple, ceiling, "update_accuracy"),
                "cost_ratio_by_seed": _by_seed(ripple, ceiling, "cost_per_ripple"),
                "folders": ripple["folders"] + ceiling["folders"],
            }
        )
    return readings


def _h2(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """ADR-0110 point 8: append_only stale retrieval minus ripple's, in points."""
    readings: list[dict[str, Any]] = []
    for suite, split in _pairs(rows):
        ripple, standard = (
            _find(rows, suite, split, "ripple"),
            _find(rows, suite, split, "append_only"),
        )
        newest = _find(rows, suite, split, "newest_wins")
        if ripple is None or standard is None:
            continue
        _same_seeds(ripple, standard)
        a, r = _mean(standard, "stale_retrieval_rate"), _mean(ripple, "stale_retrieval_rate")
        readings.append(
            {
                "suite": suite,
                "split": split,
                "append_only_stale_retrieval": a,
                "ripple_stale_retrieval": r,
                "newest_wins_stale_retrieval": _mean(newest, "stale_retrieval_rate"),
                "gap_points": None if a is None or r is None else (a - r) * 100,
                "folders": standard["folders"] + ripple["folders"],
            }
        )
    return readings


def _same_seeds(left: Mapping[str, Any], right: Mapping[str, Any]) -> None:
    """A ratio or difference of seed means compares like with like only over one seed set."""
    if left["seeds"] != right["seeds"]:
        raise SummaryError(
            f"{left['strategy']} and {right['strategy']} on {left['suite']}/{left['split']} "
            f"ran different seeds: {left['seeds']} and {right['seeds']}"
        )


def _by_seed(
    left: Mapping[str, Any], right: Mapping[str, Any], key: str
) -> dict[str, float | None]:
    seeds = dict(zip(right["seeds"], right["cells"][key]["values"], strict=True))
    return {
        str(seed): _ratio(value, seeds.get(seed))
        for seed, value in zip(left["seeds"], left["cells"][key]["values"], strict=True)
    }


def _ratio(left: float | None, right: float | None) -> float | None:
    if left is None or right is None or right == 0:
        return None
    return left / right


def _fmt(value: float | None, key: str) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.1f}%" if key in SHARES else f"{value:.2f}"


def _fmt_cell(c: Mapping[str, Any], key: str) -> str:
    if c["mean"] is None:
        return "n/a"
    if c["low"] == c["high"]:
        return _fmt(c["mean"], key)
    return f"{_fmt(c['mean'], key)} [{_fmt(c['low'], key)} to {_fmt(c['high'], key)}]"


def _passed(cells: Mapping[str, Any]) -> str:
    passed, total = cells["scenarios_passed"], cells["scenarios"]["mean"]
    text = f"{passed['mean']:.1f}/{total:.0f}"
    if passed["low"] != passed["high"]:
        text += f" [{passed['low']:.0f} to {passed['high']:.0f}]"
    return text


def _count(c: Mapping[str, Any]) -> str:
    mean = c["mean"]
    text = f"{mean:.0f}" if float(mean).is_integer() else f"{mean:.1f}"
    if c["low"] != c["high"]:
        text += f" [{c['low']:.0f} to {c['high']:.0f}]"
    return text


def markdown(summary: Mapping[str, Any], folder: str) -> str:
    lines = [
        f"# Benchmark summary — {folder}",
        "",
        "Means over generator seeds, [min to max] when the seeds differ. Scripted oracle "
        "resolver, synthetic data, 0 LLM calls (see each run's config.json).",
        "",
        "| suite | split | strategy | ablation | seeds | passed | "
        + " | ".join(KEY_METRICS)
        + " |",
        "|" + "---|" * (6 + len(KEY_METRICS)),
    ]
    for row in summary["rows"]:
        cells = row["cells"]
        passed = _passed(cells)
        lines.append(
            f"| {row['suite']} | {row['split'] or '-'} | {row['strategy']} | "
            f"{row['ablation'] or '-'} | {len(row['seeds'])} | {passed} | "
            + " | ".join(_fmt_cell(cells[k], k) for k in KEY_METRICS)
            + " |"
        )
    counts = (*COUNT_KEYS, *TOTAL_KEYS)
    lines += ["", "## Counts per run (mean over seeds, [min to max] when they differ)", ""]
    lines += ["| suite | split | strategy | ablation | " + " | ".join(counts) + " |"]
    lines += ["|" + "---|" * (4 + len(counts))]
    for row in summary["rows"]:
        lines.append(
            f"| {row['suite']} | {row['split'] or '-'} | {row['strategy']} | "
            f"{row['ablation'] or '-'} | "
            + " | ".join(_count(row["cells"][k]) for k in counts)
            + " |"
        )
    lines += ["", "## H1 (ripple / check_everything, ratio of seed means)", ""]
    lines += [
        "| suite | split | accuracy ratio | cost ratio | by seed |",
        "|---|---|---|---|---|",
    ]
    for h in summary["h1"]:
        # "; " between seeds and no comma after a number: paper/i8.py only vouches for a
        # number not followed by a digit, comma, dot, slash or percent sign.
        by_seed = "; ".join(
            f"{seed}: accuracy {_fmt(h['accuracy_ratio_by_seed'][seed], 'update_accuracy')} "
            f"cost {_fmt(h['cost_ratio_by_seed'][seed], 'update_accuracy')}"
            for seed in h["accuracy_ratio_by_seed"]
        )
        lines.append(
            f"| {h['suite']} | {h['split']} | {_fmt(h['accuracy_ratio'], 'update_accuracy')} | "
            f"{_fmt(h['cost_ratio'], 'update_accuracy')} | {by_seed} |"
        )
    lines += ["", "## H2 (stale retrieval rate, append_only minus ripple)", ""]
    lines += [
        "| suite | split | append_only | newest_wins | ripple | gap (points) |",
        "|---|---|---|---|---|---|",
    ]
    for h in summary["h2"]:
        gap = "n/a" if h["gap_points"] is None else f"{h['gap_points']:.1f}"
        lines.append(
            f"| {h['suite']} | {h['split']} | "
            f"{_fmt(h['append_only_stale_retrieval'], 'stale_retrieval_rate')} | "
            f"{_fmt(h['newest_wins_stale_retrieval'], 'stale_retrieval_rate')} | "
            f"{_fmt(h['ripple_stale_retrieval'], 'stale_retrieval_rate')} | {gap} |"
        )
    lines += ["", "## Source folders", ""]
    for row in summary["rows"]:
        label = "/".join(
            str(x) for x in (row["suite"], row["split"], row["strategy"], row["ablation"])
        )
        lines.append(f"- {label}: " + ", ".join(f"results/{f}" for f in row["folders"]))
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Summarise the benchmark grid")
    parser.add_argument("--results", type=Path, default=bench_run.RESULTS_DIR)
    args = parser.parse_args(argv)
    digest = bench_run.source_digest()
    runs, incomplete = load_runs(args.results, digest)
    for folder in incomplete:
        print(f"left out (scenarios not runnable): {folder}")
    if not runs:
        print(f"no bench runs of the current code (source_sha256 {digest[:12]}) in {args.results}")
        return 1
    summary = summarise(runs)
    today = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    base = args.results / f"{today}_benchsummary_{bench_run.git_short_sha()}"
    out, counter = base, 1
    while out.exists():
        counter += 1
        out = base.with_name(f"{base.name}_{counter}")
    out.mkdir(parents=True)
    document = {
        "kind": "bench_summary",
        "source_sha256": digest,
        "git_sha": bench_run.git_short_sha(),
        "run_at": datetime.now(tz=UTC).isoformat(),
        "runs": len(runs),
        "incomplete_runs_left_out": incomplete,
        **summary,
    }
    (out / "metrics.json").write_text(json.dumps(document, indent=2), encoding="utf-8")
    (out / "report.md").write_text(markdown(summary, out.name), encoding="utf-8")
    print(f"{len(runs)} runs summarised -> {bench_run.display_path(out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
