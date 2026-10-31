# ADR-0028: Langfuse tracer implemented now behind the Tracer protocol
Status: Accepted · Date: 2026-10-24 (under the autonomous mandate; amends ADR-0018's timing)

## Context
ADR-0018 chose Langfuse over OpenTelemetry but deferred the dependency to "Phase 2 with
the first real provider adapter". The Anthropic adapter exists (ADR-0027) and the
production plan requires traces before the first real run, so the deferral has ended.

## Decision
Add `langfuse` (exact pin) and implement `LangfuseTracer` in `ripple.llm.tracing`
behind the existing `Tracer` protocol. Spans carry the attributes the Router and
agents already set (task, model, tokens, latency, trace_id), never prompt or user
content. Configuration from LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST
(already in .env.example); when any is missing the wiring falls back to
LoggingTracer and logs that it did, so tracing is never on the critical path. Flushing
happens on shutdown hooks of the API and the worker.

## Alternatives considered
- Keep deferring — leaves the first real runs without traces, exactly when they are
  most needed. Lost.
- OpenTelemetry exporter to a generic backend — ADR-0018 already weighed it; Langfuse
  speaks OTel, so switching stays cheap.

## Consequences
- One dependency (plus its OTel SDK transitively). Tests use a fake Langfuse client;
  no network.
- Content stays out of traces by construction: the tracer only sees attribute dicts.

## Revisit if
Langfuse's SDK changes its OTel export, or self-hosting proves heavier than the pilot
can carry (then the cloud free tier remains).
