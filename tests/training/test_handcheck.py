import csv
import json
from collections import Counter
from pathlib import Path

import pytest
from bench.linkpairs import Provenance, Split, read_pairs, write_pairs
from training.handcheck import (
    SHEET_COLUMNS,
    Agreement,
    HandLabel,
    SheetError,
    agreement,
    allocate,
    gold_pairs,
    key_path,
    read_sheet,
    sample_for_handcheck,
    stratum,
    write_report,
    write_sheet,
)
from training.jobs_pairs import pairs_path

from ripple.domains.jobs.vocabulary import jobs_registry
from tests.training.support import pair


def test_allocate_gives_each_stratum_its_minimum_then_shares_the_rest_exactly():
    quota = allocate({"a": 500, "b": 100, "c": 4}, 300, minimum=10)
    assert quota["c"] == 4 and sum(quota.values()) == 300
    assert quota["a"] > quota["b"] >= 10


def test_allocate_keeps_the_minimums_when_they_exceed_the_total():
    assert allocate({"a": 50, "b": 50, "c": 50}, 20, minimum=10) == {"a": 10, "b": 10, "c": 10}


def test_allocate_takes_everything_when_the_set_is_small():
    assert allocate({"a": 5, "b": 7}, 300) == {"a": 5, "b": 7}


def test_sample_for_handcheck_is_seeded_stratified_and_shuffled():
    pairs = list(read_pairs(pairs_path()))
    sample = sample_for_handcheck(pairs, 300)
    assert len(sample) == min(300, len(pairs))
    assert [p.pair_id for p in sample] == [p.pair_id for p in sample_for_handcheck(pairs, 300)]
    assert {stratum(p) for p in sample} == {stratum(p) for p in pairs}
    strata_in_order = [stratum(p) for p in sample]
    assert strata_in_order != sorted(strata_in_order)


def _small_pair_file(tmp_path: Path) -> Path:
    path = tmp_path / "pairs.jsonl"
    write_pairs(
        path,
        [
            pair("a"),
            pair("b", link_type=None, split=Split.TRAIN, persona="p0_jay", template="exam_block"),
        ],
    )
    return path


def _rows(sheet: Path) -> list[dict[str, str]]:
    with sheet.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _fill(sheet: Path, answers: dict[str, tuple[str, str, str]], *, encoding: str = "utf-8"):
    """Answers by pair_id, translated to row numbers through the key file."""
    key = json.loads(key_path(sheet).read_text(encoding="utf-8"))
    row_of = {pair_id: number for number, pair_id in enumerate(key["rows"], start=1)}
    rows = _rows(sheet)
    for pair_id, answer in answers.items():
        row = rows[row_of[pair_id] - 1]
        row["human_link_type"], row["sure"], row["labeller"] = answer
    with sheet.open("w", encoding=encoding, newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SHEET_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row[column] for column in SHEET_COLUMNS})


def test_sheet_shows_memories_and_hides_pair_id_and_silver_label(tmp_path: Path):
    sheet = tmp_path / "sheet.csv"
    write_sheet(sheet, _small_pair_file(tmp_path))
    rows = _rows(sheet)
    assert tuple(rows[0]) == SHEET_COLUMNS
    flat = " ".join(" ".join(row.values()) for row in rows)
    for hidden in ("eligibility_of", "scenario", "p3_esha", "p0_jay", "jobs_v0"):
        assert hidden not in flat
    key = json.loads(key_path(sheet).read_text(encoding="utf-8"))
    assert sorted(key["rows"]) == ["a", "b"] and key["n"] == 300


def test_read_sheet_returns_labels_and_counts_blank_rows_as_pending(tmp_path: Path):
    sheet = tmp_path / "sheet.csv"
    write_sheet(sheet, _small_pair_file(tmp_path))
    _fill(sheet, {"a": ("none", "yes", "ORG")})
    labels, pending = read_sheet(sheet, jobs_registry())
    assert labels == [HandLabel("a", None, True, "ORG", "")]
    assert pending == 1


def test_read_sheet_accepts_the_byte_order_mark_of_spreadsheet_csv(tmp_path: Path):
    sheet = tmp_path / "sheet.csv"
    write_sheet(sheet, _small_pair_file(tmp_path))
    _fill(sheet, {"a": ("none", "yes", "ORG")}, encoding="utf-8-sig")
    labels, _ = read_sheet(sheet, jobs_registry())
    assert [label.pair_id for label in labels] == ["a"]


@pytest.mark.parametrize(
    ("answer", "message"),
    [
        (("eligibility_of", "yes", ""), "both required"),
        (("is_about", "yes", "ORG"), "not a link type"),
        (("none", "maybe", "ORG"), "yes or no"),
    ],
)
def test_read_sheet_refuses_a_half_filled_or_invalid_row(tmp_path: Path, answer, message):
    sheet = tmp_path / "sheet.csv"
    write_sheet(sheet, _small_pair_file(tmp_path))
    _fill(sheet, {"a": answer})
    with pytest.raises(SheetError, match=message):
        read_sheet(sheet, jobs_registry())


def test_read_sheet_refuses_a_duplicated_row(tmp_path: Path):
    sheet = tmp_path / "sheet.csv"
    write_sheet(sheet, _small_pair_file(tmp_path))
    first = _rows(sheet)[0]
    with sheet.open("a", encoding="utf-8", newline="") as handle:
        csv.writer(handle).writerow([first[column] for column in SHEET_COLUMNS])
    with pytest.raises(SheetError, match="duplicated"):
        read_sheet(sheet, jobs_registry())


def test_report_refuses_a_sheet_that_is_not_the_seeded_sample(tmp_path: Path):
    pairs_file = _small_pair_file(tmp_path)
    sheet = tmp_path / "sheet.csv"
    write_sheet(sheet, pairs_file)
    key = json.loads(key_path(sheet).read_text(encoding="utf-8"))
    key["rows"] = list(reversed(key["rows"]))
    key_path(sheet).write_text(json.dumps(key), encoding="utf-8")
    with pytest.raises(SheetError, match="not the seeded sample"):
        write_report(pairs_file, sheet, registry=jobs_registry(), results_root=tmp_path / "r")
    assert not (tmp_path / "r").exists()


def test_kappa_matches_a_hand_computed_value():
    table = Agreement()
    votes = [("x", "x")] * 20 + [("x", None)] * 5 + [(None, "x")] * 10 + [(None, None)] * 15
    for silver, human in votes:
        table.add(silver, human)
    # p_o = 35/50 = 0.7; p_e = 0.5*0.6 + 0.5*0.4 = 0.5; kappa = 0.4
    assert table.kappa() == pytest.approx(0.4)


def test_kappa_is_undefined_when_both_raters_use_one_class():
    table = Agreement()
    table.add("x", "x")
    assert table.kappa() is None


def test_agreement_is_reported_overall_by_provenance_and_by_stratum():
    pairs = [pair("a"), pair("b", provenance=Provenance.RULE), pair("c", link_type=None)]
    labels = [
        HandLabel("a", "eligibility_of", True, "ORG", ""),
        HandLabel("b", None, False, "ORG", ""),
        HandLabel("c", None, True, "ORG", ""),
    ]
    table = agreement(pairs, labels)
    assert table["overall"]["n"] == 3 and table["overall"]["silver_link_human_none"] == 1
    assert table["provenance=rule"]["detection_agreement"] == 0.0
    assert table["overall_sure_only"]["n"] == 2
    assert "stratum=test/scenario/link" in table


def test_gold_pairs_are_human_provenance_with_the_labeller_and_the_silver_label_kept():
    [gold] = gold_pairs([pair("a")], [HandLabel("a", None, False, "ORG", "")], jobs_registry())
    assert gold.provenance is Provenance.HUMAN and gold.labeller == "ORG"
    assert gold.link_type is None and gold.link_class is None
    assert gold.note == "silver scenario:eligibility_of; unsure"


def test_write_report_writes_agreement_and_the_gold_pair_file(tmp_path: Path):
    pairs_file = _small_pair_file(tmp_path)
    sheet = tmp_path / "sheet.csv"
    write_sheet(sheet, pairs_file)
    _fill(sheet, {"a": ("eligibility_of", "yes", "ORG")})
    run_dir = write_report(pairs_file, sheet, registry=jobs_registry(), results_root=tmp_path / "r")
    config = json.loads((run_dir / "config.json").read_text(encoding="utf-8"))
    assert (config["labelled"], config["pending"]) == (1, 1)
    assert config["sample"]["seed"] == 20261031
    [gold] = list(read_pairs(run_dir / "gold_pairs.jsonl"))
    assert gold.provenance is Provenance.HUMAN
    assert Counter(p.name for p in run_dir.iterdir()) == Counter(
        ["config.json", "metrics.json", "report.md", "gold_pairs.jsonl"]
    )
