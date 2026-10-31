# ADR-0105: Pilot feedback is one row per (student, memory, kind), first statement wins
Status: Accepted under the autonomous mandate · Date: 2026-10-31

## Context
Claim C3 and docs/04 "Pilot metrics" need to know what students did with what Ripple
showed them: whether a recommendation was saved, applied to or dismissed, and whether
a question the resolver asked (FR-7) was worth asking. Nothing in the store records
that. Wave B (docs/plans/wave-b.md, WS-16) asks for a table, a store and
`POST /feedback`, with I1 and I6 respected and the rows erased with the account
(FR-15, ADR-0044). The bot buttons and dashboard controls that will call it belong to
other workstreams.

## Decision
1. Table `pilot_feedback` (`ripple.storage.feedback_tables`, migration 0009, hand-
   written per ADR-0016; `down_revision` 0006 because 0007 and 0008 are reserved):
   `id`, `user_id` (FK to users, ON DELETE CASCADE), `target_memory_id` (FK to
   memories, ON DELETE CASCADE), `kind`, `note` (≤ 280 characters, optional),
   `created_at` (timezone-aware). A unique constraint on `(user_id, target_memory_id,
   kind)` and an index on `created_at` for the weekly report.
2. Five kinds (`FeedbackKind`): `saved`, `applied`, `dismissed` are about a
   recommended opening; `question_useful`, `question_not_useful` are about a memory
   the resolver asked about. `ripple.pilot.feedback.record_feedback` checks the split
   for every caller (the API now, the Telegram buttons next): a recommendation kind
   needs a target of kind `opening`; a question kind needs at least one ChangeEvent with
   an `ask` decision on the target (`Store.events_asking`). It writes the feedback row
   and nothing else.
3. **First statement wins.** `FeedbackStore.record` returns the existing row when
   `(user, target, kind)` is already there (Postgres: `INSERT ... ON CONFLICT DO
   NOTHING` on the named constraint, then a read in the same transaction; if a
   concurrent delete removed the conflicting row in between, `FeedbackRecordRaceError`
   and the API answers 409). `POST /feedback` answers 201 for a new row and 200 with the
   first row for a repeat, so a double-tapped Telegram button or a retried request is
   one statement. A student who changes their mind records another kind; the report
   decides how kinds combine (ADR-0106).
4. `POST /feedback` and `GET /feedback` (own rows, oldest first, optional
   `target_memory_id` filter) sit behind the same bearer auth and write-rate limit as
   every product route. A target that is unknown or another user's is 404, as in
   ADR-0040; a kind that does not fit the target is 422. Responses carry ids, kinds,
   notes and times, never memory content, so a RETIRED target is never returned (I1).
   "applied" stores that the student says they applied; nothing is sent or submitted
   anywhere (I6), and no memory or ChangeEvent is written.
5. **Forgetting a memory removes the feedback about it.** The target FK cascades, so
   the forget API (I7, the only hard deletion) deletes the rows in its own transaction,
   whichever path called it (dashboard, bot, MCP, `DELETE /me`). A note such as "my
   real CGPA is 7.2" never outlives the memory it is about. A new version of an opening
   keeps the old version's rows, because versions are not deleted; the report joins
   versions (ADR-0106).
6. Until `Services` gains a `feedback_store` field (coordinator-owned file), the router
   reads `app.state.feedback_store` through one dependency, `feedback_store_of`.

## Alternatives considered
- Append-only rows, one per tap — keeps the full history, but every duplicate tap
  would need deduplication in every consumer, and a retried request would inflate the
  saved share. The unique key moves that rule into one place. Lost.
- Last statement wins (upsert the kind, note and time) — "applied" on Monday then a
  second tap on Friday would move the date the student applied. Lost; the report's
  rules handle changed minds instead.
- A single `state` column per (student, opening) such as saved → applied → dismissed —
  a state machine the pilot does not need, and it loses that an opening was saved
  before it was dismissed. Lost.
- Storing feedback as memories (kind `feedback`) so the ripple engine sees them —
  feedback is about the system, not a belief about the student's world; it would enter
  retrieval and the dependency graph and could change agent behaviour, which would
  contaminate the pilot measurement. Lost.
- `target_memory_id` as a plain string (as `delivery_log` does, ADR-0095) plus an
  explicit `delete_for_targets` call after each forget — four call sites today (memories
  router, bot, MCP, DELETE /me) and any future one could miss it, leaving a note behind
  (I7). The FK makes the database enforce it. Lost. The cost: the in-memory store does
  not cascade, so the property is tested only in the slow Postgres test.

## Consequences
- The coordinator registers `feedback_tables` in `ripple.storage.__init__` before or
  with migration 0009 (otherwise autogenerate proposes dropping the table and the
  unfiltered drift tests fail when run alone), adds the router to `create_app`, the
  `Services.feedback_store` field (in-memory default, Postgres in wiring), the
  `delete_for_user` line in `DELETE /me` (the in-memory store needs it; Postgres
  cascades anyway) and the rows in `GET /me/export`. Two tests in
  tests/api/test_feedback.py are xfail(strict) until then.
- When migration 0007 or 0008 lands with `down_revision` 0006, 0009 must be re-pointed
  before any database runs it (tests/storage/test_feedback_migration.py fails on two
  heads).
- The OpenAPI document gains a `feedback` tag; the dashboard snapshot is regenerated.
- A note never leaves the database: the weekly report ignores notes (ADR-0106).

## Revisit if
Students need to undo a statement (add `DELETE /feedback/{id}`), or the report needs a
per-tap history (drop the unique key and dedupe in the report).
