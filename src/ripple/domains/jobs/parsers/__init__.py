"""Resume and JD parsers for the jobs domain (FR-1, FR-2; ADR-0024, ADR-0035).

Outputs are only the shared contract types in ripple.domains.jobs.vocabulary
(ParsedOpening, ParsedField, CandidateFact, TextSpan) plus ripple.core.intake.Statement
for a confirmed candidate, so the adapter and the API consume them without importing
anything from here but the functions below.
"""

from ripple.domains.jobs.parsers.envelope import strip_email_envelope
from ripple.domains.jobs.parsers.errors import UnparseableResumeError
from ripple.domains.jobs.parsers.jd import parse_jd
from ripple.domains.jobs.parsers.resume import candidate_to_statement, extract_text, parse_resume

__all__ = [
    "UnparseableResumeError",
    "candidate_to_statement",
    "extract_text",
    "parse_jd",
    "parse_resume",
    "strip_email_envelope",
]
