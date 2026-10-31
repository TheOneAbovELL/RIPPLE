# ADR-0010: Provider-agnostic LLM router with structured outputs
Status: Accepted · Date: 2026-10-19

## Context
Many components call LLMs; we need reliability, testability and reproducible evals.

## Decision
All LLM calls go through ripple.llm.Router: a model per task from config, JSON-schema
outputs validated by Pydantic (I4), retries with backoff, provider fallback, cost and
latency logging, model versions pinned per eval run. FakeLLM implements the same interface.

## Alternatives considered
- Direct SDK calls everywhere — untestable, no single place for retries or logging.

## Consequences
One choke point to maintain; offline tests become easy.

## Revisit if
A provider feature we need cannot pass through the router.
