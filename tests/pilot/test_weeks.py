from datetime import UTC, datetime, timedelta, timezone

import pytest

from ripple.pilot.weeks import parse_week, week_of

IST = timezone(timedelta(hours=5, minutes=30))
# "2026-W45" with full-width digits: `\d` would accept them, [0-9] must not.
FULLWIDTH_YEAR = "".join(chr(0xFF10 + int(digit)) for digit in "2026") + "-W45"


def test_parse_week_is_monday_to_monday_utc():
    week = parse_week("2026-W45")
    assert week.start == datetime(2026, 11, 2, tzinfo=UTC)
    assert week.end == datetime(2026, 11, 9, tzinfo=UTC)


def test_parse_week_handles_iso_year_boundary():
    # ISO 2027-W01 starts on Monday 2027-01-04.
    assert parse_week("2027-W01").start == datetime(2027, 1, 4, tzinfo=UTC)


@pytest.mark.parametrize(
    "label",
    ["2026-45", "2026-W5", "2026W45", "2026-W00", "2027-W53", "2026-W45\n", FULLWIDTH_YEAR],
)
def test_parse_week_rejects_malformed_or_impossible_labels(label: str):
    with pytest.raises(ValueError):
        parse_week(label)


def test_week_contains_is_half_open():
    week = parse_week("2026-W45")
    assert week.contains(week.start)
    assert not week.contains(week.end)
    assert week.contains(week.end - timedelta(microseconds=1))


def test_week_of_converts_to_utc_first():
    # Monday 01:00 in India is Sunday 19:30 UTC: the previous ISO week.
    assert week_of(datetime(2026, 11, 2, 1, 0, tzinfo=IST)).label == "2026-W44"


def test_week_of_rejects_a_naive_datetime():
    with pytest.raises(ValueError):
        week_of(datetime(2026, 11, 2, 1, 0))
