# ADR-0016: SQLAlchemy 2 (async, psycopg) + Alembic, in a storage package outside core
Status: Accepted · Date: 2026-10-19 (under the author's blanket authorization for Phase 0;
revisit on request)

## Context
ADR-0004 chose PostgreSQL + pgvector but no ORM, driver, migration tool or home for the
SQL code. CLAUDE.md's stack line names SQLAlchemy 2 + Alembic. The architecture-guardian
asked where the SQL store lives, because core is pure (python.md) and ADR-0005 keeps
frameworks out of it, and whether the engine is sync or async, which FastAPI and
LangGraph will force.

## Decision
- **SQLAlchemy 2.0** with the **async engine** over **psycopg 3** (`postgresql+psycopg://`,
  the URL already in .env.example). One driver serves both the async app and Alembic.
- **Alembic** for migrations, config at `alembic.ini`, scripts in `infra/migrations/`,
  run with `uv run alembic upgrade head`. Alembic drives the async engine through
  `run_sync`.
- A new package **`src/ripple/storage`** holds the declarative base, table definitions
  and the Postgres Store implementation. It imports `ripple.core`; `ripple.core` never
  imports it or SQLAlchemy (enforced by tests/core/test_boundaries.py). Core's domain
  models stay Pydantic; storage maps them to rows.
- Exact pins: sqlalchemy, alembic, psycopg[binary] as recorded in pyproject.toml.

## Alternatives considered
- asyncpg driver — faster, but a second driver next to the sync one Alembic would need;
  psycopg 3 does both. Lost on simplicity.
- SQLModel — one class as Pydantic model and table; couples core's domain models to the
  ORM, which breaks core purity. Lost.
- Plain SQL with psycopg and a SQL-file migration tool (yoyo, dbmate) — fewer
  abstractions, but hand-written SQL for every query and no autogenerate; the author
  knows SQLAlchemy. Lost on effort.
- Sync engine only — simpler, but every FastAPI and LangGraph call would block a
  worker thread (python.md: no blocking calls inside async functions). Lost.

## Consequences
- `ripple.storage` is a new module in docs/02's table (may import core; everything
  above it may import storage). CLAUDE.md's code map gains it.
- Two Store implementations (in-memory in tests, Postgres in storage) must pass the same
  contract tests (Phase 1).
- Alembic autogenerate is used with review; migrations are committed, never edited
  after they run anywhere.

## Revisit if
pgvector's SQLAlchemy integration or async psycopg blocks a requirement, or the
in-memory and Postgres stores drift.
