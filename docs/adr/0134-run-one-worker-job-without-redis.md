# ADR-0134: Run one worker job locally without Redis
Status: Accepted under the autonomous mandate · Date: 2026-10-31 · workstream: WS-20

## Context
The worker's jobs (nightly_sweep, daily_digest, hourly_alerts, scout_run) run only
under arq, which needs Redis (ADR-0017). The author's machine has neither Docker nor
Redis, so a developer could not run a sweep against the local database or see what a
digest would say. The job functions are already plain async functions over a
`JobContext` (ADR-0017), and `InMemoryLease` exists for single-process use.

## Decision
`uv run python -m ripple.worker.run_once <job>` with job one of `nightly_sweep`,
`daily_digest`, `hourly_alerts`, `scout_run`:
1. Builds a `JobContext` against `DATABASE_URL` with the same components as
   `job_context_from_env` (Postgres store, jobs rules plus LLM fallback,
   `ProfileDerivationObserver`, directory, sweep, digest; a test pins the runner's
   observers to the worker's) and an `InMemoryLease`. The lease excludes only this
   process's own work; a local API on the same database holds no event lease. No
   criteria-change enqueue (there is no queue); the output says so. The mirror exists
   because `job_context_from_env` cannot take a transport or delivery log; the handover
   asks for those two parameters so run_once can delegate instead.
2. Transport: with `TELEGRAM_BOT_TOKEN` set, the real `TelegramTransport` and the
   Postgres delivery log (a real send is recorded, ADR-0095). Without it, a
   `PrintingTransport` writes each message that would be sent, with its chat id, to
   stdout, and an in-memory delivery log is used so a dry run never marks a digest as
   sent in the database.
3. Prints the job's summary as one JSON line (`messages`: "printed" or "sent"; jobs
   still write their ripples for real) and exits 0, or 1 when `JobFailedForUsersError` names failed users, 2 on a
   configuration error.
4. Calls `use_selector_event_loop()` first (ADR-0115).

## Alternatives considered
- fakeredis for arq: a new dependency to emulate a queue nobody needs for one run.
- Calling the job from a Python shell: undocumented and easy to get wrong (lease,
  transport, loop policy).

## Consequences
- `scout_run` and the sweep's LLM fallback still need `ANTHROPIC_API_KEY`; without it
  a user whose ripple reaches the fallback fails and the run exits 1, naming them.
- Only a single run: no schedule. The arq worker remains the production path.

## Revisit if
Redis becomes available locally, or a job gains state that an in-memory lease cannot
represent.
