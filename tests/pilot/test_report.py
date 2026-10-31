"""The weekly report writes results/pilot/<week>/ from the sources (ADR-0106, I8)."""

import asyncio
import json
from datetime import timedelta
from pathlib import Path

import pytest

from ripple.pilot import report
from ripple.pilot.metrics import TBD
from ripple.pilot.report import (
    ReportExistsError,
    WeekNotOverError,
    first_versions,
    generate,
    main,
    parse_args,
)
from tests.pilot.support import (
    ACCOUNTS,
    EXPECTED_SHARE,
    NOTE_SENTINEL,
    VERSIONS,
    WEEK,
    StaticHistory,
    constructed_sources,
)

AFTER_WEEK = WEEK.end + timedelta(hours=6)
FILES = ["config.json", "metrics.json", "report.md"]


def run(tmp_path: Path, *, extra_active: int = 0, **kwargs) -> Path:
    async def go() -> Path:
        return await generate(
            await constructed_sources(extra_active),
            WEEK,
            results_dir=tmp_path,
            now=kwargs.pop("now", AFTER_WEEK),
            code_version="abc1234",
            **kwargs,
        )

    return asyncio.run(go())


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_generate_small_cohort_goes_to_the_gitignored_raw_folder(tmp_path: Path):
    week_dir = run(tmp_path)
    assert week_dir == tmp_path / "raw" / "2026-W45"
    assert sorted(p.name for p in week_dir.iterdir()) == FILES
    assert read_json(week_dir / "config.json")["published"] is False


def test_generate_publishable_cohort_goes_to_the_week_folder(tmp_path: Path):
    week_dir = run(tmp_path, extra_active=1)  # 4 + 1 = 5 active students
    assert week_dir == tmp_path / "2026-W45"
    assert sorted(p.name for p in week_dir.iterdir()) == FILES
    assert read_json(week_dir / "config.json")["published"] is True


def test_generate_metrics_json_carries_the_computed_share(tmp_path: Path):
    share = read_json(run(tmp_path) / "metrics.json")["pilot_metrics"]["saved_or_applied_share"]
    assert (share["numerator"], share["denominator"], share["value"]) == EXPECTED_SHARE


def test_generate_config_records_provenance(tmp_path: Path):
    config = read_json(run(tmp_path) / "config.json")
    assert config["week"] == "2026-W45"
    assert config["code_version"] == "abc1234"
    assert config["partial"] is False
    assert config["generated_at"] == AFTER_WEEK.isoformat()
    assert config["sources"].startswith("constructed test week")


def test_generate_report_md_shows_each_computed_value_with_its_counts(tmp_path: Path):
    week_dir = run(tmp_path)
    text = (week_dir / "report.md").read_text(encoding="utf-8")
    pilot = read_json(week_dir / "metrics.json")["pilot_metrics"]
    computed = [m for m in pilot.values() if m["value"] != TBD]
    assert len(computed) == 2
    for metric in computed:
        assert f"| {metric['value']} | {metric['numerator']} / {metric['denominator']}:" in text
    assert text.count(TBD) == 3
    assert "Not for publication: 4 active students" in text


def test_generate_output_holds_no_user_id_or_note(tmp_path: Path):
    week_dir = run(tmp_path)
    text = "".join(p.read_text(encoding="utf-8") for p in week_dir.iterdir())
    assert NOTE_SENTINEL not in text
    for user_id in ACCOUNTS:
        assert f'"{user_id}"' not in text and f" {user_id} " not in text


def test_generate_refuses_an_unfinished_week(tmp_path: Path):
    with pytest.raises(WeekNotOverError):
        run(tmp_path, now=WEEK.end - timedelta(seconds=1))
    assert list(tmp_path.iterdir()) == []


def test_generate_marks_a_partial_week_when_allowed(tmp_path: Path):
    week_dir = run(tmp_path, now=WEEK.start + timedelta(days=3), partial=True)
    assert read_json(week_dir / "config.json")["partial"] is True
    assert "Partial week" in (week_dir / "report.md").read_text(encoding="utf-8")


def test_generate_refuses_to_overwrite_an_existing_week(tmp_path: Path):
    run(tmp_path)
    with pytest.raises(ReportExistsError):
        run(tmp_path)


def test_generate_overwrite_records_the_version_it_replaced(tmp_path: Path):
    run(tmp_path)
    later = AFTER_WEEK + timedelta(days=1)
    config = read_json(run(tmp_path, now=later, overwrite=True) / "config.json")
    assert config["generated_at"] == later.isoformat()
    assert config["replaces_generated_at"] == AFTER_WEEK.isoformat()


def test_first_versions_maps_known_versions_and_skips_forgotten_ids():
    history = StaticHistory(versions=VERSIONS)
    canonical = asyncio.run(first_versions(history, ["o1v2", "o1", "forgotten"]))
    assert canonical == {"o1": "o1", "o1v2": "o1"}


def test_parse_args_rejects_a_malformed_week():
    with pytest.raises(SystemExit):
        parse_args(["--week", "2026-45"])


def test_parse_args_code_version_is_passed_through():
    args = parse_args(["--week", "2026-W45", "--code-version", "ghcr.io/x/ripple:1"])
    assert args.code_version == "ghcr.io/x/ripple:1"


def test_main_without_database_url_exits_2(monkeypatch: pytest.MonkeyPatch, capsys, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    code = main(["--week", "2026-W45", "--results-dir", str(tmp_path), "--code-version", "x"])
    assert code == 2
    assert "DATABASE_URL is not set" in capsys.readouterr().err
    assert list(tmp_path.iterdir()) == []


def test_git_short_sha_outside_a_repository_is_uncommitted(tmp_path: Path):
    assert report.git_short_sha(tmp_path) == "uncommitted"
