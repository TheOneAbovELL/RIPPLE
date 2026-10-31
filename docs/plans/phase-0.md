# Phase 0 plan — Foundation
Written 2026-10-19 by the collaborator. Status: **approved by the author on 2026-10-19**.

## Goal and exit criteria (from docs/05-roadmap.md)
Phase 0, 2026-10-20 → 2026-11-08.
- [x] Repo, uv, ruff, pyright, pytest config
- [ ] CI green on GitHub Actions (workflow written 2026-10-19; needs a remote and a push)
- [x] ADRs: observability; ORM + migrations (sync vs async); job queue (Redis vs Postgres-backed)
- [ ] infra/docker-compose.yml: postgres+pgvector, redis (written 2026-10-19; Docker not installed locally, verify there or in CI)
- [ ] Alembic set up; initial migration enables pgvector (offline `--sql` verified 2026-10-19; live upgrade needs Docker or CI)
- [x] llm router skeleton + FakeLLM; FakeClock; tests/fakes
- [x] Author approves ADR-0013, 0014, 0015 (ripple semantics, versioning, triggers)
Exit: CI green; offline tests pass; services start.

## Environment found on 2026-10-19
| Tool | State | Consequence |
|---|---|---|
| git | 2.52, but the folder is **not a repository** | author runs `git init` before task 0.1 (collaborator never runs git write commands) |
| uv | not installed | author installs uv (ADR-0011) before task 0.1 |
| python | 3.13.3 on PATH | fine; uv will pin 3.12+ per project, so `requires-python = ">=3.12"` |
| docker | not installed | tasks 0.3 and 0.4's live checks need Docker Desktop; CI can cover them meanwhile |
| node | 22.19 | not needed until apps/web (Phase 4) |
| folder | lives under OneDrive\Desktop | **risk**: OneDrive syncs .venv and caches, causing slow installs and file locks; see Risks |

## Ordered tasks (each one session; tests first; [human] marks author-owned work)

### 0.1 Project skeleton and tooling
Files: pyproject.toml (uv, pinned versions, `[tool.ruff]`, `[tool.pyright]`,
`[tool.pytest.ini_options]` with the `slow` marker), uv.lock, src/ripple/__init__.py and
one `__init__.py` per existing package dir, tests/conftest.py, tests/test_smoke.py,
.gitignore additions (.venv, __pycache__, .pytest_cache, results/*/raw).
Tests first: test_smoke_imports_ripple_package.
Acceptance: `uv sync`, `uv run ruff check .`, `uv run pyright`, `uv run pytest -m "not slow"`
all pass with real output shown.
Decision needed: none (ADR-0011 covers the tools). Exact pins recorded in pyproject.

### 0.2 CI on GitHub Actions
Files: .github/workflows/ci.yml running uv sync, ruff check + format --check, pyright,
pytest -m "not slow" on ubuntu-latest, Python 3.12; a second job with a pgvector
service container running `pytest -m slow` once task 0.4 exists.
Tests first: none (infrastructure); acceptance is a green run on the author's remote.
Acceptance: CI badge green after the author pushes.
Depends on: the author creating the GitHub remote.

### 0.3 Services: docker compose (after ADR-0017)
Files: infra/docker-compose.yml (postgres with a pinned pgvector image, healthchecks,
volumes; redis only if ADR-0017 keeps a Redis-backed queue), .env.example wiring.
Tests first: tests/infra/test_services_reachable.py marked slow, skipped when
DATABASE_URL is unset; this test is the acceptance check (no separate script).
Acceptance: `docker compose -f infra/docker-compose.yml up -d` then the slow test
passes. Blocked locally until Docker is installed; CI service containers cover it.
Decision needed: the pgvector image tag (pinned), recorded in the compose file comment.

### 0.4 Migrations pipeline (after ADR-0016)
Files per ADR-0016, which also decides where the SQL store lives (inside core, or a
separate storage package so core never imports an ORM) and whether `sqlalchemy` joins
the forbidden set in the 0.5 import test. If SQLAlchemy + Alembic is accepted:
alembic.ini, the migrations env reading DATABASE_URL, one empty initial migration.
Tests first: test_migrations_upgrade_head_on_empty_db (slow).
Acceptance: `uv run alembic upgrade head` (or the ADR's equivalent) succeeds against
the compose database.
Note: Memory/Link/ChangeEvent tables are Phase 1; this task proves the pipeline only.

### 0.5 Clock, ids and errors in core
Files: src/ripple/core/clock.py (Clock protocol, SystemClock), src/ripple/core/ids.py,
src/ripple/core/errors.py (RippleError hierarchy), tests/fakes/clock.py (FakeClock with
advance()), tests/builders/__init__.py (empty builders module; builders land with models
in Phase 1).
Tests first: test_fake_clock_advance_moves_now, test_core_never_imports_forbidden_modules
(a plain test over the module graph; forbidden set = ripple.llm, ripple.agents,
ripple.api, ripple.domains, ripple.linking, langgraph, fastapi, any provider SDK).
Acceptance: fast tests pass; pyright strict on src/ripple/core.
Decision needed: none. Ids are stdlib uuid4; ordering comes from recorded_at, so no
ULID/UUIDv7 dependency.

### 0.6 LLM router skeleton and FakeLLM
Files: src/ripple/llm/router.py (Router with `complete(task, schema, messages)` that
validates into a Pydantic schema, retries invalid output up to N times, raises
LLMOutputInvalid after; provider adapters raise NotImplementedError with
TODO(roadmap: Phase 1 "LLM linker")), src/ripple/llm/config.py (model-per-task table),
src/ripple/llm/schemas/__init__.py, tests/fakes/llm.py (FakeLLM with scripted
responses and a call log), tests/llm/test_router.py.
Tests first: test_router_validates_output_into_schema,
test_router_rejects_invalid_output_after_n_retries, test_fake_llm_records_calls.
The named invariant test for I4 lands in Phase 1 with the resolver commit, where there
is something to partially apply; naming it now would be a placeholder.
Acceptance: fast tests pass; no network import at module load.
Decision needed: none beyond ADR-0010. Provider SDKs are **not** added in Phase 0.

### 0.7 ADRs for pending dependencies (before 0.3 and 0.4)
Write, via /adr, with the author approving each:
- 0016 ORM and migrations: SQLAlchemy 2 + Alembic (sync vs async engine) vs
  psycopg/asyncpg with plain SQL migrations vs SQLModel. Includes the async decision,
  which LangGraph will force.
- 0017 Job queue: Redis + library (arq / rq / dramatiq) vs Postgres-backed
  (procrastinate, SKIP LOCKED) which removes a service, in the spirit of ADR-0004.
- 0018 Observability: Langfuse + OpenTelemetry vs OpenTelemetry-only vs structured logs
  only (roadmap task).
Embeddings (BGE-M3) are deferred to Phase 3; nothing before then uses them.
Acceptance: three ADRs Accepted; CLAUDE.md "Pending ADRs" line updated.
Also needs the author's approval of ADR-0013, 0014, 0015 (Proposed today). CLAUDE.md
I1, I2 and I7 already carry the Proposed wording; if the author rejects 0013 or 0015,
revert those three lines to their 2026-10-19 originals.

### 0.8 Phase close
Run /session-end; tick roadmap boxes only where acceptance passed; /explain for
src/ripple/llm and src/ripple/core; hand-over with suggested commit message.

## Decisions that need new ADRs
0013–0015 (approval), 0016 ORM + migrations, 0017 job queue, 0018 observability.
Deferred: embeddings (Phase 3), LangGraph checkpointer (Phase 2), resume PDF parser
(Phase 2). CI provider (GitHub Actions) is taken from the roadmap, not an ADR.

## Risks and open questions
1. **OneDrive folder.** .venv, .pytest_cache and uv's cache inside a synced folder cause
   lock errors and slow syncs. Recommendation: move the repo out of OneDrive
   (e.g. C:\dev\ripple), or at minimum exclude .venv via OneDrive's folder settings.
   Author's call.
2. **No Docker locally.** Tasks 0.3 and 0.4 can be written and verified in CI, but the
   exit criterion "services start" needs Docker Desktop on the author's machine.
3. **No git repository / remote yet.** Everything so far is uncommitted; task 0.2 is
   blocked until a remote exists.
4. **Python 3.13 on PATH.** uv will download 3.12 if the project pins it; decide whether
   to pin 3.12 or allow 3.13 (`>=3.12` allows both; CI tests 3.12).
5. **Open questions carried from the kickoff interview (not blocking Phase 0):**
   identity and auth model for the pilot (Phase 2); email digest scheduling (Phase 3);
   sensitivity assignment and ask thresholds for FR-7 (Phase 1 resolver); the metrics
   named in docs/04 "Open" (Phase 3 ADR); the collaborator's assumptions on link
   direction notation and I7 cascade per class in docs/03 (author to confirm).

## Suggested session order
0.1 → 0.5 → 0.6 → 0.7 (offline, unblocked now) · 0.3 → 0.4 → 0.2 (after the ADRs,
Docker and the remote exist) · 0.8.

## Architecture-guardian review (2026-10-19)
First draft verdict: NEEDS ADR, 18 findings. Fixed in this version: forget semantics
aligned with ADR-0007 (two classes, hard-delete cascade), supersedes link dropped,
per-wave transactions, ChangeEvent coverage, link-type mapping location, Linker
protocol in core, Redis and ORM moved behind ADRs, embeddings deferred, placeholder
invariant test renamed, FR-16 added for weak-link re-check, roadmap Phase 1 updated,
forbidden-import set widened.
Second pass: NEEDS ADR, 9 findings. Fixed: the engine traverses from an explicit seed
set with no status filter ("history" = parent superseded, used only by the inspector
and retrieval); the ChangeEvent is created in the trigger's write transaction and has
completed_at; Decision has a wave number; outgoing depends_on links are copied and
re-pointed on update; Memory.kind is adapter-declared; amended ADRs marked in the
index; ask marks its subtree SUSPECT (author may reverse); strength vs confidence
defined; ORM home left to ADR-0016; ADR-0014 renamed to match its decision.
