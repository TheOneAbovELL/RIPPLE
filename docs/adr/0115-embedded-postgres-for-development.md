# ADR-0115: Embedded Postgres with pgvector for development and the local slow suite
Status: Accepted under the autonomous mandate · Date: 2026-10-31 · checkpoint: final delivery

## Context
Every Postgres path (the Store, migrations, retrieval, delivery log, uploads, feedback)
was verified only by the slow suite, which needs a database. The author's machine has
no Docker, so the slow suite had never run: every database test and the migration
chain were unverified. CI would run them, but no commit or remote exists yet. Running the product
locally had the same blocker.

## Decision
1. Add `pgserver==0.1.4` as a development dependency. It ships Postgres and pgvector
   binaries as a wheel for Windows, macOS and Linux and starts a private server in a
   data directory, with no system install and no admin rights.
2. `tools/embedded_pg.py`: `test` starts a fresh server in a temporary directory, runs
   `pytest -m slow` against it and deletes it; `serve` keeps a persistent server under
   `~/.ripple/pgdata` and prints the DATABASE_URL for local runs.
3. psycopg's async mode refuses Windows' default ProactorEventLoop. Entry points that
   drive async Postgres on a developer machine call
   `ripple.storage.loop.use_selector_event_loop()` first. It runs when `ripple.storage`
   is imported (every process that reaches Postgres imports it to register the tables),
   and explicitly in tests/conftest.py and Alembic's env.py. Production runs in Linux
   containers and is unaffected; the call is a no-op off Windows. A uvicorn server on
   Windows must set it before uvicorn creates its loop (the local run does).
4. Production and CI keep the pgvector container (ADR-0004, ADR-0029); pgserver is never
   a runtime dependency.

## Alternatives considered
- Install Docker Desktop: the plan's intent, but it is a system install the collaborator
  should not perform, and it blocked verification for two weeks.
- Install PostgreSQL system-wide: needs admin rights and pgvector built for Windows.
- SQLite for tests: a different SQL dialect, no pgvector, no JSONB; it would verify
  something other than production.

## Consequences
- The first live run found and fixed three real problems: the Windows event-loop
  incompatibility, two contract tests inserting rows for users that did not exist (the
  foreign keys were right, the tests were wrong), and a migration test still pinned to
  revision 0001. The whole slow suite passes on embedded Postgres with pgvector (run output
  in docs/DEVLOG.md, 2026-10-31); the one skip needs Redis.
- Redis has no equivalent here; the lease's Redis test stays skipped locally.

## Revisit if
pgserver stops publishing wheels for a platform the author uses, or its bundled
Postgres major version falls behind the production image's.
