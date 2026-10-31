# WS-1 handover: jobs adapter (schemas, rules, ranking)
Status: **Locally verified** · 2026-10-20 · session WS-1 (collaborator, autonomous mandate)
Round 2: code-reviewer findings fixed (2 blockers, 7 majors, most minors; see below).

## Plan (written before implementation, kept here because docs/plans/ is coordinator-owned)
1. Representation (ADR-0030): anchor + field facts + `depends_on_fact` links, one
   transaction, one ChangeEvent; `OpeningFieldRule` so the record-time wave is free.
2. Profile builders (Statement for Intake, Memory for direct writes, CandidateFact bridge).
3. Pure belief computations shared by derivation and rules (`beliefs.py`), with the
   structured value on every derived memory so rules and ranking never parse prose.
4. Derivation writers (`derive.py`) through `writes.record_memory` + runner.
5. Rules (ADR-0031) and `jobs_rules()`; criteria gets its own rule because a CGPA
   change reaches criteria in the same wave as eligibility.
6. Ranking (ADR-0032) over `visible_for_retrieval`.
7. Tests first per module; end-to-end with a fallback resolver that fails the test.

## Files
Source (new, all under src/ripple/domains/jobs/):
- `schemas.py`: `OPENING_KEY`, `anchor_structured`, `opening_key`, `opening_subject_of`,
  `ProfileView`, `OpeningView` (both with `include_flagged`), value parsers, `span_ref`.
- `openings.py`: `record_opening`, `find_opening`, `OpeningAlreadyRecordedError`,
  `RecordedOpening`, `field_memory`, `opening_memories`.
- `profile.py`: `profile_fact`, `profile_statement`, `profile_memory`,
  `statement_from_candidate`, `record_profile_fact`.
- `beliefs.py`: `Belief`, `compute_eligibility`, `compute_fit`, `compute_reminder`,
  `compute_criteria`, `fit_reasons`.
- `derive.py`: `derive_for_opening`, `derive_criteria`, `DerivedBeliefs`.
- `rules.py`: `OpeningFieldRule`, `EligibilityRule`, `FitRule`, `ReminderRule`,
  `CriteriaRule`, `jobs_rules()`.
- `ranking.py`: `JobsRecommender` (implements `RecommendationSource`).
Tests (new, tests/domains/jobs/): `helpers.py`, `test_openings.py`, `test_profile.py`,
`test_derive.py`, `test_rules.py`, `test_end_to_end.py`, `test_lifecycle.py`,
`test_ranking.py`, `test_invariants_jobs.py`: 122 tests.
Docs: `docs/adr/0030-opening-representation.md`, `docs/adr/0031-jobs-rule-resolvers.md`,
`docs/adr/0032-jobs-ranking.md` (all amended in round 2), `docs/learning/jobs-adapter.md`,
this file. Not touched: `vocabulary.py`, `parsers/`, anything coordinator-owned
(checked by file timestamps after the format runs).

## Public surface other workstreams build against
```python
from ripple.domains.jobs.openings import record_opening, OpeningAlreadyRecordedError
from ripple.domains.jobs.derive import derive_for_opening, derive_criteria
from ripple.domains.jobs.profile import profile_statement, statement_from_candidate, record_profile_fact
from ripple.domains.jobs.rules import jobs_rules  # ResolverChain(jobs_rules(), fallback=LLMResolver(...))
from ripple.domains.jobs.ranking import JobsRecommender  # .recommendations_for(user_id, now=..., limit=...)
```
Wiring notes:
- `record_opening` raises `OpeningAlreadyRecordedError` (an `InvalidObjectError`, with
  `.anchor_id`) when the source is already a live opening. WS-3 maps it to 409, the
  Scout treats it as "seen".
- `record_profile_fact` now returns `(memory, ChangeEvent | None)`: None when the value
  is already held. A second CGPA becomes version 2 and ripples.
- `derive_for_opening` accepts any version id of the anchor, raises
  `InvalidObjectError` for a closed or questioned opening, and returns any live belief
  untouched. `derive_criteria` is per user, `derive_for_opening` per opening; both are
  idempotent.
- Rules need nothing but `jobs_rules()`; the worker builds
  `ResolverChain(jobs_rules(), fallback=LLMResolver(router))`.

## Code review (round 2, code-reviewer subagent) and what was done
| Finding | Outcome |
|---|---|
| B1 rules compute around SUSPECT/PENDING_USER parents | Fixed: None when a parent is in doubt; a field SUSPECT only in its own anchor's wave still counts (else an anchor edit sends every belief to the LLM). ADR-0031 point 2. Tests in test_rules.py. |
| B2 anchor edit orphans fields and beliefs | Fixed: stable opening key in the anchor's structured triple, carried over by versioning. ADR-0030 point 6. test_inspector_edit_of_the_anchor_keeps_fields_and_beliefs_attached. |
| M1 derive duplicates a SUSPECT belief | Fixed: any non-RETIRED belief counts as existing. |
| M2 second CGPA fact beside the first | Fixed: versioned through `update_memory`; same value writes nothing. |
| M3 ranking drops flagged fields | Fixed: views take `include_flagged`; ranking uses it. |
| M4 later skill never reaches fit or criteria | Fixed on the adapter's write path: rule links `fit_of` / `criteria_from` (ADR-0031 point 5). The Intake path still depends on the Linker. |
| M5 same JD recorded twice | Fixed: `OpeningAlreadyRecordedError`. |
| M6 repeated single-valued fields | Fixed: rejected at write time. Multi-batch JDs ("2026/2027") are therefore rejected; see open problems. |
| M7 record-time wave and closing untested | Fixed: test_lifecycle.py, both through the runner with a fallback that fails when called. |
| Minors | Done: span must equal the source text, refuse derive on a closed opening, O(n) grouping and precomputed positions in ranking, flag only from used memories, no-company variety bucket, `InvalidObjectError` for unknown candidate attributes, deterministic duplicate tie-break, misnamed I3 test renamed, tautological determinism test replaced, helper annotation, `__import__` removed. Documented in ADR-0031 consequences: CGPA always updates eligibility content, copied links vs evidence, eligible-when-none-parsed asymmetry. Not changed: `record_opening` still raises after commit if the ripple fails (documented; the sweep resumes it). |

## Verification (real output, 2026-10-20, final run)
```
$ uv run ruff check src/ripple/domains tests/domains
All checks passed!
$ uv run ruff format --check src/ripple/domains tests/domains
38 files already formatted
$ uv run pyright src/ripple/domains tests/domains
0 errors, 0 warnings, 0 informations
$ uv run pytest tests/domains -q
208 passed in 1.60s
$ uv run pytest tests/domains/jobs -q
122 passed in 0.94s
```
`ruff format` was run in write mode only on WS-1's own files; the shared folders were
checked with `--check` so no other workstream's file was rewritten.
Outside my paths, `tests/core tests/scenarios tests/linking` ran 160 passed, 21 xfailed
and 1 failed. The failure is WS-7's `test_bench_generate.py::test_adding_a_persona_leaves_earlier_personas_scenarios_unchanged`,
seen on 2026-10-19 and not caused by WS-1.

## Contract change requests for vocabulary.py (coordinator)
Applied by the coordinator since round 1: `DerivedAttribute`,
`MULTI_VALUED_PROFILE_ATTRIBUTES` with core Intake support, and
`Recommendation.hours_until_deadline(now)`. WS-1 now imports the first two from the vocabulary.
New:
1. **`OPENING_KEY = "opening_key"`**: the attribute of an anchor's own structured
   triple (ADR-0030 point 6). Lives in `schemas.py` today. WS-3's inspector must keep
   carrying `structured` over on edit, which it does now, and must not let a user edit
   that triple. Suggest moving the constant to the vocabulary and documenting the rule.
2. **CGPA scale.** `ProfileAttribute.CGPA_SCALE` arrived (4 or 10). `profile.py` accepts
   it, but eligibility still compares the raw CGPA with the raw cutoff. There is no
   `OpeningAttribute.CGPA_SCALE`, so a 4-point profile against a 10-point cutoff is
   silently wrong. Proposal: add `OpeningAttribute.CGPA_SCALE` (default 10), and have
   `compute_eligibility` return None when the scales differ, so the LLM decides or the
   agent asks. Small change once the attribute exists.
3. **Batch ranges.** JDs often say "2026/2027 batch". Today a second batch field is
   rejected (M6). Either make `OpeningAttribute.BATCH` multi-valued (eligibility =
   membership), or have WS-2 emit one field per year and the adapter accept that.

## Open problems (not blockers)
- **Closing an opening.** Nothing retires an anchor when its deadline passes. The
  ripple below a RETIRED anchor is fully rule-driven and tested. What is missing is the
  trigger: the Scout retiring the anchor, or `valid_to = deadline` on the anchor so the
  sweep expires it. The second goes stale when the deadline moves. This needs a
  coordinator decision.
- **Re-recording a changed JD.** Duplicates are refused, but there is no `update_opening`
  that diffs a re-parsed JD into field updates. ADR-0030's "Revisit if" covers it.
- **Hidden links on the Intake path.** The rule links of ADR-0031 point 5 are written
  only by `record_profile_fact`. A skill stated in conversation goes through Intake and
  the Linker. Offering the adapter's rule links as a `Linker` would close the gap and
  is a small follow-up.
- **Eligibility with no profile fact** is not derived, so the opening ranks "not
  eligible" until the agent asks for the CGPA.
- **Real engine.** All runner tests use the scripted engine and replay the wave the
  `DependencyGraph` reports. The scenario suite will exercise the real one once the
  author's engine lands.

## Suggested commit message
```
jobs adapter: openings, profile, derived beliefs, rule resolvers, ranking — Phase 2 jobs core built test-first (ADR-0030..0032)

- An opening is an anchor memory plus one structured fact per parsed field,
  linked depends_on_fact so forget cascades; one transaction, one ChangeEvent;
  a stable opening key survives anchor edits; duplicate sources refused.
- Eligibility, fit, reminder and search criteria are derived memories whose
  content and structured value are pure functions of their parents, linked
  eligibility_of / fit_of / reminder_for / criteria_from; later skills get
  deterministic rule links.
- Rule resolvers recompute each belief from current parents (keep / update
  with cited evidence / retire when the opening closed / None for the LLM
  when a parent is missing or in doubt).
- JobsRecommender ranks from beliefs only: eligible, urgent, fit, variety;
  flags SUSPECT/PENDING_USER, never shows RETIRED (I1).
- 122 offline tests incl. CGPA ripple, anchor edit, closing an opening and a
  later skill, each with a fallback that fails when called; I1/I5 invariants.
```
