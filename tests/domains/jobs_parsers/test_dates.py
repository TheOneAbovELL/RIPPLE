from datetime import UTC

import pytest

from ripple.domains.jobs.parsers.dates import find_dates, normalise_deadline


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2026-11-15", "2026-11-15T23:59:59+05:30"),
        ("2026-11-15T18:00:00Z", "2026-11-15T18:00:00+00:00"),
        ("2026-11-15T23:59:00+05:30", "2026-11-15T23:59:00+05:30"),
        ("15 November 2026", "2026-11-15T23:59:59+05:30"),
        ("15th Nov, 2026 at 23:59", "2026-11-15T23:59:00+05:30"),
        ("Apply by 15 November 2026, 11:59 PM IST", "2026-11-15T23:59:00+05:30"),
        ("November 15, 2026 12:00 am", "2026-11-15T00:00:00+05:30"),
        ("Nov 15 2026 5pm UTC", "2026-11-15T17:00:00+00:00"),
        ("15/11/2026", "2026-11-15T23:59:59+05:30"),
        ("15-11-26 5 PM", "2026-11-15T17:00:00+05:30"),
    ],
)
def test_normalise_deadline_returns_iso_with_offset(raw, expected):
    assert normalise_deadline(raw) == expected


def test_normalise_deadline_returns_none_when_year_is_missing():
    assert normalise_deadline("applications close 15 Nov") is None
    assert normalise_deadline("by Nov 15 at 5 PM") is None


def test_normalise_deadline_skips_impossible_dates():
    assert normalise_deadline("31 February 2026") is None


def test_normalise_deadline_uses_the_default_timezone_given():
    assert normalise_deadline("15 November 2026", default_tz=UTC) == "2026-11-15T23:59:59+00:00"


def test_find_dates_ignores_version_numbers_and_stray_numbers():
    matches = find_dates("Python 3.12 preferred; 2 rounds; deadline 20/11/26 5pm UTC")
    assert [m.text for m in matches] == ["20/11/26 5pm UTC"]


def test_find_dates_keeps_source_offsets():
    text = "Drive on 01 Dec 2026. Apply by 15 November 2026."
    [drive, apply] = find_dates(text)
    assert text[drive.start : drive.end] == "01 Dec 2026"
    assert text[apply.start : apply.end] == "15 November 2026"


def test_normalise_deadline_keeps_the_date_when_the_time_is_impossible():
    assert normalise_deadline("15 November 2026, 24:00 IST") == "2026-11-15T23:59:59+05:30"


def test_find_dates_does_not_read_a_word_starting_with_am_as_a_time():
    [match] = find_dates("15 November 2026 5 amazing rounds")
    assert match.text == "15 November 2026"
