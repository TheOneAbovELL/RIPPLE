# ADR-0018: Observability with Langfuse over OpenTelemetry; structured logging until then
Status: Accepted · Date: 2026-10-19 (under the author's blanket authorization for Phase 0;
revisit on request)

## Context
NFR-6 requires every agent step traced with cost and latency; NFR-2 requires cost and
latency per ripple step; C4 is a cost claim and needs trustworthy numbers. The roadmap
asked Phase 0 to pick the tool. The proposal suggested Langfuse with OpenTelemetry.

## Decision
- **Langfuse**, whose Python SDK v3 is built on OpenTelemetry, is the tracing backend:
  cloud free tier for development, self-hosted in compose for the pilot if data
  residency requires it (NFR-3). The dependency is added in Phase 2 with the first real
  provider adapter, with an exact pin; the Router emits one span per LLM attempt and
  the Curator one span per ripple wave.
- Until then, and underneath it always, **stdlib logging with structured `extra`
  fields** (task, model, attempts, latency_ms, tokens, trace_id, memory_id). No prompt
  or user message content at INFO (python.md).
- Eval runs (ADR-0012) do not depend on Langfuse: the Router's returned usage is what
  results/ records, so numbers trace to files, not a dashboard (I8).

## Alternatives considered
- OpenTelemetry only, exported to a generic backend (Jaeger, Grafana Tempo) — vendor
  neutral, but no LLM-specific views (prompts, cost per model) without building them.
  Lost on effort; kept open because Langfuse speaks OTel, so switching later is cheap.
- LangSmith — tight LangGraph integration, but ties tracing to one vendor's ecosystem
  and its free tier is limited. Lost.
- Logs only — no trace tree, no cost dashboards; fine for Phase 0–1, not for the pilot.
  Kept as the baseline that must always work.

## Consequences
- .env.example already carries LANGFUSE_* keys; they stay empty until Phase 2.
- Tracing must never be on the critical path: a Langfuse outage cannot fail a ripple.
- One more account (or compose service) to manage.

## Revisit if
Langfuse's SDK changes break the OTel export, or self-hosting proves heavier than the
pilot can carry.
