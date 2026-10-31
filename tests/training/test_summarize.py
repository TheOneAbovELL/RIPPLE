"""training.summarize (ADR-0127): mean and spread over run folders, from files only."""

import json
from pathlib import Path

import pytest
from training.evaluate import LinkerSpec, run
from training.summarize import spread, summarize, write

from tests.training.test_evaluate import ScriptedLinker, _pair_file


def test_spread_skips_null_values_and_has_no_sd_for_one_value():
    assert spread([0.5, None]) == {"n": 1, "mean": 0.5, "sd": None, "min": 0.5, "max": 0.5}
    assert spread([None]) == {"n": 0, "mean": None, "sd": None, "min": None, "max": None}
    assert spread([0.2, 0.4])["sd"] == pytest.approx(0.1414, abs=1e-4)


def test_summarize_groups_runs_by_linker_and_track(tmp_path: Path):
    pairs = _pair_file(tmp_path)
    found = run(LinkerSpec("s", ScriptedLinker("eligibility_of")), pairs, results_root=tmp_path)
    silent = run(LinkerSpec("s", ScriptedLinker(None)), pairs, results_root=tmp_path)
    other = run(LinkerSpec("t", ScriptedLinker(None)), pairs, results_root=tmp_path)
    [s_group, t_group] = summarize([found, silent, other])["groups"]  # type: ignore[misc]
    assert (s_group["linker"], len(s_group["runs"])) == ("s", 2)
    # found: one tp of one gold link -> recall 1; silent: recall 0.
    assert s_group["cells"]["overall"]["recall"]["mean"] == 0.5
    assert t_group["linker"] == "t"


def test_write_puts_summary_and_report_in_a_fresh_results_folder(tmp_path: Path):
    pairs = _pair_file(tmp_path)
    one = run(LinkerSpec("s", ScriptedLinker(None)), pairs, results_root=tmp_path / "runs")
    out = write([one], results_root=tmp_path / "r")
    assert "_linkpairs_summary_" in out.name
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert summary["groups"][0]["runs"] == [one.resolve().as_posix()]
    assert "summary over runs" in (out / "report.md").read_text(encoding="utf-8")
    assert write([one], results_root=tmp_path / "r") != out


def test_summarize_refuses_a_folder_that_is_not_a_link_pair_run(tmp_path: Path):
    (tmp_path / "config.json").write_text(json.dumps({"suite": "v0"}), encoding="utf-8")
    (tmp_path / "metrics.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="not a link-pair run"):
        summarize([tmp_path])


def test_summarize_counts_a_folder_named_twice_once(tmp_path: Path):
    one = run(LinkerSpec("s", ScriptedLinker(None)), _pair_file(tmp_path), results_root=tmp_path)
    [group] = summarize([one, one])["groups"]  # type: ignore[misc]
    assert len(group["runs"]) == 1


def test_summarize_never_averages_runs_on_different_base_models(tmp_path: Path):
    pairs = _pair_file(tmp_path)
    tiny = LinkerSpec("trained", ScriptedLinker(None), models={"base_model": "scratch:tiny"})
    bert = LinkerSpec("trained", ScriptedLinker(None), models={"base_model": "modernbert"})
    runs = [run(spec, pairs, results_root=tmp_path) for spec in (tiny, bert)]
    groups = summarize(runs)["groups"]
    assert [g["base_model"] for g in groups] == ["modernbert", "scratch:tiny"]  # type: ignore[index]


def test_summarize_never_averages_runs_on_different_pair_files(tmp_path: Path):
    first = run(
        LinkerSpec("s", ScriptedLinker(None)), _pair_file(tmp_path / "a"), results_root=tmp_path
    )
    other = tmp_path / "b"
    other.mkdir()
    pairs = _pair_file(other)
    pairs.write_text(pairs.read_text(encoding="utf-8").splitlines()[0] + "\n", encoding="utf-8")
    second = run(LinkerSpec("s", ScriptedLinker(None)), pairs, results_root=tmp_path)
    assert len(summarize([first, second])["groups"]) == 2  # type: ignore[arg-type]
