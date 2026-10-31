# ADR-0095: A Postgres delivery log keyed by (user, kind, key) makes digests and alerts survive restarts
Status: Accepted under the autonomous mandate · Date: 2026-10-26

## Context
ADR-0056 made the worker's digest and alert jobs idempotent through a `DeliveryLog`
protocol (`ripple.notify.contracts`) and shipped only `InMemoryDeliveryLog`. Its own
consequences say a worker restart on digest day can resend a digest "until the Postgres
DeliveryLog lands". The production plan (WS-13, "Idempotency and leases") asks for that
log. The protocol is fixed: `last_digest_day`, `record_digest`, `last_alert_at`,
`record_alert`. `DigestService` reads before it sends and records after it sends; it
does not change here.

## Decision
1. One table, `delivery_log` (`ripple.storage.delivery_tables`, migration 0005,
   hand-written per ADR-0016): `user_id`, `kind`, `key`, `sent_at` (timezone-aware).
   The primary key is `(user_id, kind, key)`; an index on `(user_id, kind, sent_at)`
   serves "newest digest for this user".
2. A digest is the row `kind="digest"`, `key=<ISO day>`, `sent_at=<that day, midnight
   UTC>`. An alert is `kind=<AlertKind value>` (`high_fit`, `deadline_soon`),
   `key=<opening memory id>`, `sent_at=<when it was sent>`.
3. `PostgresDeliveryLog(engine)` in `ripple.notify.delivery_log`, one short transaction
   per call like the other Postgres stores:
   - `record_digest` is `INSERT ... ON CONFLICT DO NOTHING`: recording a day twice
     leaves one row.
   - `last_digest_day` is `max(sent_at)` over the user's digest rows, returned as a
     UTC date.
   - `record_alert` is `INSERT ... ON CONFLICT DO UPDATE SET sent_at = excluded.sent_at`:
     the row is the (user, opening, kind) pair's state, and a re-alert after the
     cooldown moves its time forward.
   - `last_alert_at` reads that one row, returned timezone-aware in UTC.
4. Memory ids are plain strings, not foreign keys, so an alert's record outlives a
   forgotten opening, as the event tables do.
5. `InMemoryDeliveryLog` moves out of the notify tests into the same module and keeps
   the latest day on `record_digest`, matching the Postgres read. Both implementations
   run one contract (`tests/notify/test_hardening_delivery_log.py`; the Postgres run
   is `tests/storage/test_hardening_delivery_log_postgres.py`, slow), including "a
   DigestService rebuilt over the same log does not resend".

## Alternatives considered
- Redis keys with a TTL (the worker already has Redis, ADR-0017) — Redis is the job
  queue, not a store of record; a flushed or restarted Redis would forget the day's
  sends, which is the failure this ADR exists to remove. Lost.
- Two tables, one for digests and one for alerts — the shapes are the same (who, what
  kind, which item, when); one table with a three-part key is less schema and one
  drift test. Lost.
- Append-only rows with one row per send — gives a send history, but `last_alert_at`
  would need a `max()` per pair and the table would grow every night with nothing
  reading the history. The upsert keeps one row per pair. Lost for now; the access log
  and ChangeEvents already carry history.
- A foreign key from `key` to `memories.id` — the forget cascade (I7) would delete the
  alert row with the opening, so a re-created opening could be alerted again inside
  the cooldown, and digests have no memory to point at. Lost.

## Consequences
- Production gains nothing until the worker uses it: `ripple.worker.wiring` still
  builds `DigestService` with `InMemoryDeliveryLog()` (a TODO there names the WS-6
  follow-up). Swapping it is a one-line coordinator change, listed in the WS-13
  handover.
- Sends stay at-least-once. `DigestService` sends and then records; a crash between
  the two resends after restart. The log removes the restart-and-retry duplicate, not
  this window.
- The primary key stops duplicate rows, not duplicate sends. Two workers running the
  digest job for the same user at the same moment can both read "not sent today" and
  both send; the digest and alert jobs take no per-user lease today (only the sweep
  and the Scout do, ADR-0056, ADR-0072). With one worker process in the pilot this
  does not arise.
- Digest days are UTC days, as in ADR-0056; a digest stored at midnight UTC carries no
  send time.
- The rows hold no content, only a user id, an opening id and times. Neither the
  export nor `DELETE /me` (ADR-0044) touches `delivery_log` today, so a deleted user's
  rows stay; the handover lists adding them to `DELETE /me` as an open problem.

## Revisit if
The worker runs more than one process, or a student reports a duplicate digest: then
claim the day with an insert before sending (insert-then-send) or put the digest and
alert jobs under the per-user lease.
