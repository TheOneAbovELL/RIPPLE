# WS-2 handover: Resume and JD parsers
Status: **Locally verified** · 2026-10-19 · ADR-0035

## What was built
- `src/ripple/domains/jobs/parsers/`
  - `jd.py` — `parse_jd(router, text, source_ref, *, trace_id=None) -> ParsedOpening`
    (task `jd_parser`, prompt `jd_parser.v1`, schema `JDParse`). Span location, value
    coercion, deadline normalisation from the span text, regex cross-check for
    `cgpa_cutoff` and `deadline` (same-sentence window), summary from fields.
  - `resume.py` — `extract_text(pdf_bytes) -> str` (pypdf; raises
    `UnparseableResumeError` on no text layer, damaged bytes or a password),
    `parse_resume(router, text, *, trace_id=None) -> list[CandidateFact]` (task
    `resume_parser`, prompt `resume_parser.v1`, schema `ResumeParse`),
    `candidate_to_statement(candidate, user_id, source_ref, *, origin="conversation")
    -> ripple.core.intake.Statement` (delegates to WS-1's `profile_statement`).
  - `envelope.py` — `strip_email_envelope(text) -> str`.
  - `dates.py` — `find_dates`, `normalise_deadline` (ISO 8601 with offset; IST default).
  - `numbers.py` — `cgpa_value`, `graduation_year` (shared coercions).
  - `spans.py` — `locate_span(text, quote) -> TextSpan | None`.
  - `errors.py` — `UnparseableResumeError(RippleError)`.
- `src/ripple/llm/schemas/jd.py`, `src/ripple/llm/schemas/resume.py` (seven resume
  attributes only; `accepted_offer`, `looking`, `resume` are refused by the schema).
- `src/ripple/llm/prompts/jd_parser.v1.md`, `src/ripple/llm/prompts/resume_parser.v1.md`
- `tests/domains/jobs_parsers/` (86 tests; helpers in `support.py`), plus the empty
  package markers `tests/domains/__init__.py` and `tests/domains/jobs_parsers/__init__.py`.
- `docs/adr/0035-parser-post-validation-policy.md`, `docs/learning/parsers.md`.

Outputs are only the contract types from `vocabulary.py` (`ParsedOpening`,
`ParsedField`, `CandidateFact`, `TextSpan`) and `Statement`.

## How consumers call it
```python
from ripple.domains.jobs.parsers import (
    parse_jd,
    strip_email_envelope,
    extract_text,
    parse_resume,
    candidate_to_statement,
    UnparseableResumeError,
)

opening = await parse_jd(
    router, strip_email_envelope(email_text), "email:<id>"
)  # spans index raw_text
text = await asyncio.to_thread(extract_text, pdf_bytes)  # sync, CPU-bound
candidates = await parse_resume(router, text)  # hold until the user confirms
statement = candidate_to_statement(candidate, user_id, "resume:<upload id>")  # on a yes
await intake.ingest(statement)
```
Router config needs tasks `jd_parser` and `resume_parser`.

## Verification (run 2026-10-19 after the review fixes, WS-2 paths only)
```
$ uv run ruff check src/ripple/domains/jobs/parsers src/ripple/llm/schemas tests/domains/jobs_parsers
All checks passed!
$ uv run ruff format src/ripple/domains/jobs/parsers src/ripple/llm/schemas tests/domains/jobs_parsers
25 files left unchanged
$ uv run pyright src/ripple/domains/jobs/parsers src/ripple/llm/schemas tests/domains/jobs_parsers
0 errors, 0 warnings, 0 informations
$ uv run pytest tests/domains/jobs_parsers -q
........................................................................ [ 83%]
..............                                                           [100%]
86 passed in 0.79s
```

## Code review (code-reviewer subagent, same day)
Blockers fixed: a year-less deadline was kept as raw text, which WS-1's
`parse_deadline` would have rejected and failed the whole opening (now dropped and
logged); the cgpa regex could read "Stipend: 8 LPA" or "75%" as a cutoff (window now
stops at a sentence end, value may not be followed by a digit or `%`; invariant test
added). Majors fixed: resume schema restricted to seven attributes; `/` no longer
splits skills; deadline normalised from the span before the model's value; deadline
keyword window ends at the sentence; `2023-27` reads as 2027; pypdf's plain
`ValueError`/`KeyError`/`IndexError`/`zlib.error` wrapped as `UnparseableResumeError`;
`candidate_to_statement` delegates to WS-1's `profile_statement`; tests added for
dedupe, role types, confidence passthrough, multi-page and encrypted PDFs, and an
end-to-end ingest through `Intake` with the in-memory store. Minors fixed: header
lines only stripped at the top or after a marker; disclaimer cut before signature;
`--` cut only in the tail; impossible times fall back to end of day; am/pm needs a word
boundary; `trace_id` threaded through router calls and drop logs; fences inside
evidence neutralised; helpers moved out of `conftest.py`.
Not done (noted, small): ISO dates followed by a separate "5 PM" lose the time; a short
`+05` offset falls back to IST.

## Contract change requests (vocabulary.py, coordinator-owned)
None required. Observations:
1. `ParsedField.value` / `CandidateFact.value` allow `bool`; the parsers never emit one.
2. `OpeningAttribute.DEADLINE` is honoured strictly now: a deadline the text dates
   without a year is dropped, so an opening may have no deadline field. Consumers
   already handle `deadline is None`.

## Decisions the coordinator must make at integration
- **Two candidate → Statement builders exist**: WS-2 `candidate_to_statement`
  (confidence 1.0 because the user confirmed; delegates to `profile_statement`) and
  WS-1 `profile.statement_from_candidate` (passes the model's confidence). The API
  protocol `CandidateStatements.statement_for(user_id, candidate, *, source_ref)`
  matches neither signature exactly. Recommendation: keep one (either is a one-line
  adapter to the protocol) and decide whether a confirmed fact carries 1.0 or the
  model's score; WS-2's view is 1.0, since the user is now the source.
- **CGPA scale**: both parsers accept any number ≤ 10 as a 10-point CGPA, so a
  "3.8/4.0" resume becomes `cgpa=3.8`. Options: a `cgpa_scale` profile attribute
  (vocabulary change), or normalise 4-point to 10-point in the adapter. Not decided here.

## Shared-file note
`tests/domains/__init__.py` (empty) was created so `tests.domains.jobs_parsers.support`
imports under the repo's package-style tests. WS-1 may create the same empty file for
`tests/domains/jobs/`; identical content, no conflict.

## Dependencies
None beyond pyproject (pypdf 6.21.1 already pinned, ADR-0024). No `uv add` run.

## Open problems / follow-ups
- Confidence constants 0.5 / 0.6 are policy, not measured; calibrate when the bench
  has a parser suite (Phase 3).
- The date matcher covers ISO, "15 November 2026", "Nov 15, 2026", "15/11/2026" (day
  first), optional 12h/24h time, IST/UTC/GMT. Shapes like "mid-November" are dropped.
- `extract_text` is synchronous; the API should call it through `asyncio.to_thread`.
- Prompt behaviour has no bench smoke numbers yet (the bench has no parser suite);
  recorded here rather than in DEVLOG, which is coordinator-owned.

## Suggested commit message
```
jobs/parsers: JD and resume parsers with span-checked LLM extraction — FR-1/FR-2 need
typed fields that each point at their source text; the model quotes, deterministic code
locates spans, coerces numbers, normalises deadlines and cross-checks with regexes
(ADR-0035), so nothing without a span and nothing the model wrote becomes memory (I5).
```
