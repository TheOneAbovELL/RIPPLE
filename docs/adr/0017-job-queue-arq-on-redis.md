# ADR-0017: Background jobs with arq on Redis
Status: Accepted · Date: 2026-10-19 (under the author's blanket authorization for Phase 0;
revisit on request)

## Context
FR-8 (daily Scout, re-run on criteria change) and the Curator's nightly sweep need a
scheduler and a worker. The stack in CLAUDE.md and the project proposal names a
Redis-backed queue; no ADR chose the library, and the architecture-guardian asked
whether a Postgres-backed queue would remove a service entirely.

## Decision
**arq** on **Redis**. arq is async-native (matches ADR-0016 and LangGraph), has cron
scheduling built in, and is a few hundred lines to understand and defend. Redis is a
compose service from Phase 0 (`redis:7.4-alpine`); the arq dependency is added in
Phase 3 with the worker, with an exact pin. No other code may talk to Redis directly.

## Alternatives considered
- Postgres-backed queue (procrastinate, SKIP LOCKED) — removes a service, in the
  spirit of ADR-0004. Lost because the author's stated stack is Redis, Redis also
  serves rate-limit and dedupe caches for the Scout later, and arq is more widely
  known, which matters for a thesis defence. Recorded as the fallback if Redis
  operations prove a burden on one VPS.
- rq — simple but synchronous workers; every job would wrap async code. Lost.
- dramatiq — solid, but its scheduling needs a separate periodic add-on. Lost.
- Celery — far more machinery than one developer and one VPS need. Lost.

## Consequences
- One more service to run and monitor; compose healthchecks cover it.
- Jobs must be idempotent: a ripple resumed by the sweep (ADR-0013) must not double-apply.
- Tests never need Redis: the worker's job functions are plain async functions tested
  directly; only a slow test checks the queue end to end.

## Revisit if
Redis operations cost real time in the pilot, or arq stops being maintained; then
move to procrastinate on Postgres.
