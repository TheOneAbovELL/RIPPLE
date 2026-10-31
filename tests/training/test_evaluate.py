import asyncio
import json
from collections.abc import Sequence
from pathlib import Path

import pytest
from bench.linkpairs import PairMemory, Provenance, Split, write_pairs
from training.evaluate import (
    PLUMBING_NOTE,
    Confusion,
    LinkerSpec,
    PairPrediction,
    fake_llm_linker,
    metrics,
    predict,
    rule_linker,
    run,
)
from training.jobs_pairs import pairs_path

from ripple.core.errors import LLMOutputInvalidError
from ripple.core.linking import LinkProposal
from ripple.core.models import LinkCreator, Memory
from tests.training.support import CGPA, ELIGIBILITY, pair


class ScriptedLinker:
    """Proposes the given link type from the candidate to the new memory, or the reverse."""

    def __init__(self, link_type: str | None, *, backwards: bool = False) -> None:
        self.link_type = link_type
        self.backwards = backwards
        self.seen: list[tuple[Memory, Sequence[Memory]]] = []

    async def propose(self, memory: Memory, candidates: Sequence[Memory]) -> list[LinkProposal]:
        self.seen.append((memory, candidates))
        if self.link_type is None:
            return []
        [candidate] = candidates
        parent, dependent = (memory, candidate) if self.backwards else (candidate, memory)
        return [
            LinkProposal(
                parent.id, dependent.id, self.link_type, 0.9, "scripted", LinkCreator.MODEL
            )
        ]


class InvalidOutputLinker:
    async def propose(self, memory: Memory, candidates: Sequence[Memory]) -> list[LinkProposal]:
        raise LLMOutputInvalidError("linker", 2, "not the schema")


def _prediction(gold: str | None, predicted: str | None, provenance: str = "scenario"):
    return PairPrediction("x", provenance, "both", None, gold, predicted, None, 0)


def test_predict_counts_a_proposal_parent_to_dependent_as_the_pairs_prediction():
    prediction = asyncio.run(predict(ScriptedLinker("eligibility_of"), pair("a")))
    assert prediction.predicted_type == "eligibility_of"
    assert prediction.reversed_proposals == 0


def test_predict_does_not_count_a_proposal_in_the_wrong_direction():
    prediction = asyncio.run(predict(ScriptedLinker("eligibility_of", backwards=True), pair("a")))
    assert prediction.predicted_type is None
    assert prediction.reversed_proposals == 1


def test_predict_gives_the_linker_opaque_ids_that_name_neither_persona_nor_side():
    linker = ScriptedLinker(None)
    for pair_id in ("jobs_v0:p3_esha:aaaa", "jobs_v0:p3_esha:bbbb", "jobs_v0:p3_esha:cccc"):
        asyncio.run(predict(linker, pair(pair_id)))
    ids = [(memory.id, candidates[0].id) for memory, candidates in linker.seen]
    assert {i for pair_ids in ids for i in pair_ids} == {"m1", "m2"}
    assert len(set(ids)) == 2  # the seeded coin puts the parent first sometimes, not always


def test_predict_with_the_parent_as_new_memory_offers_the_dependent_as_candidate():
    linker = ScriptedLinker(None)
    asyncio.run(predict(linker, pair("a"), "parent"))
    [(memory, [candidate])] = linker.seen
    assert (memory.content, candidate.content) == (CGPA.content, ELIGIBILITY.content)


def test_predict_counts_invalid_model_output_as_an_abstention():
    prediction = asyncio.run(predict(InvalidOutputLinker(), pair("a")))
    assert prediction.abstained and prediction.predicted_type is None


def test_confusion_counts_and_scores_detection_and_type():
    confusion = Confusion()
    for gold, predicted in [
        ("eligibility_of", "eligibility_of"),
        ("eligibility_of", "depends_on_fact"),
        ("reminder_for", None),
        (None, "depends_on_fact"),
        (None, None),
    ]:
        confusion.add(_prediction(gold, predicted))
    scores = confusion.as_dict()
    assert (scores["tp"], scores["fp"], scores["fn"], scores["tn"]) == (2, 1, 1, 1)
    assert scores["typed_tp"] == 1
    assert scores["precision"] == 2 / 3 and scores["recall"] == 2 / 3
    assert scores["typed_precision"] == 1 / 3 and scores["typed_recall"] == 1 / 3
    assert scores["typed_f1"] == 2 * 1 / (2 * 2 + 1 + 1)


def test_confusion_reports_undefined_precision_as_none_and_f1_as_zero():
    confusion = Confusion()
    confusion.add(_prediction("eligibility_of", None))
    confusion.add(_prediction(None, None))
    scores = confusion.as_dict()
    assert scores["precision"] is None and scores["recall"] == 0.0 and scores["f1"] == 0.0


def test_confusion_without_gold_negatives_reports_no_precision():
    confusion = Confusion()
    confusion.add(_prediction("eligibility_of", "eligibility_of"))
    scores = confusion.as_dict()
    assert scores["precision"] is None and scores["f1"] is None and scores["recall"] == 1.0


def test_confusion_for_an_untyped_linker_reports_no_typed_metrics():
    confusion = Confusion()
    confusion.add(_prediction("eligibility_of", "depends_on_fact"))
    confusion.add(_prediction(None, None))
    scores = confusion.as_dict(typed=False)
    assert scores["typed_precision"] is None and scores["typed_f1"] is None


def test_metrics_stratify_and_report_recall_only_per_gold_type():
    result = metrics(
        [
            _prediction("eligibility_of", "eligibility_of", "rule"),
            _prediction(None, None, "scenario"),
            _prediction("depends_on_fact", None, "scenario"),
        ],
        train_link_types=frozenset({"eligibility_of"}),
    )
    by_provenance = result["by_provenance"]
    assert isinstance(by_provenance, dict)
    assert set(by_provenance) == {"rule", "scenario"}
    by_type = result["by_gold_link_type"]
    assert isinstance(by_type, dict)
    assert set(by_type["eligibility_of"]) == {"tp", "fn", "recall", "typed_recall", "seen_in_train"}
    assert by_type["depends_on_fact"]["seen_in_train"] is False


def test_metrics_report_false_positives_per_negative_kind():
    reversed_fp = PairPrediction("r", "scenario", "both", "reversed link", None, "x", 0.9, 0)
    other_tn = PairPrediction(
        "o", "scenario", "both", "same scenario, no link", None, None, None, 0
    )
    negatives = metrics([reversed_fp, other_tn])["false_positives_by_negative_kind"]
    assert negatives == {
        "reversed link": {"n": 1, "fp": 1, "fp_rate": 1.0},
        "same scenario, no link": {"n": 1, "fp": 0, "fp_rate": 0.0},
    }


def _pair_file(tmp_path: Path) -> Path:
    path = tmp_path / "pairs.jsonl"
    other = PairMemory(kind="derived", content="remind about the acme interview slot")
    write_pairs(
        path,
        [
            pair("p1"),
            pair("p2", parent=ELIGIBILITY, dependent=CGPA, link_type=None),
            pair("p3", dependent=other, link_type=None, provenance=Provenance.SCENARIO),
        ],
    )
    return path


def test_run_writes_config_metrics_report_and_predictions(tmp_path: Path):
    linker = ScriptedLinker("eligibility_of")
    run_dir = run(LinkerSpec("scripted", linker), _pair_file(tmp_path), results_root=tmp_path / "r")
    assert "_linkpairs_jobs_v0_scripted_" in run_dir.name
    assert {p.name for p in run_dir.iterdir()} == {
        "config.json",
        "metrics.json",
        "report.md",
        "predictions.jsonl",
    }
    config = json.loads((run_dir / "config.json").read_text(encoding="utf-8"))
    assert config["pair_count"] == 3 and config["new_memory"] == "dependent"
    assert config["models"] == {} and config["prompt_versions"] == {}
    assert config["seeds"]["run_seed"] == 20261031
    result = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    assert result["overall"]["tp"] == 1 and result["overall"]["fp"] == 2
    assert result["llm_calls"] == 0 and result["linker_calls"] == 3
    assert len(linker.seen) == 3


def test_run_never_overwrites_an_earlier_folder(tmp_path: Path):
    pairs = _pair_file(tmp_path)
    first = run(LinkerSpec("s", ScriptedLinker(None)), pairs, results_root=tmp_path / "r")
    second = run(LinkerSpec("s", ScriptedLinker(None)), pairs, results_root=tmp_path / "r")
    assert first != second and second.name.endswith("_2")


def test_run_refuses_a_trained_linker_scored_on_another_pair_file(tmp_path: Path):
    spec = LinkerSpec("trained", ScriptedLinker(None), train_pairs_sha256="0" * 64)
    with pytest.raises(ValueError, match="trained on pair file"):
        run(spec, _pair_file(tmp_path), results_root=tmp_path / "r")


def test_fake_llm_run_is_labelled_a_plumbing_check(tmp_path: Path):
    run_dir = run(fake_llm_linker(3), _pair_file(tmp_path), results_root=tmp_path / "r")
    assert PLUMBING_NOTE in (run_dir / "report.md").read_text(encoding="utf-8")
    config = json.loads((run_dir / "config.json").read_text(encoding="utf-8"))
    assert config["plumbing_only"] is True and config["prompt_versions"] == {"linker": 1}
    result = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    assert result["note"] == PLUMBING_NOTE and result["overall"]["tp"] == 0
    assert result["llm_calls"] == 3


def test_rule_linker_run_on_the_checked_in_pairs_reports_held_out_cells(tmp_path: Path):
    run_dir = run(rule_linker(), pairs_path(), results_root=tmp_path)
    config = json.loads((run_dir / "config.json").read_text(encoding="utf-8"))
    assert config["typed"] is False
    assert config["data"]["source"]["test_templates"] == ["cgpa_rise", "deadline_moved"]
    result = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    assert set(result["by_held_out"]) == {"persona", "template", "both"}
    assert result["overall"]["typed_f1"] is None


def test_train_split_pairs_score_in_the_none_cell(tmp_path: Path):
    run_dir = run(rule_linker(), pairs_path(), split=Split.TRAIN.value, results_root=tmp_path)
    result = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    assert set(result["by_held_out"]) == {"none"}
