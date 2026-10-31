"""The explicit registry of every number the paper and thesis may print (ADR-0110, I8).

A number in docs/paper is never typed: it is a macro whose value `python -m paper.numbers`
reads from results/ through an entry below. An entry names the run folders it may come
from (a glob under results/ plus a config filter), the JSON path inside metrics.json or
config.json, the printed format and whether it is a headline number. Headline numbers
carry the docs/04 protocol: pinned models and prompt versions, a committed clean sha and
at least three run seeds.

Entries marked `provisional` read a JSON path no producer writes yet (the memory metrics
are the author's bench/metrics.py; the linker and pilot harnesses are wave-B work in
progress). They are refused until a run carries the path; the reason says so. Moving a
path is a registry edit plus a line in the paper's ADR trail, never a typed number.
"""

import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal

MACRO_NAME = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z0-9_]+)+$")

# docs/04-evaluation.md, Protocol: "Three seeds minimum for headline numbers."
MIN_HEADLINE_SEEDS = 3

FORMAT_KINDS = ("int", "float", "pct", "points", "usd")


class Source(StrEnum):
    METRICS = "metrics.json"
    CONFIG = "config.json"


class Aggregate(StrEnum):
    SINGLE = "single"  # the newest qualifying run folder
    MEAN = "mean"  # mean over the newest consistent group of seeded run folders


@dataclass(frozen=True)
class Format:
    """How a value prints. pct and points expect a share in [0, 1] and print x100."""

    kind: str
    digits: int = 0

    @classmethod
    def parse(cls, spec: str) -> "Format":
        kind, _, digits = spec.partition(":")
        if kind not in FORMAT_KINDS:
            raise ValueError(f"unknown format kind {kind!r} in {spec!r}")
        if kind == "int" and digits:
            raise ValueError("int takes no digits")
        return cls(kind=kind, digits=int(digits) if digits else 0)


@dataclass(frozen=True)
class Prefix:
    """A config_match value that matches any string starting with `text` (a resolver
    description carries details after its kind)."""

    text: str


@dataclass(frozen=True)
class MacroSpec:
    name: str
    description: str
    run_pattern: str  # glob relative to results/, matched against run folders
    json_path: str  # dotted keys inside `source`
    fmt: str
    # Dotted config.json path -> required value; None also matches a missing key, so
    # the main ripple runs never pick up an ablation run.
    config_match: Mapping[str, object] = field(default_factory=dict[str, object])
    source: Source = Source.METRICS
    headline: bool = False
    aggregate: Aggregate = Aggregate.SINGLE
    supports: tuple[str, ...] = ()  # C1..C4, H1..H4, baseline, ablation, pilot
    provisional: str | None = None  # why no producer writes `json_path` yet
    # MEAN only: the config.json path holding the seed that varies between the averaged
    # runs when it is not the run seed (a trained linker's training seed, ADR-0135), and
    # the top-level config fields that change with that seed (excluded from grouping).
    seed_path: str | None = None
    seed_varies: tuple[str, ...] = ()


@dataclass(frozen=True)
class DerivedSpec:
    """A macro computed from two others; refused when either input is refused."""

    name: str
    description: str
    op: Literal["ratio", "difference"]
    inputs: tuple[str, str]
    fmt: str
    headline: bool = False
    supports: tuple[str, ...] = ()
    # Top-level config.json fields the compared runs may differ in (what the comparison
    # is about); every other field must agree, git sha and data included.
    differ: tuple[str, ...] = ()


@dataclass(frozen=True)
class FigureSpec:
    """A figure as data: one row per label, one macro per column (ADR-0110)."""

    name: str
    title: str
    columns: tuple[str, ...]
    rows: tuple[tuple[str, tuple[str, ...]], ...]
    bar_column: str  # the column the SVG draws
    differ: tuple[str, ...] = ()  # as DerivedSpec.differ, across all rendered cells


AnySpec = MacroSpec | DerivedSpec

V0_STRATEGIES = ("ripple", "append_only", "newest_wins", "check_everything")
RUN_COUNTS = ("scenarios", "scenarios_passed", "checks", "checks_failed", "resolver_calls")
# bench.run's description of its scripted resolver; the sanity macros are oracle-only so a
# later LLM-resolver run can never take their place under the same name.
ORACLE = Prefix("scripted oracle")
# Fields that legitimately differ between strategies of one bench run: what is compared.
STRATEGY_FIELDS = ("strategy", "engine", "linker")
# bench/generate.py DEFAULT_SEED: the generator seed that reproduces bench/data/jobs_v0.
V0_CHECKED_IN_SEED = 20261019

# Phase 3 memory-level metrics (ADR-0063). bench.run writes `memory_metrics` as the
# string "TBD (pending run)" today; the keys below are the contract request in
# docs/plans/parallel-execution/ws-17.md.
MEMORY_METRICS: tuple[tuple[str, str, str], ...] = (
    ("update_accuracy", "pct:1", "correct_updates / should-change targets (ADR-0063 H1)"),
    ("stale_kept", "float:1", "should-change targets the strategy left untouched"),
    ("wrongful_changes", "float:1", "should-stay targets the strategy moved"),
    ("questions_asked", "float:1", "ASK decisions across the scenario's ChangeEvents"),
    ("stale_retrieval_rate", "pct:1", "unflagged gold-stale retrieved memories (H2)"),
    ("stale_recommendation_rate", "pct:1", "unflagged recommendations on stale beliefs"),
    ("ttc_share_never_converged", "pct:1", "should-change targets never consistent"),
    ("cost_per_ripple", "float:2", "resolver calls per ChangeEvent (H1 cost, C4)"),
    ("tokens_per_ripple", "float:0", "LLM tokens per ChangeEvent (C4)"),
    ("usd_per_ripple", "usd:4", "priced from config/llm.default.toml (C4)"),
)
MEMORY_PROVISIONAL = (
    "bench.run writes memory_metrics (ADR-0120); refused while runs carry an uncommitted "
    "sha, and the ripple headline needs linker 'trained', which no bench run has (ADR-0122 "
    "records linker 'scenario')"
)
# Headline memory metrics read the held-out split (ADR-0061: test = unseen persona or
# template). Provisional until the Phase 3 baseline ADR fixes the protocol.
HEADLINE_SPLIT = "test"

# The tracks bench.matrix runs with three generator seeds (ADR-0121).
BENCH_SUITES = ("v0", "news_v1", "finance_v1")
# Oracle runs make no LLM call, so tokens and USD are null there (ADR-0122); the dependent
# accuracy leaves out the alias the event itself wrote (ADR-0120 point 5).
ORACLE_MEMORY_METRICS: tuple[tuple[str, str, str], ...] = (
    *(m for m in MEMORY_METRICS if m[0] not in ("tokens_per_ripple", "usd_per_ripple")),
    ("dependent_update_accuracy", "pct:1", "update accuracy without the event's own alias"),
)
OFFLINE_ABLATIONS = ("no_graph", "no_ask_user")

ABLATIONS = ("no_graph", "llm_linker", "no_curator", "no_evidence", "no_ask_user")

LINKERS = ("rule", "llm", "trained")
LINK_TRACKS = ("jobs_v0", "finance_v1")
# (key, format, JSON path, split). Untyped F1 is the H3/H4 reading until the Phase 3
# baseline ADR; typed F1, scenario-provenance F1 (no rule-labelled pairs, so the rule
# linker is not scored on its own labels) and the strict split are reported beside it.
LINK_METRICS: tuple[tuple[str, str, str, str], ...] = (
    ("f1", "pct:1", "overall.f1", "test"),
    ("typed_f1", "pct:1", "overall.typed_f1", "test"),
    ("f1_scenario", "pct:1", "by_provenance.scenario.f1", "test"),
    ("f1_strict", "pct:1", "overall.f1", "strict_test"),
    ("usd_per_1k_pairs", "usd:4", "overall.usd_per_1k_pairs", "test"),
    ("cpu_seconds_per_call", "float:4", "cost.cpu_seconds_per_call", "test"),
)
# The harness (training/evaluate.py, ADR-0127) writes suite "linkpairs", `linker`,
# `typed`, `split`, `new_memory`, `plumbing_only`, `models`, `prompt_versions`,
# `seeds.run_seed`, `transfer` and a `data` block in config.json; `overall`,
# `by_provenance`, `by_held_out` and `cost` in metrics.json.
LINK_PROVISIONAL = (
    "training/evaluate.py writes results/<date>_linkpairs_<track>_<sha>/; usd_per_1k_pairs "
    "and the strict split are not written yet, and the LLM linker needs a valid API key"
)
HELD_OUT_CELLS = ("both", "persona", "template")
TRAINED_SEED_PATH = "linker_details.seed"
# The trained linker's config leaves that change with its training seed: the artifact
# folder, the chosen epoch and threshold, the training record, and the model entry naming
# the folder. models.base_model_revision is among them because the first two runs predate
# the revision lookup and record null (docs/results/link-finder.md). Every other leaf,
# the base model and the training data included, must agree (ADR-0135).
TRAINED_SEED_FIELDS = (
    "linker_details.seed",
    "linker_details.model_dir",
    "linker_details.chosen_epoch",
    "linker_details.threshold",
    "linker_details.training.history",
    "linker_details.training.train_seconds",
    "linker_details.training.validation",
    "models.linker",
    "models.base_model_revision",
)
# Fields that legitimately differ between linkers, and between the jobs and finance tracks
# (finance runs are `--transfer` runs, ADR-0127).
LINKER_FIELDS = ("linker", "linker_details", "models", "prompt_versions", "typed")
TRACK_FIELDS = ("track", "data", "pair_count", "provenances", "transfer")

PILOT_METRICS: tuple[tuple[str, str, str], ...] = (
    ("students", "int", "students who used the agent during the season (C3)"),
    ("saved_or_applied_share", "pct:1", "recommendations saved or applied"),
    ("days_earlier_than_self_discovery", "float:1", "median days earlier"),
    ("stale_recommendation_rate", "pct:1", "recommendations shown on a stale belief"),
    ("question_usefulness_share", "pct:1", "questions marked useful"),
    ("trust_score", "float:1", "self-reported trust, survey scale"),
)
PILOT_PROVISIONAL = (
    "the WS-16 weekly report writes results/pilot/<week>/; a season summary folder and "
    "these keys are a contract request"
)

# training/handcheck.py writes results/<date>_handcheck_<track>_<sha>/ with an
# `overall` agreement table between the silver labels and the author's hand labels.
HANDCHECK_METRICS: tuple[tuple[str, str, str], ...] = (
    ("pairs", "int", "n"),
    ("agreement", "pct:1", "detection_agreement"),
    ("kappa", "float:2", "detection_kappa"),
    ("type_agreement", "pct:1", "type_agreement_when_both_link"),
)


def _oracle_run_counts() -> Iterator[AnySpec]:
    """Scripted-oracle replays of v0 (zero LLM calls, split all): a sanity check of write
    and ripple semantics, never a comparison with LLM-resolver runs (ADR-0060). Pinned to
    the checked-in data's generator seed (ADR-0121, ADR-0135): the grid also writes one
    split-all folder per regenerated seed, and "newest" would otherwise pick the last."""
    for strategy in V0_STRATEGIES:
        match = {
            "suite": "v0",
            "strategy": strategy,
            "split": "all",
            "resolver": ORACLE,
            "ablation": None,
            "seeds.generator_seed": V0_CHECKED_IN_SEED,
        }
        for key in RUN_COUNTS:
            yield MacroSpec(
                name=f"oracle.v0.{strategy}.{key}",
                description=f"v0 scripted-oracle replay, {strategy}: {key.replace('_', ' ')}",
                run_pattern=f"*_v0_{strategy}_*",
                config_match=match,
                json_path=key,
                fmt="int",
                supports=("baseline",) if strategy != "ripple" else (),
            )
        yield DerivedSpec(
            name=f"oracle.v0.{strategy}.pass_share",
            description=f"v0 scripted-oracle replay, {strategy}: scenarios passed / scenarios",
            op="ratio",
            inputs=(f"oracle.v0.{strategy}.scenarios_passed", f"oracle.v0.{strategy}.scenarios"),
            fmt="pct:1",
            supports=("baseline",) if strategy != "ripple" else (),
        )


def _smoke() -> Iterator[AnySpec]:
    match = {"suite": "smoke", "strategy": "ripple", "resolver": ORACLE}
    for key in ("scenarios", "scenarios_passed"):
        yield MacroSpec(
            name=f"smoke.ripple.{key}",
            description=f"smoke suite (tests/scenarios), ripple: {key.replace('_', ' ')}",
            run_pattern="*_smoke_*",
            config_match=match,
            json_path=key,
            fmt="int",
        )


def _memory_metrics() -> Iterator[AnySpec]:
    for strategy in V0_STRATEGIES:
        match: dict[str, object] = {
            "suite": "v0",
            "strategy": strategy,
            "split": HEADLINE_SPLIT,
            "ablation": None,
        }
        if strategy == "ripple":
            match["linker"] = "trained"  # the system C1 claims; other linkers are ablations
        for key, fmt, meaning in MEMORY_METRICS:
            yield MacroSpec(
                name=f"mem.{strategy}.{key}",
                description=f"RippleBench v0 {HEADLINE_SPLIT} split, {strategy}: {meaning}",
                run_pattern=f"*_v0_{strategy}_*",
                config_match=match,
                json_path=f"memory_metrics.{key}",
                fmt=fmt,
                headline=True,
                aggregate=Aggregate.MEAN,
                supports=_memory_supports(key),
                provisional=MEMORY_PROVISIONAL,
            )


def _oracle_memory() -> Iterator[AnySpec]:
    """Memory metrics of the runs that exist: scripted oracle resolver, gold links from the
    scenario file, mean over three generator seeds, test split (ADR-0121, ADR-0122,
    ADR-0135). They test the engine's semantics, not a link finder or an LLM resolver, so
    they never stand in for the `mem.*` macros of the system C1 claims."""
    for suite in BENCH_SUITES:
        for strategy in V0_STRATEGIES:
            match: dict[str, object] = {
                "suite": suite,
                "strategy": strategy,
                "split": HEADLINE_SPLIT,
                "resolver": ORACLE,
                "linker": "scenario",
                "ablation": None,
                "seeds.kind": "generator",
            }
            for key, fmt, meaning in ORACLE_MEMORY_METRICS:
                if key == "stale_recommendation_rate" and suite != "v0":
                    continue  # the placeholder ranking ranks jobs openings only
                yield MacroSpec(
                    name=f"oracle_mem.{suite}.{strategy}.{key}",
                    description=f"{suite} {HEADLINE_SPLIT} split, {strategy}, scripted oracle "
                    f"and gold links: {meaning}",
                    run_pattern=f"*_{suite}_{strategy}_*",
                    config_match=match,
                    json_path=f"memory_metrics.{key}",
                    fmt=fmt,
                    headline=True,
                    aggregate=Aggregate.MEAN,
                    supports=_memory_supports(key),
                )
            # Run-level counts beside the rates, so a reader sees what each rests on.
            for key in ("scenarios", "scenarios_passed", "resolver_calls"):
                yield MacroSpec(
                    name=f"oracle_mem.{suite}.{strategy}.{key}",
                    description=f"{suite} {HEADLINE_SPLIT} split, {strategy}, scripted oracle: "
                    f"{key.replace('_', ' ')} per run, mean over generator seeds",
                    run_pattern=f"*_{suite}_{strategy}_*",
                    config_match=match,
                    json_path=key,
                    fmt="float:1",
                    headline=True,
                    aggregate=Aggregate.MEAN,
                    supports=("C2",),
                )
        yield DerivedSpec(
            name=f"oracle_h1.{suite}.accuracy_ratio",
            description=f"{suite}: ripple update accuracy / check_everything's (oracle)",
            op="ratio",
            inputs=(
                f"oracle_mem.{suite}.ripple.update_accuracy",
                f"oracle_mem.{suite}.check_everything.update_accuracy",
            ),
            fmt="pct:1",
            headline=True,
            supports=("H1",),
            differ=STRATEGY_FIELDS,
        )
        yield DerivedSpec(
            name=f"oracle_h1.{suite}.cost_ratio",
            description=f"{suite}: ripple resolver calls per ripple / check_everything's (oracle)",
            op="ratio",
            inputs=(
                f"oracle_mem.{suite}.ripple.cost_per_ripple",
                f"oracle_mem.{suite}.check_everything.cost_per_ripple",
            ),
            fmt="pct:1",
            headline=True,
            supports=("H1", "C4"),
            differ=STRATEGY_FIELDS,
        )
        yield DerivedSpec(
            name=f"oracle_h2.{suite}.stale_retrieval_gap_points",
            description=f"{suite}: append_only stale retrieval rate minus ripple's (oracle)",
            op="difference",
            inputs=(
                f"oracle_mem.{suite}.append_only.stale_retrieval_rate",
                f"oracle_mem.{suite}.ripple.stale_retrieval_rate",
            ),
            fmt="points:1",
            headline=True,
            supports=("H2",),
            differ=STRATEGY_FIELDS,
        )


def _oracle_ablations() -> Iterator[AnySpec]:
    """The two ablations that run offline (ADR-0122), under the same oracle protocol."""
    for suite in BENCH_SUITES:
        for ablation in OFFLINE_ABLATIONS:
            match = {
                "suite": suite,
                "strategy": "ripple",
                "split": HEADLINE_SPLIT,
                "resolver": ORACLE,
                "linker": "scenario",
                "ablation": ablation,
                "seeds.kind": "generator",
            }
            for key in ("update_accuracy", "questions_asked", "cost_per_ripple"):
                fmt = next(f for k, f, _ in MEMORY_METRICS if k == key)
                yield MacroSpec(
                    name=f"oracle_ablation.{suite}.{ablation}.{key}",
                    description=f"{suite}: ripple without {ablation.removeprefix('no_')} "
                    f"(oracle): {key}",
                    run_pattern=f"*_{suite}_ripple_{ablation}_*",
                    config_match=match,
                    json_path=f"memory_metrics.{key}",
                    fmt=fmt,
                    headline=True,
                    aggregate=Aggregate.MEAN,
                    supports=("ablation",),
                )


def _memory_supports(key: str) -> tuple[str, ...]:
    if key == "update_accuracy":
        return ("H1", "Q1")
    if key == "stale_retrieval_rate":
        return ("H2",)
    if key == "stale_recommendation_rate" or key.startswith("ttc"):
        return ("C2", "Q2")
    if key in ("cost_per_ripple", "tokens_per_ripple", "usd_per_ripple"):
        return ("H1", "C4", "Q3")
    return ("Q1",)


def _ratio_vs_check_everything(key: str, name: str, supports: tuple[str, ...]) -> DerivedSpec:
    return DerivedSpec(
        name=name,
        description=f"ripple {key} / check_everything {key}",
        op="ratio",
        inputs=(f"mem.ripple.{key}", f"mem.check_everything.{key}"),
        fmt="pct:1",
        headline=True,
        supports=supports,
        differ=STRATEGY_FIELDS,
    )


def _hypotheses() -> Iterator[AnySpec]:
    yield _ratio_vs_check_everything("update_accuracy", "h1.accuracy_ratio", ("H1",))
    # H1's "cost" is resolver calls per ripple (ADR-0063) until the Phase 3 baseline ADR;
    # tokens and USD are reported beside it because prompt sizes differ by strategy.
    yield _ratio_vs_check_everything("cost_per_ripple", "h1.cost_ratio", ("H1", "C4"))
    yield _ratio_vs_check_everything("tokens_per_ripple", "h1.tokens_ratio", ("H1", "C4"))
    yield _ratio_vs_check_everything("usd_per_ripple", "h1.usd_ratio", ("H1", "C4"))
    yield DerivedSpec(
        name="h2.stale_retrieval_gap_points",
        description="append_only stale retrieval rate minus ripple's, in points",
        op="difference",
        inputs=("mem.append_only.stale_retrieval_rate", "mem.ripple.stale_retrieval_rate"),
        fmt="points:1",
        headline=True,
        supports=("H2",),
        differ=STRATEGY_FIELDS,
    )
    yield DerivedSpec(
        name="h3.f1_difference_points",
        description="LLM linker F1 minus trained linker F1 on the jobs test split, points",
        op="difference",
        inputs=("link.llm.jobs_v0.f1", "link.trained.jobs_v0.f1"),
        fmt="points:1",
        headline=True,
        supports=("H3", "C1"),
        differ=LINKER_FIELDS,
    )
    yield DerivedSpec(
        name="h3.cost_ratio",
        description="trained linker cost / LLM linker cost per 1k pairs",
        op="ratio",
        inputs=("link.trained.jobs_v0.usd_per_1k_pairs", "link.llm.jobs_v0.usd_per_1k_pairs"),
        fmt="pct:1",
        headline=True,
        supports=("H3", "C1"),
        differ=LINKER_FIELDS,
    )
    # The jobs side is the strict held_out=both cell, the one WS-19's report reads; the
    # overall jobs F1 includes cells whose templates were seen in training (ADR-0135).
    yield DerivedSpec(
        name="h4.transfer_difference_points",
        description="trained linker F1, jobs held_out=both minus finance transfer, points",
        op="difference",
        inputs=("link.trained.jobs_v0.f1_both", "link.trained.finance_v1.f1"),
        fmt="points:1",
        headline=True,
        supports=("H4", "C1"),
        differ=(*TRACK_FIELDS, "typed", *TRAINED_SEED_FIELDS),
    )


def _link_spec(linker: str, track: str, key: str, fmt: str, path: str, split: str) -> MacroSpec:
    # A FakeLLM plumbing run (plumbing_only) never stands in for the LLM linker, and a
    # `--new parent` orientation run never doubles a seed (ADR-0127).
    match = {
        "suite": "linkpairs",
        "track": track,
        "linker": linker,
        "split": split,
        "plumbing_only": False,
        "new_memory": "dependent",
    }
    # What varies between the trained runs is the training seed (ADR-0126); the
    # evaluation's run seed is the same in all of them (ADR-0135).
    trained = linker == "trained"
    deterministic = linker == "rule"
    return MacroSpec(
        name=f"link.{linker}.{track}.{key}",
        description=f"{linker} linker on {track} {split} pairs: {path}"
        + (" (deterministic, one run)" if deterministic else ""),
        run_pattern=f"*_linkpairs_{track}_*",
        config_match=match,
        json_path=path,
        fmt=fmt,
        # The rule linker has no seed to vary, so it is one run and not a seed mean.
        headline=not deterministic,
        aggregate=Aggregate.SINGLE if deterministic else Aggregate.MEAN,
        supports=("C1", "H3") if track == "jobs_v0" else ("C1", "H4"),
        provisional=LINK_PROVISIONAL,
        seed_path=TRAINED_SEED_PATH if trained else None,
        seed_varies=TRAINED_SEED_FIELDS if trained else (),
    )


def _linkers() -> Iterator[AnySpec]:
    for linker in LINKERS:
        for track in LINK_TRACKS:
            for key, fmt, path, split in LINK_METRICS:
                if split != "test" and track != "jobs_v0":
                    continue  # finance is test-only (H4); no strict split exists there
                yield _link_spec(linker, track, key, fmt, path, split)


def _link_cells() -> Iterator[AnySpec]:
    """The held-out cells WS-19's report reads (ADR-0127): held_out=both (unseen persona
    and template) is the primary jobs cell; finance is all transfer pairs."""
    for linker in LINKERS:
        for cell in HELD_OUT_CELLS:
            for metric in ("f1", "precision", "recall", "typed_f1"):
                fmt = "pct:1"
                yield _link_spec(
                    linker,
                    "jobs_v0",
                    f"{metric}_{cell}",
                    fmt,
                    f"by_held_out.{cell}.{metric}",
                    "test",
                )
        for metric in ("precision", "recall"):
            yield _link_spec(linker, "finance_v1", metric, "pct:1", f"overall.{metric}", "test")
    # Pair counts, read from the deterministic rule run (every linker sees the same file).
    for track, key, path in (
        ("jobs_v0", "test_pairs", "overall.n"),
        ("jobs_v0", "test_pairs_both", "by_held_out.both.n"),
        ("finance_v1", "test_pairs", "overall.n"),
    ):
        yield _link_spec("rule", track, key, "int", path, "test")
    yield DerivedSpec(
        name="link.jobs_v0.f1_both_trained_minus_rule_points",
        description="trained (three-seed mean) minus rule F1, jobs held_out=both, points",
        op="difference",
        inputs=("link.trained.jobs_v0.f1_both", "link.rule.jobs_v0.f1_both"),
        fmt="points:1",
        supports=("C1",),
        differ=LINKER_FIELDS,
    )
    yield DerivedSpec(
        name="h4.finance_trained_minus_rule_points",
        description="trained (three-seed mean) minus rule F1 on finance transfer, points",
        op="difference",
        inputs=("link.trained.finance_v1.f1", "link.rule.finance_v1.f1"),
        fmt="points:1",
        supports=("H4", "C1"),
        differ=(*LINKER_FIELDS, "transfer"),
    )


def _handcheck() -> Iterator[AnySpec]:
    for key, fmt, field_name in HANDCHECK_METRICS:
        yield MacroSpec(
            name=f"handcheck.jobs_v0.{key}",
            description=f"hand-checked link pairs against silver labels: {field_name}",
            run_pattern="*_handcheck_jobs_v0_*",
            config_match={"suite": "handcheck"},
            json_path=f"overall.{field_name}",
            fmt=fmt,
            supports=("C1",),
            provisional="the hand labels are the author's (WS-14 protocol, ADR-0009)",
        )


def _ablations() -> Iterator[AnySpec]:
    for ablation in ABLATIONS:
        match = {"suite": "v0", "strategy": "ripple", "split": HEADLINE_SPLIT}
        for key in ("update_accuracy", "stale_recommendation_rate", "cost_per_ripple"):
            fmt = next(f for k, f, _ in MEMORY_METRICS if k == key)
            yield MacroSpec(
                name=f"ablation.{ablation}.{key}",
                description=f"ripple without {ablation.removeprefix('no_')}: {key}",
                run_pattern="*_v0_ripple_*",
                config_match={**match, "ablation": ablation},
                json_path=f"memory_metrics.{key}",
                fmt=fmt,
                headline=True,
                aggregate=Aggregate.MEAN,
                supports=("ablation",),
                provisional=MEMORY_PROVISIONAL + "; bench.run --ablation exists (ADR-0122)",
            )


def _pilot() -> Iterator[AnySpec]:
    for key, fmt, meaning in PILOT_METRICS:
        yield MacroSpec(
            name=f"pilot.{key}",
            description=f"pilot season: {meaning}",
            run_pattern="pilot/season*",
            config_match={"kind": "pilot_season"},
            json_path=f"pilot_metrics.{key}",
            fmt=fmt,
            supports=("C3",),
            provisional=PILOT_PROVISIONAL,
        )


def _build() -> dict[str, AnySpec]:
    specs: dict[str, AnySpec] = {}
    for producer in (
        _oracle_run_counts,
        _smoke,
        _memory_metrics,
        _oracle_memory,
        _hypotheses,
        _linkers,
        _link_cells,
        _handcheck,
        _ablations,
        _oracle_ablations,
        _pilot,
    ):
        for spec in producer():
            if spec.name in specs:
                raise ValueError(f"duplicate macro {spec.name}")
            specs[spec.name] = spec
    return specs


REGISTRY: Mapping[str, AnySpec] = _build()

ORACLE_COLUMNS = ("pass_share", "scenarios_passed", "scenarios", "checks_failed", "checks")

FIGURES: tuple[FigureSpec, ...] = (
    FigureSpec(
        name="baselines_v0",
        title="v0 scripted-oracle replay (split all, sanity check): scenarios passed",
        columns=ORACLE_COLUMNS,
        rows=tuple(
            (strategy, tuple(f"oracle.v0.{strategy}.{column}" for column in ORACLE_COLUMNS))
            for strategy in V0_STRATEGIES
        ),
        bar_column="pass_share",
        differ=STRATEGY_FIELDS,
    ),
    FigureSpec(
        name="h1_accuracy_cost",
        title="H1: update accuracy and cost per ripple",
        columns=("update_accuracy", "cost_per_ripple"),
        rows=tuple(
            (strategy, (f"mem.{strategy}.update_accuracy", f"mem.{strategy}.cost_per_ripple"))
            for strategy in V0_STRATEGIES
        ),
        bar_column="update_accuracy",
        differ=STRATEGY_FIELDS,
    ),
    FigureSpec(
        name="linker_f1",
        title="H3/H4: link finder F1, jobs held_out=both and finance transfer",
        columns=("jobs_v0_both", "finance_v1"),
        rows=tuple(
            (linker, (f"link.{linker}.jobs_v0.f1_both", f"link.{linker}.finance_v1.f1"))
            for linker in LINKERS
        ),
        bar_column="jobs_v0_both",
        differ=LINKER_FIELDS + TRACK_FIELDS,
    ),
)
