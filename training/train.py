"""The trained link finder's training loop (roadmap Phase 4, "[human] Training loop and
evaluation"; ADR-0009, ADR-0094, ADR-0125, ADR-0126).

    uv run python -m training.train --validation-persona p2_harsh --seed 20261031

Written by the collaborator at the author's request on 2026-10-31. The data view
(`training_examples`, `label_space`) fixes which pairs a run may see; `train`
fine-tunes a pretrained encoder (default answerdotai/ModernBERT-base) as a pair
classifier over the label space on CPU, picks the epoch and the decision threshold on
held-back train personas, and saves weights, tokenizer and `ripple_artifact.json` in
one folder. The served linker is ripple.linking.trained.TrainedLinker, re-exported here.
The base model "scratch:tiny" is a randomly initialised two-layer encoder with a word
tokenizer built from the training texts: the offline test model, and a "no pretraining"
ablation, never a link finder anyone should serve.
"""

import argparse
import copy
import json
import platform
import random
import sys
import time
from collections import Counter
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from bench.domains import registry_for
from bench.linkpairs import LabelledPair, PairMemory, Provenance, Split, read_pairs

from ripple.core.links import LinkTypeRegistry
from ripple.linking.trained import (
    ARTIFACT_FILE,
    ARTIFACT_FORMAT,
    ARTIFACT_VERSION,
    DEFAULT_THRESHOLD,
    NO_LINK,
    TrainedArtifact,
    TrainedLinker,
    decide,
    memory_text,
)
from training.jobs_pairs import REPO_ROOT, file_sha256, pairs_path

__all__ = [
    "NO_LINK",
    "TrainConfig",
    "TrainedArtifact",
    "TrainedLinker",
    "TrainingExample",
    "label_space",
    "train",
    "training_examples",
]

DEFAULT_BASE_MODEL = "answerdotai/ModernBERT-base"
SCRATCH_TINY = "scratch:tiny"
ARTIFACTS_DIR = REPO_ROOT / "training" / "artifacts"
# Grid for the decision threshold; ties go to the value nearest the default 0.5.
THRESHOLD_GRID = tuple(round(0.05 * step, 2) for step in range(1, 20))


@dataclass(frozen=True)
class TrainConfig:
    pairs_file: Path
    output_dir: Path
    base_model: str  # ADR-0125: answerdotai/ModernBERT-base; SCRATCH_TINY for tests
    base_model_revision: str | None = None  # a hub commit to pin; None takes the cached/latest
    seed: int = 20261031
    epochs: int = 3
    learning_rate: float = 2e-5
    batch_size: int = 16
    max_length: int = 128
    domain: str = "jobs"  # whose link-type registry is the label space
    weight_decay: float = 0.01
    warmup_ratio: float = 0.1
    # SCENARIO and RULE are the generated labels; HUMAN pairs are the gold set and stay
    # out of training unless a run says otherwise (ADR-0094).
    # Train personas held back for epoch and threshold choice (recipe step 4): validation
    # is split by persona like the test set, never by item.
    validation_personas: frozenset[str] = frozenset()
    provenances: frozenset[Provenance] = field(
        default_factory=lambda: frozenset({Provenance.SCENARIO, Provenance.RULE})
    )


@dataclass(frozen=True)
class TrainingExample:
    pair_id: str
    parent: PairMemory
    dependent: PairMemory
    label: str  # a link type or NO_LINK
    persona: str


def label_space(registry: LinkTypeRegistry) -> list[str]:
    """Every registered link type plus NO_LINK, sorted: the classifier's output layer."""
    return [*sorted(registry.known_types()), NO_LINK]


def training_examples(
    pairs: Sequence[LabelledPair], config: TrainConfig, registry: LinkTypeRegistry
) -> list[TrainingExample]:
    """Train-split pairs of the chosen provenances, in pair_id order. Refuses a pair whose
    link type the registry does not know: the output layer could not represent it."""
    known = registry.known_types()
    examples: list[TrainingExample] = []
    for pair in sorted(pairs, key=lambda p: p.pair_id):
        if pair.split is not Split.TRAIN or pair.provenance not in config.provenances:
            continue
        if pair.link_type is not None and pair.link_type not in known:
            raise ValueError(f"{pair.pair_id}: link type {pair.link_type!r} is not registered")
        examples.append(
            TrainingExample(
                pair.pair_id,
                pair.parent,
                pair.dependent,
                pair.link_type or NO_LINK,
                pair.persona,
            )
        )
    if not examples:
        # A test-only file (the finance track, H4) or a provenance filter that matches
        # nothing would otherwise train on nothing without a word.
        raise ValueError("no train-split pairs of the chosen provenances; nothing to train on")
    return examples


# ---- validation -----------------------------------------------------------------------


@dataclass(frozen=True)
class ValidationScore:
    f1: float
    threshold: float
    precision: float | None
    recall: float | None


def link_f1(
    linked: Sequence[bool], gold: Sequence[bool]
) -> tuple[float, float | None, float | None]:
    """Untyped F1 (link or not), with precision and recall (None when undefined)."""
    tp = sum(p and g for p, g in zip(linked, gold, strict=True))
    fp = sum(p and not g for p, g in zip(linked, gold, strict=True))
    fn = sum(g and not p for p, g in zip(linked, gold, strict=True))
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = 2 * tp / (2 * tp + fp + fn) if tp + fp + fn else 0.0
    return f1, precision, recall


def choose_threshold(
    forward: Sequence[Sequence[float]],
    backward: Sequence[Sequence[float]],
    gold: Sequence[bool],
    labels: Sequence[str],
) -> ValidationScore:
    """The grid threshold with the best untyped F1 when pairs are decided exactly as the
    served linker decides them (`decide`: forward edge, more probable than the reverse)."""
    best: ValidationScore | None = None
    for threshold in sorted(THRESHOLD_GRID, key=lambda t: (abs(t - DEFAULT_THRESHOLD), t)):
        linked = [
            (d := decide(f, b, labels, threshold)) is not None and d.direction == "forward"
            for f, b in zip(forward, backward, strict=True)
        ]
        f1, precision, recall = link_f1(linked, gold)
        if best is None or f1 > best.f1:
            best = ValidationScore(f1, threshold, precision, recall)
    assert best is not None  # the grid is not empty
    return best


# ---- the loop -------------------------------------------------------------------------


def _scratch_model(config: TrainConfig, labels: Sequence[str], texts: Sequence[str]) -> Any:
    """SCRATCH_TINY: a word-level tokenizer over the training texts and a randomly
    initialised two-layer ModernBERT. No download; meaningful only as plumbing or as a
    no-pretraining ablation."""
    from tokenizers import Tokenizer, models, pre_tokenizers, processors, trainers
    from transformers import (
        ModernBertConfig,
        ModernBertForSequenceClassification,
        PreTrainedTokenizerFast,
    )

    specials = ["[PAD]", "[UNK]", "[CLS]", "[SEP]", "[MASK]"]
    word_tokenizer = Tokenizer(models.WordLevel(unk_token="[UNK]"))
    word_tokenizer.pre_tokenizer = pre_tokenizers.Whitespace()
    word_tokenizer.train_from_iterator(texts, trainers.WordLevelTrainer(special_tokens=specials))
    word_tokenizer.post_processor = processors.TemplateProcessing(
        single="[CLS] $A [SEP]",
        pair="[CLS] $A [SEP] $B:1 [SEP]:1",
        special_tokens=[("[CLS]", 2), ("[SEP]", 3)],
    )
    tokenizer = PreTrainedTokenizerFast(
        tokenizer_object=word_tokenizer,
        unk_token="[UNK]",
        pad_token="[PAD]",
        cls_token="[CLS]",
        sep_token="[SEP]",
        mask_token="[MASK]",
    )
    model_config: Any = ModernBertConfig(  # num_labels and friends reach PretrainedConfig
        vocab_size=tokenizer.vocab_size,
        hidden_size=32,
        intermediate_size=64,
        num_hidden_layers=2,
        num_attention_heads=2,
        max_position_embeddings=max(256, config.max_length),
        pad_token_id=0,
        cls_token_id=2,
        sep_token_id=3,
        bos_token_id=2,
        eos_token_id=3,
        **_label_kwargs(labels),
    )
    return tokenizer, ModernBertForSequenceClassification(model_config)


def _label_kwargs(labels: Sequence[str]) -> dict[str, Any]:
    return {
        "num_labels": len(labels),
        "id2label": dict(enumerate(labels)),
        "label2id": {label: i for i, label in enumerate(labels)},
    }


def _pretrained_model(config: TrainConfig, labels: Sequence[str]) -> Any:
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    revision = config.base_model_revision
    tokenizer = AutoTokenizer.from_pretrained(config.base_model, revision=revision)
    model = AutoModelForSequenceClassification.from_pretrained(
        config.base_model, revision=revision, **_label_kwargs(labels)
    )
    return tokenizer, model


def _loaded_revision(config: TrainConfig) -> str | None:
    """The hub commit the weights came from: the cache keeps each download under
    snapshots/<commit>/. None for a local folder or the scratch model."""
    if config.base_model == SCRATCH_TINY or Path(config.base_model).is_dir():
        return None
    from transformers.utils.hub import cached_file

    config_file = cached_file(config.base_model, "config.json", revision=config.base_model_revision)
    parts = Path(str(config_file)).parts
    return parts[-2] if len(parts) > 2 and parts[-3] == "snapshots" else None


def _class_weights(examples: Sequence[TrainingExample], labels: Sequence[str]) -> list[float]:
    """Balanced weights over the classes present ("none" is about three quarters of train);
    an absent class keeps weight 1, it is never a target anyway."""
    counts = Counter(e.label for e in examples)
    present = [label for label in labels if counts[label]]
    return [
        len(examples) / (len(present) * counts[label]) if counts[label] else 1.0 for label in labels
    ]


def train(config: TrainConfig, examples: Sequence[TrainingExample]) -> TrainedArtifact:
    """Fine-tune `config.base_model` as a pair classifier over `label_space` and save
    it under `config.output_dir`. Deterministic for a fixed seed on one machine."""
    import torch
    import transformers

    transformers.utils.logging.disable_progress_bar()
    transformers.utils.logging.set_verbosity_error()
    labels = label_space(registry_for(config.domain))
    unknown = {e.label for e in examples} - set(labels)
    if unknown:
        raise ValueError(f"labels outside the {config.domain} label space: {sorted(unknown)}")
    fit = [e for e in examples if e.persona not in config.validation_personas]
    held = [e for e in examples if e.persona in config.validation_personas]
    if config.validation_personas and not held:
        raise ValueError(
            f"no examples for validation personas {sorted(config.validation_personas)}"
        )
    if held and all(e.label == NO_LINK for e in held):
        raise ValueError("validation personas have no gold link; F1 cannot choose a threshold")
    if not fit:
        raise ValueError("every example is a validation persona's; nothing left to fit")

    previous = (
        torch.are_deterministic_algorithms_enabled(),
        torch.is_deterministic_algorithms_warn_only_enabled(),
    )
    torch.use_deterministic_algorithms(True, warn_only=True)
    try:
        return _fit_and_save(config, labels, fit, held)
    finally:
        # A process-wide switch: leave it as the caller had it.
        torch.use_deterministic_algorithms(previous[0], warn_only=previous[1])


def _fit_and_save(
    config: TrainConfig,
    labels: list[str],
    fit: list[TrainingExample],
    held: list[TrainingExample],
) -> TrainedArtifact:
    import torch
    import transformers

    random.seed(config.seed)
    torch.manual_seed(config.seed)
    started = time.perf_counter()

    def encode(batch: Sequence[TrainingExample]) -> Any:
        return tokenizer(
            [memory_text(e.parent) for e in batch],
            [memory_text(e.dependent) for e in batch],
            padding=True,
            truncation=True,
            max_length=config.max_length,
            return_tensors="pt",
        )

    if config.base_model == SCRATCH_TINY:
        texts = sorted({memory_text(m) for e in fit for m in (e.parent, e.dependent)})
        tokenizer, model = _scratch_model(config, labels, texts)
    else:
        tokenizer, model = _pretrained_model(config, labels)
    revision = _loaded_revision(config)
    label_index = {label: i for i, label in enumerate(labels)}
    loss_fn = torch.nn.CrossEntropyLoss(
        weight=torch.tensor(_class_weights(fit, labels), dtype=torch.float32)
    )
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay
    )
    steps_per_epoch = -(-len(fit) // config.batch_size)
    total_steps = max(1, steps_per_epoch * config.epochs)
    warmup = int(total_steps * config.warmup_ratio)

    def schedule(step: int) -> float:  # linear warmup, then linear decay to zero
        if step < warmup:
            return (step + 1) / (warmup + 1)
        return max(0.0, (total_steps - step) / max(1, total_steps - warmup))

    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, schedule)
    order_rng = torch.Generator().manual_seed(config.seed)

    def score(batch_pairs: Sequence[tuple[PairMemory, PairMemory]]) -> list[list[float]]:
        model.eval()
        rows: list[list[float]] = []
        with torch.inference_mode():
            for start in range(0, len(batch_pairs), 32):
                chunk = batch_pairs[start : start + 32]
                encoded = tokenizer(
                    [memory_text(p) for p, _ in chunk],
                    [memory_text(d) for _, d in chunk],
                    padding=True,
                    truncation=True,
                    max_length=config.max_length,
                    return_tensors="pt",
                )
                rows.extend(torch.softmax(model(**encoded).logits, dim=-1).tolist())
        return rows

    history: list[dict[str, object]] = []
    best_state: dict[str, Any] | None = None
    best_score: ValidationScore | None = None
    best_epoch = config.epochs
    for epoch in range(1, config.epochs + 1):
        model.train()
        losses: list[float] = []
        for batch_ids in torch.randperm(len(fit), generator=order_rng).split(config.batch_size):
            batch = [fit[i] for i in batch_ids.tolist()]
            targets = torch.tensor([label_index[e.label] for e in batch])
            loss = loss_fn(model(**encode(batch)).logits, targets)
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            losses.append(float(loss.item()))
        entry: dict[str, object] = {"epoch": epoch, "train_loss": sum(losses) / len(losses)}
        if held:
            forward = score([(e.parent, e.dependent) for e in held])
            backward = score([(e.dependent, e.parent) for e in held])
            result = choose_threshold(forward, backward, [e.label != NO_LINK for e in held], labels)
            entry.update(asdict(result))
            # Strictly better only: ties keep the earlier, less fitted epoch.
            if best_score is None or result.f1 > best_score.f1:
                best_score, best_epoch = result, epoch
                best_state = copy.deepcopy(model.state_dict())
        history.append(entry)
    if best_state is not None:
        model.load_state_dict(best_state)
    seconds = time.perf_counter() - started

    threshold = best_score.threshold if best_score is not None else DEFAULT_THRESHOLD
    output = config.output_dir
    output.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(output)
    tokenizer.save_pretrained(output)
    train_sha = file_sha256(config.pairs_file)
    manifest: dict[str, object] = {
        "format": ARTIFACT_FORMAT,
        "version": ARTIFACT_VERSION,
        "label_space": labels,
        "train_pairs_file": _display(config.pairs_file),
        "train_pairs_sha256": train_sha,
        "seed": config.seed,
        "threshold": threshold,
        "threshold_source": "validation personas" if best_score else "default (no validation)",
        "base_model": config.base_model,
        "base_model_revision": revision,
        "max_length": config.max_length,
        "text_template": "[kind] content || subject attribute value (pair: parent, dependent)",
        "train_config": _config_dict(config),
        "training": {
            "fit_examples": len(fit),
            "validation_examples": len(held),
            "fit_label_counts": dict(sorted(Counter(e.label for e in fit).items())),
            "validation_label_counts": dict(sorted(Counter(e.label for e in held).items())),
            "class_weights": dict(zip(labels, _class_weights(fit, labels), strict=True)),
            "chosen_epoch": best_epoch,
            "validation": None if best_score is None else asdict(best_score),
            "history": history,
            "train_seconds": round(seconds, 1),
            "torch_threads": torch.get_num_threads(),
        },
        "versions": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "transformers": transformers.__version__,
            "platform": platform.platform(),
            "processor": platform.processor(),
        },
    }
    (output / ARTIFACT_FILE).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return TrainedArtifact.read(output)


def _display(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def _config_dict(config: TrainConfig) -> dict[str, object]:
    return {
        "pairs_file": _display(config.pairs_file),
        "output_dir": _display(config.output_dir),
        "base_model": config.base_model,
        "base_model_revision": config.base_model_revision,
        "seed": config.seed,
        "epochs": config.epochs,
        "learning_rate": config.learning_rate,
        "batch_size": config.batch_size,
        "max_length": config.max_length,
        "domain": config.domain,
        "weight_decay": config.weight_decay,
        "warmup_ratio": config.warmup_ratio,
        "validation_personas": sorted(config.validation_personas),
        "provenances": sorted(p.value for p in config.provenances),
    }


def _slug(base_model: str) -> str:
    return base_model.rsplit("/", 1)[-1].replace(":", "-").lower()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fine-tune the trained link finder.")
    parser.add_argument("--pairs", type=Path, default=pairs_path())
    parser.add_argument("--base-model", default=DEFAULT_BASE_MODEL)
    parser.add_argument("--base-model-revision", help="hub commit to pin (recorded either way)")
    parser.add_argument("--seed", type=int, default=20261031)
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--learning-rate", type=float, default=5e-5)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--max-length", type=int, default=128)
    parser.add_argument("--domain", default="jobs")
    parser.add_argument(
        "--validation-persona", action="append", default=[], help="repeatable; a train persona"
    )
    parser.add_argument(
        "--output-dir", type=Path, help="default training/artifacts/<model>_seed<n>"
    )
    args = parser.parse_args(argv)
    output_dir = args.output_dir or ARTIFACTS_DIR / f"{_slug(args.base_model)}_seed{args.seed}"
    if (output_dir / ARTIFACT_FILE).exists():
        raise SystemExit(f"{output_dir} already holds a trained linker; choose another folder")
    config = TrainConfig(
        pairs_file=args.pairs,
        output_dir=output_dir,
        base_model=args.base_model,
        base_model_revision=args.base_model_revision,
        seed=args.seed,
        epochs=args.epochs,
        learning_rate=args.learning_rate,
        batch_size=args.batch_size,
        max_length=args.max_length,
        domain=args.domain,
        validation_personas=frozenset(args.validation_persona),
    )
    examples = training_examples(list(read_pairs(args.pairs)), config, registry_for(args.domain))
    artifact = train(config, examples)
    training = artifact.manifest["training"]
    print(f"wrote {artifact.model_dir}")
    print(
        f"threshold {artifact.threshold} ({artifact.manifest['threshold_source']}), "
        f"epoch {training['chosen_epoch']}, validation {training['validation']}, "
        f"{training['train_seconds']} s"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
