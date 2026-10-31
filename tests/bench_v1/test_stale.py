"""STALE loader (ADR-0103): local path only, loud on a missing copy or a different shape."""

import json
from pathlib import Path

import pytest
from bench import stale
from bench.stale import (
    STALE_PATH_VAR,
    StaleFormatError,
    iter_stale,
    load_stale,
    stale_path_from_env,
    summarise,
)

from ripple.core.errors import ConfigurationError

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "stale"


@pytest.mark.parametrize("environ", [{}, {STALE_PATH_VAR: ""}, {STALE_PATH_VAR: "   "}])
def test_stale_path_from_env_names_the_variable_when_unset(environ):
    with pytest.raises(ConfigurationError, match=STALE_PATH_VAR):
        stale_path_from_env(environ)


def test_stale_path_from_env_names_the_variable_when_the_path_is_missing(tmp_path):
    with pytest.raises(ConfigurationError, match=f"{STALE_PATH_VAR}=.*does not exist"):
        stale_path_from_env({STALE_PATH_VAR: str(tmp_path / "nowhere")})


def test_load_stale_reads_the_hand_written_fixture_folder():
    items = load_stale({STALE_PATH_VAR: str(FIXTURE_DIR)})
    assert [item.item_id for item in items] == ["tiny-001", "tiny-002"]
    assert items[0].sessions[1].date.isoformat() == "2026-05-14"
    assert summarise(items) == {
        "items": 2,
        "sessions": 4,
        "turns": 5,
        "conflict_types": {"explicit": 1, "implicit": 1},
    }


def test_load_stale_reads_a_single_file():
    assert len(load_stale({STALE_PATH_VAR: str(FIXTURE_DIR / "tiny.jsonl")})) == 2


def test_a_folder_without_jsonl_files_is_a_configuration_error(tmp_path):
    with pytest.raises(ConfigurationError, match=r"no \.jsonl files"):
        load_stale({STALE_PATH_VAR: str(tmp_path)})


def _write_item(path: Path, **changes) -> None:
    first = json.loads((FIXTURE_DIR / "tiny.jsonl").read_text(encoding="utf-8").splitlines()[0])
    first.update(changes)
    path.write_text(json.dumps(first) + "\n", encoding="utf-8")


def test_a_field_the_declared_shape_does_not_know_stops_the_load_with_its_location(tmp_path):
    _write_item(tmp_path / "a.jsonl", haystack=["unexpected"])
    with pytest.raises(StaleFormatError, match=r"a\.jsonl:1: not in the ADR-0103 shape"):
        list(iter_stale(tmp_path))


def test_a_missing_required_field_stops_the_load(tmp_path):
    first = json.loads((FIXTURE_DIR / "tiny.jsonl").read_text(encoding="utf-8").splitlines()[0])
    del first["question"]
    (tmp_path / "a.jsonl").write_text(json.dumps(first) + "\n", encoding="utf-8")
    with pytest.raises(StaleFormatError, match=r"a\.jsonl:1"):
        list(iter_stale(tmp_path))


def test_a_line_that_is_not_json_stops_the_load(tmp_path):
    (tmp_path / "a.jsonl").write_text("{not json\n", encoding="utf-8")
    with pytest.raises(StaleFormatError, match=r"a\.jsonl:1"):
        list(iter_stale(tmp_path))


def test_evidence_must_name_sessions_of_the_item(tmp_path):
    _write_item(tmp_path / "a.jsonl", evidence_session_ids=["s9"])
    with pytest.raises(StaleFormatError, match="unknown sessions"):
        list(iter_stale(tmp_path))


def test_a_byte_order_mark_is_not_a_format_error(tmp_path):
    text = (FIXTURE_DIR / "tiny.jsonl").read_text(encoding="utf-8")
    (tmp_path / "a.jsonl").write_text(text, encoding="utf-8-sig")
    assert len(list(iter_stale(tmp_path))) == 2


def test_non_utf8_bytes_are_a_format_error_not_a_crash(tmp_path):
    (tmp_path / "a.jsonl").write_bytes(b"\xff\xfe\x00garbage")
    with pytest.raises(StaleFormatError, match="not UTF-8"):
        list(iter_stale(tmp_path))


def test_an_empty_copy_is_refused(tmp_path):
    (tmp_path / "a.jsonl").write_text("\n", encoding="utf-8")
    with pytest.raises(StaleFormatError, match="no items"):
        load_stale({STALE_PATH_VAR: str(tmp_path)})


def test_a_duplicate_item_id_across_files_stops_the_load(tmp_path):
    _write_item(tmp_path / "a.jsonl")
    _write_item(tmp_path / "b.jsonl")
    with pytest.raises(StaleFormatError, match="duplicate item_id 'tiny-001'"):
        list(iter_stale(tmp_path))


def test_main_exits_2_and_says_why_when_stale_is_not_configured(monkeypatch, capsys):
    monkeypatch.delenv(STALE_PATH_VAR, raising=False)
    assert stale.main([]) == 2
    assert STALE_PATH_VAR in capsys.readouterr().err


def test_main_prints_the_summary_of_a_local_copy(monkeypatch, capsys):
    monkeypatch.setenv(STALE_PATH_VAR, str(FIXTURE_DIR))
    assert stale.main([]) == 0
    assert "items: 2" in capsys.readouterr().out
