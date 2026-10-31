# ADR-0019: Rule-first resolution
Status: Accepted · Date: 2026-10-19 (under the autonomous mandate; from proposal 0001)

## Context
ADR-0003 has the LLM decide the action for every affected memory. Many derived
beliefs in the jobs domain are arithmetic over structured fields (CGPA against a
cutoff, batch match, deadline reminders). Sending those to an LLM costs a call per
memory, risks arithmetic errors, and flatters the check-everything baseline (C4).
docs/proposals/0001-rule-first-resolution.md has the evidence.

## Decision
The Resolver is a chain: a sequence of pure `RuleResolver`s is tried first; the first
one that returns a Resolution wins; otherwise the LLM resolver decides. Rules live in
domain adapters (Phase 2 ships the jobs rules); core provides the chain and the
protocols (`ripple.core.resolver`). A rule's decision cites the structured fields it
read as evidence, so I2 holds. The chain is the default wiring; a run can disable rules
for the ablation "without rules" by passing an empty rule list.

## Alternatives considered
- LLM-only resolution — simplest, every ripple pays per memory; lost on cost and on
  arithmetic reliability.
- A calculator tool for the LLM — still one call per memory, plus tool-use complexity.
- Rules inside the Linker — the Linker finds edges, it does not decide values.

## Consequences
- A wrong rule is confidently wrong. Rules are written only for kinds with labelled
  bench cases, and the ablation measures their effect.
- I3 untouched: rules run in the Resolver stage, never in the engine.
- The Resolver interface gains nothing; `ResolverChain` is a Resolver.

## Revisit if
Rules disagree with the LLM on more than a few percent of labelled cases, or the jobs
rules grow into a second business-logic layer that the adapter cannot own cleanly.
