# Linkers, change detection and intake
Written 2026-10-19 for ripple.core.linking, ripple.core.change_detection,
ripple.core.intake, ripple.linking.rules, ripple.linking.llm, ripple.llm.resolver,
ripple.llm.change_detector.

## 1. What it does
Intake takes a statement ("CGPA is 7.9", "busy with exams this month"), decides whether
it is new, an update or temporary, writes it, finds its dependency links, and runs the
ripple. Linkers propose typed edges; the LLM resolver and change detector are the two
model-backed components, each behind a validated schema.

## 2. Why it exists
C1 (learned dependency induction) starts with two baselines: rules and an LLM linker
(ADR-0009). ADR-0020 makes change detection deterministic for structured facts and
model-backed for prose. ADR-0019 lets rules resolve before the LLM. I4 and I5 shape every
prompt: validated JSON, no invented facts, evidence as data.

## 3. How it works
- `core.linking.Linker.propose(memory, candidates)` returns `LinkProposal`s in either
  direction; `proposals_to_links` stamps the class from the `LinkTypeRegistry`, drops
  duplicates and weak proposals, and refuses unknown types (write-time boundary).
- `linking.rules.RuleLinker`: whole-word, case-insensitive mentions of a structured
  fact's attribute or value, both directions, never between versions of the same fact.
  Cheap, deterministic, low recall on hidden links; the baseline C1 must beat.
- `linking.llm.LLMLinker`: prompt linker.v1, candidates as JSON evidence in the user
  message, schema `LinkProposals`; proposals naming unknown ids or types are dropped
  deterministically rather than retried.
- `core.change_detection.detect_structured_update`: same subject and attribute as a
  VALID candidate is an update; the same value is UNCHANGED and intake writes nothing
  (no duplicate row, no event). `llm.change_detector` handles prose with the current
  date in the message so "this month" becomes a valid_to; a valid_to in the past is
  rejected as invalid output.
- `core.intake.Intake.ingest`: deterministic detection, else the detector; update →
  `update_memory` (links copied, linker may add); new → `record_memory` with proposed
  links; then `RippleRunner.run`. `Statement.origin` decides the trigger kind: the
  inspector is a user_edit, a conversation message or an agent write is a ripple.
- `llm.resolver.LLMResolver`: prompt resolver.v1, trigger/belief/parents as evidence,
  schema `ResolverVerdict` whose validators mirror `Resolution` (an update needs
  content, an ask needs a question), so the Router retries malformed verdicts.

## 4. Trade-offs
- Dropping unknown ids instead of retrying: the schema was valid, the content was not;
  a filter is cheaper and more predictable than another model call.
- Preferring "new" over "update" when unsure: a wrong update rewrites history.
- Candidates are all of the user's live memories today; a pre-filter
  (docs/proposals/0002) comes when the pilot makes the list long.
- Rule confidence is a constant 0.6: honest about being a heuristic, and below the LLM's
  typical scores so the LLM wins ties when both are wired.

## 5. Failure modes and tests
| Failure | Test |
|---|---|
| Rule links versions of the same fact | test_rule_linker_does_not_link_versions_of_the_same_fact |
| Substring false positives ("ML" in "HTML") | test_rule_linker_matches_whole_words_only |
| Model proposes a self link or unknown id | test_llm_linker_drops_unknown_candidate_ids_and_link_types |
| Evidence leaks into the system prompt | test_llm_linker_sends_evidence_in_the_user_message_only, test_llm_resolver_puts_prompt_in_system_and_evidence_in_user_message |
| Verdict shape wrong | test_llm_resolver_retries_update_without_content_then_accepts, test_invariant_I4_* |
| Update target unknown | test_llm_detector_update_with_unknown_id_becomes_new |
| Temporary without a date | test_llm_detector_retries_temporary_without_valid_to |

## 6. Interview questions
1. *Why both a rule linker and an LLM linker before training a model?* They are the
   baselines H3 compares against; without them "within 5 points of the LLM linker" is
   unmeasurable.
2. *How do you stop a JD from instructing the model?* Evidence goes in the user message
   inside fenced blocks and the system prompt says to treat it as data; tests pin this.
3. *Why is change detection two-stage?* Structured facts are mechanical; prose needs
   judgement; paying for a model call on "cgpa=7.9" is waste and non-determinism.
4. *What happens if the model names a memory you do not hold?* Stored as new with the
   reason recorded; no guess, no retry.
5. *Where does I5 live in this code?* In the prompts ("never invent") and, more
   strongly, in the fact that the resolver can only rewrite content; it cannot create
   profile facts, which only the intake of a user statement can.

## 7. Exercise
Write a FakeLLM-scripted test where the linker proposes the same edge twice with
different confidences and check which one `proposals_to_links` keeps, and why.
