# Deployment, CI and observability (WS-8)
Written 2026-10-19.

## 1. What it does
One container image runs the API or the worker; compose runs Postgres, Redis and, with
the `app` profile, both services; CI lints, type-checks, tests, runs the slow suite
against real Postgres and Redis, runs the bench smoke suite informationally, and builds
the image. Tracing spans wrap every LLM attempt.

## 2. Why it exists
ADR-0004 (one Postgres), ADR-0017 (Redis for arq), ADR-0018 (observability), ADR-0022
(uvicorn), NFR-5/NFR-6. The pilot runs on one VPS with compose (docs/02 Deployment).

## 3. How it works
- infra/docker-compose.prod.yml (ADR-0029): postgres, redis, a one-shot `migrate` job,
  api, worker, Caddy (TLS, reverse proxy, security headers, static dashboard from
  infra/web-dist) and a `backup` sidecar running infra/scripts/backup.sh nightly;
  infra/scripts/restore.sh restores a dump into a fresh database and swaps names.
  docs/ops/deploy.md and docs/ops/runbook.md are the operator's pages.
- CI publishes the image to GHCR on main and tags (docker/metadata-action tags: sha,
  tag, latest) and validates both compose files with `docker compose config`.
- src/ripple/llm/tracing.py now has LangfuseTracer (ADR-0028); `tracer_from_env`
  returns it when LANGFUSE_* are set and LoggingTracer otherwise; both routers use
  it and the worker flushes on shutdown.
- infra/Dockerfile: multi-stage; dependencies are installed from uv.lock in a cached
  layer, the project in a second `uv sync`, runs as a non-root user; entrypoint.sh
  starts `api`, `worker`, `mcp` or the one-shot `migrate`. Only `migrate` runs
  `alembic upgrade head` in production; the development compose sets
  RIPPLE_MIGRATE_ON_START=1 on the api instead.
- infra/docker-compose.yml: postgres and redis always; api and worker under
  `--profile app` so `up -d` for development stays infra-only.
- .github/workflows/ci.yml: `checks` (ruff, pyright, fast tests, bench smoke with
  results uploaded as an artifact), `services` (migrations, slow tests with
  TEST_DATABASE_URL and REDIS_URL), `image` (docker build with layer cache).
- src/ripple/llm/tracing.py: `Tracer` protocol with `NoopTracer` and `LoggingTracer`;
  the Router opens `llm.attempt` per call and `llm.complete` per success, with model,
  tokens and latency but never content. A Langfuse tracer slots in here later.

## 4. Trade-offs
- One image for two commands keeps builds simple; the cost is that the worker image
  carries FastAPI, which is small.
- Migrations run at container start; for a single VPS that is right, for multiple
  replicas it should become a one-shot job (`migrate` command exists for that).
- The bench step never fails CI while the engine is a stub; it is labelled as
  informational so nobody mistakes a green build for a passing benchmark.

## 5. Failure modes and tests
Tracing is tested through the Router (tests/llm/test_router_transport.py); compose
and the image are verified by CI only until Docker exists locally.

## 6. Interview questions
1. Why migrate on start? One replica, one database, no race; documented escape hatch.
2. Why upload bench results from CI? Numbers must trace to a results folder (I8).
3. What does a span contain? Attributes, never prompt or user content.
4. Why profiles in compose? Developers want the infra without rebuilding the app.
5. How would you add Langfuse? Implement `Tracer` once; no caller changes.

## 7. Exercise
Run `docker compose -f infra/docker-compose.yml --profile app up --build` once Docker
is installed and read the api container's first log lines: the migration output
should appear before uvicorn's banner.
