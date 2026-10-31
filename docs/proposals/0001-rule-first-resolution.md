# Proposal 0001: Rule-first resolution
Status: proposed · Date: 2026-10-19 · Tier B

## Problem
The worked example in docs/03-data-model.md sends "is cgpa 7.9 ≥ cutoff 7.8" to the LLM.
Eligibility, batch match and deadline reminders are arithmetic over structured fields
that FR-2 already extracts with spans. Asking an LLM costs a call per affected memory
and risks arithmetic mistakes, and it makes the check-everything baseline look cheaper
relative to Ripple than it should (C4).

## Proposed change
The Resolver gets a first stage before the LLM. A domain adapter may register, per
derived kind, a pure function `rule(parents) -> Decision | None` over structured facts.
If a rule returns a decision, the LLM is not called for that memory; the decision cites
the structured fields as evidence. If the rule returns None (fields missing or
ambiguous), the LLM stage runs as today. Config flag: `resolver.rules_first`.

## Rationale
Fewer LLM calls on exactly the memories that ripple most often (every CGPA or deadline
change touches many eligibility beliefs). Deterministic decisions are testable without
FakeLLM scripts. The thesis "code decides which, LLM decides how" extends naturally to
"code decides how, when it can".

## Alternatives
- Keep LLM-only resolution — simplest, but every ripple pays per memory; lost on cost.
- Give the LLM a calculator tool — still one call per memory; adds tool-use complexity.
- Put rules in the Linker instead — the Linker finds links, it does not decide values;
  wrong layer.

## Cost
About 150 lines: a RuleResolver protocol in core, a jobs-domain rule set, tests. No new
dependency. Runtime cost drops.

## Risks
- Rules that are wrong are confidently wrong. Mitigation: rules only for kinds with
  labelled bench cases; ablation "without rules".
- Touches the Resolver interface (ADR-0003 consequences) → needs an ADR.
- I3 untouched (rules live in the Resolver, not the engine). I5 untouched.

## How we measure it
Bench jobs track: LLM calls per ripple and eligibility accuracy with the flag on vs off;
report both in results/.

## Recommendation
Do now: define the protocol in Phase 1 once the engine interface exists; the jobs rules
land in Phase 2.
