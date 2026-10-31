# ADR-0099: The runner holds a per-ChangeEvent lease while it drives an event
Status: Accepted under the autonomous mandate · Date: 2026-10-26 (wired in the worker and, at the same checkpoint, in the API: ADR-0079 point 4)
Amends ADR-0056 (its open problem "lease per ChangeEvent inside the runner"); builds on ADR-0013.

## Context
A ripple spans several commits and waits on its resolver between them (ADR-0013), so
an event stays open for as long as the slowest LLM call in its waves. The sweep resumes
any open event older than `stale_after` (1 h). ADR-0056 put a per-user lease around the
sweep, which stops two *sweeps* colliding but not a sweep colliding with the live
driver of the event: the API finishing a user's edit under a slow provider, or the
Scout's ripple in the worker. Both would resolve the same outstanding wave and append
two sets of decisions (two LLM calls, possibly two different verdicts on one memory).
IDEAS 8 and the DEVLOG recorded this as waiting for the arq worker, which now exists.
A second, smaller race had the same root: the sweep lists open events, then resumes
each from that snapshot; if the live driver completes the event in between, the
snapshot still looks open and its replayed decisions are behind the store's.

## Decision
1. Core defines `ripple.core.lease.EventLease` (`acquire(event_id) -> bool`,
   `release(event_id)`) and a `holding()` context manager. Core knows nothing about
   ttl or storage.
2. `RippleRunner(..., event_lease=None)`. With a lease, `run` and `resume` acquire it
   keyed by the event id before doing anything and hold it until the event completes
   or the call raises (released in `finally`). Not acquired: the call logs
   `ripple skipped: event leased elsewhere` and returns the event unchanged and open.
   An open event returned by `resume` therefore always means "skipped".
3. With a lease, after acquiring, the runner re-reads the event from the store and
   drives that copy: a completed one is returned as is; otherwise both `run` and
   `resume` continue it through the resume path, so a crashed holder's progress is
   continued, not restarted (for an untouched event resume replays nothing and equals
   run). Without a lease the runner neither re-reads nor changes path: every existing
   caller, the bench and the tests behave exactly as before.
4. `NightlySweep.resume_open` leaves skipped (still open) events out of its result and
   logs `resume skipped: event leased elsewhere` with event and user ids; the next
   sweep tries again.
5. `ripple.worker.lease.ChangeEventLease` adapts the worker's keyed `Lease` (Redis
   `SET NX PX` with a per-acquisition token, ADR-0056) to `EventLease`: key
   `ripple-event:<id>`, ttl `EVENT_LEASE_TTL` = 2 h, pinned by a test above the sweep's
   and the Scout's cron timeouts. `job_context_from_env` gives the worker's runner a
   `ChangeEventLease` over the same backend as the per-user leases.
6. **The API.** `ripple.api.wiring` gives its runner `ChangeEventLease(LazyRedisLease(...))`
   over the same Redis as the worker when REDIS_URL is set (ADR-0079 point 4), which
   closes the API-versus-sweep race. Without REDIS_URL (development) the API runs
   without a lease, and a worker without arq's Redis falls back to a per-process
   in-memory lease.

## Alternatives considered
- Keep only the per-user sweep lease (ADR-0056 as is) — leaves the live-ripple race,
  which is the one that happens: the API and the worker are separate processes.
- A lease taken by the sweep around `resume` only — the live driver never takes it,
  so it excludes nothing; both sides must go through one choke point, the runner.
- Optimistic concurrency on the ChangeEvent row (a version column, compare-and-swap in
  each commit) — detects the collision only after the second resolver call has been
  paid for, needs a migration and a Store protocol change, and still needs a policy for
  the loser. The lease prevents the call instead.
- Lowering the race by raising `stale_after` — trades it for longer SUSPECT windows
  after a real crash and still fails on an unusually slow provider.
- A renewing (heartbeat) lease with a short ttl — removes the fixed-ttl guess but adds
  a background task per ripple; deferred until a run is measured near the ttl.
- Raising an exception when the lease is held — every caller (answers, profile writes,
  derivation, the sweep) would need a handler for a case whose right answer is always
  "someone else is finishing it"; returning the open event says exactly that.

## Consequences
- With a lease, the runner reads the event once more per call (one indexed read).
- A process that crashes while holding a lease blocks that event for up to 2 h; its
  memories stay SUSPECT (flagged, I1) until a later sweep. Recovery is slower, never
  wrong.
- A run longer than the ttl loses its exclusion; the damage is bounded as before
  (only still-SUSPECT, undecided members are re-resolved). The ttl is a guess until runs
  are measured (Revisit).
- The bench and tests run without a lease and are unaffected.
- `RedisLease` keeps one token per key per instance. If a holder outlives the ttl and
  the same process re-acquires that key, the stale holder's release frees the new
  holder's lease. Per-event keys make this rarer than for sweeps, but a per-acquisition
  token is the follow-up.
- A release that fails (Redis down) after a completed ripple is logged by
  `ChangeEventLease.release` and not raised, so a committed write never reports an
  error; the ttl frees the key.

## Revisit if
Langfuse traces show a ripple's wall time above half the ttl, or a second worker or API
replica is deployed without a shared Redis (then the lease needs a shared backend or
moves to the database).
