"""Deterministic date normaliser for deadlines (ADR-0035).

No LLM and no third-party date library: the shapes placement JDs use are few, and a
hand-written matcher stays predictable and testable. Policy:
- A date without a year is not guessed; the caller keeps the raw text at lower confidence.
- A date without a time means the end of that day (deadlines close at midnight, not at
  00:00).
- Numeric dates are day-first (15/11/2026): the product serves Indian campuses.
- The timezone is the one the text names (IST, UTC, GMT) or the default, IST.
"""

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone, tzinfo

IST = timezone(timedelta(hours=5, minutes=30), "IST")
_NAMED_ZONES: dict[str, tzinfo] = {"IST": IST, "UTC": UTC, "GMT": UTC}
_END_OF_DAY = (23, 59, 59)
_INVALID = datetime.min  # sentinel: the regex matched but the numbers are not a date

_MONTHS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}  # fmt: skip
_MONTH = r"(?P<mon>" + "|".join(sorted(_MONTHS, key=len, reverse=True)) + r")\.?"
_DAY = r"(?P<d>\d{1,2})(?:st|nd|rd|th)?"
_YEAR = r"(?P<y>\d{4})"
# A time needs a colon or an am/pm marker so a stray number ("2 rounds") is not a time.
_TIME = (
    r"(?:[ ,]*(?:at|by)?\s*(?P<H>\d{1,2})"
    r"(?::(?P<M>\d{2})(?::(?P<S>\d{2}))?\s*(?P<ampm>[ap]\.?m\.?\b)?|\s*(?P<ampm2>[ap]\.?m\.?\b))"
    r"(?:\s*(?P<tz>IST|UTC|GMT)\b)?)?"
)
_PATTERNS: tuple[re.Pattern[str], ...] = (
    # ISO 8601: 2026-11-15, 2026-11-15T23:59:00+05:30
    re.compile(
        r"\b(?P<y>\d{4})-(?P<m>\d{2})-(?P<d>\d{2})"
        r"(?:[T ](?P<H>\d{2}):(?P<M>\d{2})(?::(?P<S>\d{2}))?(?P<off>Z|[+-]\d{2}:?\d{2})?)?"
    ),
    # 15 November 2026, 15th Nov, 2026 11:59 PM IST
    re.compile(rf"\b{_DAY}\s+{_MONTH},?\s+{_YEAR}\b{_TIME}", re.IGNORECASE),
    # November 15, 2026 / Nov 15 2026
    re.compile(rf"\b{_MONTH}\s+{_DAY},?\s+{_YEAR}\b{_TIME}", re.IGNORECASE),
    # 15/11/2026, 15-11-26 (day first; no dot separator, which would match version numbers)
    re.compile(
        r"\b(?P<d>\d{1,2})[/-](?P<m>\d{1,2})[/-](?P<y>\d{4}|\d{2})\b" + _TIME, re.IGNORECASE
    ),
    # Year missing: 15 November / Nov 15 — matched so the caller can see it, never guessed.
    re.compile(rf"\b{_DAY}\s+{_MONTH}\b(?!,?\s*\d{{4}})", re.IGNORECASE),
    re.compile(rf"\b{_MONTH}\s+{_DAY}\b(?!,?\s*\d{{4}})", re.IGNORECASE),
)


@dataclass(frozen=True)
class DateMatch:
    start: int
    end: int
    text: str
    # None when the text gives no year: the match exists but cannot be normalised.
    moment: datetime | None

    @property
    def iso(self) -> str | None:
        return None if self.moment is None else self.moment.isoformat()


def find_dates(text: str, *, default_tz: tzinfo = IST) -> list[DateMatch]:
    """Every date-like phrase in reading order; overlapping matches keep the earlier pattern."""
    found: list[DateMatch] = []
    for pattern in _PATTERNS:
        for match in pattern.finditer(text):
            if any(m.start < match.end() and match.start() < m.end for m in found):
                continue
            moment = _moment_of(match, default_tz)
            if moment is _INVALID:
                continue
            found.append(DateMatch(match.start(), match.end(), match.group(0), moment))
    return sorted(found, key=lambda m: m.start)


def normalise_deadline(raw: str, *, default_tz: tzinfo = IST) -> str | None:
    """ISO 8601 with offset for the first dated phrase in `raw`; None when the year is missing."""
    for match in find_dates(raw, default_tz=default_tz):
        if match.moment is not None:
            return match.moment.isoformat()
    return None


def _moment_of(match: re.Match[str], default_tz: tzinfo) -> datetime | None:
    groups = match.groupdict()
    year_text = groups.get("y")
    if year_text is None:
        return None
    year = int(year_text)
    if year < 100:
        year += 2000
    month = _MONTHS[groups["mon"].lower()] if groups.get("mon") else int(groups["m"])
    day = int(groups["d"])
    hour, minute, second = _END_OF_DAY
    if groups.get("H") is not None:
        hour = int(groups["H"])
        minute = int(groups["M"] or 0)
        second = int(groups["S"] or 0)
        ampm = (groups.get("ampm") or groups.get("ampm2") or "").replace(".", "").lower()
        if ampm == "pm" and hour < 12:
            hour += 12
        if ampm == "am" and hour == 12:
            hour = 0
    zone = _zone_of(groups.get("off"), groups.get("tz"), default_tz)
    try:
        return datetime(year, month, day, hour, minute, second, tzinfo=zone)
    except ValueError:
        pass
    # An impossible time ("24:00") does not lose the date: fall back to the end of day.
    try:
        return datetime(year, month, day, *_END_OF_DAY, tzinfo=zone)
    except ValueError:
        return _INVALID


def _zone_of(offset: str | None, name: str | None, default_tz: tzinfo) -> tzinfo:
    if offset:
        if offset == "Z":
            return UTC
        sign = 1 if offset[0] == "+" else -1
        digits = offset[1:].replace(":", "")
        return timezone(sign * timedelta(hours=int(digits[:2]), minutes=int(digits[2:])))
    if name:
        return _NAMED_ZONES[name.upper()]
    return default_tz
