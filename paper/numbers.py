"""Render the registry's macros from results/ run folders (ADR-0110, I8).

    uv run python -m paper.numbers            # writes docs/paper/generated/
    uv run python -m paper.numbers --check    # exit 1 if the generated files are stale
    uv run python -m paper.numbers --strict   # exit 1 if any macro is refused
    uv run python -m paper.numbers --draft    # development view, docs/paper/generated/draft/

Every macro is either rendered from run folders that pass the provenance checks, or
refused with the reason; a refused macro prints "TBD (pending run)" and never a number.
Nothing here computes a metric: values are read from metrics.json or config.json and at
most averaged over seeds or combined by a declared ratio or difference.
"""

import argparse
import csv
import io
import json
import math
import re
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from paper.registry import (
    FIGURES,
    MIN_HEADLINE_SEEDS,
    REGISTRY,
    Aggregate,
    AnySpec,
    DerivedSpec,
    FigureSpec,
    Format,
    MacroSpec,
    Prefix,
    Source,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = REPO_ROOT / "results"
PAPER_DIR = REPO_ROOT / "docs" / "paper"
GENERATED_DIR = PAPER_DIR / "generated"
# The drafts rendered with their macros filled in (ADR-0136); the sources stay macro-only.
DOCUMENTS = ("paper.md", "thesis.md")
MACRO_REFERENCE = re.compile(r"\{\{num:([^}\s]*)\}\}")
MACRO_OPENING = "{{num:"  # any opening MACRO_REFERENCE does not match is malformed
INLINE_CODE = re.compile(r"(`[^`\n]*`)")
PENDING = "TBD (pending run)"
COMMITTED_SHA = re.compile(r"^[0-9a-f]{7,40}$")
# Fields that may differ between runs of one configuration (seeds, timing, host).
VOLATILE_CONFIG = frozenset({"seeds", "run_at", "platform", "python"})
OLDEST = datetime.min.replace(tzinfo=UTC)
_MISSING = object()


@dataclass(frozen=True)
class RunRecord:
    """One results/ run folder with both JSON files parsed."""

    folder: str  # posix path relative to the results directory
    config: Mapping[str, Any]
    metrics: Mapping[str, Any]

    @property
    def run_at(self) -> datetime | None:
        """When the run started; None when missing or not ISO 8601 (a provenance problem)."""
        raw = self.config.get("run_at")
        if not isinstance(raw, str):
            return None
        try:
            parsed = datetime.fromisoformat(raw)
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)

    @property
    def git_sha(self) -> str:
        return str(self.config.get("git_sha") or "")

    @property
    def seed_kind(self) -> str:
        """Which seed `run_seeds` holds; seed sets of different kinds never compare."""
        seeds = self.config.get("seeds")
        generator = isinstance(seeds, Mapping) and seeds.get("kind") == "generator"  # pyright: ignore[reportUnknownMemberType]
        return "generator_seed" if generator else "run_seed"

    @property
    def run_seeds(self) -> tuple[object, ...]:
        """Run seeds; for a generator-seeded bench run (ADR-0121) the generator seed is
        what varies between the runs averaged, so it counts as the run's seed."""
        seeds = self.config.get("seeds")
        if not isinstance(seeds, Mapping):
            return ()
        if self.seed_kind == "generator_seed":
            generator = seeds.get("generator_seed")  # pyright: ignore[reportUnknownMemberType]
            return () if generator is None else (generator,)
        listed = seeds.get("run_seeds")  # pyright: ignore[reportUnknownMemberType]
        if isinstance(listed, list):
            return tuple(s for s in listed if s is not None)  # pyright: ignore[reportUnknownVariableType]
        single = seeds.get("run_seed")  # pyright: ignore[reportUnknownMemberType]
        return () if single is None else (single,)

    def source(self) -> dict[str, object]:
        return {
            "folder": self.folder,
            "git_sha": self.git_sha,
            "run_at": self.config.get("run_at"),
            "run_seeds": list(self.run_seeds),
            "models": self.config.get("models"),
            "prompt_versions": self.config.get("prompt_versions"),
        }


@dataclass(frozen=True)
class Superseded:
    """A qualifying run that was not chosen (older, or another configuration)."""

    folder: str
    value: float | None


@dataclass(frozen=True)
class Rendered:
    name: str
    value: float
    markdown: str
    tex: str
    sources: tuple[RunRecord, ...]
    values: tuple[float, ...] = ()  # one per source run; the spread behind a mean
    # Shown so a reader sees what a newer run replaced; never used to pick a value.
    superseded: tuple[Superseded, ...] = ()
    # The seeds the value was averaged over, normalised (spec_seeds); a derived macro
    # holds the union of its inputs'.
    seeds: frozenset[str] = frozenset()


@dataclass(frozen=True)
class Refused:
    name: str
    reason: str


Outcome = Rendered | Refused


def lookup(document: Mapping[str, Any], dotted: str) -> object:
    node: object = document
    for key in dotted.split("."):
        if not isinstance(node, Mapping) or key not in node:
            return _MISSING
        node = node[key]  # pyright: ignore[reportUnknownVariableType]
    return node  # pyright: ignore[reportUnknownVariableType]


def _why_missing(document: Mapping[str, Any], dotted: str) -> str:
    """Name the step where the path breaks, quoting a value that stands in the way (the
    bench writes `memory_metrics` as a TBD string until the metric bodies exist)."""
    node: object = document
    walked: list[str] = []
    for key in dotted.split("."):
        if not isinstance(node, Mapping):
            return f"{'.'.join(walked)} is {node!r}"[:160]
        if key not in node:
            return f"missing key {key!r}"
        walked.append(key)
        node = node[key]  # pyright: ignore[reportUnknownVariableType]
    return "missing"


def discover_runs(results_dir: Path, pattern: str) -> tuple[list[RunRecord], list[str]]:
    """Run folders matching `pattern` with a parseable config.json and metrics.json, and
    the matching folders that hold one of the two but cannot be read (a half-written or
    corrupt run: the caller refuses rather than fall back to an older run). A folder
    with neither file is not a run."""
    runs: list[RunRecord] = []
    broken: list[str] = []
    for folder in sorted(results_dir.glob(pattern)):
        if not folder.is_dir():
            continue
        name = folder.relative_to(results_dir).as_posix()
        files = (folder / "config.json", folder / "metrics.json")
        if not any(f.exists() for f in files):
            continue
        try:
            config, metrics = (json.loads(f.read_text(encoding="utf-8")) for f in files)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            broken.append(name)
            continue
        if isinstance(config, dict) and isinstance(metrics, dict):
            runs.append(RunRecord(name, config, metrics))  # pyright: ignore[reportUnknownArgumentType]
        else:
            broken.append(name)
    return runs, broken


def matches_config(run: RunRecord, wanted: Mapping[str, object]) -> bool:
    for path, value in wanted.items():
        found = lookup(run.config, path)
        if value is None:
            if found is not _MISSING and found is not None:
                return False
        elif isinstance(value, Prefix):
            if not isinstance(found, str) or not found.startswith(value.text):
                return False
        elif found != value:
            return False
    return True


def _normalise(node: object) -> object:
    """Backslashes and slashes are one path separator; the same run on Windows and Linux
    must compare equal."""
    if isinstance(node, str):
        return node.replace("\\", "/")
    if isinstance(node, Mapping):
        return {str(k): _normalise(v) for k, v in node.items()}  # pyright: ignore[reportUnknownVariableType]
    if isinstance(node, list):
        return [_normalise(v) for v in node]  # pyright: ignore[reportUnknownVariableType]
    return node


def _without(node: object, path: Sequence[str]) -> object:
    """`node` with the dotted `path` removed; a path that does not exist removes nothing."""
    if not path or not isinstance(node, Mapping):
        return node
    head, rest = path[0], path[1:]
    if rest:
        return {k: (_without(v, rest) if k == head else v) for k, v in node.items()}  # pyright: ignore[reportUnknownVariableType]
    return {k: v for k, v in node.items() if k != head}  # pyright: ignore[reportUnknownVariableType]


def comparable(run: RunRecord, ignore: Iterable[str] = ()) -> str:
    """The run's whole configuration minus seeds, timestamps, host fields and `ignore`
    (top-level fields or dotted paths to one leaf, ADR-0135): runs averaged or compared
    must agree on every other field."""
    kept: object = {k: v for k, v in run.config.items() if k not in VOLATILE_CONFIG}
    for path in ignore:
        kept = _without(kept, path.split("."))
    return json.dumps(_normalise(kept), sort_keys=True, default=str)


def model_ids(models: object) -> list[str]:
    """Every string leaf of the config's `models` entry (a mapping, list or string)."""
    if isinstance(models, str):
        return [models]
    if isinstance(models, Mapping):
        return [m for v in models.values() for m in model_ids(v)]  # pyright: ignore[reportUnknownVariableType, reportUnknownArgumentType]
    if isinstance(models, list):
        return [m for v in models for m in model_ids(v)]  # pyright: ignore[reportUnknownVariableType]
    return []


def unpinned(identifier: str) -> bool:
    text = identifier.strip().lower()
    return not text or "latest" in text or "*" in text


def _all_filled(prompts: object) -> bool:
    """A non-empty mapping whose values are all non-empty strings."""
    if not isinstance(prompts, Mapping) or not prompts:
        return False
    return all(isinstance(v, str) and v.strip() for v in prompts.values())  # pyright: ignore[reportUnknownVariableType]


def _not_runnable(run: RunRecord) -> int | None:
    """Scenarios that did not run; None when the run does not say (fail closed for
    bench runs, which always report it)."""
    per_scenario = run.metrics.get("per_scenario")
    if isinstance(per_scenario, list):
        return sum(
            1
            for item in per_scenario  # pyright: ignore[reportUnknownVariableType]
            if isinstance(item, Mapping) and item.get("runnable") is False  # pyright: ignore[reportUnknownMemberType]
        )
    count = run.metrics.get("scenarios_not_runnable")
    return count if isinstance(count, int) else None


def spec_seeds(spec: MacroSpec, run: RunRecord) -> tuple[object, ...]:
    """The seeds that vary between the runs `spec` averages: the config path the spec
    names (a trained linker's training seed, ADR-0135), else the run's own seeds."""
    if spec.seed_path is None:
        return run.run_seeds
    found = lookup(run.config, spec.seed_path)
    return () if found is _MISSING or found is None else (found,)


def provenance_problems(spec: MacroSpec, run: RunRecord, *, draft: bool = False) -> list[str]:
    """Why `run` may not supply `spec`; empty when it may. The seed count is checked over
    the selected group, not here."""
    problems: list[str] = []
    if run.run_at is None:
        problems.append("config.json run_at is missing or not ISO 8601")
    not_runnable = _not_runnable(run)
    if not_runnable is None and "strategy" in run.config:
        problems.append("cannot tell whether the bench run is complete")
    elif not_runnable:
        problems.append(f"incomplete run: {not_runnable} scenarios not runnable")
    llm_calls = run.metrics.get("llm_calls")
    used_llm = isinstance(llm_calls, int | float) and llm_calls > 0
    models = run.config.get("models")
    ids = model_ids(models)
    if used_llm or models is not None or spec.headline:
        if models is None:
            problems.append("config.json records no models (null)")
        elif used_llm and not ids:
            problems.append("the run called an LLM but config.json names no model")
        elif not ids and "llm_calls" not in run.metrics:
            problems.append("models is empty but metrics.json has no llm_calls to confirm it")
        bad = [m for m in ids if unpinned(m)]
        if bad:
            problems.append(f"unpinned model versions: {', '.join(bad)}")
    prompts = run.config.get("prompt_versions")
    # A model with no prompt (a trained classifier) needs none, but only when the run
    # itself reports that it made no LLM call (ADR-0135).
    reported_none = isinstance(llm_calls, int) and not isinstance(llm_calls, bool) and not llm_calls
    prompted = used_llm or (bool(ids) and not reported_none)
    if (used_llm or ids or spec.headline) and prompts is None:
        problems.append("config.json records no prompt versions (null)")
    elif prompted and not _all_filled(prompts):
        problems.append("a model was used but prompt_versions is empty or has blank entries")
    # --draft relaxes the clean-commit gate for every macro, headline included; its
    # output is marked DRAFT and never used camera-ready (ADR-0135).
    if not draft and not COMMITTED_SHA.match(run.git_sha):
        problems.append(f"git_sha {run.git_sha!r} is not a clean commit")
    if spec.aggregate is Aggregate.MEAN and not spec_seeds(spec, run):
        where = f" at config.json {spec.seed_path}" if spec.seed_path else ""
        problems.append(f"no run seed recorded{where}")
    return problems


def _when(run: RunRecord) -> tuple[datetime, str]:
    return (run.run_at or OLDEST, run.folder)


def select_runs(spec: MacroSpec, qualifying: Sequence[RunRecord]) -> list[RunRecord] | str:
    """SINGLE: the newest run. MEAN: the newest group of runs sharing one configuration,
    one run per seed (the newest when a seed was run twice). Never chosen by value. A
    string is a refusal reason."""
    if spec.aggregate is Aggregate.SINGLE:
        return [max(qualifying, key=_when)]
    groups: dict[str, list[RunRecord]] = {}
    for run in qualifying:
        groups.setdefault(comparable(run, spec.seed_varies), []).append(run)
    group = max(groups.values(), key=lambda g: max(_when(r) for r in g))
    if len(group) > 1 and any(len(spec_seeds(spec, r)) > 1 for r in group):
        folders = ", ".join(sorted(r.folder for r in group))
        return f"one-folder-per-seed and multi-seed folders mixed: {folders}"
    per_seed: dict[str, RunRecord] = {}
    for run in sorted(group, key=_when):
        per_seed[json.dumps([_seed(s) for s in spec_seeds(spec, run)])] = run
    return list(per_seed.values())


def _seed(seed: object) -> str:
    number = _numeric(seed) if not isinstance(seed, str) else None
    if number is None and isinstance(seed, str):
        try:
            number = float(seed)
        except ValueError:
            return seed
    return repr(number) if number is not None else repr(seed)


def seed_keys(runs: Sequence[RunRecord], spec: MacroSpec) -> frozenset[str]:
    """Normalised seeds tagged with their kind, so a set of training seeds never equals a
    set of run or generator seeds that happen to share values (ADR-0135)."""
    return frozenset(
        f"{spec.seed_path or run.seed_kind}={_seed(s)}"
        for run in runs
        for s in spec_seeds(spec, run)
    )


def seed_count(runs: Sequence[RunRecord], spec: MacroSpec) -> int:
    return len(seed_keys(runs, spec))


def format_value(value: float, fmt: Format) -> tuple[str, str] | str:
    """(markdown, tex) or a refusal reason."""
    if fmt.kind == "int":
        if not float(value).is_integer():
            return f"value {value!r} is not an integer"
        text = str(int(value))
        return text, text
    if fmt.kind in ("pct", "points"):
        text = f"{round(value * 100, fmt.digits) + 0.0:.{fmt.digits}f}"
        return (f"{text}%", f"{text}\\%") if fmt.kind == "pct" else (text, text)
    if fmt.kind == "usd":
        text = f"{value:.{fmt.digits}f}"
        return f"${text}", f"\\${text}"
    text = f"{value:.{fmt.digits}f}"
    return text, text


def _numeric(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _value(spec: MacroSpec, run: RunRecord) -> float | str:
    """The number at the spec's path in `run`, or why there is none."""
    document = run.metrics if spec.source is Source.METRICS else run.config
    raw = lookup(document, spec.json_path)
    number = _numeric(raw)
    if number is not None:
        return number
    shown = _why_missing(document, spec.json_path) if raw is _MISSING else repr(raw)[:80]
    reason = f"{run.folder}/{spec.source.value} {spec.json_path}: {shown}"
    return reason + (f" ({spec.provisional})" if spec.provisional else "")


def resolve_macro(spec: MacroSpec, results_dir: Path, *, draft: bool = False) -> Outcome:
    runs, broken = discover_runs(results_dir, spec.run_pattern)
    if broken:
        return Refused(spec.name, f"unreadable run folder(s) match: {', '.join(broken)}")
    candidates = [r for r in runs if matches_config(r, spec.config_match)]
    if not candidates:
        wanted = {k: getattr(v, "text", v) for k, v in spec.config_match.items()}
        reason = f"no run folder matches results/{spec.run_pattern} with config {wanted}"
        return Refused(spec.name, reason + (f" ({spec.provisional})" if spec.provisional else ""))
    problems = {r.folder: provenance_problems(spec, r, draft=draft) for r in candidates}
    qualifying = [r for r in candidates if not problems[r.folder]]
    if not qualifying:
        newest = max(candidates, key=_when)
        return Refused(
            spec.name, f"newest candidate {newest.folder}: " + "; ".join(problems[newest.folder])
        )
    selected = select_runs(spec, qualifying)
    if isinstance(selected, str):
        return Refused(spec.name, selected)
    # Fail closed: a newer run that fails the checks (an aborted re-run, a dirty tree)
    # means the older number may no longer describe the code.
    latest = max(_when(r) for r in selected)
    newer_failing = [
        r for r in candidates if problems[r.folder] and (r.run_at is None or _when(r) > latest)
    ]
    if newer_failing:
        run = max(newer_failing, key=_when)
        return Refused(
            spec.name,
            f"newer run {run.folder} fails the checks ({'; '.join(problems[run.folder])}); "
            "the older qualifying run is not used",
        )
    if spec.headline and seed_count(selected, spec) < MIN_HEADLINE_SEEDS:
        folders = ", ".join(r.folder for r in selected)
        return Refused(
            spec.name,
            f"headline number needs {MIN_HEADLINE_SEEDS} run seeds (docs/04); "
            f"{seed_count(selected, spec)} in {folders}",
        )
    values: list[float] = []
    for run in selected:
        found = _value(spec, run)
        if isinstance(found, str):
            return Refused(spec.name, found)
        values.append(found)
    chosen = {r.folder for r in selected}
    superseded: list[Superseded] = []
    for run in sorted(qualifying, key=_when):
        if run.folder in chosen:
            continue
        found = _value(spec, run)
        older = Superseded(run.folder, None if isinstance(found, str) else found)
        superseded.append(older)
        # The same configuration and seed must give the same number; if not, the run is
        # not reproducible and neither value may be printed.
        twin = next(
            (
                s
                for s, v in zip(selected, values, strict=True)
                if older.value is not None
                and older.value != v
                and seed_keys([s], spec) == seed_keys([run], spec)
                and comparable(s, spec.seed_varies) == comparable(run, spec.seed_varies)
            ),
            None,
        )
        if twin is not None:
            return Refused(
                spec.name,
                f"runs of one configuration disagree: {run.folder}={older.value}, "
                f"{twin.folder}={values[selected.index(twin)]}",
            )
    value = sum(values) / len(values)
    if Format.parse(spec.fmt).kind == "pct" and not all(0.0 <= v <= 1.0 for v in values):
        return Refused(spec.name, f"a share outside [0, 1] in {values} (pct expects a share)")
    texts = format_value(value, Format.parse(spec.fmt))
    if isinstance(texts, str):
        return Refused(spec.name, texts)
    return Rendered(
        spec.name,
        value,
        texts[0],
        texts[1],
        tuple(selected),
        tuple(values),
        tuple(superseded),
        seed_keys(selected, spec),
    )


def inconsistent_sources(outcomes: Iterable[Outcome], differ: Iterable[str]) -> str | None:
    """Why rendered outcomes may not be compared: their runs differ in a configuration
    field other than `differ` (the field the comparison is about)."""
    allowed = tuple(differ)
    runs = {r.folder: r for o in outcomes if isinstance(o, Rendered) for r in o.sources}
    keys = {comparable(r, allowed) for r in runs.values()}
    if len(keys) <= 1:
        return None
    return f"inputs come from runs that differ beyond {list(allowed)}: " + ", ".join(sorted(runs))


def resolve_derived(spec: DerivedSpec, inputs: Sequence[Outcome]) -> Outcome:
    refused = [o for o in inputs if isinstance(o, Refused)]
    if refused:
        return Refused(spec.name, "input refused: " + ", ".join(o.name for o in refused))
    mismatch = inconsistent_sources(inputs, spec.differ)
    if mismatch:
        return Refused(spec.name, mismatch)
    seed_sets = {o.seeds for o in inputs if isinstance(o, Rendered)}
    if spec.headline and len(seed_sets) > 1:
        return Refused(spec.name, "inputs were averaged over different run seeds")
    left, right = (o for o in inputs if isinstance(o, Rendered))
    if spec.op == "ratio":
        if right.value == 0:
            return Refused(spec.name, f"ratio undefined: {right.name} is 0")
        value = left.value / right.value
    else:
        value = left.value - right.value
    texts = format_value(value, Format.parse(spec.fmt))
    if isinstance(texts, str):
        return Refused(spec.name, texts)
    by_folder = {run.folder: run for run in left.sources + right.sources}
    return Rendered(
        spec.name,
        value,
        texts[0],
        texts[1],
        tuple(by_folder.values()),
        seeds=left.seeds | right.seeds,
    )


def resolve_all(
    results_dir: Path = RESULTS_DIR,
    registry: Mapping[str, AnySpec] = REGISTRY,
    *,
    draft: bool = False,
) -> dict[str, Outcome]:
    outcomes: dict[str, Outcome] = {}
    resolving: set[str] = set()

    def resolve(name: str) -> Outcome:
        if name in outcomes:
            return outcomes[name]
        if name in resolving:
            raise ValueError(f"derived macros form a cycle through {name}")
        resolving.add(name)
        spec = registry[name]
        if isinstance(spec, MacroSpec):
            outcomes[name] = resolve_macro(spec, results_dir, draft=draft)
        else:
            outcomes[name] = resolve_derived(spec, [resolve(i) for i in spec.inputs])
        return outcomes[name]

    for name in registry:
        resolve(name)
    return {name: outcomes[name] for name in sorted(outcomes)}


# ------------------------------------------------------------------ rendering


DRAFT_NOTE = (
    "DRAFT: uncommitted runs allowed (--draft, ADR-0135); "
    "not for a camera-ready paper, thesis or README"
)


def _markdown_value(outcome: Outcome) -> str:
    return outcome.markdown if isinstance(outcome, Rendered) else PENDING


def render_json(
    outcomes: Mapping[str, Outcome], registry: Mapping[str, AnySpec], *, draft: bool = False
) -> str:
    entries: list[dict[str, object]] = []
    for name, outcome in outcomes.items():
        spec = registry[name]
        entry: dict[str, object] = {
            "name": name,
            "status": "rendered" if isinstance(outcome, Rendered) else "refused",
            "description": spec.description,
            "format": spec.fmt,
            "headline": spec.headline,
            "supports": list(spec.supports),
        }
        if isinstance(outcome, Rendered):
            entry["value"] = outcome.value
            entry["markdown"] = outcome.markdown
            entry["tex"] = outcome.tex
            if outcome.values:
                entry["per_run_values"] = list(outcome.values)
                entry["min"] = min(outcome.values)
                entry["max"] = max(outcome.values)
            entry["sources"] = [run.source() for run in outcome.sources]
            entry["seeds"] = sorted(outcome.seeds)
            entry["superseded"] = [
                {"folder": s.folder, "value": s.value} for s in outcome.superseded
            ]
        else:
            entry["markdown"] = PENDING
            entry["reason"] = outcome.reason
        entries.append(entry)
    document: dict[str, object] = {"generated_by": "python -m paper.numbers (ADR-0110)"}
    if draft:
        document["draft"] = DRAFT_NOTE
    document["macros"] = entries
    return json.dumps(document, indent=2, default=str) + "\n"


def render_tex(outcomes: Mapping[str, Outcome], *, draft: bool = False) -> str:
    lines = [
        "% Generated by `uv run python -m paper.numbers` (ADR-0110). Do not edit.",
        "% Use \\rnum{<macro>}; an unknown macro prints ??<macro> in bold.",
        *([f"% {DRAFT_NOTE}"] if draft else []),
        # \detokenize: every macro name holds underscores, which bold text cannot take.
        "\\providecommand{\\rnum}[1]{\\ifcsname rnum@#1\\endcsname"
        "\\csname rnum@#1\\endcsname\\else\\textbf{??\\detokenize{#1}}\\fi}",
    ]
    for name, outcome in outcomes.items():
        if isinstance(outcome, Rendered):
            value = f"{outcome.tex}\\textsuperscript{{draft}}" if draft else outcome.tex
            note = ", ".join(r.folder for r in outcome.sources)
        else:
            value, note = f"\\textbf{{{PENDING}}}", outcome.reason
        lines.append(f"% {name}: {note}")
        lines.append(f"\\expandafter\\newcommand\\csname rnum@{name}\\endcsname{{{value}}}")
    return "\n".join(lines) + "\n"


def render_markdown(
    outcomes: Mapping[str, Outcome], registry: Mapping[str, AnySpec], *, draft: bool = False
) -> str:
    rendered = sum(1 for o in outcomes.values() if isinstance(o, Rendered))
    lines = [
        "# Rendered numbers",
        "Generated by `uv run python -m paper.numbers` (ADR-0110). Do not edit; every value",
        "comes from the results/ folders named beside it. Refused macros print",
        f'"{PENDING}" with the reason.',
        *(["", f"**{DRAFT_NOTE}.**"] if draft else []),
        "",
        f"Rendered: {rendered} of {len(outcomes)} macros.",
        "",
        "| macro | value | headline | supports | source or reason |",
        "|---|---|---|---|---|",
    ]
    for name, outcome in outcomes.items():
        spec = registry[name]
        if isinstance(outcome, Rendered):
            detail = ", ".join(f"results/{r.folder}" for r in outcome.sources)
            if len(outcome.values) > 1:
                detail += f" (per-run min {min(outcome.values)}, max {max(outcome.values)})"
            if outcome.superseded:
                older = "; ".join(f"{s.folder}={s.value}" for s in outcome.superseded)
                detail += f" (superseded: {older})"
        else:
            detail = outcome.reason.replace("|", "/")
        lines.append(
            f"| `{name}` | {_markdown_value(outcome)} | {'yes' if spec.headline else 'no'} | "
            f"{', '.join(spec.supports) or '-'} | {detail} |"
        )
    return "\n".join(lines) + "\n"


def _plain(outcome: Rendered, registry: Mapping[str, AnySpec]) -> str:
    """Machine value for a data file: an int prints as an int, the rest unrounded."""
    if Format.parse(registry[outcome.name].fmt).kind == "int":
        return str(int(outcome.value))
    return repr(outcome.value)


def figure_cells(
    figure: FigureSpec, outcomes: Mapping[str, Outcome]
) -> tuple[list[list[Outcome]], str | None]:
    """The figure's cells, all refused when its rendered cells come from runs that may
    not be drawn side by side (ADR-0110: same code, data and resolver)."""
    cells = [[outcomes[macro] for macro in macros] for _, macros in figure.rows]
    mismatch = inconsistent_sources((c for row in cells for c in row), figure.differ)
    if mismatch is None:
        return cells, None
    return [[Refused(c.name, mismatch) for c in row] for row in cells], mismatch


def render_figure_csv(
    figure: FigureSpec, outcomes: Mapping[str, Outcome], registry: Mapping[str, AnySpec]
) -> str:
    cells, _ = figure_cells(figure, outcomes)
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["label", *figure.columns, "sources"])
    for (label, _), row in zip(figure.rows, cells, strict=True):
        folders = sorted({r.folder for c in row if isinstance(c, Rendered) for r in c.sources})
        writer.writerow(
            [
                label,
                *(_plain(c, registry) if isinstance(c, Rendered) else PENDING for c in row),
                ";".join(folders),
            ]
        )
    return buffer.getvalue()


def render_figure_dat(
    figure: FigureSpec, outcomes: Mapping[str, Outcome], registry: Mapping[str, AnySpec]
) -> str:
    """A pgfplots table: whitespace separated, `nan` where the macro is refused."""
    cells, mismatch = figure_cells(figure, outcomes)
    lines = [
        f"% {figure.title}. Generated by python -m paper.numbers (ADR-0110).",
        "% nan = TBD (pending run). Use with \\pgfplotstableread.",
        *([f"% refused: {mismatch}"] if mismatch else []),
        " ".join(["label", *figure.columns]),
    ]
    for (label, _), row in zip(figure.rows, cells, strict=True):
        values = [_plain(c, registry) if isinstance(c, Rendered) else "nan" for c in row]
        lines.append(" ".join([label, *values]))
    return "\n".join(lines) + "\n"


def render_figure_svg(
    figure: FigureSpec, outcomes: Mapping[str, Outcome], registry: Mapping[str, AnySpec]
) -> str:
    """A hand-written horizontal bar chart of `bar_column`; refused bars say so."""
    column = figure.columns.index(figure.bar_column)
    rows, _ = figure_cells(figure, outcomes)
    cells = [row[column] for row in rows]
    fmt = Format.parse(registry[figure.rows[0][1][column]].fmt)
    values = [c.value for c in cells if isinstance(c, Rendered)]
    scale = 1.0 if fmt.kind in ("pct", "points") else max([*values, 0.0])
    label_w, bar_w, row_h, top = 140, 300, 28, 36
    height = top + row_h * len(cells) + 12
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{label_w + bar_w + 140}" '
        f'height="{height}" font-family="sans-serif" font-size="12">',
        f"<title>{_xml(figure.title)}</title>",
        f'<text x="0" y="18" font-weight="bold">{_xml(figure.title)}</text>',
    ]
    for index, ((label, _), cell) in enumerate(zip(figure.rows, cells, strict=True)):
        y = top + index * row_h
        parts.append(f'<text x="0" y="{y + 15}">{_xml(label)}</text>')
        if isinstance(cell, Rendered):
            width = 0 if scale <= 0 else round(bar_w * max(cell.value, 0.0) / scale, 1)
            parts.append(
                f'<rect x="{label_w}" y="{y + 4}" width="{width}" height="16" fill="#4a6fa5"/>'
            )
            parts.append(
                f'<text x="{label_w + width + 6}" y="{y + 16}">{_xml(cell.markdown)}</text>'
            )
        else:
            parts.append(
                f'<text x="{label_w}" y="{y + 16}" fill="#777" font-style="italic">{PENDING}</text>'
            )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def _xml(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_document(
    name: str, text: str, outcomes: Mapping[str, Outcome], *, draft: bool = False
) -> str:
    """A draft with every `{{num:key}}` replaced by its rendered value, "TBD (pending
    run)" when refused, or a visible ??key when the key is not registered. A reference
    inside inline code documents the syntax and is left as written (as in paper.i8)."""

    def value(match: re.Match[str]) -> str:
        outcome = outcomes.get(match.group(1))
        return f"??{match.group(1)}" if outcome is None else _markdown_value(outcome)

    def render_part(part: str) -> str:
        filled = MACRO_REFERENCE.sub(value, part)
        return filled.replace(MACRO_OPENING, f"??malformed {MACRO_OPENING}")

    def render_line(line: str) -> str:
        parts = INLINE_CODE.split(line)  # odd indexes are the code spans
        return "".join(part if index % 2 else render_part(part) for index, part in enumerate(parts))

    header = [
        f"<!-- Rendered from docs/paper/{name} by `uv run python -m paper.numbers` "
        "(ADR-0136). Do not edit: edit the source and re-render. Each value's results/ "
        "folders are in numbers.md beside this file. -->",
        # Visible, not a comment: a reader of the rendered draft must see it (ADR-0135).
        *(["", f"**{DRAFT_NOTE}.**"] if draft else []),
        "",
    ]
    return "\n".join(header) + "".join(map(render_line, text.splitlines(keepends=True)))


def read_documents(paper_dir: Path = PAPER_DIR) -> dict[str, str]:
    return {
        name: (paper_dir / name).read_text(encoding="utf-8")
        for name in DOCUMENTS
        if (paper_dir / name).is_file()
    }


def render_files(
    outcomes: Mapping[str, Outcome],
    registry: Mapping[str, AnySpec] = REGISTRY,
    *,
    draft: bool = False,
    documents: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Relative path under the generated directory -> file content. `documents` maps a
    draft's file name to its macro-only source text."""
    files = {
        "numbers.json": render_json(outcomes, registry, draft=draft),
        "numbers.tex": render_tex(outcomes, draft=draft),
        "numbers.md": render_markdown(outcomes, registry, draft=draft),
    }
    for name, text in (documents or {}).items():
        files[name] = render_document(name, text, outcomes, draft=draft)
    for figure in FIGURES:
        shown = replace(figure, title=f"DRAFT: {figure.title}") if draft else figure
        csv_text = render_figure_csv(shown, outcomes, registry)
        files[f"figures/{figure.name}.csv"] = (
            csv_text.replace("label,", "label (DRAFT),", 1) if draft else csv_text
        )
        files[f"figures/{figure.name}.dat"] = render_figure_dat(shown, outcomes, registry)
        files[f"figures/{figure.name}.svg"] = render_figure_svg(shown, outcomes, registry)
    return files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render paper macros from results/")
    parser.add_argument("--results", type=Path, default=RESULTS_DIR)
    parser.add_argument("--out", type=Path, default=None, help=f"default {GENERATED_DIR}")
    parser.add_argument("--check", action="store_true", help="exit 1 if --out is stale")
    # --strict is the camera-ready gate; a draft render can never pass it.
    gate = parser.add_mutually_exclusive_group()
    gate.add_argument("--strict", action="store_true", help="exit 1 if a macro is refused")
    gate.add_argument(
        "--draft",
        action="store_true",
        help="allow uncommitted runs (ADR-0135); writes to <out>/draft",
    )
    args = parser.parse_args(argv)
    out: Path = args.out or GENERATED_DIR
    if args.draft:
        out = out / "draft"
    outcomes = resolve_all(args.results, draft=args.draft)
    files = render_files(outcomes, draft=args.draft, documents=read_documents())
    stale = [
        path
        for path, content in files.items()
        if not (out / path).is_file() or (out / path).read_text(encoding="utf-8") != content
    ]
    if args.check:
        for path in stale:
            print(f"stale: {path}")
    else:
        for path, content in files.items():
            target = out / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8", newline="\n")
    refused = [o for o in outcomes.values() if isinstance(o, Refused)]
    print(f"{len(outcomes) - len(refused)} rendered, {len(refused)} refused ({PENDING}) -> {out}")
    if args.strict:
        for outcome in refused:
            print(f"  refused {outcome.name}: {outcome.reason}")
    if args.check and stale:
        return 1
    return 1 if args.strict and refused else 0


if __name__ == "__main__":
    sys.exit(main())
