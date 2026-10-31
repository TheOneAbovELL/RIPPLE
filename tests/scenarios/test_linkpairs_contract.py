"""Contract C5 (bench/linkpairs.py): the labelled-pair format both wave-B tracks share."""

import pytest
from bench.linkpairs import (
    LabelledPair,
    PairMemory,
    Provenance,
    Split,
    read_pairs,
    split_for,
    write_pairs,
)

from ripple.core.models import LinkClass, StructuredFact


def _pair(pair_id: str = "p1", **overrides) -> LabelledPair:
    fields = {
        "pair_id": pair_id,
        "track": "jobs_v0",
        "domain": "jobs",
        "persona": "p0_jay",
        "template": "cgpa_rise",
        "split": Split.TEST,
        "parent": PairMemory(
            kind="fact",
            content="CGPA is 7.6",
            structured=StructuredFact(subject="student", attribute="cgpa", value=7.6),
        ),
        "dependent": PairMemory(kind="derived", content="not eligible for Acme"),
        "link_type": "eligibility_of",
        "link_class": LinkClass.DEPENDS_ON,
        "provenance": Provenance.RULE,
    }
    fields.update(overrides)
    return LabelledPair(**fields)


def test_pairs_round_trip_through_json_lines_sorted_by_id(tmp_path):
    path = tmp_path / "pairs.jsonl"
    written = write_pairs(path, [_pair("b"), _pair("a", link_type=None, link_class=None)])
    back = list(read_pairs(path))
    assert written == 2 and [p.pair_id for p in back] == ["a", "b"]
    assert back[0].is_link is False and back[1] == _pair("b")


def test_link_type_and_class_must_be_set_together():
    with pytest.raises(ValueError, match="together"):
        _pair(link_class=None)


def test_llm_and_human_labels_name_their_labeller():
    with pytest.raises(ValueError, match="labeller"):
        _pair(provenance=Provenance.HUMAN)
    assert _pair(provenance=Provenance.LLM, labeller="claude-x@linker.v1").labeller


def test_duplicate_pair_ids_are_refused(tmp_path):
    with pytest.raises(ValueError, match="duplicate"):
        write_pairs(tmp_path / "pairs.jsonl", [_pair("a"), _pair("a")])


def test_split_is_train_only_when_persona_and_template_are_both_train():
    assert split_for(True, True) is Split.TRAIN
    assert {split_for(True, False), split_for(False, True), split_for(False, False)} == {Split.TEST}
