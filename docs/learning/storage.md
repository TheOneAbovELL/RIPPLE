# ripple.storage — PostgresStore, tables and migrations
Written 2026-10-19 for Phase 1 task 1.8.

## 1. What it does
Persists memories, links, change events and forget events in PostgreSQL and exposes
them through the same `Store` protocol the in-memory store implements, so every core
component works unchanged against either.

## 2. Why it exists
ADR-0004 (one Postgres with pgvector), ADR-0016 (SQLAlchemy 2 async over psycopg,
Alembic, storage outside core). NFR-4 (transactional commits) and I7 (an audit trail
that survives deletion).

## 3. How it works
- `tables.py` defines four `sa.Table`s on the shared metadata. Event rows reference
  memory ids as plain strings, not foreign keys, so an audit row outlives a forget.
  Links do carry foreign keys; forget deletes links before memories.
- `postgres.py`: `_Reads` implements every read over an `AsyncConnection`;
  `PostgresTransaction` adds the writes and is yielded by `PostgresStore.transaction()`
  inside `engine.begin()`, so the runner's reads inside a transaction see its own
  writes and a raised exception rolls everything back. Reads outside a transaction use
  a short-lived connection each.
- Row/model conversion: `model_dump(mode="json")` for JSONB columns, with real
  datetimes re-applied for timestamptz columns; `Decision`s are rebuilt from JSON on
  the way back.
- `version_chain` walks supersedes_id backwards, then forwards by querying
  `supersedes_id = tail.id` until nothing is newer.
- Migration 0002 is hand-written; the slow test
  `test_migrations_match_table_metadata` runs Alembic's autogenerate comparison against
  the migrated database and asserts no diff, so tables.py and the migration cannot
  drift.

## 4. Trade-offs
- SQLAlchemy Core statements over `sa.Table`, not ORM sessions: fewer moving parts,
  explicit SQL shape, no identity-map surprises with immutable Pydantic models.
- A connection per read outside transactions is simple and correct; pooling at the
  session level is a later optimisation if profiling asks for it.
- JSONB for `decisions` and `affected_ids` keeps the event write to one row; querying
  inside them is not needed yet (the inspector reads whole events).
- No `ON DELETE CASCADE`: deletion must stay explicit and logged (I7).

## 5. Failure modes and tests
The contract in tests/core/store_contract.py runs against both stores: not found
errors, ordering, status filters, version chains, rollback on error, open events,
expiry queries, deletion. `test_postgres_store.py` adds the schema-drift check. Both
are slow tests that need TEST_DATABASE_URL; CI provides it, the author's machine will
once Docker is installed.

## 6. Interview questions
1. *Why no foreign keys from events to memories?* Forget deletes memories; the audit
   must remain.
2. *What guarantees the in-memory and Postgres stores behave the same?* One shared
   contract test class, parameterised by fixture.
3. *Why async?* FastAPI and LangGraph are async; a sync driver would block the event
   loop (python.md).
4. *How do you know the migration matches the code?* Autogenerate comparison in a test,
   not by eye.
5. *Where will the embedding column go?* A Phase 3 migration adding a pgvector column
   to memories, with its own ADR for the model.

## 7. Exercise
Start the compose services, set TEST_DATABASE_URL, run
`uv run pytest -m slow -q`, then delete one index from migration 0002 and watch the
drift test name it.
