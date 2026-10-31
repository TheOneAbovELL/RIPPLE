"""Resume parser: pypdf text, LLM candidates, deterministic post-validation (FR-1, ADR-0024).

    pdf bytes -> extract_text -> parse_resume -> [CandidateFact] -> (user confirms)
             -> candidate_to_statement -> Intake

Nothing here writes a memory. Candidates are proposals the user confirms one by one
(I5); the API workstream holds them and calls `candidate_to_statement` on a yes. Every
candidate has a span found in the resume text; `content` is composed from attribute and
value by the profile template, so the model never writes the sentence that becomes a
memory.
"""

import logging
import re
import zlib
from io import BytesIO
from typing import Literal

from pypdf import PdfReader
from pypdf.errors import PyPdfError

from ripple.core.intake import Statement
from ripple.domains.jobs.parsers.errors import UnparseableResumeError
from ripple.domains.jobs.parsers.numbers import cgpa_value, graduation_year
from ripple.domains.jobs.parsers.spans import locate_span
from ripple.domains.jobs.profile import profile_content, profile_statement
from ripple.domains.jobs.vocabulary import CandidateFact, ProfileAttribute, TextSpan
from ripple.llm.client import Message
from ripple.llm.prompts import load_prompt
from ripple.llm.router import Router
from ripple.llm.schemas.resume import ResumeCandidate, ResumeParse

log = logging.getLogger("ripple.domains.jobs.parsers.resume")

TASK = "resume_parser"
PROMPT_VERSION = 1

# Mirrors Statement.origin (ripple.core.intake); the confirming caller decides it.
StatementOrigin = Literal["conversation", "inspector", "agent"]

# Lists the model failed to split: commas, semicolons, pipes, " and ". Never "/", which
# is part of names such as CI/CD and TCP/IP.
_SKILL_SEPARATOR = re.compile(r"\s*[,;|]\s*|\s+and\s+")
# pypdf reports damaged content streams with these as well as its own error type.
_PDF_FAILURES = (PyPdfError, ValueError, KeyError, IndexError, TypeError, zlib.error)


def extract_text(pdf_bytes: bytes) -> str:
    """Text layer of a PDF, pages joined by blank lines. Raises UnparseableResumeError.

    Synchronous and CPU-bound: an async caller runs it in a worker thread.
    """
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        # decrypt("") returns a PasswordType whose only falsy member is NOT_DECRYPTED.
        if reader.is_encrypted and not reader.decrypt(""):
            raise UnparseableResumeError("the PDF is password protected")
        pages = [page.extract_text() or "" for page in reader.pages]
    except _PDF_FAILURES as exc:
        raise UnparseableResumeError(f"the file is not a readable PDF ({exc})") from exc
    text = "\n\n".join(page.strip() for page in pages if page.strip())
    if not text.strip():
        raise UnparseableResumeError("the PDF has no text layer (scanned image?)")
    return text


async def parse_resume(
    router: Router, text: str, *, trace_id: str | None = None
) -> list[CandidateFact]:
    system = load_prompt("resume_parser", PROMPT_VERSION)
    user = f"RESUME:\n```text\n{text.replace('```', '` ` `')}\n```"
    completion = await router.complete(
        TASK,
        [Message(role="system", content=system), Message(role="user", content=user)],
        ResumeParse,
        trace_id=trace_id,
    )
    candidates: list[CandidateFact] = []
    seen: set[tuple[str, str | int | float | bool]] = set()
    for item in completion.output.candidates:
        span = locate_span(text, item.quote)
        if span is None:
            _dropped("quote not in text", item.attribute, trace_id)
            continue
        for candidate in _coerce(item, span, trace_id):
            key = (candidate.attribute, candidate.value)
            if key in seen:
                continue
            seen.add(key)
            candidates.append(candidate)
    return candidates


def candidate_to_statement(
    candidate: CandidateFact,
    user_id: str,
    source_ref: str,
    *,
    origin: StatementOrigin = "conversation",
) -> Statement:
    """The intake statement for a candidate the user has confirmed.

    Delegates to the profile builder so sensitivity, validation and wording have one
    source. Confidence is 1.0: the user, not the model, is now the source. The
    source_ref keeps the upload reference and the character span for the inspector.
    """
    return profile_statement(
        user_id,
        ProfileAttribute(candidate.attribute),
        candidate.value,
        content=candidate.content or None,
        source_ref=f"{source_ref}#{candidate.span.start}-{candidate.span.end}",
        origin=origin,
        confidence=1.0,
    )


def _dropped(reason: str, attribute: ProfileAttribute, trace_id: str | None) -> None:
    log.info(
        f"resume candidate dropped: {reason}",
        extra={"attribute": attribute.value, "trace_id": trace_id},
    )


def _coerce(item: ResumeCandidate, span: TextSpan, trace_id: str | None) -> list[CandidateFact]:
    attribute = ProfileAttribute(item.attribute)
    if attribute is ProfileAttribute.CGPA:
        cgpa = cgpa_value(item.value)
        if cgpa is None:
            _dropped("cgpa not a number on a ten-point scale", attribute, trace_id)
            return []
        return [_candidate(attribute, cgpa, span, item.confidence)]
    if attribute is ProfileAttribute.BATCH:
        year = graduation_year(item.value)
        if year is None:
            _dropped("batch not a year", attribute, trace_id)
            return []
        return [_candidate(attribute, year, span, item.confidence)]
    if not isinstance(item.value, str) or not item.value.strip():
        _dropped("value not text", attribute, trace_id)
        return []
    if attribute is ProfileAttribute.SKILL:
        # The prompt asks for one skill per candidate; a list that slipped through is
        # split here so each skill becomes its own fact, all citing the same line.
        skills = [s.strip() for s in _SKILL_SEPARATOR.split(item.value) if s.strip()]
        return [_candidate(attribute, skill, span, item.confidence) for skill in skills]
    return [_candidate(attribute, item.value.strip(), span, item.confidence)]


def _candidate(
    attribute: ProfileAttribute, value: str | int | float, span: TextSpan, confidence: float
) -> CandidateFact:
    return CandidateFact(
        attribute=attribute.value,
        value=value,
        span=span,
        confidence=confidence,
        # The template, not the model, writes the memory sentence (I5).
        content=profile_content(attribute, value),
    )
