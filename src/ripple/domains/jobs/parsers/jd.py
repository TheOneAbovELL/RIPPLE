"""JD parser: LLM extraction, then deterministic post-validation (FR-2, I4, I5, ADR-0035).

    text -> Router (prompt jd_parser, schema JDParse) -> locate spans -> coerce values
         -> normalise deadline -> regex cross-check -> ParsedOpening

Every field that leaves this module has a span found in the text. A field the model
quoted wrongly is dropped and logged, not retried: the schema was valid, the content
was not, and a filter is cheaper and more predictable than another model call. The
regex extractors for cgpa_cutoff and deadline are a second opinion, not a replacement:
a disagreement lowers the model's confidence, and a value the model missed is added
at a lower confidence of its own.
"""

import logging
import re

from ripple.domains.jobs.parsers.dates import DateMatch, find_dates, normalise_deadline
from ripple.domains.jobs.parsers.numbers import cgpa_value, graduation_year
from ripple.domains.jobs.parsers.spans import locate_span, span_of_match
from ripple.domains.jobs.vocabulary import OpeningAttribute, ParsedField, ParsedOpening, TextSpan
from ripple.llm.client import Message
from ripple.llm.prompts import load_prompt
from ripple.llm.router import Router
from ripple.llm.schemas.jd import JDField, JDParse

log = logging.getLogger("ripple.domains.jobs.parsers.jd")

TASK = "jd_parser"
PROMPT_VERSION = 1

# Confidence ceilings applied by the post-validation (ADR-0035).
DISAGREEMENT_CONFIDENCE = 0.5  # model and regex read different values
REGEX_ONLY_CONFIDENCE = 0.6  # the model missed it; the regex found it

# The window after the keyword stops at a sentence end, so "CGPA: no bar. Stipend: 8 LPA"
# yields nothing; the value must not be followed by more digits or a percent sign.
_CGPA_PATTERNS = (
    re.compile(
        r"\b(?:cgpa|gpa|cpi)\b[^0-9\n.;]{0,30}?(?P<v>\d{1,2}(?:\.\d{1,2})?)(?![\d.]|\s*%)", re.I
    ),
    re.compile(
        r"(?<![\d.])(?P<v>\d{1,2}(?:\.\d{1,2})?)\s*(?:\+|or above|and above)?\s*"
        r"(?:cgpa|gpa|cpi)\b(?!\s*scale)",
        re.I,
    ),
)
_DEADLINE_KEYWORD = re.compile(
    r"\b(?:deadline|last date|apply (?:by|before)|applications? clos(?:e|es|ing)|"
    r"closes? on|register(?:ation)? (?:by|before|closes?)|due (?:by|on)|submit (?:by|before))\b",
    re.I,
)
_DEADLINE_WINDOW = 80  # characters after the keyword in which the date must start
_SENTENCE_END = re.compile(r"[.\n]")


async def parse_jd(
    router: Router, text: str, source_ref: str, *, trace_id: str | None = None
) -> ParsedOpening:
    system = load_prompt("jd_parser", PROMPT_VERSION)
    user = f"JD:\n```text\n{_fence_safe(text)}\n```"
    completion = await router.complete(
        TASK,
        [Message(role="system", content=system), Message(role="user", content=user)],
        JDParse,
        trace_id=trace_id,
    )
    fields = _validate_fields(completion.output.fields, text, trace_id)
    fields = _cross_check(fields, text, trace_id)
    return ParsedOpening(
        source_ref=source_ref,
        raw_text=text,
        fields=tuple(fields),
        summary=_summary(fields, text),
    )


def _fence_safe(text: str) -> str:
    """Evidence is sent inside a ``` fence; a fence inside the evidence must not close it."""
    return text.replace("```", "` ` `")


def _validate_fields(proposed: list[JDField], text: str, trace_id: str | None) -> list[ParsedField]:
    fields: list[ParsedField] = []
    seen: set[tuple[str, str | int | float | bool]] = set()
    for item in proposed:
        span = locate_span(text, item.quote)
        if span is None:
            _dropped("quote not in text", item.attribute, trace_id)
            continue
        field = _coerce(item, span)
        if field is None:
            _dropped("value not usable", item.attribute, trace_id)
            continue
        key = (field.attribute, field.value)
        if key in seen:
            continue
        seen.add(key)
        fields.append(field)
    return fields


def _dropped(reason: str, attribute: OpeningAttribute, trace_id: str | None) -> None:
    log.info(
        f"jd field dropped: {reason}", extra={"attribute": attribute.value, "trace_id": trace_id}
    )


def _coerce(item: JDField, span: TextSpan) -> ParsedField | None:
    attribute = item.attribute
    value: str | int | float | bool = item.value
    if attribute is OpeningAttribute.CGPA_CUTOFF:
        cutoff = cgpa_value(value)
        if cutoff is None:
            return None
        value = cutoff
    elif attribute is OpeningAttribute.BATCH:
        year = graduation_year(value)
        if year is None:
            return None
        value = year
    elif attribute is OpeningAttribute.DEADLINE:
        # The span is the verbatim source; the model's value may be a reformatted copy.
        # No year in either: dropped, because the contract wants ISO 8601 with offset
        # and guessing a year would create a wrong reminder silently (ADR-0035).
        normalised = normalise_deadline(span.text) or (
            normalise_deadline(value) if isinstance(value, str) else None
        )
        if normalised is None:
            return None
        value = normalised
    elif attribute is OpeningAttribute.ROLE_TYPE:
        role_type = _role_type(value) if isinstance(value, str) else None
        if role_type is None:
            return None
        value = role_type
    else:
        if not isinstance(value, str) or not value.strip():
            return None
        value = value.strip()
    return ParsedField(
        attribute=attribute.value, value=value, span=span, confidence=item.confidence
    )


def _cross_check(fields: list[ParsedField], text: str, trace_id: str | None) -> list[ParsedField]:
    checked = list(fields)
    regex_cgpa = _regex_cgpa(text)
    if regex_cgpa is not None:
        value, span = regex_cgpa
        checked = _reconcile(checked, OpeningAttribute.CGPA_CUTOFF, value, span, trace_id)
    regex_deadline = _regex_deadline(text)
    if regex_deadline is not None and regex_deadline.iso is not None:
        span = TextSpan(regex_deadline.start, regex_deadline.end, regex_deadline.text)
        checked = _reconcile(checked, OpeningAttribute.DEADLINE, regex_deadline.iso, span, trace_id)
    return checked


def _reconcile(
    fields: list[ParsedField],
    attribute: OpeningAttribute,
    regex_value: str | float,
    regex_span: TextSpan,
    trace_id: str | None,
) -> list[ParsedField]:
    extra = {"attribute": attribute.value, "trace_id": trace_id}
    if not any(f.attribute == attribute.value for f in fields):
        log.info("jd field added from regex", extra=extra)
        return [
            *fields,
            ParsedField(attribute.value, regex_value, regex_span, REGEX_ONLY_CONFIDENCE),
        ]
    result: list[ParsedField] = []
    for field in fields:
        if field.attribute == attribute.value and not _agree(field.value, regex_value):
            log.info("jd field disagrees with regex", extra=extra)
            field = ParsedField(
                field.attribute,
                field.value,
                field.span,
                min(field.confidence, DISAGREEMENT_CONFIDENCE),
            )
        result.append(field)
    return result


def _agree(model_value: str | int | float | bool, regex_value: str | float) -> bool:
    if isinstance(regex_value, float) and isinstance(model_value, int | float):
        return abs(float(model_value) - regex_value) < 1e-9
    return model_value == regex_value


def _regex_cgpa(text: str) -> tuple[float, TextSpan] | None:
    for pattern in _CGPA_PATTERNS:
        for match in pattern.finditer(text):
            value = cgpa_value(match.group("v"))
            if value is not None:
                return value, span_of_match(match, "v")
    return None


def _regex_deadline(text: str) -> DateMatch | None:
    """The first date that starts after a deadline keyword, in the same sentence or line."""
    dates = find_dates(text)
    for keyword in _DEADLINE_KEYWORD.finditer(text):
        sentence_end = _SENTENCE_END.search(text, keyword.end())
        window_end = min(
            keyword.end() + _DEADLINE_WINDOW,
            sentence_end.start() if sentence_end else len(text),
        )
        for date in dates:
            if keyword.end() <= date.start <= window_end:
                return date
    return None


def _role_type(value: str) -> str | None:
    lowered = value.strip().lower()
    if "intern" in lowered:
        return "internship"
    if "full" in lowered or lowered in {"ft", "fte"}:
        return "full_time"
    return None


def _summary(fields: list[ParsedField], text: str) -> str:
    """One line, built from parsed fields rather than written by the model (I5)."""
    title = next((f for f in fields if f.attribute == OpeningAttribute.TITLE), None)
    company = next((f for f in fields if f.attribute == OpeningAttribute.COMPANY), None)
    if title and company:
        return f"{title.value} at {company.value}"
    if title:
        return str(title.value)
    if company:
        return str(company.value)
    first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
    return first_line[:80] or "untitled opening"
