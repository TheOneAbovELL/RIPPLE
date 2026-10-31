"""ISO weeks as half-open UTC windows (ADR-0106).

UTC because the delivery log stores digest days as UTC days (ADR-0056, ADR-0095); a
report in local time would split one digest day across two weeks.
"""

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

# ASCII digits only and a full match: the label becomes a directory name.
_WEEK = re.compile(r"(?P<year>[0-9]{4})-W(?P<week>[0-9]{2})")


@dataclass(frozen=True)
class Week:
    label: str  # "2026-W45"
    start: datetime  # Monday 00:00 UTC, inclusive
    end: datetime  # the next Monday 00:00 UTC, exclusive

    def contains(self, moment: datetime) -> bool:
        return self.start <= moment < self.end


def parse_week(label: str) -> Week:
    """`YYYY-Www` → the week; ValueError for anything else, including W53 in a
    52-week year."""
    match = _WEEK.fullmatch(label)
    if match is None:
        raise ValueError(f"week must look like 2026-W45, got {label!r}")
    monday = date.fromisocalendar(int(match.group("year")), int(match.group("week")), 1)
    start = datetime.combine(monday, time(), tzinfo=UTC)
    return Week(label=label, start=start, end=start + timedelta(days=7))


def week_of(moment: datetime) -> Week:
    if moment.tzinfo is None:
        raise ValueError("week_of needs a timezone-aware datetime")
    year, week, _ = moment.astimezone(UTC).isocalendar()
    return parse_week(f"{year:04d}-W{week:02d}")
