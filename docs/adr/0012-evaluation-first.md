# ADR-0012: Evaluation-first development
Status: Accepted · Date: 2026-10-19

## Context
The project's value is measured claims. Building first and evaluating late invites
unmeasured, inflated claims.

## Decision
A bench smoke suite exists from Phase 1. Behaviour changes run it. Every result lives in
results/ with config and commit (I8). The eval-auditor reviews before publishing.

## Alternatives considered
- Build the product first, evaluate at the end — fast start, untrustworthy end.

## Consequences
A slower start; claims stay defensible.

## Revisit if
Never, for headline claims.
