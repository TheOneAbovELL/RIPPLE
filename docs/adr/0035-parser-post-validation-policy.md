# ADR-0035: Parsers: LLM extraction with deterministic span, value and date validation
Status: Accepted under the autonomous mandate · Date: 2026-10-19

## Context
FR-1 (resume → confirmed profile facts) and FR-2 (JD → structured requirements with
source spans) both need text turned into typed fields. I4 says LLM output is validated
into a schema before use; I5 says the agent never invents facts or numbers; the
acceptance criterion of FR-2 says every parsed field links to the text span it came
from. A model can satisfy the schema and still misquote, round a number, or write a
deadline in a shape the ranking code cannot compare. ADR-0024 fixed the resume pipeline
(pypdf text, LLM structuring, user confirmation) but not what happens between the
model's reply and the contract types in `ripple.domains.jobs.vocabulary`.

## Decision
Both parsers (`ripple.domains.jobs.parsers.jd`, `.resume`) follow one policy:

1. **The model quotes, the code locates.** Each schema item carries `quote`, the exact
   substring the value came from. `spans.locate_span` finds it in the source text
   (exact, then whitespace-tolerant, then case-insensitive) and the resulting `TextSpan`
   always holds the source's own characters. A quote that is not found makes the item
   disappear, logged at INFO with the attribute only. It is not retried: the schema was
   valid, the content was not, and a filter is cheaper and more predictable than a
   second model call (same reasoning as the LLM linker's unknown-id filter).
2. **Typed values are coerced or dropped.** `cgpa` and `cgpa_cutoff` become floats on a
   ten-point scale (values above 10 are dropped); `batch` becomes the last four-digit
   year in the value ("2023-2027" → 2027); `role_type` becomes `internship` or
   `full_time`; anything that cannot be coerced is dropped and logged.
3. **Deadlines are normalised by a hand-written matcher** (`dates.normalise_deadline`),
   not by a library and not by the model: ISO 8601 with offset, read from the located
   span first (the verbatim source) and from the model's value only as a fallback. A
   date without a time means the end of that day. A date without a year is never
   guessed: the field is dropped and logged, because the C1 contract types a deadline
   as ISO 8601 and the adapter (`jobs.schemas.parse_deadline`) refuses anything else;
   a raw value would fail the whole opening, not just the field. Numeric dates are
   day-first (Indian campuses). The timezone is the one the text names (IST, UTC,
   GMT) or IST.
4. **Regex cross-checks for `cgpa_cutoff` and `deadline`.** The regexes are a second
   opinion: a disagreement caps the model's field at 0.5 and keeps the model's value;
   a value the model missed is added at 0.6 with the regex's own span. Both regexes
   are written not to invent: the cgpa window stops at a sentence end and refuses a
   value followed by a digit or a percent sign ("CGPA: no bar. Stipend: 8 LPA" and
   "75% or above" yield nothing); the deadline regex only accepts a date that starts
   after a deadline keyword in the same sentence or line, so a drive date in the next
   sentence is not promoted to a deadline.
5. **The model never writes memory content.** `ParsedOpening.summary` is built from the
   title and company fields; `CandidateFact.content` comes from the jobs adapter's
   `profile_content` template ("CGPA is 8.1", "knows Python"), the same wording a
   fact stated in conversation gets. The schemas have no free-text field in which to
   embellish, which is the strongest form of I5 the parsers can offer. The resume
   schema also admits only the seven attributes a document can state: `accepted_offer`,
   `looking` and `resume` are conversation decisions, and a reply naming them fails I4
   validation instead of becoming a candidate.
6. **One skill per fact.** The prompts ask for it; the resume parser also splits a list
   that slipped through (commas, semicolons, pipes, "and"), each skill citing the same
   span. A slash is never a separator: CI/CD and TCP/IP are single skills.
7. **Forwarded emails are stripped deterministically** (`envelope.strip_email_envelope`)
   before parsing: header blocks (only at the top of the text or right after a
   forward/reply marker, so a "Date:" line inside a JD body stays), quote prefixes,
   legal disclaimers, then a closing signature or `--` delimiter when at most ten lines
   follow it. Spans are offsets into the stripped text, which `ParsedOpening.raw_text`
   holds.
8. **One statement builder.** `candidate_to_statement` delegates to the adapter's
   `profile_statement` (WS-1), so sensitivity, value validation and wording have one
   source; it sets confidence to 1.0 because the user, not the model, confirmed the
   fact. WS-1's `statement_from_candidate` passes the model's confidence instead; the
   coordinator picks one at integration (handover, open problems).

The schemas live in `ripple.llm.schemas.{jd,resume}` and import the attribute enums
from the jobs vocabulary, so the JSON schema the model sees is an enum of the names the
adapter understands. `ripple.llm` thereby depends on `ripple.domains.jobs.vocabulary`,
which depends only on core; no cycle, and the same shape WS-4's agent schemas take.

Points 3 (drop, not raw value), 4 (no-invention regexes, sentence window), 5 (seven
attributes), 6 (no slash), 7 (header position) and 8 were tightened the same day after
the code-reviewer pass found that the first draft let a year-less deadline crash the
adapter and let the cgpa regex read "8 LPA" as a cutoff.

## Alternatives considered
- Ask the model for offsets instead of quotes — models count characters badly; a
  wrong offset is undetectable, a wrong quote is. Lost.
- Retry the model when a quote is not found — spends tokens on a content problem the
  retry message cannot describe well, and makes behaviour depend on the failure path.
  Lost; drop and log.
- A date library (python-dateutil) — a new dependency for a handful of shapes, and its
  fuzzy mode guesses years, which point 3 forbids. Lost; revisit if pilot JDs show
  shapes the matcher misses.
- Let the model normalise the deadline to ISO itself — it would have to invent the
  year and the timezone when the text omits them. Lost.
- Let the model write the candidate's `content` sentence — natural wording, but a
  second place where numbers and experience can be invented. Lost.
- Regex-only extraction, no LLM — cheap and deterministic, but titles, locations,
  branches and skills have no reliable surface pattern. Kept only as the cross-check.

## Consequences
- Every field and candidate that leaves the parsers has a span found in the text
  (test_invariant_I5_parsers_never_emit_fields_without_a_span).
- Recall is traded for precision: a misquoted field, a year-less deadline or a
  number outside the ten-point scale is lost rather than guessed. The user confirms
  resume facts anyway (ADR-0024) and the inspector shows JD spans. A 4-point GPA is
  silently accepted as a 10-point value; the scale decision is an open problem for the
  coordinator (handover).
- Confidence values 0.5 and 0.6 are policy constants, not measured; Phase 3 can
  calibrate them against labelled JDs once the bench has a parser suite.
- `extract_text` is synchronous (pypdf is CPU-bound); the API must run it in a worker
  thread.

## Revisit if
Pilot JDs carry dates in shapes the matcher misses, the cross-check disagrees with the
model more often than it agrees (which would argue for regex-first), or the pilot
shows the end-of-day default to be wrong for a common source (portals that close at
noon, for instance).
