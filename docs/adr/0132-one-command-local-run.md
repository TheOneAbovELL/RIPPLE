# ADR-0132: One-command local run of the whole product
Status: Accepted under the autonomous mandate · Date: 2026-10-31 · workstream: WS-20

## Context
Running the product locally took five manual steps (start Postgres, migrate, create a
user, start uvicorn with the right event loop, build and serve the dashboard on a second
origin with CORS). The author has no Docker (ADR-0115), and the thesis demo and every
reviewer need "clone, one command, open the browser".

## Decision
`uv run python -m tools.local_run` does, in order:
1. Starts (or attaches to) embedded Postgres in `~/.ripple/pgdata` through
   `tools.embedded_pg.start` (ADR-0115); `--data` moves it, `--fresh` uses a temporary
   directory deleted at exit.
2. Runs `alembic upgrade head` as a subprocess with that DATABASE_URL.
3. Reuses `apps/web/out` when it is newer than every file under `apps/web/src` and
   `apps/web/openapi.json`; otherwise runs `npm ci` (only when `node_modules` is
   missing) and `npm run build`. `--rebuild-web` forces a build, `--no-web` serves the
   API only.
4. Builds the API with the production wiring (`ripple.api.wiring.build_services`,
   `create_app`, the in-process rate limiter, the readiness probe) and mounts it at
   `/api` next to the export at `/`, on one origin, like Caddy: `/api/*` is stripped of
   its prefix, the static side answers `{path}`, `{path}/index.html`, then
   `/index.html`, and every response carries the Caddyfile's security headers and CSP,
   so a CSP violation shows up locally first.
5. Creates a user through `ripple.api.admin.create_user` and prints the token once,
   with the URL, which features need `ANTHROPIC_API_KEY` and which need
   `TELEGRAM_BOT_TOKEN`.
6. Serves with uvicorn on 127.0.0.1 (`--port`, default 8765) under the selector event
   loop (ADR-0115 point 3) until Ctrl+C.
Without `ANTHROPIC_API_KEY` the run switches to the offline stand-ins of ADR-0133 and
says so in its banner. The Telegram webhook is not mounted locally; the banner points to
`ripple.worker.telegram_poll` instead.

## Alternatives considered
- `next dev` plus uvicorn with CORS: two origins and two processes, and it does not
  exercise the static export or the CSP that production serves.
- Docker compose: the production path, but unavailable on the author's machine.
- A Caddy binary in the repository: a native binary to vendor for three platforms.

## Consequences
- Each run creates a new user (tokens are printed once, ADR-0040); old users stay in
  the persistent database until deleted from the dashboard.
- The local server is single-process: rate limits and leases are per process.
- Static serving is Starlette's `StaticFiles`; behaviour differences from Caddy beyond
  the try-files order and headers are not covered.

## Revisit if
Docker becomes available on the author's machine, or the API gains a second process
(the worker) that local runs must start too.
