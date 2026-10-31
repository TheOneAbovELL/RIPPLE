# ADR-0007: Retire, never silently delete
Status: Accepted · Date: 2026-10-19

## Context
Explanations, undo and auditing need history; privacy needs real deletion.

## Decision
State changes keep history with ChangeEvents. Hard deletion happens only via the forget API,
cascading along derived_from links (I7).

## Alternatives considered
- Overwrite in place — no history, no undo, no explanations.
- Soft-delete flag only — no reasons recorded; forget is not real deletion.

## Consequences
Storage grows; needs a retention policy. Forget must truly delete, in line with the DPDP Act.

## Revisit if
Storage cost becomes a problem in the pilot.
