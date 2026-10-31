"""TrainedLinker (ADR-0126, ADR-0128): direction, threshold, candidate filtering and
configuration, on a scripted scorer; loading real weights is covered by the training
tests on the offline "scratch:tiny" model."""

import asyncio
import json
from collections.abc import Sequence
from pathlib import Path

import pytest

from ripple.core.errors import ConfigurationError
from ripple.core.links import LinkTypeRegistry
from ripple.core.models import LinkClass, LinkCreator, StructuredFact
from ripple.linking.trained import (
    ARTIFACT_FILE,
    ARTIFACT_FORMAT,
    ARTIFACT_VERSION,
    NO_LINK,
    TrainedArtifact,
    TrainedLinker,
    decide,
    memory_text,
    select_linker,
)
from tests.builders import derived, fact, memory

LABELS = ("depends_on_fact", "eligibility_of", NO_LINK)


def _artifact(threshold: float = 0.5) -> TrainedArtifact:
    return TrainedArtifact(Path("unused"), LABELS, "0" * 64, 1, threshold=threshold)


class ScriptedScorer:
    """Answers a fixed probability row per (parent text, dependent text)."""

    def __init__(self, rows: dict[tuple[str, str], list[float]]) -> None:
        self.rows = rows
        self.calls: list[list[tuple[str, str]]] = []

    def __call__(self, pairs: Sequence[tuple[str, str]]) -> list[list[float]]:
        self.calls.append(list(pairs))
        return [self.rows.get(p, [0.0, 0.0, 1.0]) for p in pairs]


def test_memory_text_spells_out_kind_content_and_structure():
    cgpa = fact("student", "cgpa", 7.4, content="CGPA is 7.4")
    assert memory_text(cgpa) == "[fact] CGPA is 7.4 || student cgpa 7.4"
    assert memory_text(derived("eligible for acme")) == "[derived] eligible for acme"


def test_decide_takes_the_more_probable_direction_only():
    forward, backward = [0.7, 0.1, 0.2], [0.1, 0.8, 0.1]
    decision = decide(forward, backward, LABELS, 0.5)
    assert decision is not None
    assert (decision.direction, decision.link_type, decision.probability) == (
        "backward",
        "eligibility_of",
        0.8,
    )


def test_decide_proposes_nothing_on_an_exact_tie_between_directions():
    # Otherwise the answer would depend on which memory happens to be the new one.
    assert decide([0.6, 0.1, 0.3], [0.1, 0.6, 0.3], LABELS, 0.5) is None


def test_decide_proposes_nothing_below_the_threshold():
    assert decide([0.4, 0.1, 0.5], [0.1, 0.1, 0.8], LABELS, 0.5) is None


def test_propose_writes_a_model_edge_from_the_candidate_to_the_new_memory():
    cgpa = fact("student", "cgpa", 7.4, content="CGPA is 7.4")
    belief = derived("not eligible for acme")
    scorer = ScriptedScorer({(memory_text(cgpa), memory_text(belief)): [0.1, 0.85, 0.05]})
    linker = TrainedLinker(_artifact(), scorer)
    [proposal] = asyncio.run(linker.propose(belief, [cgpa]))
    assert (proposal.parent_id, proposal.dependent_id) == (cgpa.id, belief.id)
    assert proposal.link_type == "eligibility_of"
    assert proposal.confidence == pytest.approx(0.85)
    assert proposal.created_by is LinkCreator.MODEL
    # Both orientations are scored in one batch.
    assert scorer.calls == [
        [(memory_text(cgpa), memory_text(belief)), (memory_text(belief), memory_text(cgpa))]
    ]


def test_propose_finds_a_hidden_link_from_the_new_fact_to_an_existing_belief():
    skill = fact("student", "skills", "pytorch", content="knows pytorch")
    fit = derived("fit for acme ml intern")
    scorer = ScriptedScorer({(memory_text(skill), memory_text(fit)): [0.9, 0.05, 0.05]})
    [proposal] = asyncio.run(TrainedLinker(_artifact(), scorer).propose(skill, [fit]))
    assert (proposal.parent_id, proposal.dependent_id) == (skill.id, fit.id)


def test_propose_skips_itself_and_other_users_memories_without_scoring():
    belief = derived("eligible for acme")
    stranger = memory(content="CGPA is 9.0", user_id="student-2")
    scorer = ScriptedScorer({})
    assert asyncio.run(TrainedLinker(_artifact(), scorer).propose(belief, [belief, stranger])) == []
    assert scorer.calls == []


def test_an_explicit_threshold_overrides_the_validated_one():
    cgpa = fact("student", "cgpa", 7.4, content="CGPA is 7.4")
    belief = derived("eligible for acme")
    scorer = ScriptedScorer({(memory_text(cgpa), memory_text(belief)): [0.0, 0.6, 0.4]})
    assert asyncio.run(TrainedLinker(_artifact(0.7), scorer).propose(belief, [cgpa])) == []
    linker = TrainedLinker(_artifact(0.7), scorer, threshold=0.5)
    assert len(asyncio.run(linker.propose(belief, [cgpa]))) == 1


def test_a_threshold_outside_zero_one_is_refused():
    with pytest.raises(ConfigurationError, match="threshold"):
        TrainedLinker(_artifact(), ScriptedScorer({}), threshold=1.5)


def _write_manifest(folder: Path, **overrides: object) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, object] = {
        "format": ARTIFACT_FORMAT,
        "version": ARTIFACT_VERSION,
        "label_space": list(LABELS),
        "train_pairs_sha256": "0" * 64,
        "seed": 7,
        "threshold": 0.35,
        "base_model": "scratch:tiny",
        "max_length": 64,
    } | overrides
    (folder / ARTIFACT_FILE).write_text(json.dumps(manifest), encoding="utf-8")
    return folder


def test_artifact_read_takes_the_manifest_fields(tmp_path: Path):
    artifact = TrainedArtifact.read(_write_manifest(tmp_path / "m"))
    assert (artifact.label_space, artifact.seed, artifact.threshold) == (LABELS, 7, 0.35)


def test_artifact_read_refuses_a_folder_without_a_manifest_or_with_another_format(tmp_path: Path):
    with pytest.raises(ConfigurationError, match="not a trained linker"):
        TrainedArtifact.read(tmp_path)
    with pytest.raises(ConfigurationError, match="format"):
        TrainedArtifact.read(_write_manifest(tmp_path / "m", format="other"))
    with pytest.raises(ConfigurationError, match="followed by"):
        TrainedArtifact.read(_write_manifest(tmp_path / "n", label_space=["none", "fit_of"]))


def test_artifact_read_refuses_a_label_space_without_a_link_type(tmp_path: Path):
    with pytest.raises(ConfigurationError, match="followed by"):
        TrainedArtifact.read(_write_manifest(tmp_path / "m", label_space=["none"]))


def test_artifact_read_reports_a_missing_field_as_configuration(tmp_path: Path):
    folder = _write_manifest(tmp_path / "m")
    manifest = json.loads((folder / ARTIFACT_FILE).read_text(encoding="utf-8"))
    del manifest["seed"]
    (folder / ARTIFACT_FILE).write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ConfigurationError, match="seed"):
        TrainedArtifact.read(folder)


def test_load_refuses_a_registry_that_lacks_the_models_link_types(tmp_path: Path):
    folder = _write_manifest(tmp_path / "m")
    registry = LinkTypeRegistry({"depends_on_fact": LinkClass.DEPENDS_ON})
    with pytest.raises(ConfigurationError, match="eligibility_of"):
        TrainedLinker.load(folder, registry=registry)


def test_select_linker_defaults_to_the_llm_linker():
    llm = object()
    registry = LinkTypeRegistry()
    assert select_linker({}, llm=llm, registry=registry) is llm  # type: ignore[arg-type]
    assert select_linker({"RIPPLE_LINKER": "LLM"}, llm=llm, registry=registry) is llm  # type: ignore[arg-type]


def test_select_linker_trained_needs_a_model_folder_and_a_known_choice():
    llm, registry = object(), LinkTypeRegistry()
    with pytest.raises(ConfigurationError, match="RIPPLE_TRAINED_LINKER_MODEL"):
        select_linker({"RIPPLE_LINKER": "trained"}, llm=llm, registry=registry)  # type: ignore[arg-type]
    with pytest.raises(ConfigurationError, match="'llm' or 'trained'"):
        select_linker({"RIPPLE_LINKER": "rules"}, llm=llm, registry=registry)  # type: ignore[arg-type]


def test_structured_fact_values_of_every_type_render():
    for value in (7, 7.5, True, "pytorch"):
        text = memory_text(
            memory(structured=StructuredFact(subject="s", attribute="a", value=value))
        )
        assert text.endswith(f"|| s a {value}")
