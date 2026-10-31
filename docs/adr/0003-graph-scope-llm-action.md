# ADR-0003: The graph decides scope; the LLM decides action
Status: Accepted · Date: 2026-10-19

## Context
Re-checking every memory with an LLM is accurate but costs one call per memory per change.
Letting an LLM choose the scope is non-deterministic and hard to test.

## Decision
Deterministic traversal over typed links computes the affected set (I3). The LLM resolves
only memories in that set.

## Alternatives considered
- Check everything — kept as the strongest baseline.
- Embedding-similarity scoping — misses dependents that are not textually similar
  (CGPA → eligibility).
- LLM-chosen scope — non-deterministic, untestable.

## Consequences
Quality is bounded by link recall, so the link finder is critical (ADR-0009). We measure
missed-link rate.

## Revisit if
Link recall stays below target after Phase 4.
