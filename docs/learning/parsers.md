# ripple.domains.jobs.parsers — resume and JD parsers
Written 2026-10-19 for src/ripple/domains/jobs/parsers, src/ripple/llm/schemas/{jd,resume}.py
and src/ripple/llm/prompts/{jd_parser,resume_parser}.v1.md (workstream WS-2).

## 1. What it does
The parsers turn a job description, a forwarded placement email or a resume PDF into
typed fields that each point at the exact characters they came from. A model does the
reading; deterministic code decides what survives: the quote must be in the text, the
number must be a number, the date must normalise. Nothing here writes a memory; the
outputs are the contract types in `vocabulary.py` plus a `Statement` for a resume fact
the user has confirmed.

## 2. Why it exists
FR-1 (profile from a resume, confirmed fact by fact) and FR-2 (openings from paste or
email, every field with a source span). I4 (validated schema before use), I5 (never
invent facts or numbers). ADR-0024 chose pypdf plus LLM structuring plus confirmation;
ADR-0035 fixes the post-validation policy this module implements. ADR-0010 puts every
model call behind the Router.

## 3. How it works
- `jd.parse_jd(router, text, source_ref, trace_id=None)`: system prompt
  `jd_parser.v1`, the JD in a fenced block in the user message (a fence inside the JD
  is neutralised first), schema `JDParse` (a list of `JDField`: attribute from
  `OpeningAttribute`, value, verbatim `quote`, confidence). `_validate_fields` runs
  `spans.locate_span` on every quote and `_coerce` on every value (cutoff → float,
  batch → int, deadline → `dates.normalise_deadline` on the span text, role_type →
  enum word; anything else dropped and logged). `_cross_check` runs the cgpa and
  deadline regexes: a disagreement caps the model's field at
  `DISAGREEMENT_CONFIDENCE`, a miss adds the regex's field at `REGEX_ONLY_CONFIDENCE`.
  `_summary` builds "title at company" from the fields.
- `numbers.py`: `cgpa_value` (first number, ≤ 10), `graduation_year` (an int, the last
  four-digit year, or "2023-27" expanded to 2027), shared by both parsers.
- `dates.find_dates` / `normalise_deadline`: six regexes (ISO, day-month-year,
  month-day-year, numeric day-first, and two year-less shapes) with an optional time
  that needs a colon or am/pm. No year → `moment is None`, which the JD parser turns
  into a dropped field. No time, or an impossible time → 23:59:59.
- `envelope.strip_email_envelope(text)`: drops header runs at the top of the text or
  after a forward/reply marker, removes `>` prefixes, cuts from a disclaimer line, then
  cuts the last closing line or `--` when at most ten lines follow it, collapses blank
  runs. The caller parses the stripped text, so spans index into it.
- `resume.extract_text(pdf_bytes)`: pypdf per page; empty text layer, damaged bytes or
  a password all raise `UnparseableResumeError` (a `RippleError`).
  `parse_resume(router, text, trace_id=None)`: prompt `resume_parser.v1`, schema
  `ResumeParse` (seven resume attributes only); the same locate-then-coerce loop, with
  a skill list split into one candidate per skill (never on "/") and `content` filled
  from the adapter's `profile_content` template.
  `candidate_to_statement(candidate, user_id, source_ref, origin=...)`: delegates to
  the adapter's `profile_statement`, confidence 1.0, `source_ref` suffixed with
  `#start-end`.

## 4. Trade-offs
- Drop, do not retry, a bad quote: predictable and cheap; costs recall on models that
  paraphrase. Wrong when: the model is weak enough that most quotes miss; then the fix
  is a better model in the router config, not a retry loop.
- A hand-written date matcher: no dependency, never guesses a year. Wrong when: JDs use
  shapes it does not know ("mid-November", "end of this week"); those fields are
  dropped and the opening has no deadline until the user adds one in the inspector.
- Templates for `content`: removes an invention vector; sentences are plain. Wrong
  when: a product needs richer memory text; add attributes, not model prose.
- Regex-only fields at 0.6: catches a missed deadline, the costliest miss. Wrong when:
  the keyword window picks a nearby unrelated date; the span shows which one it took.
- Signature cut only when little follows: never loses a requirement to a stray
  "Thanks"; may keep a long signature. Acceptable: a signature is noise, not a fact.

## 5. Failure modes and tests
| Failure | Test |
|---|---|
| Quote not in text (JD) | test_parse_jd_drops_field_whose_quote_is_not_in_text_and_logs |
| Quote not in text (resume) | test_parse_resume_drops_candidate_whose_quote_is_not_in_text_and_logs |
| Plausible fields with no span | test_invariant_I5_parsers_never_emit_fields_without_a_span |
| Regex reads a stipend or percentage as a cutoff | test_invariant_I5_regex_cross_check_never_adds_a_number_the_jd_does_not_state |
| Model invents a cutoff absent from the JD | test_parse_jd_never_adds_an_invented_cutoff |
| Schema miss then fix / never valid | test_parse_jd_retries_invalid_schema_then_accepts, test_invariant_I4_parsers_reject_output_that_never_matches_the_schema |
| Resume reply names accepted_offer or looking | test_parse_resume_rejects_attributes_a_resume_cannot_state |
| Model and regex disagree | test_parse_jd_lowers_confidence_when_regex_disagrees_on_cutoff |
| Model reformatted the deadline and lost the time | test_parse_jd_normalises_deadline_from_the_span_not_the_models_reformatted_value |
| Model missed the deadline | test_parse_jd_adds_deadline_from_regex_when_model_missed_it |
| A date in the next sentence is not the deadline | test_parse_jd_does_not_take_a_date_from_the_next_sentence_as_deadline |
| Deadline without a year | test_parse_jd_drops_a_deadline_without_a_year_rather_than_guessing |
| "CI/CD" split into two skills | test_parse_resume_keeps_a_slash_inside_a_single_skill_name |
| "2023-27" read as 2023 | test_parse_resume_reads_a_short_year_range_as_the_graduation_year |
| Date shapes, offsets, version numbers, bad times | tests in test_dates.py |
| Line breaks and case in quotes | tests in test_spans.py |
| Headers, quotes, signatures, disclaimers, body "Date:" lines | tests in test_envelope.py |
| Scanned, damaged, encrypted or multi-page PDF | test_extract_text_* |
| Confirmed candidate through Intake | test_candidate_to_statement_result_is_ingested_as_a_valid_profile_memory |
| Evidence leaking into the system prompt | test_parse_jd_sends_prompt_in_system_and_jd_text_in_user_message_only, test_parse_resume_sends_resume_text_in_user_message_only |

## 6. Interview questions
1. *Why ask the model for a quote rather than character offsets?* A wrong offset looks
   like a right one; a wrong quote fails a string search and is dropped.
2. *What stops a JD from instructing the parser?* The JD sits in a fenced block in the
   user message and the system prompt says to treat it as data; the schema is an enum
   of attributes, so an injected "attribute" cannot exist.
3. *Where is I5 enforced for resumes?* Three places: the quote must be in the text, the
   `content` sentence is a template, and nothing is stored until the user confirms and
   the API calls `candidate_to_statement`.
4. *Why is a deadline without a year not completed with the current year?* October's JD
   for "15 Jan" means next year; guessing would create a wrong reminder silently, and
   the contract types a deadline as ISO 8601, so the field is dropped and logged.
5. *Why does the regex cross-check lower confidence instead of overwriting?* The model
   read the whole sentence, the regex read a window; neither is certainly right, so the
   disagreement is recorded for the ranking and the inspector rather than resolved.

## 7. Exercise
Write a JD line "Cutoff: 70% or 7.0 CGPA, batch 2026/2027" and predict, before running
the parser with a FakeLLM reply that quotes it, which cgpa value the regex cross-check
finds, whether it agrees with a model value of 7.0, and how many batch fields a correct
model reply should produce.
