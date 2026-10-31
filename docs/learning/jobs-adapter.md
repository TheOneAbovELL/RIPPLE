# ripple.domains.jobs: openings, profile, beliefs, rules, ranking
Written 2026-10-19 (WS-1) for ripple.domains.jobs.{schemas, openings, profile,
beliefs, derive, rules, ranking}. The shared vocabulary (`vocabulary.py`) is the
coordinator's contract C1 and is only read here.

## 1. What it does
Turns a parsed job description into memories the ripple engine can reason about: one
anchor plus one structured fact per field. Derives the beliefs a student acts on
(eligibility, skill fit, a reminder, search criteria) as memories linked to the exact
facts they were computed from. Keeps those beliefs current with pure rules when a
parent changes, and ranks openings from the beliefs, flagging anything that is in doubt.

## 2. Why it exists
ADR-0002 (jobs is the product), ADR-0003 and ADR-0019 (rules decide what arithmetic
can decide; the LLM decides the rest), ADR-0013/0014 (links are what propagate and
what is copied on update), ADR-0030 (representation), ADR-0031 (rules), ADR-0032
(ranking). Invariants I1 (ranking never shows RETIRED, flags SUSPECT/PENDING_USER),
I2 (every rule decision cites its parents), I3 (rules run in the Resolver, never in
the engine), I5 (no invented values: every number in a belief is a parent's value),
I7 (forgetting an opening cascades to everything built on it).

## 3. How it works
- `openings.record_opening(store, clock, user_id, parsed, runner)`: validates each
  `ParsedField` (cutoff numeric, batch int, deadline ISO with timezone, span equal to the
  source text, single-valued attributes at most once), refuses a source already held
  as a live opening (`OpeningAlreadyRecordedError`), writes the anchor (kind `opening`,
  content = summary, structured = the stable opening key `opening:<first id>`), one
  fact per field (that subject, content = the JD span text, `source_ref` =
  `<source>#start-end`) and a `depends_on_fact` link from each field to the anchor, all
  in one transaction with one ChangeEvent; then the runner ripples it.
- `schemas.opening_key(anchor)`: the subject every field and belief carries. It lives
  in the anchor's structured triple, which versioning carries over, so an inspector
  edit of the anchor keeps everything attached.
- `profile.profile_statement` / `profile_memory` / `record_profile_fact`: typed builders
  for `ProfileAttribute` facts (cgpa float in 0..10, cgpa_scale 4 or 10, batch int,
  skills one memory per value). `record_profile_fact` writes nothing for a value
  already held, versions a single-valued fact through `update_memory` so it ripples,
  and gives a new skill, cgpa or batch rule links to the fit and criteria beliefs it
  affects. `statement_from_candidate` turns a confirmed resume `CandidateFact` into a
  statement with the resume span as `source_ref`.
- `schemas.ProfileView` / `OpeningView`: read facts by attribute (VALID only, or also
  SUSPECT and PENDING_USER with `include_flagged=True`) and parse the values once.
  Multi-valued facts come back sorted by value so content is deterministic.
- `beliefs.compute_eligibility / compute_fit / compute_reminder / compute_criteria`:
  pure functions from views to a `Belief` (kind, content, structured triple, link type,
  parents read). Eligibility: cgpa >= cutoff and batch == batch, only when the profile
  has the needed fact (else None). Fit: overlap of normalised skills, one reason line
  per required skill quoting the JD span. Reminder: deadline minus 48 h. Criteria: the
  cgpa, batch and skills clauses the Scout filters with.
- `derive.derive_for_opening(store, clock, runner, anchor_id)` and
  `derive_criteria(store, clock, runner, user_id)`: compute, return any live (not
  RETIRED) belief for the same subject and attribute untouched, otherwise write through
  `writes.record_memory` with one link per parent (`eligibility_of`, `fit_of`,
  `reminder_for`, `criteria_from`; every per-opening belief also links to the anchor),
  then ripple. A closed or questioned opening is refused.
- `rules.jobs_rules()`: `OpeningFieldRule` (a field follows its anchor: keep while
  VALID, retire when RETIRED), then `EligibilityRule`, `FitRule`, `ReminderRule`,
  `CriteriaRule`. Each recomputes with the same `beliefs` function from
  `context.parents`, answers keep when content and structured value match, update
  otherwise (evidence = parent ids), retire when the anchor is RETIRED, and None when a
  needed parent is missing or any parent is in doubt (PENDING_USER, or SUSPECT other
  than a field of its own opening mid-wave).
- CGPA scale (ADR-0034): JD cutoffs are ten-point only.
  `EligibilityRule` reads the student's cgpa_scale fact among its parents
  (`rules.profile_cgpa_scale`, default 10) and returns None when the opening has a
  cutoff and the scale is 4: converting 4-point GPA to 10-point CGPA would be a guess,
  so the LLM resolver decides or asks. `record_profile_fact` links a cgpa_scale fact to
  every eligibility belief (`eligibility_of`) and to the criteria (`criteria_from`).
  Derivation reads the scale too: `ProfileView.cgpa_scale`, `compute_eligibility`
  derives nothing off the cutoff scale and links the scale fact when it compares, and
  `compute_criteria` drops the CGPA gate off the cutoff scale (ADR-0034).
- `ranking.JobsRecommender(store).recommendations_for(user_id, now=, limit=)`: reads
  the user's memories through `visible_for_retrieval(include_flagged=True)`, groups
  them by opening subject once, builds a `Recommendation` per anchor from the title,
  company and deadline fields (flagged ones included) and the eligibility and fit
  beliefs, drops openings whose deadline passed, sorts by (eligible, deadline within
  48 h, fit, earliest deadline) and spreads companies within each tier.

## 4. Trade-offs
- One ChangeEvent per JD with the anchor as trigger means, under the real engine, a
  wave of `keep` decisions over the opening's own fields at record time. Chosen over
  "no event" (every other write has one) and "one event per row" (not atomic).
- Content equality as the "unchanged" test is strict: a cosmetic change to a content
  format would update every belief once. Acceptable because the format is code shared
  by derivation and rules, and the bench would show the burst.
- Rules return None rather than guessing when a parent is missing. More LLM calls in
  odd states, zero confidently-wrong rule decisions.
- Urgency outranks fit (ADR-0032); the task sketch listed fit first. With continuous
  scores urgency would otherwise almost never matter.
- No `valid_to` anywhere yet: an opening is not closed automatically. The recommender
  hides past deadlines; closing (retiring the anchor) is an open lifecycle question.

## 5. Failure modes and tests
| Failure | Test |
|---|---|
| Malformed parser output half-written | test_record_opening_rejects_a_malformed_field_and_writes_nothing |
| Forget leaves fields or beliefs behind | test_record_opening_forget_anchor_cascades_to_every_field, test_derive_forget_anchor_cascades_to_the_derived_beliefs |
| Belief invents a number | test_invariant_I5_derived_beliefs_cite_only_values_held_by_their_parents, ..._rule_updates_cite_only_values_... |
| Rule decides without the profile fact | test_eligibility_rule_returns_none_when_the_profile_cgpa_is_missing, ..._retired_without_successor |
| Equal CGPA and cutoff mis-ranked | test_eligibility_rule_treats_an_equal_cgpa_as_eligible |
| Batch mismatch hidden by a good CGPA | test_eligibility_rule_batch_mismatch_makes_it_not_eligible_despite_the_cgpa |
| CGPA change reaches the LLM | test_cgpa_rise_updates_eligibility_and_criteria_through_the_rules_without_an_llm, test_invariant_I3_... |
| Deadline change touches eligibility | test_deadline_extension_updates_the_reminder_and_leaves_eligibility_alone |
| RETIRED opening recommended; SUSPECT not flagged | test_invariant_I1_recommender_never_returns_retired_and_flags_suspect_or_pending |
| One company fills the digest | test_recommender_spreads_companies_within_a_tier, ..._never_lifts_an_ineligible_opening_above_an_eligible_one |
| Non-deterministic belief content | test_jobs_rules_are_deterministic_across_calls, sorted views in schemas.py |
| Rule computes around a flagged parent | test_eligibility_rule_defers_when_the_profile_parent_is_in_doubt, test_fit_rule_defers_when_a_skill_parent_is_in_doubt |
| Anchor edit orphans its opening | test_inspector_edit_of_the_anchor_keeps_fields_and_beliefs_attached |
| Closing an opening needs the LLM | test_closing_an_opening_retires_its_fields_and_beliefs_without_the_fallback |
| A later skill never reaches fit | test_a_skill_learned_later_reaches_fit_and_criteria_through_rule_links |
| Same JD recorded twice | test_record_opening_rejects_the_same_source_twice |
| Second CGPA fact beside the first | test_record_profile_fact_versions_a_single_valued_fact_instead_of_adding_a_second |

## 6. Interview questions
1. *Why is an opening several memories and not one?* Rules and the linker read one
   subject/attribute/value triple; a deadline change must be a structured update of one
   fact, not a prose rewrite, or the LLM has to interpret it.
2. *How does a CGPA change reach eligibility without an LLM?* The belief links to the
   CGPA fact; versioning copies that link to the new version (ADR-0014); the wave marks
   the belief SUSPECT; `EligibilityRule` recomputes from the current parents and
   answers update with the parent ids as evidence.
3. *Where is I5 enforced?* `beliefs.py` receives only views over parent memories; the
   invariant test parses every number and quoted phrase in a belief and checks it
   against the parents.
4. *What happens when the student has no CGPA on file?* No eligibility belief is
   derived; the recommender ranks the opening as not eligible; the rule returns None
   so, if a belief exists from before, the LLM decides with the evidence.
5. *Why does the recommender read beliefs instead of recomputing?* A stale belief must
   be visible to the layer that exists to flag it; recomputing would hide every
   failure the action-level metrics are meant to measure.
6. *Bonus: why is a SUSPECT field not "in doubt" for a rule?* Fields become SUSPECT
   only while their own anchor ripples, in the same wave as the beliefs, and
   `OpeningFieldRule` keeps them; treating them as doubtful would send every belief
   to the LLM on a harmless summary edit.

## 7. Exercise
Add `OpeningAttribute.LOCATION` to the fit computation as a preference match (profile
`preference` facts vs the opening's location). Decide, before coding, whether the
reason line may quote the preference's content, what the rule returns when the
preference fact is PENDING_USER, and which existing test breaks first.
