"""Mean and spread over link-pair run folders (ADR-0127), so a report cites one file.

    uv run python -m training.summarize results/<run-a> results/<run-b> ...

Groups the named runs by (linker, track, split, new memory) and writes
results/<date>_linkpairs_summary_<sha>/ with summary.json and report.md: per group, the
mean, sample standard deviation, minimum and maximum of precision, recall, F1 and typed
F1, overall and per held-out cell, and of the cost per call, each with the folders it
came from. Nothing is computed that a run folder does not already hold (I8).
"""

import argparse
import json
import statistics
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from bench.run import RESULTS_DIR, git_short_sha

from training.jobs_pairs import REPO_ROOT

METRICS = ("precision", "recall", "f1", "typed_f1")
COSTS = ("wall_seconds_per_call", "cpu_seconds_per_call")


def spread(values: Sequence[float | None], digits: int = 4) -> dict[str, object]:
    """n counts the runs with a value; null values (an undefined metric) are skipped.
    Costs pass more digits: a rule call takes well under a millisecond."""
    present = [v for v in values if v is not None]
    if not present:
        return {"n": 0, "mean": None, "sd": None, "min": None, "max": None}
    return {
        "n": len(present),
        "mean": round(statistics.fmean(present), digits),
        "sd": round(statistics.stdev(present), digits) if len(present) > 1 else None,
        "min": round(min(present), digits),
        "max": round(max(present), digits),
    }


def _read(run_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    config = json.loads((run_dir / "config.json").read_text(encoding="utf-8"))
    result = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    if config.get("suite") != "linkpairs":
        raise ValueError(f"{run_dir} is not a link-pair run")
    return config, result


def _cells(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    cells: dict[str, dict[str, Any]] = {"overall": result["overall"]}
    by_held_out: dict[str, Any] = result.get("by_held_out", {})
    cells |= {f"held_out={k}": v for k, v in by_held_out.items()}
    return cells


GroupKey = tuple[str, str, str, str, str, str, bool]


def _group_key(config: dict[str, Any]) -> GroupKey:
    """Runs average together only when they differ by seed alone: same linker, base model,
    pair file, split, query side and transfer setting."""
    models = config.get("models") or {}
    return (
        str(config["linker"]),
        str(models.get("base_model", "")),
        str(config["track"]),
        str(config["data"]["pairs_sha256"]),
        str(config["split"]),
        str(config["new_memory"]),
        config.get("transfer") is not None,
    )


def summarize(run_dirs: Sequence[Path]) -> dict[str, object]:
    groups: dict[GroupKey, list[tuple[Path, dict[str, Any], dict[str, Any]]]] = {}
    unique = list(dict.fromkeys(d.resolve() for d in run_dirs))  # a folder counts once
    for run_dir in unique:
        config, result = _read(run_dir)
        groups.setdefault(_group_key(config), []).append((run_dir, config, result))
    summary: list[dict[str, object]] = []
    for (linker, base_model, track, pairs_sha, split, new, transfer), runs in sorted(
        groups.items()
    ):
        cell_names = sorted({name for _, _, r in runs for name in _cells(r)})
        cells = {
            name: {
                "pairs": sorted({int(_cells(r).get(name, {}).get("n", 0)) for _, _, r in runs}),
                **{
                    metric: spread([_cells(r).get(name, {}).get(metric) for _, _, r in runs])
                    for metric in METRICS
                },
            }
            for name in cell_names
        }
        costs = {
            cost: spread([r.get("cost", {}).get(cost) for _, _, r in runs], digits=6)
            for cost in COSTS
        }
        summary.append(
            {
                "linker": linker,
                "base_model": base_model or None,
                "track": track,
                "pairs_sha256": pairs_sha,
                "transfer": transfer,
                "split": split,
                "new_memory": new,
                "runs": [_display(d) for d, _, _ in runs],
                "seeds": [c.get("linker_details", {}).get("seed") for _, c, _ in runs],
                "typed": sorted({bool(c["typed"]) for _, c, _ in runs}),
                "cells": cells,
                "cost": costs,
            }
        )
    return {"suite": "linkpairs_summary", "groups": summary}


def _display(path: Path) -> str:
    resolved = path.resolve()
    if resolved.is_relative_to(REPO_ROOT):
        return resolved.relative_to(REPO_ROOT).as_posix()
    return resolved.as_posix()


def _fmt(stat: dict[str, object], runs: int) -> str:
    """Mean ± sd; "(n=k)" when only k of the runs define the metric."""
    if stat["mean"] is None:
        return "n/a"
    text = f"{stat['mean']:.3f}"
    if stat["sd"] is not None:
        text += f" ± {stat['sd']:.3f}"
    if stat["n"] != runs:
        text += f" (n={stat['n']})"
    return text


def report(summary: dict[str, object]) -> str:
    lines = [
        "# Link pairs: summary over runs",
        "",
        "mean ± sample standard deviation over the runs listed (one value: no spread; "
        "(n=k): only k runs define the metric, e.g. precision with no predicted link). "
        "Read held_out=both for H3 on the jobs track. n/a: undefined in that cell "
        "(no gold negatives, or typed metrics off).",
        "",
    ]
    groups = summary["groups"]
    assert isinstance(groups, list)
    for group in groups:
        runs = len(group["runs"])
        lines += [
            f"## {_title(group)} ({len(group['runs'])} runs)",
            "",
            "Runs: " + ", ".join(f"`{r}`" for r in group["runs"]),
            "",
            "| cell | pairs | precision | recall | F1 | typed F1 |",
            "|---|---|---|---|---|---|",
        ]
        for name, cell in group["cells"].items():
            lines.append(
                f"| {name} | {', '.join(map(str, cell['pairs']))} "
                + "".join(f"| {_fmt(cell[m], runs)} " for m in METRICS)
                + "|"
            )
        cost = group["cost"]
        lines += [
            "",
            f"Cost per call: wall {_fmt_cost(cost['wall_seconds_per_call'])} s, "
            f"process CPU {_fmt_cost(cost['cpu_seconds_per_call'])} s.",
            "",
        ]
    return "\n".join(lines)


def _title(group: dict[str, Any]) -> str:
    linker = str(group["linker"])
    if group["base_model"]:
        linker += f" ({group['base_model']})"
    if group["transfer"]:
        linker += " · transfer"
    return f"{linker} · {group['track']} · split {group['split']} · new {group['new_memory']}"


def _fmt_cost(stat: dict[str, object]) -> str:
    return "n/a" if stat["mean"] is None else f"{stat['mean']:.6f}"


def summary_dir_for(results_root: Path, sha: str) -> Path:
    today = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    base = results_root / f"{today}_linkpairs_summary_{sha}"
    candidate, counter = base, 1
    while candidate.exists():
        counter += 1
        candidate = base.with_name(f"{base.name}_{counter}")
    return candidate


def write(run_dirs: Sequence[Path], results_root: Path = RESULTS_DIR) -> Path:
    summary = summarize(run_dirs)
    summary["written_at"] = datetime.now(tz=UTC).isoformat()
    out = summary_dir_for(results_root, git_short_sha())
    out.mkdir(parents=True)
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (out / "report.md").write_text(report(summary), encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Summarize link-pair run folders.")
    parser.add_argument("runs", nargs="+", type=Path)
    args = parser.parse_args(argv)
    out = write(args.runs)
    print(f"wrote {out}")
    print((out / "report.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
