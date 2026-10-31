# ADR-0020: Change detection: deterministic for structured facts, LLM for prose
Status: Accepted · Date: 2026-10-19 (under the autonomous mandate)

## Context
FR-5 requires detecting whether an incoming statement is new, replaces an existing
memory, or holds only temporarily, and ADR-0015 turns "temporary" into a valid_to.
A model call for every statement is expensive and non-deterministic for cases that
are mechanical.

## Decision
Intake (`ripple.core.intake`) classifies in two stages:
1. **Deterministic**: a statement with structured subject and attribute matching a VALID
   memory is an update of that memory (same value: nothing changes). No LLM.
2. **LLM** (`ripple.llm.change_detector`, prompt change_detector.v1): for prose, the
   model returns new | update(id) | temporary(valid_to) through a validated schema,
   given the current date so relative periods become concrete. An update naming an id
   the store does not hold is stored as new rather than guessed.
The classification then drives an ordinary write (new memory or new version) and the
ripple. The prompt prefers "new" when unsure between new and update, because a wrong
update rewrites history.

## Alternatives considered
- LLM for everything — simplest; lost on cost and determinism for structured facts.
- Rules for everything — cannot read "busy with exams this month"; lost on recall.
- Embedding similarity to find the memory being updated — finds similar text, not the
  same fact; kept as a possible candidate pre-filter for the LLM stage (Phase 3).

## Consequences
- Temporary statements never replace permanent memories; they coexist and expire.
- The bench's temporary-unavailability scenario tests stage 2 with FakeLLM; label
  quality of the LLM stage is measured in Phase 3 with real models.

## Revisit if
Stage 1 produces wrong updates (same attribute name, different meaning across
domains), which would argue for domain-scoped attribute namespaces.
