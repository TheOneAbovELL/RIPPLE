# ADR-0031: Jobs rule resolvers recompute derived beliefs from their parents
Status: Accepted under the autonomous mandate · Date: 2026-10-19 (WS-1)
Implements ADR-0019 (rule-first resolution) for the jobs domain.

## Context
ADR-0019 puts a chain of pure `RuleResolver`s before the LLM resolver. The jobs
domain's derived beliefs (eligibility, fit, reminder, search criteria) are arithmetic
over structured fields, and the bench's C4 claim (graph-scoped resolution at a
fraction of check-everything cost) depends on those beliefs never needing a model call.

## Decision
1. Every derived belief is a memory whose content **and** structured value are a pure
   function of its parents' current values (`ripple.domains.jobs.beliefs`). The same
   functions run at derivation time and inside the rules, so a rule can compare its
   recomputation with what is stored.
2. One rule per belief kind: `EligibilityRule`, `FitRule`, `ReminderRule`,
   `CriteriaRule`, plus `OpeningFieldRule` for an opening's field facts (ADR-0030).
   Each rule:
   - returns `None` unless the memory is the kind it owns;
   - returns `retire` when the opening anchor among the parents is RETIRED (the
     opening closed);
   - returns `None` when a parent the computation needs is missing or not VALID, so
     the LLM resolver decides with the evidence in front of it;
   - returns `keep` when the recomputed content equals the stored content, otherwise
     `update` with the new content, the new structured value, and `evidence_refs` =
     the ids of every parent it read (I2).
3. `jobs_rules()` returns the chain in the order field rule, eligibility, fit,
   reminder, criteria. Order does not change outcomes because each rule claims a
   disjoint kind; it is fixed for determinism.
   Parents **in doubt** make every rule return None: any parent PENDING_USER, or
   SUSPECT for a reason other than being a field of this opening. A field is SUSPECT
   only while its own anchor ripples, and `OpeningFieldRule` keeps it in that same
   wave, so its value stands; without this exception an anchor edit would send every
   belief to the LLM. A **RETIRED** parent (latest version of a removed fact) is
   treated as absent: a removed opening constraint lifts it, a removed profile fact
   leaves nothing to compute with (None). (Added after the WS-1 code review, B1.)
5. **Rule links for facts recorded later.** A belief links only to the parents it read
   when derived, so a skill learned afterwards would never reach the fit belief that
   reports it missing. `profile.record_profile_fact` therefore writes deterministic
   rule links: a new skill → `fit_of` to every fit belief whose opening requires it;
   a new cgpa, batch or skill → `criteria_from` to the criteria belief. The Intake
   path still relies on the Linker for these hidden links.
6. Rules never read the clock, the store or a model: `ResolutionContext` is their
   whole world (I3 stays with the engine; I5 holds because a rule can only cite values
   it was handed).

## Alternatives considered
- One generic "recompute" rule keyed on a registry of belief kinds: fewer classes,
  but every belief's failure modes would hide behind one test surface. One rule per
  kind keeps each edge case (missing cutoff, equal values, batch mismatch) a named
  test.
- Rules that retire a belief whose profile parent is missing: confidently wrong
  when the fact was merely re-versioned under a different id. Deferring to the LLM
  is the behaviour ADR-0019 promised for "no rule applies".
- Storing only prose and parsing it back in the rule: fragile. The structured value
  is the machine-readable belief and the prose is for people and retrieval.

## Consequences
- A wrong rule is confidently wrong (ADR-0019); the end-to-end test pins the CGPA
  path with a fallback resolver that fails the test when called.
- Content formats are now part of the contract between derivation and rules; changing
  one means changing both (they share the code, so the type checker enforces it).
- The ablation "without rules" is still `ResolverChain([], llm)`.
- Eligibility content cites the CGPA, so every CGPA change is an `update` even when
  the verdict is unchanged. The bench's over-correction metric must count verdict
  changes (the structured value), not content changes.
- An update re-cites its new parents in `evidence_refs`, but the links are the copied
  old set (ADR-0014): a cutoff that disappears keeps its link, a newly matched skill
  gains one only through point 5 or the Linker.
- Asymmetry, accepted: an opening with no parsed cutoff or batch is "eligible" (the
  content says so), while a profile with no CGPA yields no eligibility belief and
  ranks "not eligible" (ADR-0032). A parser miss therefore errs towards showing the
  opening, a profile gap towards asking the student.

## Revisit if
The LLM and the rules disagree on more than a few percent of labelled bench cases, or
a belief kind needs judgement that no pure function expresses (then it leaves the
chain and goes back to the LLM).
