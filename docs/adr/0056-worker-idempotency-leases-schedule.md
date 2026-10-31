# ADR-0056: Worker jobs are idempotent per user; sweeps hold a per-user lease; UTC schedule
Status: Accepted under the autonomous mandate · Date: 2026-10-19 (WS-6)

## Context
ADR-0017 chose arq on Redis and required jobs to be idempotent, because a ripple resumed
by the sweep (ADR-0013) must not double-apply. arq's cron can fire a job on more than one
worker, a job can be retried after a timeout, and `NightlySweep.resume_open` resumes any
open ChangeEvent older than `stale_after` (1 h). Two sweeps of the same user running at
once would both call `RippleRunner.resume` on the same event and resolve the same wave
twice (two LLM calls, two sets of decisions appended). The digest side must not send a
user two digests on one day because a cron fired twice.

## Decision
1. **Plain job functions** (`ripple.worker.jobs`) take a `JobContext` (store, runner,
   clock, user directory, sweep, digest service, lease) and are tested without Redis.
   The arq layer (`ripple.worker.settings`) only unpacks the context from arq's `ctx`.
2. **Per-user lease for the sweep**: `sweep:<user_id>` is acquired before
   `NightlySweep.run` and released after, with a 2 h ttl so a crashed holder cannot
   block the next night. In tests the lease is in memory and expires by the FakeClock;
   in the worker it is Redis `SET NX PX` on arq's own connection (`RedisLease`) with a
   per-acquisition token, released by a compare-and-delete script so a holder that
   outlived its ttl cannot free the next holder's lease. A user whose lease is held is
   skipped and reported, not retried in the same run. The lease ttl (2 h) is pinned
   above the sweep cron's timeout (1 h) by a test.
3. **Per-user failure isolation**: one user's exception (the sweep's or the lease
   backend's) is logged with the traceback, the loop continues, and the job raises
   `JobFailedForUsersError` at the end, with the originals as an `ExceptionGroup` in
   `__cause__`, so arq records a failed run with every traceback. Nothing is swallowed;
   nothing stops the other users.
4. **Delivery idempotency** is the DigestService's, through a `DeliveryLog`: one digest
   per user per UTC day, one alert per (user, opening, kind) per cooldown (ADR-0055). The
   day or alert is recorded only after the transport accepted the message, so a failed
   send is retried by the next run and a successful one is never repeated.
5. **Schedule (UTC)**: Scout 01:00 (Phase 3, raises NotImplementedError until built),
   sweep 21:00, digest 02:30 (08:00 IST, after Scout and sweep), alerts every hour at
   :15. All cron jobs are `unique`, so arq itself refuses to start a second copy of a
   job that is still running.
6. **Startup refuses defaults**: `REDIS_URL` unset means `on_startup` raises
   `ConfigurationError` rather than letting arq fall back to localhost.

## Alternatives considered
- One global lease for the whole sweep — simpler, but one slow user blocks everyone,
  and it does not scale to two workers splitting users. Lost.
- Lease per ChangeEvent inside the runner — the right long-term place for the
  double-resolution guard, but the runner is coordinator-owned core (frozen this round).
  Recorded as the open problem below.
- Skip failed users silently and return a report — hides failures from the scheduler's
  run history. Lost (python.md: never swallow exceptions).
- Store "last digest day" on the user row — couples delivery state to identity (WS-3)
  and to one transport. A `DeliveryLog` protocol keeps it separate; the Postgres
  implementation is a follow-up.

## Consequences
- Tests cover expiry plus resume per user, lease overlap, lease release on failure,
  digest reruns and alert cooldown with FakeClock; none needs Redis. One slow test
  exercises `RedisLease` against `TEST_REDIS_URL` (skipped without one).
- Open problem (for DEVLOG, coordinator-owned): the lease stops two *sweeps* colliding,
  not a sweep colliding with a *live* ripple that is legitimately slow (an LLM call
  longer than `stale_after`, or an ask waiting on the user). `resume` only resolves
  members that are still SUSPECT and undecided, which bounds the damage to one extra
  resolution of the outstanding wave; a per-event lease in the runner would remove it.
- `InMemoryDeliveryLog` forgets on restart, so a worker restart on digest day could
  resend one digest until the Postgres DeliveryLog lands.

## Revisit if
Two workers are deployed, or a sweep's run time approaches the 2 h lease ttl; then the
lease moves into the runner per event and the ttl is measured, not assumed.
