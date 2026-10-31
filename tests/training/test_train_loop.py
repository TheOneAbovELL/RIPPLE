"""The training loop (ADR-0126) on the offline "scratch:tiny" model: determinism,
validation by persona, threshold choice and the saved artifact. Nothing downloads."""

import asyncio
import json
from pathlib import Path

import pytest
from bench.linkpairs import read_pairs
from training.evaluate import trained_linker
from training.jobs_pairs import pairs_path
from training.train import (
    NO_LINK,
    SCRATCH_TINY,
    THRESHOLD_GRID,
    TrainConfig,
    TrainedLinker,
    TrainingExample,
    _class_weights,
    choose_threshold,
    label_space,
    link_f1,
    train,
    training_examples,
)

from ripple.domains.jobs.vocabulary import jobs_registry
from ripple.linking.trained import (
    ARTIFACT_FILE,
    HuggingFaceScorer,
    decide,
    memory_text,
    select_linker,
)
from tests.builders import derived, fact
from tests.training.support import CGPA, ELIGIBILITY

LABELS = label_space(jobs_registry())


def _config(tmp_path: Path, name: str = "model", **overrides: object) -> TrainConfig:
    values: dict[str, object] = {
        "pairs_file": pairs_path(),
        "output_dir": tmp_path / name,
        "base_model": SCRATCH_TINY,
        "epochs": 1,
        "learning_rate": 1e-3,
    } | overrides
    return TrainConfig(**values)  # type: ignore[arg-type]


def _examples(tmp_path: Path) -> list[TrainingExample]:
    every = training_examples(list(read_pairs(pairs_path())), _config(tmp_path), jobs_registry())
    # Two personas keep the loop quick; p1_dev is the validation persona below.
    return [e for e in every if e.persona in {"p0_jay", "p1_dev"}]


def test_link_f1_counts_links_regardless_of_type():
    f1, precision, recall = link_f1([True, True, False, False], [True, False, True, False])
    assert (f1, precision, recall) == (0.5, 0.5, 0.5)
    assert link_f1([False], [False]) == (0.0, None, None)


def test_choose_threshold_decides_like_the_served_linker():
    labels = ["fit_of", NO_LINK]
    # Pair 1: a link, forward 0.6 beats backward 0.2. Pair 2: no link, but its reverse
    # direction scores 0.9, so the served linker proposes the reverse edge, not this one.
    forward = [[0.6, 0.4], [0.3, 0.7]]
    backward = [[0.2, 0.8], [0.9, 0.1]]
    score = choose_threshold(forward, backward, [True, False], labels)
    assert score.f1 == 1.0 and score.precision == 1.0
    assert score.threshold == 0.5  # every threshold up to 0.6 ties; the one nearest 0.5 wins
    assert score.threshold in THRESHOLD_GRID


def test_class_weights_balance_the_present_classes_and_leave_absent_ones_at_one():
    examples = [
        TrainingExample(str(i), CGPA, ELIGIBILITY, label, "p0_jay")
        for i, label in enumerate(["eligibility_of", NO_LINK, NO_LINK, NO_LINK])
    ]
    weights = dict(zip(LABELS, _class_weights(examples, LABELS), strict=True))
    assert weights["eligibility_of"] == 2.0
    assert weights[NO_LINK] == pytest.approx(4 / 6)
    assert weights["fit_of"] == 1.0


def test_train_is_deterministic_for_a_seed(tmp_path: Path):
    examples = _examples(tmp_path)
    first = train(_config(tmp_path, "a"), examples)
    second = train(_config(tmp_path, "b"), examples)
    history = [a.manifest["training"]["history"] for a in (first, second)]
    assert history[0] == history[1]
    assert (first.model_dir / "model.safetensors").read_bytes() == (
        second.model_dir / "model.safetensors"
    ).read_bytes()


def test_train_picks_epoch_and_threshold_on_the_validation_persona(tmp_path: Path):
    config = _config(tmp_path, epochs=2, validation_personas=frozenset({"p1_dev"}))
    artifact = train(config, _examples(tmp_path))
    training = artifact.manifest["training"]
    assert training["validation_examples"] > 0
    assert training["fit_examples"] + training["validation_examples"] == len(_examples(tmp_path))
    assert [entry["epoch"] for entry in training["history"]] == [1, 2]
    assert all("f1" in entry for entry in training["history"])
    assert training["chosen_epoch"] in (1, 2)
    assert artifact.threshold == training["validation"]["threshold"]
    assert artifact.manifest["threshold_source"] == "validation personas"
    assert artifact.manifest["train_config"]["validation_personas"] == ["p1_dev"]


def test_train_without_validation_keeps_the_last_epoch_and_the_default_threshold(tmp_path: Path):
    artifact = train(_config(tmp_path), _examples(tmp_path))
    assert artifact.threshold == 0.5
    assert artifact.manifest["training"]["validation"] is None


def test_train_refuses_a_validation_persona_with_no_examples(tmp_path: Path):
    config = _config(tmp_path, validation_personas=frozenset({"p9_nobody"}))
    with pytest.raises(ValueError, match="no examples for validation personas"):
        train(config, _examples(tmp_path))


def test_train_refuses_labels_outside_the_domains_label_space(tmp_path: Path):
    stray = [TrainingExample("x", CGPA, ELIGIBILITY, "assumes", "p0_jay")]
    with pytest.raises(ValueError, match="outside the jobs label space"):
        train(_config(tmp_path), stray)


def test_saved_artifact_loads_and_serves_the_trained_label_space(tmp_path: Path):
    artifact = train(_config(tmp_path), _examples(tmp_path))
    manifest = json.loads((artifact.model_dir / ARTIFACT_FILE).read_text(encoding="utf-8"))
    assert manifest["label_space"] == LABELS
    linker = TrainedLinker.load(artifact.model_dir, threshold=0.0, registry=jobs_registry())
    cgpa = fact("student", "cgpa", 7.4, content="CGPA is 7.4")
    belief = derived("not eligible for acme (7.4 < 7.6)")
    # Threshold 0 forces one proposal per candidate: the loaded model really scores.
    [proposal] = asyncio.run(linker.propose(belief, [cgpa]))
    assert proposal.link_type in jobs_registry().known_types()


def test_train_refuses_validation_personas_without_a_gold_link(tmp_path: Path):
    examples = [e for e in _examples(tmp_path) if e.persona == "p0_jay" or e.label == NO_LINK]
    config = _config(tmp_path, validation_personas=frozenset({"p1_dev"}))
    with pytest.raises(ValueError, match="no gold link"):
        train(config, examples)


def test_train_restores_the_process_wide_determinism_setting(tmp_path: Path):
    import torch

    assert not torch.are_deterministic_algorithms_enabled()
    train(_config(tmp_path), _examples(tmp_path))
    assert not torch.are_deterministic_algorithms_enabled()


def test_saved_model_reproduces_the_validation_score_of_the_chosen_epoch(tmp_path: Path):
    # Fails if the best epoch's weights are not restored before saving (when a later
    # epoch scored differently), or if serving decides pairs unlike validation.
    examples = _examples(tmp_path)
    config = _config(tmp_path, epochs=3, validation_personas=frozenset({"p1_dev"}))
    artifact = train(config, examples)
    held = [e for e in examples if e.persona == "p1_dev"]
    scorer = HuggingFaceScorer(artifact)
    forward = scorer([(memory_text(e.parent), memory_text(e.dependent)) for e in held])
    backward = scorer([(memory_text(e.dependent), memory_text(e.parent)) for e in held])
    linked = [
        (d := decide(f, b, artifact.label_space, artifact.threshold)) is not None
        and d.direction == "forward"
        for f, b in zip(forward, backward, strict=True)
    ]
    f1, _, _ = link_f1(linked, [e.label != NO_LINK for e in held])
    assert f1 == pytest.approx(artifact.manifest["training"]["validation"]["f1"])


def test_trained_linker_spec_carries_the_training_record_into_results(tmp_path: Path):
    artifact = train(_config(tmp_path), _examples(tmp_path))
    spec = trained_linker(artifact.model_dir)
    assert spec.train_pairs_file == pairs_path().resolve()
    assert spec.train_pairs_sha256 == artifact.train_pairs_sha256
    assert spec.fitted_link_types == frozenset(
        e.label for e in _examples(tmp_path) if e.label != NO_LINK
    )
    training = spec.details["training"]
    assert isinstance(training, dict)
    assert training["fit_examples"] == len(_examples(tmp_path))
    assert spec.models["base_model"] == SCRATCH_TINY


def test_select_linker_loads_a_trained_model_from_configuration(tmp_path: Path):
    artifact = train(_config(tmp_path), _examples(tmp_path))
    env = {"RIPPLE_LINKER": "trained", "RIPPLE_TRAINED_LINKER_MODEL": str(artifact.model_dir)}
    linker = select_linker(env, llm=object(), registry=jobs_registry())  # type: ignore[arg-type]
    assert isinstance(linker, TrainedLinker)
    assert linker.threshold == artifact.threshold
