# ADR-0009: A trained small model for link finding
Status: Accepted · Date: 2026-10-19

## Context
Recent cascading work assumes dependency links are given. Inferring them is open (C1).
LLM linking on every write is expensive.

## Decision
Three linkers behind one interface: rules (baseline), LLM, and a trained small encoder
(ModernBERT or DeBERTa-v3) pair classifier. The trained model becomes the default if it
meets H3.

## Alternatives considered
- LLM only — cost on every write.
- Rules only — low recall on hidden links.
- Embedding similarity — measures similarity, not dependency.

## Consequences
Needs labelled data: synthetic, hand-checked, and pilot corrections.

## Revisit if
The trained model misses H3 by a wide margin after two training rounds.
