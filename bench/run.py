"""Bench runner (ADR-0012, ADR-0060, ADR-0062, ADR-0120..0122).

    uv run python -m bench.run --suite smoke
    uv run python -m bench.run --suite v0 --strategy append_only [--split <name>]
    uv run python -m bench.run --suite news_v1|finance_v1 --strategy <name> [--split <name>]
    uv run python -m bench.run --suite v0 --strategy ripple --split test --generator-seeds 3
    uv run python -m bench.run --suite v0 --strategy ripple --ablation no_graph|no_ask_user
    (splits: all | train | test | strict_test; v1 tracks add curated)

smoke replays tests/scenarios/*.yaml; v0 replays bench/data/jobs_v0 (RippleBench v0,
jobs track); news_v1 and finance_v1 replay bench/data/<track> (RippleBench v1,
ADR-0101; synthetic until real stories are curated, finance test only). All run every
scenario against one memory strategy (bench/strategies.py) with the scripted oracle
resolver, so they measure the engine and the write/ripple semantics at zero LLM calls;
LLM quality needs a real resolver and the key.

`--generator-seeds N` regenerates the track in memory with its first N generator seeds
(ADR-0121) and writes one folder per seed; the checked-in data is the first seed and is
never rewritten. `--ablation` runs a docs/04 ablation of the ripple strategy (ADR-0122).

Output: results/<YYYY-MM-DD>_<suite>_<strategy>[_<ablation>][_g<seed>]_<shortsha>/ with
config.json (strategy, ablation, linker, seeds, data hash, engine, resolver, models and
prompt versions), metrics.json (run counts, `memory_metrics` from bench/metrics.py,
`llm_calls` counted from the resolvers), report.md and snapshots/<scenario>.json (the
replay traces the metrics are computed from). Numbers quoted anywhere must come from
those files (I8).
"""

import argparse
import functools
import hashlib
import json
import platform
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from tests.scenarios.runner import load_scenario, scenario_paths

import ripple
from bench.generate import DATA_DIR, load_jobs_v0, load_manifest
from bench.metrics import suite_metrics
from bench.probe import PROBE_SCOPE
from bench.scenario import ScenarioOutcome, ScenarioRunner, ScenarioSpec, validate_scenario
from bench.seeds import GENERATORS, SeededTrack, generate_track, generator_seeds, select_split
from bench.strategies import ABLATIONS, STRATEGY_NAMES
from bench.tracks import TRACK_SPLITS, curated_digest, load_track, load_track_manifest

REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = REPO_ROOT / "results"
# RippleBench v1 tracks: suite name -> data folder (ADR-0101).
# Paths, not generator imports: a broken generator must not break the other suites.
TEST_ONLY_TRACKS = frozenset({"finance_v1"})
V1_TRACKS: dict[str, Path] = {
    "news_v1": REPO_ROOT / "bench" / "data" / "news_v1",
    "finance_v1": REPO_ROOT / "bench" / "data" / "finance_v1",
}
SUITES = ("smoke", "v0", *V1_TRACKS)
NOT_RUNNABLE = "not runnable: engine raised NotImplementedError"
RESOLVER = "scripted oracle (bench/scenario.py AliasResolver, trigger-aware)"
# Where the links in the store come from. No link finder runs in the bench: every link
# is written from the scenario file (created_by human), the gold graph (ADR-0122).
LINKER = "scenario"
# Exactly the packages a bench run imports (a test runs the bench in a fresh process and
# checks every loaded repository module lies under one of these). Not all of src/ripple:
# other workstreams edit the API or the worker in this checkout, and hashing code the
# bench never runs would orphan every run on each such edit.
DIGEST_ROOTS = (
    REPO_ROOT / "bench",
    REPO_ROOT / "src" / "ripple" / "__init__.py",
    REPO_ROOT / "src" / "ripple" / "core",
    REPO_ROOT / "src" / "ripple" / "domains",
    REPO_ROOT / "src" / "ripple" / "retrieval",
    REPO_ROOT / "tests" / "__init__.py",
    REPO_ROOT / "tests" / "fakes",
    REPO_ROOT / "tests" / "scenarios" / "__init__.py",
    REPO_ROOT / "tests" / "scenarios" / "runner.py",
)
NOT_RUN_BY_A_BENCH_RUN = frozenset(
    {REPO_ROOT / "bench" / "matrix.py", REPO_ROOT / "bench" / "summary.py"}
)
LLM_CALLS_NOTE = (
    "counted from the resolvers' llm_calls; the scripted oracle calls no model, so this is "
    "0 and resolver_calls is the number of calls an LLM resolver would have made"
)


@dataclass(frozen=True)
class RunConfig:
    suite: str
    strategy: str
    split: str
    ablation: str | None = None
    seed: int | None = None  # a generator seed (ADR-0121); None = the checked-in data
    seed_set: tuple[int, ...] = ()  # every seed of the group this run belongs to


def git_short_sha() -> str:
    """HEAD's short sha, with "-dirty" when the working tree differs from it, so a
    results folder never claims a commit it was not run from (I8). "uncommitted"
    while the repository has no commits at all."""
    try:
        head = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "uncommitted"
    if not head:
        return "uncommitted"
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=REPO_ROOT, capture_output=True, text=True
    )
    return f"{head}-dirty" if status.stdout.strip() else head


@functools.cache
def _seeded(suite: str, seed: int) -> SeededTrack:
    return generate_track(suite, seed)


def scenarios_for(config: RunConfig) -> list[tuple[str, ScenarioSpec]]:
    if config.suite == "smoke":
        return [(path.stem, load_scenario(path)) for path in scenario_paths()]
    if config.seed is not None:
        track = _seeded(config.suite, config.seed)
        return [(entry.name, spec) for entry, spec in select_split(track.scenarios, config.split)]
    if config.suite in V1_TRACKS:
        return [
            (entry.name, spec) for entry, spec in load_track(V1_TRACKS[config.suite], config.split)
        ]
    return [(entry.name, spec) for entry, spec in load_jobs_v0(config.split)]


def run_suite(
    config: RunConfig, scenarios: list[tuple[str, ScenarioSpec]] | None = None
) -> list[ScenarioOutcome]:
    outcomes: list[ScenarioOutcome] = []
    for name, spec in scenarios_for(config) if scenarios is None else scenarios:
        problems = validate_scenario(spec)
        if problems:
            outcome = ScenarioOutcome(name, strategy=config.strategy)
            outcome.errors.append(f"not runnable: invalid scenario: {'; '.join(problems)}")
            outcomes.append(outcome)
            continue
        try:
            runner = ScenarioRunner(spec, strategy=config.strategy, ablation=config.ablation)
            outcomes.append(runner.run())
        except NotImplementedError as exc:
            outcome = ScenarioOutcome(name, strategy=config.strategy)
            outcome.errors.append(f"{NOT_RUNNABLE}: {exc}")
            outcomes.append(outcome)
    return outcomes


def run_dir_for(config: RunConfig, sha: str) -> Path:
    """A fresh folder per run: an existing same-day folder is never overwritten."""
    today = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    # The smoke suite keeps its historical name when it runs the real system.
    tag = (
        config.suite
        if config.suite == "smoke" and config.strategy == "ripple" and config.ablation is None
        else f"{config.suite}_{config.strategy}"
    )
    if config.ablation is not None:
        tag += f"_{config.ablation}"
    if config.seed is not None:
        tag += f"_g{config.seed}"
    base = RESULTS_DIR / f"{today}_{tag}_{sha}"
    candidate, counter = base, 1
    while candidate.exists():
        counter += 1
        candidate = base.with_name(f"{base.name}_{counter}")
    return candidate


def write_results(config: RunConfig, outcomes: list[ScenarioOutcome], started: float) -> Path:
    sha = git_short_sha()
    run_dir = run_dir_for(config, sha)
    run_dir.mkdir(parents=True, exist_ok=False)
    runnable = [o for o in outcomes if o.runnable]
    passed = sum(1 for o in runnable if o.passed)
    checks = sum(o.checks for o in outcomes)
    failed_checks = sum(o.checks_failed for o in outcomes)
    errors = sum(len(o.errors) for o in runnable)
    memory = suite_metrics([o.metrics for o in outcomes if o.metrics is not None])
    metrics = {
        "suite": config.suite,
        "strategy": config.strategy,
        "ablation": config.ablation,
        "split": config.split if config.suite != "smoke" else None,
        "scenarios": len(outcomes),
        "scenarios_runnable": len(runnable),
        "scenarios_not_runnable": len(outcomes) - len(runnable),
        "scenarios_passed": passed,
        "checks": checks,
        "checks_failed": failed_checks,
        "errors": errors,
        "resolver_calls": sum(o.resolver_calls for o in outcomes),
        "llm_calls": sum(o.llm_calls for o in outcomes),
        "llm_calls_note": LLM_CALLS_NOTE,
        **memory,
        "wall_seconds": round(time.perf_counter() - started, 3),
        "per_scenario": [_scenario_row(o) for o in outcomes],
    }
    config_json = {
        "suite": config.suite,
        "strategy": config.strategy,
        "ablation": config.ablation,
        "linker": LINKER,
        "linker_details": "links written from the scenario file (gold graph); no link finder ran",
        "split": config.split if config.suite != "smoke" else None,
        "data": _data_description(config),
        "ripple_version": ripple.__version__,
        "git_sha": sha,
        # Before the first commit every run says "uncommitted"; this hash of the code
        # that ran tells two such runs apart (I8).
        "source_sha256": source_digest(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "resolver": RESOLVER
        + (", asks replaced by keeps (no_ask_user)" if config.ablation == "no_ask_user" else ""),
        "engine": _engine(config),
        "action_layer": "bench/replay.py StubActionLayer (deterministic placeholder ranking)",
        "retrieval_probe": (
            f"bench/probe.py: HybridRetriever, lexical BM25 in memory, {PROBE_SCOPE}, graph "
            "expansion on, flagged included; one query per gold alias (its first content)"
        ),
        # Empty, not null: no model and no prompt was used, and llm_calls confirms it.
        "models": {},
        "prompt_versions": {},
        "seeds": _seeds(config),
        "run_at": datetime.now(tz=UTC).isoformat(),
    }
    (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    (run_dir / "config.json").write_text(json.dumps(config_json, indent=2), encoding="utf-8")
    snapshots = run_dir / "snapshots"
    snapshots.mkdir(exist_ok=True)
    for o in outcomes:
        if o.trace is not None:
            (snapshots / f"{o.name}.json").write_text(
                json.dumps(o.trace.to_dict(), indent=2), encoding="utf-8"
            )
    (run_dir / "report.md").write_text(
        _report(config, config_json, metrics, outcomes), encoding="utf-8"
    )
    return run_dir


def _scenario_row(o: ScenarioOutcome) -> dict[str, object]:
    row: dict[str, object] = {
        "name": o.name,
        "strategy": o.strategy,
        "runnable": o.runnable,
        "passed": o.passed,
        "checks": o.checks,
        "checks_failed": o.checks_failed,
        "failures": o.failures,
        "errors": o.errors,
        "events_run": o.events_run,
        "resolver_calls": o.resolver_calls,
        "llm_calls": o.llm_calls,
    }
    if o.metrics is not None:
        m = o.metrics
        row["memory"] = {
            "should_change": m.should_change,
            "should_stay": m.should_stay,
            "should_change_dependents": m.should_change_dependents,
            "correct_dependents": m.correct_dependents,
            "correct_updates": m.correct_updates,
            "stale_kept": m.stale_kept,
            "wrong_updates": m.wrong_updates,
            "wrongful_changes": m.wrongful_changes,
            "questions_asked": m.questions_asked,
            "questions_needed": m.questions_needed,
            "change_events": m.change_events,
            "recommendations_shown": m.recommendations_shown,
            "stale_recommendations": m.stale_recommendations,
            "retrieved": m.retrieved,
            "stale_retrieved": m.stale_retrieved,
            "ttc_never_converged": sum(1 for r in m.ttc.records if r.ttc_events is None),
            "ttc_records": len(m.ttc.records),
        }
    return row


def _engine(config: RunConfig) -> str:
    if config.ablation == "no_graph":
        return (
            "bench/strategies.py NoGraphRippleStrategy: check_everything's one-shot scope "
            "under the ripple name (no graph to scope by; ADR-0122)"
        )
    if config.strategy == "ripple":
        return "ripple.core.engine.WaveEngine"
    if config.strategy == "check_everything":
        return (
            "bench/strategies.py check_everything (one-shot wave over every VALID "
            "memory; graph read only to order it parents first, ADR-0104)"
        )
    return f"bench/strategies.py {config.strategy} (no graph engine needed)"


def _data_description(config: RunConfig) -> dict[str, object]:
    if config.suite == "smoke":
        return {"source": "tests/scenarios/*.yaml", "count": len(scenario_paths())}
    if config.seed is not None:
        return _seeded_description(config)
    if config.suite in V1_TRACKS:
        data_dir = V1_TRACKS[config.suite]
        manifest = load_track_manifest(data_dir)
        return {
            "source": data_dir.relative_to(REPO_ROOT).as_posix(),
            "track": manifest["track"],
            "domain": manifest["domain"],
            "content": manifest["content"],
            "data_sha256": manifest["data_sha256"],
            "extra_files": manifest["extra_files"],
            "curated": curated_digest(data_dir),
            "generator": manifest["generator"],
            "split": config.split,
        }
    manifest = load_manifest()
    return {
        "source": DATA_DIR.relative_to(REPO_ROOT).as_posix(),
        "track": manifest["track"],
        "content": "synthetic",  # generated from templates (ADR-0061)
        "data_sha256": manifest["data_sha256"],
        "generator": manifest["generator"],
        "split": config.split,
    }


def _seeded_description(config: RunConfig) -> dict[str, object]:
    """Identical for every run of one seed group (ADR-0121): it names all the seeds and
    the hash of each seed's data, and `seeds.generator_seed` says which one this run
    used, so runs averaged over the group agree on every field but their seed."""
    seeds = config.seed_set or (config.seed,)
    tracks = [_seeded(config.suite, seed) for seed in seeds if seed is not None]
    manifest = tracks[0].manifest
    module, folder = GENERATORS[config.suite]
    return {
        "source": (
            f"generated in memory by {module} with seeds.generator_seed; the first seed "
            f"reproduces bench/data/{folder} (checked against its manifest)"
        ),
        "track": manifest["track"],
        "domain": manifest.get("domain", "jobs"),
        "content": "synthetic",
        "generator": manifest["generator"],
        "generator_seeds": list(seeds),
        "data_sha256_by_seed": {str(t.seed): t.data_sha256 for t in tracks},
        "curated": "not included: curated stories are not generated per seed",
        "split": config.split,
    }


def _seeds(config: RunConfig) -> dict[str, object] | None:
    if config.suite == "smoke":
        return None
    if config.seed is not None:
        return {
            "kind": "generator",
            "generator_seed": config.seed,
            "run_seed": None,
            "data_sha256": _seeded(config.suite, config.seed).data_sha256,
        }
    manifest = (
        load_track_manifest(V1_TRACKS[config.suite])
        if config.suite in V1_TRACKS
        else load_manifest()
    )
    return {"generator_seed": manifest["seed"], "run_seed": None}


def source_digest() -> str:
    """sha256 over every source file a bench run executes, sorted by path: bench/, the
    ripple packages it imports (core, domains, retrieval) and the test support it imports
    (the in-memory store and fake clock in tests/fakes/, the scenario loader in
    tests/scenarios/runner.py); DIGEST_ROOTS lists them. The grid driver and
    the summary (bench/matrix.py, bench/summary.py) never run inside a bench run and are
    left out, so fixing a report format does not orphan every run already made."""
    digest = hashlib.sha256()
    for root in DIGEST_ROOTS:
        paths = [root] if root.is_file() else sorted(root.rglob("*.py"))
        for path in paths:
            if path in NOT_RUN_BY_A_BENCH_RUN:
                continue
            digest.update(path.relative_to(REPO_ROOT).as_posix().encode("utf-8"))
            digest.update(path.read_bytes())
    return digest.hexdigest()


def _content_line(config_json: dict[str, object]) -> str:
    data = config_json["data"]
    if not isinstance(data, dict):
        return "unknown"
    content = data.get("content")
    if content is None:
        return f"{data.get('source')} (hand-written smoke scenarios)"
    seeds = config_json.get("seeds")
    digest = data.get("data_sha256")
    if digest is None and isinstance(seeds, dict):
        digest = seeds.get("data_sha256")
    return (
        f"{content} — {data.get('source')}, data sha256 {digest}; "
        "invented names, places and companies, no real story or company described"
    )


def _shown(value: object, kind: str = "float") -> str:
    if value is None:
        return "n/a"
    if not isinstance(value, int | float):
        return str(value)
    return f"{value:.1%}" if kind == "pct" else f"{value:.2f}"


def _memory_lines(metrics: dict[str, object]) -> list[str]:
    memory = metrics.get("memory_metrics")
    if not isinstance(memory, dict):
        return ["Memory metrics: none (no scenario ran)."]
    m: dict[str, object] = memory  # pyright: ignore[reportUnknownVariableType]
    skipped = metrics.get("scenarios_not_runnable")
    return [
        f"Memory metrics over {metrics['scenarios_runnable']} runnable scenarios "
        f"({skipped} not runnable, left out) (bench/metrics.py; pooled, ADR-0120): "
        f"update accuracy {_shown(m['update_accuracy'], 'pct')} · stale kept per scenario "
        f"{_shown(m['stale_kept'])} · wrongful changes per scenario "
        f"{_shown(m['wrongful_changes'])} · questions asked per scenario "
        f"{_shown(m['questions_asked'])} (needed {_shown(m['questions_needed'])}) · stale "
        f"retrieval {_shown(m['stale_retrieval_rate'], 'pct')} · stale recommendations "
        f"{_shown(m['stale_recommendation_rate'], 'pct')} · never consistent "
        f"{_shown(m['ttc_share_never_converged'], 'pct')} · resolver calls per ripple "
        f"{_shown(m['cost_per_ripple'])} · tokens and USD per ripple: n/a (no LLM).",
    ]


def _report(
    config: RunConfig,
    config_json: dict[str, object],
    metrics: dict[str, object],
    outcomes: list[ScenarioOutcome],
) -> str:
    title = f"# {config.suite} suite, strategy {config.strategy}"
    if config.ablation is not None:
        title += f", ablation {config.ablation}"
    if config.seed is not None:
        title += f", generator seed {config.seed}"
    lines = [
        f"{title} — {config_json['run_at']}",
        "",
        f"Scenarios passed: {metrics['scenarios_passed']}/{metrics['scenarios_runnable']} "
        f"runnable ({metrics['scenarios_not_runnable']} not runnable) · checks failed: "
        f"{metrics['checks_failed']}/{metrics['checks']} · errors: {metrics['errors']} · "
        f"resolver calls: "
        f"{metrics['resolver_calls']} · LLM calls: {metrics['llm_calls']} (scripted oracle "
        "resolver).",
        "",
        *_memory_lines(metrics),
        "",
        f"Data: {_content_line(config_json)}",
        "",
        "| scenario | runnable | passed | checks failed | resolver calls | problems |",
        "|---|---|---|---|---|---|",
    ]
    for o in outcomes:
        lines.append(
            f"| {o.name} | {'yes' if o.runnable else 'no'} | {'yes' if o.passed else 'no'} | "
            f"{o.checks_failed}/{o.checks} | {o.resolver_calls} | "
            f"{'; '.join(o.problems) or '-'} |"
        )
    return "\n".join(lines) + "\n"


def display_path(run_dir: Path) -> Path:
    return run_dir.relative_to(REPO_ROOT) if run_dir.is_relative_to(REPO_ROOT) else run_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a RippleBench suite")
    parser.add_argument("--suite", choices=SUITES, default="smoke")
    parser.add_argument("--strategy", choices=STRATEGY_NAMES, default="ripple")
    parser.add_argument(
        "--split", choices=TRACK_SPLITS, default="all", help="v0 and v1 tracks; curated: v1 only"
    )
    parser.add_argument("--ablation", choices=ABLATIONS, default=None, help="ripple only")
    parser.add_argument(
        "--generator-seeds",
        type=int,
        default=0,
        metavar="N",
        help="regenerate the track with its first N generator seeds, one folder each",
    )
    args = parser.parse_args(argv)
    if args.split == "curated" and args.suite not in V1_TRACKS:
        parser.error("--split curated applies to the v1 tracks only")
    if args.suite in TEST_ONLY_TRACKS and args.split == "train":
        parser.error("finance_v1 is test only (H4): it has no train split")
    if args.ablation is not None and args.strategy != "ripple":
        parser.error("--ablation applies to --strategy ripple only")
    if args.generator_seeds < 0:
        parser.error("--generator-seeds must be 0 (checked-in data) or more")
    if args.generator_seeds and (args.suite == "smoke" or args.split == "curated"):
        parser.error("--generator-seeds applies to the generated tracks (v0, news_v1, finance_v1)")
    if args.generator_seeds:
        seed_set = generator_seeds(args.suite, args.generator_seeds)
        configs = [
            RunConfig(args.suite, args.strategy, args.split, args.ablation, seed, seed_set)
            for seed in seed_set
        ]
    else:
        configs = [RunConfig(args.suite, args.strategy, args.split, args.ablation)]
    all_passed = True
    for config in configs:
        scenarios = scenarios_for(config)
        if not scenarios:
            # An empty run would write a results folder that reads as "all passed" (I8).
            parser.error(f"--suite {args.suite} --split {args.split} selects no scenarios")
        started = time.perf_counter()
        outcomes = run_suite(config, scenarios)
        run_dir = write_results(config, outcomes, started)
        runnable = [o for o in outcomes if o.runnable]
        passed = sum(1 for o in runnable if o.passed)
        label = f"{config.suite}/{config.strategy}" + (
            f"/{config.ablation}" if config.ablation else ""
        )
        seed = f" seed {config.seed}" if config.seed is not None else ""
        print(
            f"{label}{seed}: {passed}/{len(runnable)} runnable scenarios passed, "
            f"{len(outcomes) - len(runnable)} not runnable -> {display_path(run_dir)}"
        )
        for o in outcomes:
            if not o.passed:
                print(f"  FAIL {o.name}: {'; '.join(o.problems)}")
        all_passed = all_passed and passed == len(outcomes)
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
