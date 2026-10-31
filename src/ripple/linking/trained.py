"""TrainedLinker: the fine-tuned pair classifier behind the Linker protocol (ADR-0009,
ADR-0125, ADR-0126).

A model folder holds Hugging Face weights and tokenizer plus `ripple_artifact.json`
(label space, train pair file sha256, seed, validated threshold, base model). Both
orientations of every (memory, candidate) pair are scored in one batch; a candidate
gets at most one edge, the more probable direction, and only when its best link class
clears the threshold. torch and transformers are imported only when a model is
loaded, so selecting the LLM linker (the default, ADR-0128) imports neither.

Training lives in training/train.py and encodes memories with `memory_text` from here,
so the text a model was trained on and the text it is served are the same function.
"""

import asyncio
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Protocol

from ripple.core.errors import ConfigurationError
from ripple.core.linking import Linker, LinkProposal
from ripple.core.links import LinkTypeRegistry
from ripple.core.models import LinkCreator, Memory, StructuredFact

NO_LINK = "none"
ARTIFACT_FILE = "ripple_artifact.json"
ARTIFACT_FORMAT = "ripple-trained-linker"
ARTIFACT_VERSION = 1
DEFAULT_THRESHOLD = 0.5
LINKER_VAR = "RIPPLE_LINKER"
MODEL_VAR = "RIPPLE_TRAINED_LINKER_MODEL"

# (parent text, dependent text) -> one probability row per pair, in label-space order.
PairScorer = Callable[[Sequence[tuple[str, str]]], Sequence[Sequence[float]]]


class TextMemory(Protocol):
    """What the encoder reads of a memory: a store Memory and a C5 PairMemory both fit."""

    @property
    def kind(self) -> str: ...
    @property
    def content(self) -> str: ...
    @property
    def structured(self) -> StructuredFact | None: ...


def memory_text(memory: TextMemory) -> str:
    """One fixed template for both sides of a pair; the structure is spelled out because
    the rule-derived labels hang on it (subject, attribute, value)."""
    text = f"[{memory.kind}] {memory.content}"
    if memory.structured is not None:
        fact = memory.structured
        text += f" || {fact.subject} {fact.attribute} {fact.value}"
    return text


@dataclass(frozen=True)
class Decision:
    direction: Literal["forward", "backward"]
    link_type: str
    probability: float


def best_link(row: Sequence[float], labels: Sequence[str]) -> tuple[str, float]:
    """The most probable class other than NO_LINK, and its probability."""
    scored = [(p, label) for label, p in zip(labels, row, strict=True) if label != NO_LINK]
    probability, label = max(scored)
    return label, float(probability)


def decide(
    forward: Sequence[float], backward: Sequence[float], labels: Sequence[str], threshold: float
) -> Decision | None:
    """At most one edge per pair: the more probable direction, if it clears `threshold`.
    Proposing both would write a two-memory cycle, which no dependency can be. An exact
    tie proposes nothing, so the answer never depends on which memory is the new one."""
    forward_type, forward_p = best_link(forward, labels)
    backward_type, backward_p = best_link(backward, labels)
    if forward_p == backward_p:
        return None
    if forward_p > backward_p:
        decision = Decision("forward", forward_type, forward_p)
    else:
        decision = Decision("backward", backward_type, backward_p)
    return decision if decision.probability >= threshold else None


@dataclass(frozen=True)
class TrainedArtifact:
    model_dir: Path  # weights, tokenizer and ARTIFACT_FILE, all in one folder
    label_space: tuple[str, ...]
    train_pairs_sha256: str
    seed: int
    threshold: float = DEFAULT_THRESHOLD
    base_model: str = ""
    base_model_revision: str | None = None
    max_length: int = 128
    manifest: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False)

    @classmethod
    def read(cls, model_dir: Path) -> "TrainedArtifact":
        path = model_dir / ARTIFACT_FILE
        if not path.is_file():
            raise ConfigurationError(f"{model_dir} has no {ARTIFACT_FILE}: not a trained linker")
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except ValueError as exc:
            raise ConfigurationError(f"{path}: not JSON") from exc
        if manifest.get("format") != ARTIFACT_FORMAT or manifest.get("version") != ARTIFACT_VERSION:
            raise ConfigurationError(f"{path}: unknown artifact format or version")
        try:
            labels = tuple(str(label) for label in manifest["label_space"])
            artifact = cls(
                model_dir=model_dir,
                label_space=labels,
                train_pairs_sha256=str(manifest["train_pairs_sha256"]),
                seed=int(manifest["seed"]),
                threshold=float(manifest["threshold"]),
                base_model=str(manifest["base_model"]),
                base_model_revision=manifest.get("base_model_revision"),
                max_length=int(manifest["max_length"]),
                manifest=manifest,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ConfigurationError(f"{path}: missing or malformed field {exc}") from exc
        if len(labels) < 2 or labels[-1] != NO_LINK or NO_LINK in labels[:-1]:
            raise ConfigurationError(
                f"{path}: label space must be link types followed by {NO_LINK!r}"
            )
        return artifact


class HuggingFaceScorer:
    """Batched softmax over a saved sequence-classification model, CPU, no gradients."""

    def __init__(self, artifact: TrainedArtifact, *, batch_size: int = 32) -> None:
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        self._torch = torch
        self._tokenizer: Any = AutoTokenizer.from_pretrained(
            artifact.model_dir, local_files_only=True
        )
        self._model: Any = AutoModelForSequenceClassification.from_pretrained(
            artifact.model_dir, local_files_only=True
        )
        self._model.eval()
        id2label = {int(k): v for k, v in self._model.config.id2label.items()}
        if [id2label[i] for i in range(len(id2label))] != list(artifact.label_space):
            raise ConfigurationError(
                f"{artifact.model_dir}: the model's labels differ from the artifact's label space"
            )
        self._max_length = artifact.max_length
        self._batch_size = batch_size

    def __call__(self, pairs: Sequence[tuple[str, str]]) -> list[list[float]]:
        rows: list[list[float]] = []
        with self._torch.inference_mode():
            for start in range(0, len(pairs), self._batch_size):
                batch = pairs[start : start + self._batch_size]
                encoded = self._tokenizer(
                    [parent for parent, _ in batch],
                    [dependent for _, dependent in batch],
                    padding=True,
                    truncation=True,
                    max_length=self._max_length,
                    return_tensors="pt",
                )
                logits = self._model(**encoded).logits
                rows.extend(self._torch.softmax(logits, dim=-1).tolist())
        return rows


class TrainedLinker:
    """The trained model behind the Linker protocol, created_by MODEL."""

    def __init__(
        self, artifact: TrainedArtifact, scorer: PairScorer, *, threshold: float | None = None
    ) -> None:
        self.artifact = artifact
        self.threshold = artifact.threshold if threshold is None else threshold
        if not 0.0 <= self.threshold <= 1.0:
            raise ConfigurationError("threshold must be in [0, 1]")
        self._scorer = scorer

    @classmethod
    def load(
        cls,
        model_dir: Path,
        *,
        threshold: float | None = None,
        registry: LinkTypeRegistry | None = None,
    ) -> "TrainedLinker":
        """`threshold` None uses the one fixed on the validation persona at training time.
        With a registry, every type the model can propose must be registered there, or
        the links it proposes could not be stamped with a class."""
        artifact = TrainedArtifact.read(model_dir)
        if registry is not None:
            unknown = set(artifact.label_space[:-1]) - registry.known_types()
            if unknown:
                raise ConfigurationError(
                    f"{model_dir} proposes link types this registry lacks: {sorted(unknown)}"
                )
        return cls(artifact, HuggingFaceScorer(artifact), threshold=threshold)

    async def propose(self, memory: Memory, candidates: Sequence[Memory]) -> list[LinkProposal]:
        others = [c for c in candidates if c.id != memory.id and c.user_id == memory.user_id]
        if not others:
            return []
        new_text = memory_text(memory)
        pairs: list[tuple[str, str]] = []
        for candidate in others:
            candidate_text = memory_text(candidate)
            pairs.append((candidate_text, new_text))  # candidate -> memory
            pairs.append((new_text, candidate_text))  # memory -> candidate
        # Model inference is CPU-bound; keep it off the event loop.
        rows = await asyncio.to_thread(self._scorer, pairs)
        labels = self.artifact.label_space
        proposals: list[LinkProposal] = []
        for index, candidate in enumerate(others):
            decision = decide(rows[2 * index], rows[2 * index + 1], labels, self.threshold)
            if decision is None:
                continue
            parent, dependent = (
                (candidate, memory) if decision.direction == "forward" else (memory, candidate)
            )
            proposals.append(
                LinkProposal(
                    parent_id=parent.id,
                    dependent_id=dependent.id,
                    link_type=decision.link_type,
                    confidence=min(1.0, max(0.0, decision.probability)),
                    reason=f"trained model p={decision.probability:.2f}",
                    created_by=LinkCreator.MODEL,
                )
            )
        return proposals


def select_linker(env: Mapping[str, str], *, llm: Linker, registry: LinkTypeRegistry) -> Linker:
    """The write-path linker from configuration (ADR-0128). The LLM linker stays the
    default: ADR-0009 makes the trained one default only once it meets H3, which cannot
    be judged until the LLM linker has been scored with a real key."""
    choice = env.get(LINKER_VAR, "llm").strip().lower()
    if choice == "llm":
        return llm
    if choice == "trained":
        model_dir = env.get(MODEL_VAR, "").strip()
        if not model_dir:
            raise ConfigurationError(f"{LINKER_VAR}=trained needs {MODEL_VAR}=<model folder>")
        return TrainedLinker.load(Path(model_dir), registry=registry)
    raise ConfigurationError(f"{LINKER_VAR} must be 'llm' or 'trained', not {choice!r}")
