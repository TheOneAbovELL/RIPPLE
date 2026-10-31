"""The harness's transfer mode (H4) and cost record (ADR-0127)."""

import json
from pathlib import Path

import pytest
from bench.linkpairs import LabelledPair, PairMemory, Split, write_pairs
from training.evaluate import LinkerSpec, rule_linker, run
from training.jobs_pairs import file_sha256

from tests.training.support import CGPA, ELIGIBILITY, pair
from tests.training.test_evaluate import ScriptedLinker

MARGIN = PairMemory(kind="fact", content="Northwind margin is 31%")
THESIS = PairMemory(kind="derived", content="hold Northwind: margin above 25%")


def _finance(pair_id: str, **kwargs: object) -> LabelledPair:
    kwargs = {"parent": MARGIN, "dependent": THESIS} | kwargs
    base = pair(pair_id, **kwargs)  # type: ignore[arg-type]
    return base.model_copy(update={"track": "finance_v1", "domain": "finance"})


def _train_file(tmp_path: Path) -> Path:
    path = tmp_path / "train_pairs.jsonl"
    write_pairs(path, [pair("t1", split=Split.TRAIN, persona="p0_jay", template="exam_block")])
    return path


def _spec(train_file: Path, label_space: tuple[str, ...] = ("eligibility_of", "none")):
    return LinkerSpec(
        "trained",
        ScriptedLinker("eligibility_of"),
        train_pairs_sha256=file_sha256(train_file),
        train_pairs_file=train_file,
        label_space=label_space,
    )


def _eval_file(tmp_path: Path, *pairs: LabelledPair) -> Path:
    path = tmp_path / "finance_pairs.jsonl"
    write_pairs(path, pairs)
    return path


def test_transfer_run_scores_another_tracks_test_pairs_untyped(tmp_path: Path):
    train_file = _train_file(tmp_path)
    pairs = _eval_file(tmp_path, _finance("f1", link_type="assumes"))
    run_dir = run(_spec(train_file), pairs, results_root=tmp_path / "r", transfer=True)
    config = json.loads((run_dir / "config.json").read_text(encoding="utf-8"))
    assert config["track"] == "finance_v1"
    assert config["typed"] is False
    assert config["transfer"]["gold_types_in_label_space"] is False
    assert config["transfer"]["pairs_sharing_a_text_with_train"] == 0
    result = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    assert result["overall"]["tp"] == 1 and result["overall"]["typed_f1"] is None
    # seen_in_train comes from the model's training file, not the evaluated one.
    assert result["by_gold_link_type"]["assumes"]["seen_in_train"] is False
    assert "Transfer run (H4)" in (run_dir / "report.md").read_text(encoding="utf-8")


def test_transfer_run_counts_pairs_sharing_one_text_with_training(tmp_path: Path):
    train_file = _train_file(tmp_path)
    shared = _finance("f1", link_type="assumes").model_copy(update={"parent": CGPA})
    run_dir = run(
        _spec(train_file), _eval_file(tmp_path, shared), results_root=tmp_path / "r", transfer=True
    )
    config = json.loads((run_dir / "config.json").read_text(encoding="utf-8"))
    assert config["transfer"]["pairs_sharing_a_text_with_train"] == 1


def test_transfer_refuses_a_pair_repeating_a_training_text_pair(tmp_path: Path):
    train_file = _train_file(tmp_path)
    repeat = _finance("f1").model_copy(update={"parent": CGPA, "dependent": ELIGIBILITY})
    with pytest.raises(ValueError, match="repeat a training text pair"):
        run(
            _spec(train_file),
            _eval_file(tmp_path, repeat),
            results_root=tmp_path / "r",
            transfer=True,
        )


def test_transfer_refuses_train_split_pairs(tmp_path: Path):
    train_file = _train_file(tmp_path)
    leaked = _finance("f1", split=Split.TRAIN, persona="p0_jay", template="exam_block")
    with pytest.raises(ValueError, match="test pairs only"):
        run(
            _spec(train_file),
            _eval_file(tmp_path, leaked),
            split="all",
            results_root=tmp_path / "r",
            transfer=True,
        )


def test_transfer_refuses_a_changed_training_file(tmp_path: Path):
    train_file = _train_file(tmp_path)
    spec = _spec(train_file)
    write_pairs(train_file, [pair("t2", split=Split.TRAIN, persona="p1_dev", template="x")])
    with pytest.raises(ValueError, match="changed since"):
        run(spec, _eval_file(tmp_path, _finance("f1")), results_root=tmp_path / "r", transfer=True)


def test_transfer_applies_to_a_trained_linker_only(tmp_path: Path):
    with pytest.raises(ValueError, match="trained linker only"):
        run(
            rule_linker(),
            _eval_file(tmp_path, _finance("f1")),
            results_root=tmp_path / "r",
            transfer=True,
        )


def test_transfer_keeps_typed_metrics_when_the_label_space_covers_the_gold_types(tmp_path: Path):
    train_file = _train_file(tmp_path)
    pairs = _eval_file(tmp_path, _finance("f1", link_type="eligibility_of"))
    run_dir = run(_spec(train_file), pairs, results_root=tmp_path / "r", transfer=True)
    config = json.loads((run_dir / "config.json").read_text(encoding="utf-8"))
    assert config["typed"] is True


def test_every_run_records_wall_and_cpu_seconds_per_call(tmp_path: Path):
    pairs = _eval_file(tmp_path, _finance("f1"), _finance("f2", parent=THESIS, dependent=MARGIN))
    run_dir = run(rule_linker(), pairs, results_root=tmp_path / "r")
    cost = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))["cost"]
    assert cost["wall_seconds_per_call"] >= 0 and cost["cpu_seconds_per_call"] >= 0
    assert "process CPU per linker call" in (run_dir / "report.md").read_text(encoding="utf-8")


def test_transfer_refuses_the_models_own_pair_file(tmp_path: Path):
    train_file = _train_file(tmp_path)
    with pytest.raises(ValueError, match="own pair file"):
        run(
            _spec(train_file),
            train_file,
            split="all",
            results_root=tmp_path / "r",
            transfer=True,
        )


def test_transfer_refuses_test_pairs_of_the_training_track(tmp_path: Path):
    train_file = _train_file(tmp_path)
    jobs_test = pair("j1", parent=MARGIN, dependent=THESIS)  # track jobs_v0, unseen texts
    with pytest.raises(ValueError, match="another track"):
        run(
            _spec(train_file),
            _eval_file(tmp_path, jobs_test),
            results_root=tmp_path / "r",
            transfer=True,
        )


def test_a_trained_linker_is_never_scored_on_its_train_split(tmp_path: Path):
    train_file = _train_file(tmp_path)
    with pytest.raises(ValueError, match="test pairs only"):
        run(_spec(train_file), train_file, split="train", results_root=tmp_path / "r")


def test_seen_in_train_comes_from_the_fitted_link_types_when_known(tmp_path: Path):
    train_file = _train_file(tmp_path)  # its one train pair is eligibility_of
    spec = _spec(train_file)
    spec.fitted_link_types = frozenset()  # e.g. that pair was a validation persona's
    pairs = _eval_file(tmp_path, _finance("f1", link_type="eligibility_of"))
    run_dir = run(spec, pairs, results_root=tmp_path / "r", transfer=True)
    result = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    assert result["by_gold_link_type"]["eligibility_of"]["seen_in_train"] is False


def test_transfer_run_leaves_the_callers_spec_unchanged(tmp_path: Path):
    train_file = _train_file(tmp_path)
    spec = _spec(train_file)
    run(
        spec,
        _eval_file(tmp_path, _finance("f1", link_type="assumes")),
        results_root=tmp_path / "r",
        transfer=True,
    )
    assert spec.typed is True


def test_a_trained_run_report_carries_the_training_record(tmp_path: Path):
    history = [
        {"epoch": 1, "f1": 0.5, "threshold": 0.4},
        {"epoch": 2, "f1": 0.75, "threshold": 0.5},
    ]
    spec = LinkerSpec(
        "scripted",
        ScriptedLinker(None),
        details={
            "base_model": "scratch:tiny",
            "seed": 7,
            "threshold": 0.5,
            "threshold_source": "validation personas",
            "chosen_epoch": 2,
            "validation_personas": ["p1_dev"],
            "training": {
                "fit_examples": 10,
                "validation_examples": 4,
                "validation": {"f1": 0.75, "precision": 1.0, "recall": 0.6},
                "train_seconds": 1.5,
                "history": history,
            },
        },
    )
    run_dir = run(spec, _eval_file(tmp_path, _finance("f1")), results_root=tmp_path / "r")
    report = (run_dir / "report.md").read_text(encoding="utf-8")
    assert "chosen epoch 2; fitted on 10 pairs, validated on 4 pairs" in report
    assert "Validation at the chosen epoch: F1 0.750, precision 1.000, recall 0.600." in report
    assert "epoch 1: F1 0.500 at threshold 0.4; epoch 2: F1 0.750 at threshold 0.5" in report
