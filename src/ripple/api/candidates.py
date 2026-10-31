"""Between the parsers' `CandidateFact` and the stored `ResumeCandidate` (ADR-0043).

Lives in the API layer, not in storage, because storage may import only core
(docs/02) and `CandidateFact` is jobs vocabulary.
"""

from datetime import datetime

from ripple.domains.jobs.vocabulary import CandidateFact, TextSpan
from ripple.storage.candidates import ResumeCandidate


def candidate_from_fact(
    user_id: str, upload_id: str, fact: CandidateFact, now: datetime
) -> ResumeCandidate:
    return ResumeCandidate(
        user_id=user_id,
        upload_id=upload_id,
        attribute=fact.attribute,
        value=fact.value,
        span_start=fact.span.start,
        span_end=fact.span.end,
        span_text=fact.span.text,
        confidence=fact.confidence,
        content=fact.content,
        created_at=now,
    )


def fact_of(candidate: ResumeCandidate) -> CandidateFact:
    return CandidateFact(
        attribute=candidate.attribute,
        value=candidate.value,
        span=TextSpan(start=candidate.span_start, end=candidate.span_end, text=candidate.span_text),
        confidence=candidate.confidence,
        content=candidate.content,
    )
