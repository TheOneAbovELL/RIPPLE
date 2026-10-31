"""The training interface (ADR-0094) and its implementation (ADR-0126). Training runs on
the "scratch:tiny" model, so nothing here downloads weights."""

import asyncio
from pathlib import Path

import pytest
from bench.linkpairs import Provenance, Split, read_pairs
from training.jobs_pairs import file_sha256, pairs_path
from training.train import (
    NO_LINK,
    SCRATCH_TINY,
    TrainConfig,
    TrainedLinker,
    label_space,
    train,
    training_examples,
)

from ripple.core.models import LinkCreator
from ripple.domains.jobs.vocabulary import jobs_registry
from tests.builders import derived, fact
from tests.training.support import pair


def _config(tmp_path: Path) -> TrainConfig:
    return TrainConfig(
        pairs_file=pairs_path(),
        output_dir=tmp_path / "model",
        base_model=SCRATCH_TINY,
        epochs=1,
    )


def test_label_space_is_every_registered_type_plus_no_link():
    space = label_space(jobs_registry())
    assert space[-1] == NO_LINK
    assert set(space[:-1]) == jobs_registry().known_types()


def test_training_examples_take_train_split_generated_labels_only(tmp_path: Path):
    pairs = [
        pair("a", split=Split.TRAIN, persona="p0_jay", template="exam_block"),
        pair("b"),  # test split
        pair(
            "c",
            split=Split.TRAIN,
            persona="p0_jay",
            template="exam_block",
            provenance=Provenance.HUMAN,
            labeller="ORG",
        ),
        pair("d", split=Split.TRAIN, persona="p0_jay", template="exam_block", link_type=None),
    ]
    examples = training_examples(pairs, _config(tmp_path), jobs_registry())
    assert [(e.pair_id, e.label) for e in examples] == [("a", "eligibility_of"), ("d", NO_LINK)]


def test_training_examples_refuse_an_unregistered_link_type(tmp_path: Path):
    stray = pair("a", split=Split.TRAIN, persona="p0_jay", template="exam_block", link_type="about")
    with pytest.raises(ValueError, match="not registered"):
        training_examples([stray], _config(tmp_path), jobs_registry())


def test_training_examples_refuse_a_test_only_pair_set(tmp_path: Path):
    # The finance track (H4) is test-only; training on it must fail loudly, not silently.
    with pytest.raises(ValueError, match="nothing to train on"):
        training_examples([pair("b")], _config(tmp_path), jobs_registry())


def test_train_saves_an_artifact_over_the_label_space(tmp_path: Path):
    config = _config(tmp_path)
    examples = training_examples(list(read_pairs(pairs_path())), config, jobs_registry())
    artifact = train(config, examples)
    assert artifact.model_dir.is_dir()
    assert list(artifact.label_space) == label_space(jobs_registry())
    assert artifact.train_pairs_sha256 == file_sha256(pairs_path())
    assert artifact.seed == config.seed


def test_trained_linker_proposes_only_registered_links_to_candidates(tmp_path: Path):
    config = _config(tmp_path)
    artifact = train(
        config, training_examples(list(read_pairs(pairs_path())), config, jobs_registry())
    )
    # Threshold 0 forces a proposal, so the checks below always run on one.
    linker = TrainedLinker.load(artifact.model_dir, threshold=0.0)
    cgpa = fact("student", "cgpa", 7.4, content="CGPA is 7.4")
    belief = derived("not eligible for acme (7.4 < 7.6)")
    [proposal] = asyncio.run(linker.propose(belief, [cgpa]))
    assert {proposal.parent_id, proposal.dependent_id} == {cgpa.id, belief.id}
    assert proposal.link_type in jobs_registry().known_types()
    assert 0.0 <= proposal.confidence <= 1.0
    assert proposal.created_by is LinkCreator.MODEL
