# ADR-0001: Record decisions as ADRs
Status: Accepted · Date: 2026-10-19

## Context
A 19-month project built with AI assistance. The author must be able to explain every choice.

## Decision
Lightweight ADRs in docs/adr for the categories listed in CLAUDE.md. Accepted ADRs are
immutable; changes happen by superseding.

## Alternatives considered
- Decisions in chat or commit messages — lost and unsearchable.
- A wiki — drifts from the code.

## Consequences
Small overhead per decision, reduced by the /adr skill. Full traceability.

## Revisit if
ADRs are routinely skipped; then simplify the template rather than drop the practice.
