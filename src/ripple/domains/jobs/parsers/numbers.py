"""Numeric coercions shared by the JD and resume parsers (ADR-0035 point 2)."""

import re

# Both parsers accept CGPA on a ten-point scale only; a 4-point GPA is left to the user
# to correct in the inspector (handover: open problem "scale").
CGPA_SCALE_MAX = 10.0

_NUMBER = re.compile(r"\d+(?:\.\d+)?")
_YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
# "2023-27" (common on Indian resumes): the suffix is the graduation year's last two digits.
_YEAR_RANGE_SHORT = re.compile(r"\b((?:19|20)\d{2})\s*[-–/]\s*(\d{2})\b")  # noqa: RUF001  hyphen or en dash


def first_number(value: str | int | float | bool) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    match = _NUMBER.search(value)
    return float(match.group(0)) if match else None


def cgpa_value(value: str | int | float | bool) -> float | None:
    number = first_number(value)
    return None if number is None or number > CGPA_SCALE_MAX else number


def graduation_year(value: str | int | float | bool) -> int | None:
    """An int year, or the last year in text like '2023-2027' or '2023-27'."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return int(value) if 1900 <= value <= 2100 else None
    short = _YEAR_RANGE_SHORT.search(value)
    if short:
        return int(short.group(1)[:2] + short.group(2))
    years = _YEAR.findall(value)
    return int(years[-1]) if years else None
