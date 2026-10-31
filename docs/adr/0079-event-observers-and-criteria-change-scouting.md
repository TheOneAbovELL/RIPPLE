# ADR-0079: Event observers on the runner; a criteria change queues a per-user Scout run
Status: Accepted under the autonomous mandate · Date: 2026-10-26 · checkpoint C3
(FR-8 second trigger; WS-9 handover, coordinator action 2)

## Context
FR-8 says the Scout runs daily and when the student's search criteria change. The
criteria memory changes only through a ripple: a profile edit (API, Telegram, MCP), a
resume confirmation, an answer, or the nightly sweep expiring a fact. Calling the
Scout from each of those call sites would put the same check in five places and miss
the next one added. Core must stay domain-agnostic: it cannot know what "criteria" is.
A criteria change must not make the user's write wait on page fetches.

## Decision
1. `ripple.core.ripple.EventObserver` is a protocol with one method,
   `event_completed(event)`. `RippleRunner(observers=...)` calls each after the
   completion is committed, in order. An observer that raises is logged with its
   traceback and the next one still runs: the ripple is committed and correct, so a
   follow-up failure (a queue that is down) does not turn the user's write into an
   error. The daily Scout run is the backstop for a lost trigger.
2. `ripple.agents.scout.CriteriaChangeObserver(store, trigger)` calls
   `trigger.on_criteria_changed(user_id)` when `event_changed_criteria` holds (the
   trigger memory is the criteria, or a decision updated or retired it). Confirming a
   parked question ("still holds") completes its event without the runner and fires no
   observer; that is correct here, because a confirmation changes no criteria.
3. Production uses `EnqueueingScoutTrigger`: the API and the worker enqueue
   `scout_user_job(user_id)` on the arq Redis, with `_job_id=scout_user:<user id>` and a
   two-minute deferral so a burst of changes (a resume with many facts) merges into one
   run. The job runs `jobs.scout_user`: the daily `scout_run` body restricted to one
   user, under the same per-user lease and with a 30-minute timeout like the cron slot.
   It first checks the user is still active, so an account deleted after the enqueue
   gets nothing written under its id (FR-15). Without REDIS_URL (development) the API's
   runner has no observer.
4. The API's runner also gets the per-ChangeEvent lease (ADR-0099) over the same Redis,
   through `LazyRedisLease`, which opens the shared pool on first use because the
   Services are built before the event loop runs.

## Alternatives considered
- Call the trigger from each write path: five call sites, and the sweep's expiry path
  is in core where the Scout cannot be named.
- A post-commit hook on the Store: fires per transaction, several times per ripple and
  before the ripple's later waves; the event's completion is the meaningful moment.
- Run the Scout inline (`ImmediateScoutTrigger`): makes a profile edit wait on fetches
  and LLM parsing; kept for development and tests.
- Let an observer's exception propagate: the caller would report failure for a write
  that committed, and a retry would write it again.

## Consequences
- tests/core/test_event_observers.py pins "after the commit, once, never fatal, not when
  leased elsewhere"; tests/agents/test_scout_trigger.py the criteria check;
  tests/worker/test_scout_user_job.py the job, its lease and the enqueue wiring;
  tests/api/test_wiring_c3.py the API's Redis-only wiring.
- Observers run inside the runner's event lease; a slow observer extends the hold. The
  production observer only enqueues.
