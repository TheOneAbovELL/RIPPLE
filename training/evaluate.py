"""Evaluation harness: any `ripple.core.linking.Linker` over a C5 pair file (ADR-0093).

    uv run python -m training.evaluate --linker rule
    uv run python -m training.evaluate --linker fake_llm   # plumbing check, not a measurement
    uv run python -m training.evaluate --linker llm        # real provider; needs RIPPLE_LLM_CONFIG
    uv run python -m training.evaluate --linker trained --model <folder>
    uv run python -m training.evaluate --linker trained --model <folder> \
        --pairs bench/data/finance_v1/pairs.jsonl --transfer  # H4: another domain's test pairs

Protocol, per pair: the dependent is the new memory and the parent its only candidate
(`--new parent` flips this). Both memories get opaque ids ("m1", "m2", assigned by a
seeded coin per pair) so nothing in an id (persona, side) reaches a model's prompt.
The pair is predicted linked when the linker proposes an edge parent -> dependent;
its predicted type is the most confident such proposal's. An edge the other way is a
prediction for the reversed pair, not for this one. Invalid model output is an
abstention (no prediction), counted, the same rule for every linker.

Output: results/<date>_linkpairs_<track>_<linker>_<sha>/ with config.json,
metrics.json (confusion counts and P/R/F1 overall, per provenance, per held-out cell,
false positives per negative kind, recall per gold link type, a type confusion table),
predictions.jsonl and report.md. Nothing is written outside results/ (I8). Cost is
recorded as wall and process CPU seconds per linker call (ADR-0127).

A trained linker is scored on its own pair file, or with `--transfer` on a test-only
pair file of another track (H4): then no (parent, dependent) text pair may equal one of
its training pairs, and typed metrics are null when the file's link types are outside
the model's label space (ADR-0127).
"""

import argparse
import asyncio
import json
import platform
import random
import sys
import time
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from bench.linkpairs import LabelledPair, PairMemory, Split, read_pairs
from bench.run import RESULTS_DIR, git_short_sha

from ripple.core.errors import LLMOutputInvalidError
from ripple.core.linking import Linker
from ripple.core.models import Memory
from training.jobs_pairs import REPO_ROOT, file_sha256, pairs_path
from training.leakage import held_out_cell

EVAL_USER = "linkpairs-eval"
EVAL_TIME = datetime(2026, 1, 1, tzinfo=UTC)  # fixed: pairs carry no time, linkers need one
DEFAULT_RUN_SEED = 20261031
UNKNOWN_CELL = "unknown"  # the pair file has no split manifest beside it
NewSide = Literal["dependent", "parent"]
PLUMBING_NOTE = (
    "PLUMBING CHECK: the LLM linker ran on FakeLLM scripted to propose nothing. These "
    "counts show the harness runs end to end; they measure no model."
)


@dataclass(frozen=True)
class PairPrediction:
    pair_id: str
    provenance: str
    held_out: str  # none | persona | template | both | unknown
    negative_kind: str | None  # the pair's note for gold negatives ("reversed link", ...)
    gold_type: str | None
    predicted_type: str | None
    confidence: float | None
    reversed_proposals: int  # edges dependent -> parent the linker proposed
    abstained: bool = False  # invalid model output: no prediction


def _memory(pair: LabelledPair, memory_id: str, memory: PairMemory) -> Memory:
    return Memory(
        id=memory_id,
        user_id=EVAL_USER,
        domain=pair.domain,
        kind=memory.kind,
        content=memory.content,
        structured=memory.structured,
        recorded_at=EVAL_TIME,
        created_by="linkpairs-eval",
    )


async def predict(
    linker: Linker,
    pair: LabelledPair,
    new: NewSide = "dependent",
    *,
    seed: int = DEFAULT_RUN_SEED,
    held_out: str = UNKNOWN_CELL,
) -> PairPrediction:
    ids = ["m1", "m2"]
    random.Random(f"{seed}:{pair.pair_id}").shuffle(ids)
    parent = _memory(pair, ids[0], pair.parent)
    dependent = _memory(pair, ids[1], pair.dependent)
    abstained = False
    try:
        if new == "dependent":
            proposals = await linker.propose(dependent, [parent])
        else:
            proposals = await linker.propose(parent, [dependent])
    except LLMOutputInvalidError:
        proposals, abstained = [], True
    forward = [p for p in proposals if (p.parent_id, p.dependent_id) == (parent.id, dependent.id)]
    backward = [p for p in proposals if (p.parent_id, p.dependent_id) == (dependent.id, parent.id)]
    best = max(forward, key=lambda p: p.confidence, default=None)
    return PairPrediction(
        pair_id=pair.pair_id,
        provenance=pair.provenance.value,
        held_out=held_out,
        negative_kind=None if pair.is_link else (pair.note or "unspecified"),
        gold_type=pair.link_type,
        predicted_type=None if best is None else best.link_type,
        confidence=None if best is None else best.confidence,
        reversed_proposals=len(backward),
        abstained=abstained,
    )


async def predict_all(
    linker: Linker,
    pairs: Sequence[LabelledPair],
    new: NewSide = "dependent",
    *,
    seed: int = DEFAULT_RUN_SEED,
    cells: dict[str, str] | None = None,
) -> list[PairPrediction]:
    # Sequential on purpose: a real provider is rate-limited, and order keeps a
    # scripted FakeLLM's answers aligned with the pairs.
    cells = cells or {}
    return [
        await predict(linker, p, new, seed=seed, held_out=cells.get(p.pair_id, UNKNOWN_CELL))
        for p in pairs
    ]


# ---- metrics ------------------------------------------------------------------------


@dataclass
class Confusion:
    tp: int = 0
    fp: int = 0
    fn: int = 0
    tn: int = 0
    typed_tp: int = 0  # tp whose predicted type equals the gold type

    def add(self, prediction: PairPrediction) -> None:
        gold, predicted = prediction.gold_type is not None, prediction.predicted_type is not None
        if gold and predicted:
            self.tp += 1
            self.typed_tp += int(prediction.predicted_type == prediction.gold_type)
        elif predicted:
            self.fp += 1
        elif gold:
            self.fn += 1
        else:
            self.tn += 1

    def as_dict(self, *, typed: bool = True) -> dict[str, object]:
        """Precision and recall are null when their denominator is zero. In a stratum
        with no gold negatives (a RULE stratum) precision and F1 are null too: a false
        positive is impossible there, so they would only restate recall. F1 is 0, not
        null, when gold links exist and none was found. Typed metrics are null for a
        linker that does not predict types."""
        has_negatives = self.fp + self.tn > 0
        precision = _ratio(self.tp, self.tp + self.fp) if has_negatives else None
        typed_precision = _ratio(self.typed_tp, self.tp + self.fp) if has_negatives else None
        return {
            **asdict(self),
            "n": self.tp + self.fp + self.fn + self.tn,
            "precision": precision,
            "recall": _ratio(self.tp, self.tp + self.fn),
            "f1": _ratio(2 * self.tp, 2 * self.tp + self.fp + self.fn) if has_negatives else None,
            "typed_precision": typed_precision if typed else None,
            "typed_recall": _ratio(self.typed_tp, self.tp + self.fn) if typed else None,
            # harmonic mean of typed precision and recall: 2·typed_tp / (2·tp + fp + fn)
            "typed_f1": (
                _ratio(2 * self.typed_tp, 2 * self.tp + self.fp + self.fn)
                if typed and has_negatives
                else None
            ),
        }


def _ratio(numerator: int, denominator: int) -> float | None:
    return None if denominator == 0 else numerator / denominator


def confusion_by(
    predictions: Sequence[PairPrediction], key: Callable[[PairPrediction], str]
) -> dict[str, Confusion]:
    table: dict[str, Confusion] = {}
    for prediction in predictions:
        table.setdefault(key(prediction), Confusion()).add(prediction)
    return dict(sorted(table.items()))


def metrics(
    predictions: Sequence[PairPrediction],
    *,
    typed: bool = True,
    train_link_types: frozenset[str] | None = None,
) -> dict[str, object]:
    overall = Confusion()
    for prediction in predictions:
        overall.add(prediction)
    by_provenance = confusion_by(predictions, lambda p: p.provenance)
    by_held_out = confusion_by(predictions, lambda p: p.held_out)
    gold_links = [p for p in predictions if p.gold_type is not None]
    by_gold_type: dict[str, dict[str, object]] = {}
    for link_type, cell in confusion_by(gold_links, lambda p: p.gold_type or "").items():
        # Only gold links are here, so precision is not defined: tp, fn and recall only.
        by_gold_type[link_type] = {
            "tp": cell.tp,
            "fn": cell.fn,
            "recall": _ratio(cell.tp, cell.tp + cell.fn),
            "typed_recall": _ratio(cell.typed_tp, cell.tp + cell.fn) if typed else None,
            "seen_in_train": None if train_link_types is None else link_type in train_link_types,
        }
    negatives: dict[str, dict[str, object]] = {}
    for kind, cell in confusion_by(
        [p for p in predictions if p.gold_type is None], lambda p: p.negative_kind or ""
    ).items():
        negatives[kind] = {
            "n": cell.fp + cell.tn,
            "fp": cell.fp,
            "fp_rate": _ratio(cell.fp, cell.fp + cell.tn),
        }
    type_confusion = Counter(
        f"{p.gold_type or 'none'} -> {p.predicted_type or 'none'}" for p in predictions
    )
    return {
        "overall": overall.as_dict(typed=typed),
        "by_provenance": {k: v.as_dict(typed=typed) for k, v in by_provenance.items()},
        "by_held_out": {k: v.as_dict(typed=typed) for k, v in by_held_out.items()},
        "by_gold_link_type": by_gold_type,
        "false_positives_by_negative_kind": negatives,
        "type_confusion": dict(sorted(type_confusion.items())),
        "reversed_proposals": sum(p.reversed_proposals for p in predictions),
        "abstentions": sum(p.abstained for p in predictions),
    }


# ---- runs ---------------------------------------------------------------------------


@dataclass
class LinkerSpec:
    name: str  # rule, fake_llm, llm, trained
    linker: Linker
    plumbing_only: bool = False
    typed: bool = True  # False: the linker proposes one fixed type; typed metrics are null
    calls_llm: bool = False
    # paper/numbers.py reads both; {} records "no model, no prompt" rather than unknown
    models: dict[str, object] = field(default_factory=dict)
    prompt_versions: dict[str, int] = field(default_factory=dict)
    train_pairs_sha256: str | None = None  # a trained linker is scored on its own pair file
    train_pairs_file: Path | None = None  # read for the transfer overlap check
    label_space: tuple[str, ...] = ()  # the types a trained linker can propose
    # link types the model was fitted on (not its validation personas): seen_in_train
    fitted_link_types: frozenset[str] | None = None
    details: dict[str, object] = field(default_factory=dict)


def rule_linker() -> LinkerSpec:
    from ripple.linking.rules import LINK_TYPE, RULE_CONFIDENCE, RuleLinker

    return LinkerSpec(
        "rule",
        RuleLinker(),
        typed=False,
        details={
            "module": "ripple.linking.rules",
            "confidence": RULE_CONFIDENCE,
            "only_type": LINK_TYPE,
        },
    )


def fake_llm_linker(pair_count: int) -> LinkerSpec:
    """The LLM linker wired through the real router to FakeLLM answering "no proposals"
    for every pair: proves prompt, schema and router plumbing offline, measures nothing."""
    from tests.fakes.llm import FakeLLM

    from ripple.domains.jobs.vocabulary import jobs_registry
    from ripple.linking.llm import PROMPT_VERSION, LLMLinker
    from ripple.llm.config import ModelSpec, RouterConfig
    from ripple.llm.router import Router

    fake = FakeLLM(*([json.dumps({"proposals": []})] * pair_count), model="fake-linker")
    router = Router(
        RouterConfig(tasks={"linker": [ModelSpec(provider="fake", model="fake-linker")]}),
        {"fake": fake},
    )
    return LinkerSpec(
        "fake_llm",
        LLMLinker(router, jobs_registry()),
        plumbing_only=True,
        calls_llm=True,
        models={"linker": "fake/fake-linker (tests/fakes/llm.py, scripted: no proposals)"},
        prompt_versions={"linker": PROMPT_VERSION},
        details={"module": "ripple.linking.llm"},
    )


def llm_linker(domain: str = "jobs") -> LinkerSpec:  # pragma: no cover - needs a provider
    """The configured provider with the link types of the pair file's domain, so a finance
    run asks for finance types (bench.domains.registry_for)."""
    import os

    from bench.domains import registry_for

    from ripple.linking.llm import PROMPT_VERSION, TASK, LLMLinker
    from ripple.llm.config import RouterConfig
    from ripple.worker.wiring import DEFAULT_LLM_CONFIG, LLM_CONFIG_VAR, router_from_env

    config_path = Path(os.environ.get(LLM_CONFIG_VAR, DEFAULT_LLM_CONFIG))
    chain = RouterConfig.from_toml(config_path).models_for(TASK)
    return LinkerSpec(
        "llm",
        LLMLinker(router_from_env(os.environ), registry_for(domain)),
        calls_llm=True,
        models={"linker": [f"{m.provider}/{m.model}" for m in chain]},
        prompt_versions={"linker": PROMPT_VERSION},
        details={
            "module": "ripple.linking.llm",
            "config": _display(config_path),
            "config_sha256": file_sha256(config_path),
            "fallback_chain": [m.model_dump(mode="json") for m in chain],
        },
    )


def trained_linker(model_dir: Path | None) -> LinkerSpec:
    from training.train import NO_LINK, TrainedLinker

    if model_dir is None:
        raise SystemExit("--linker trained needs --model <folder>")
    linker = TrainedLinker.load(model_dir)
    artifact = linker.artifact
    train_file = artifact.manifest.get("train_pairs_file")
    training = artifact.manifest.get("training", {})
    fitted = frozenset(training.get("fit_label_counts", {})) - {NO_LINK}
    return LinkerSpec(
        "trained",
        linker,
        models={
            "linker": _display(model_dir),
            "base_model": artifact.base_model,
            "base_model_revision": artifact.base_model_revision,
        },
        train_pairs_sha256=artifact.train_pairs_sha256,
        train_pairs_file=None if train_file is None else REPO_ROOT / str(train_file),
        label_space=artifact.label_space,
        fitted_link_types=fitted,
        details={
            "module": "ripple.linking.trained",
            "model_dir": _display(model_dir),
            "base_model": artifact.base_model,
            "seed": artifact.seed,
            "threshold": linker.threshold,
            "threshold_source": artifact.manifest.get("threshold_source"),
            "chosen_epoch": training.get("chosen_epoch"),
            # Copied from the artifact manifest so a report cites results/ only (I8).
            "training": {
                key: training.get(key)
                for key in (
                    "fit_examples",
                    "validation_examples",
                    "fit_label_counts",
                    "validation_label_counts",
                    "validation",
                    "train_seconds",
                    "torch_threads",
                    "history",
                )
            },
            "validation_personas": artifact.manifest.get("train_config", {}).get(
                "validation_personas"
            ),
            "torch_threads": _torch_threads(),
        },
    )


def _torch_threads() -> int | None:
    try:
        import torch
    except ImportError:  # pragma: no cover - the linkfinder group is a default group
        return None
    return torch.get_num_threads()


def transfer_check(
    spec: LinkerSpec, pairs: Sequence[LabelledPair], pairs_sha: str
) -> tuple[dict[str, object], frozenset[str]]:
    """For `--transfer`: the evaluated pairs must all be test pairs of a track the model
    was not trained on and share no (parent, dependent) text pair with its training pairs.
    Returns the record for config.json and the link types in the training split."""
    if spec.train_pairs_file is None or not spec.train_pairs_file.is_file():
        raise ValueError(f"{spec.name}: its training pair file is not available for the check")
    if file_sha256(spec.train_pairs_file) != spec.train_pairs_sha256:
        raise ValueError(f"{spec.train_pairs_file} changed since {spec.name} was trained on it")
    if pairs_sha == spec.train_pairs_sha256:
        raise ValueError("--transfer on the model's own pair file is not a transfer")
    if any(p.split is not Split.TEST for p in pairs):
        raise ValueError("--transfer scores test pairs only; this selection has train pairs")
    train_pairs = [p for p in read_pairs(spec.train_pairs_file) if p.split is Split.TRAIN]
    same_track = sorted({p.track for p in pairs} & {p.track for p in train_pairs})
    if same_track:
        raise ValueError(f"--transfer needs another track; {same_track} is the training track")
    train_texts = {(p.parent.content, p.dependent.content) for p in train_pairs}
    single_texts = {m.content for p in train_pairs for m in (p.parent, p.dependent)}
    same_pair = sum((p.parent.content, p.dependent.content) in train_texts for p in pairs)
    if same_pair:
        raise ValueError(f"{same_pair} evaluated pairs repeat a training text pair: not a transfer")
    shared_one = sum(
        p.parent.content in single_texts or p.dependent.content in single_texts for p in pairs
    )
    gold_types = sorted({p.link_type for p in pairs if p.link_type is not None})
    record: dict[str, object] = {
        "train_pairs_file": _display(spec.train_pairs_file),
        "train_pairs_sha256": spec.train_pairs_sha256,
        "pairs_sharing_a_text_with_train": shared_one,
        "gold_link_types": gold_types,
        "gold_types_in_label_space": set(gold_types) <= set(spec.label_space),
    }
    seen = frozenset(p.link_type for p in train_pairs if p.link_type is not None)
    return record, seen


def run_dir_for(results_root: Path, track: str, linker: str, sha: str) -> Path:
    """A fresh folder per run: an existing same-day folder is never overwritten."""
    today = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    base = results_root / f"{today}_linkpairs_{track}_{linker}_{sha}"
    candidate, counter = base, 1
    while candidate.exists():
        counter += 1
        candidate = base.with_name(f"{base.name}_{counter}")
    return candidate


def select(pairs: Sequence[LabelledPair], split: str) -> list[LabelledPair]:
    return [p for p in pairs if split == "all" or p.split == Split(split)]


def pair_manifest(pairs_file: Path) -> tuple[Path, dict[str, object]] | None:
    """The generator's manifest beside a pair file (training.jobs_pairs writes
    <name>.manifest.json); None for a pair file without one."""
    path = pairs_file.with_suffix(".manifest.json")
    if not path.exists():
        return None
    return path, json.loads(path.read_text(encoding="utf-8"))


def held_out_cells(
    pairs: Sequence[LabelledPair], manifest: dict[str, object] | None
) -> dict[str, str]:
    source = manifest.get("source") if manifest else None
    if not isinstance(source, dict) or "test_personas" not in source:
        return {}
    personas = frozenset(str(p) for p in source["test_personas"])  # type: ignore[union-attr]
    templates = frozenset(str(t) for t in source["test_templates"])  # type: ignore[union-attr]
    return {
        p.pair_id: held_out_cell(p, test_personas=personas, test_templates=templates) for p in pairs
    }


def _data_block(
    pairs_file: Path, found: tuple[Path, dict[str, object]] | None
) -> dict[str, object]:
    block: dict[str, object] = {
        "pairs_file": _display(pairs_file),
        "pairs_sha256": file_sha256(pairs_file),
    }
    if found is not None:
        path, manifest = found
        block |= {
            "pairs_manifest": _display(path),
            "pairs_manifest_sha256": file_sha256(path),
            "generator": manifest.get("generator"),
            "pair_seed": manifest.get("seed"),
            "negative_ratio": manifest.get("negative_ratio"),
            "source": manifest.get("source"),
        }
    return block


def _report(config: dict[str, object], result: dict[str, object], spec: LinkerSpec) -> str:
    lines = [f"# Link pairs: {config['track']} · {config['linker']} · split {config['split']}", ""]
    if spec.plumbing_only:
        lines += [f"**{PLUMBING_NOTE}**", ""]
    data = config["data"]
    assert isinstance(data, dict)
    lines += [
        f"Pairs: {config['pair_count']} from `{data['pairs_file']}` "
        f"(sha256 {str(data['pairs_sha256'])[:12]}…). Query: the {config['new_memory']} "
        "is the new memory, the other the only candidate; ids are opaque. "
        f"Abstentions (invalid output): {result['abstentions']}.",
        "",
    ]
    transfer = config.get("transfer")
    if isinstance(transfer, dict):
        lines += [
            f"**Transfer run (H4):** a model trained on `{transfer['train_pairs_file']}` scored "
            "on another track's test pairs; no evaluated text pair equals a training one, "
            f"{transfer['pairs_sharing_a_text_with_train']} pairs share one text with training.",
            "",
        ]
    lines += _training_lines(spec)
    cost = result["cost"]
    assert isinstance(cost, dict)
    lines += [
        f"Cost: {_seconds(cost['wall_seconds_per_call'])} s wall and "
        f"{_seconds(cost['cpu_seconds_per_call'])} s "
        f"process CPU per linker call ({result['linker_calls']} calls, {result['llm_calls']} "
        "LLM calls).",
        "",
        "| stratum | n | tp | fp | fn | tn | precision | recall | F1 | typed F1 |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    rows: list[tuple[str, dict[str, object]]] = [("overall", result["overall"])]  # type: ignore[list-item]
    for block, label in (("by_provenance", "provenance"), ("by_held_out", "held_out")):
        table = result[block]
        assert isinstance(table, dict)
        rows += [(f"{label}={k}", v) for k, v in table.items()]
    for name, cell in rows:
        lines.append(
            f"| {name} | {cell['n']} | {cell['tp']} | {cell['fp']} | {cell['fn']} | {cell['tn']} "
            f"| {_fmt(cell['precision'])} | {_fmt(cell['recall'])} | {_fmt(cell['f1'])} "
            f"| {_fmt(cell['typed_f1'])} |"
        )
    lines += ["", "False positives by negative kind:", ""]
    negatives = result["false_positives_by_negative_kind"]
    assert isinstance(negatives, dict)
    for kind, cell in negatives.items():
        lines.append(f"- {kind}: {cell['fp']}/{cell['n']} ({_fmt(cell['fp_rate'])})")
    lines += ["", "Recall by gold link type (tp / tp+fn; * = no train pair of this type):", ""]
    by_type = result["by_gold_link_type"]
    assert isinstance(by_type, dict)
    for link_type, cell in by_type.items():
        unseen = "*" if cell["seen_in_train"] is False else ""
        lines.append(
            f"- {link_type}{unseen}: {cell['tp']}/{cell['tp'] + cell['fn']} "
            f"({_fmt(cell['recall'])})"
        )
    lines += [
        "",
        "Precision and F1 are n/a in a stratum without gold negatives (every RULE pair is "
        "a positive); read such a stratum for recall. held_out=both is the strict test "
        "cell (persona and template unseen). "
        + _typed_note(config, spec)
        + "Synthetic v0 data: harness numbers on a small regular track, not a headline "
        "result; a number is citable only from a run on a committed tree.",
        "",
    ]
    return "\n".join(lines)


def _training_lines(spec: LinkerSpec) -> list[str]:
    """A trained linker's training record, so a report can cite this folder for it (I8)."""
    training = spec.details.get("training")
    if not isinstance(training, dict):
        return []
    lines = [
        f"Model: `{spec.details.get('base_model')}`, seed {spec.details.get('seed')}, "
        f"threshold {spec.details.get('threshold')} ({spec.details.get('threshold_source')}), "
        f"chosen epoch {spec.details.get('chosen_epoch')}; fitted on "
        f"{training.get('fit_examples')} pairs, validated on "
        f"{training.get('validation_examples')} pairs of personas "
        f"{spec.details.get('validation_personas')}; training took "
        f"{training.get('train_seconds')} s wall.",
    ]
    validation = training.get("validation")
    if isinstance(validation, dict):
        lines.append(
            f"Validation at the chosen epoch: F1 {_fmt(validation['f1'])}, precision "
            f"{_fmt(validation['precision'])}, recall {_fmt(validation['recall'])}."
        )
    history = training.get("history")
    if isinstance(history, list) and history and "f1" in history[0]:
        steps = "; ".join(
            f"epoch {h['epoch']}: F1 {_fmt(h['f1'])} at threshold {h['threshold']}" for h in history
        )
        lines.append(f"Validation per epoch (best threshold each): {steps}.")
    return [*lines, ""]


def _seconds(value: object) -> str:
    return "n/a" if value is None else f"{float(str(value)):.6f}"


def _typed_note(config: dict[str, object], spec: LinkerSpec) -> str:
    if spec.typed:
        return ""
    if config.get("transfer"):
        return (
            "Typed metrics are n/a: this track's link types are outside the model's label space. "
        )
    return "Typed metrics are n/a: this linker proposes one fixed type. "


def _display(path: Path) -> str:
    resolved = path.resolve()
    return (
        resolved.relative_to(REPO_ROOT).as_posix()
        if resolved.is_relative_to(REPO_ROOT)
        else resolved.as_posix()
    )


def _fmt(value: object) -> str:
    return "n/a" if value is None else f"{float(str(value)):.3f}"


def run(
    spec: LinkerSpec,
    pairs_file: Path,
    *,
    split: str = "test",
    new: NewSide = "dependent",
    seed: int = DEFAULT_RUN_SEED,
    results_root: Path = RESULTS_DIR,
    transfer: bool = False,
) -> Path:
    every_pair = list(read_pairs(pairs_file))
    pairs = select(every_pair, split)
    tracks = sorted({p.track for p in pairs})
    if len(tracks) != 1:
        raise ValueError(f"expected one track in {pairs_file} for split {split}, found {tracks}")
    pairs_sha = file_sha256(pairs_file)
    transfer_record: dict[str, object] | None = None
    train_link_types = frozenset(
        p.link_type for p in every_pair if p.split is Split.TRAIN and p.link_type is not None
    )
    if transfer:
        if spec.train_pairs_sha256 is None:
            raise ValueError("--transfer applies to a trained linker only")
        transfer_record, train_link_types = transfer_check(spec, pairs, pairs_sha)
        if not transfer_record["gold_types_in_label_space"]:
            spec = replace(spec, typed=False)  # its types cannot name this domain's links
    elif spec.train_pairs_sha256 is not None and split != Split.TEST.value:
        raise ValueError(
            f"{spec.name} is scored on test pairs only; split {split!r} includes pairs it "
            "was trained or validated on"
        )
    elif spec.train_pairs_sha256 is not None and spec.train_pairs_sha256 != pairs_sha:
        raise ValueError(
            f"{spec.name} was trained on pair file {spec.train_pairs_sha256[:12]}, "
            f"not on {pairs_file} ({pairs_sha[:12]}): its split is not this file's "
            "(use --transfer for another track's test pairs)"
        )
    if spec.fitted_link_types is not None:
        train_link_types = spec.fitted_link_types
    found = pair_manifest(pairs_file)
    cells = held_out_cells(pairs, found[1] if found else None)
    started, cpu_started = time.perf_counter(), time.process_time()
    predictions = asyncio.run(predict_all(spec.linker, pairs, new, seed=seed, cells=cells))
    elapsed, cpu = time.perf_counter() - started, time.process_time() - cpu_started
    sha = git_short_sha()
    run_dir = run_dir_for(results_root, tracks[0], spec.name, sha)
    run_dir.mkdir(parents=True)
    data = _data_block(pairs_file, found)
    config: dict[str, object] = {
        "suite": "linkpairs",
        "track": tracks[0],
        "linker": spec.name,
        "linker_details": spec.details,
        "plumbing_only": spec.plumbing_only,
        "typed": spec.typed,
        "models": spec.models,
        "prompt_versions": spec.prompt_versions,
        "seeds": {"pair_seed": data.get("pair_seed"), "run_seed": seed},
        "split": split,
        "new_memory": new,
        "data": data,
        "pair_count": len(pairs),
        "provenances": sorted({p.provenance.value for p in pairs}),
        "transfer": transfer_record,
        "git_sha": sha,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "run_at": datetime.now(tz=UTC).isoformat(),
    }
    result = metrics(predictions, typed=spec.typed, train_link_types=train_link_types)
    result["linker_calls"] = len(predictions)
    result["llm_calls"] = len(predictions) if spec.calls_llm else 0
    result["elapsed_seconds"] = round(elapsed, 3)
    result["cost"] = {
        "wall_seconds_per_call": round(elapsed / len(predictions), 6) if predictions else None,
        "cpu_seconds_per_call": round(cpu / len(predictions), 6) if predictions else None,
        "cpu_seconds": round(cpu, 3),
        "processor": platform.processor(),
        "note": "process CPU time over all threads; an LLM call's provider-side cost is not in it",
    }
    if spec.plumbing_only:
        result["note"] = PLUMBING_NOTE
    (run_dir / "config.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    (run_dir / "metrics.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (run_dir / "predictions.jsonl").write_text(
        "".join(json.dumps(asdict(p), sort_keys=True) + "\n" for p in predictions),
        encoding="utf-8",
    )
    (run_dir / "report.md").write_text(_report(config, result, spec), encoding="utf-8")
    return run_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score a linker on a C5 pair file.")
    parser.add_argument("--linker", choices=("rule", "fake_llm", "llm", "trained"), required=True)
    parser.add_argument("--model", type=Path, help="model folder for --linker trained")
    parser.add_argument("--pairs", type=Path, default=pairs_path())
    parser.add_argument("--split", choices=("train", "test", "all"), default="test")
    parser.add_argument("--new", choices=("dependent", "parent"), default="dependent")
    parser.add_argument("--seed", type=int, default=DEFAULT_RUN_SEED, help="opaque id coin")
    parser.add_argument(
        "--transfer", action="store_true", help="trained linker on another track's test pairs"
    )
    args = parser.parse_args(argv)
    pairs = select(list(read_pairs(args.pairs)), args.split)
    if args.linker == "rule":
        spec = rule_linker()
    elif args.linker == "fake_llm":
        spec = fake_llm_linker(len(pairs))
    elif args.linker == "llm":
        domains = sorted({p.domain for p in pairs})
        if len(domains) != 1:
            raise SystemExit(f"expected one domain in {args.pairs}, found {domains}")
        spec = llm_linker(domains[0])
    else:
        spec = trained_linker(args.model)
    run_dir = run(
        spec, args.pairs, split=args.split, new=args.new, seed=args.seed, transfer=args.transfer
    )
    print(f"wrote {run_dir}")
    print((run_dir / "report.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
