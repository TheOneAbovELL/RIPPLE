# ADR-0078: The Telegram channel is hosted in the API's lifespan; Services carries the shared parts
Status: Accepted under the autonomous mandate · Date: 2026-10-26 · Amends ADR-0077
(wiring) and ADR-0082 point 3 (one engine) · checkpoint C3

## Context
ADR-0077 delivers Telegram updates to `POST /telegram/webhook` and left the production
wiring to the coordinator. The channel needs a Conversation agent, and the agent needs
a Postgres checkpointer (ADR-0023) that is an async context: it must be opened once and
closed at shutdown. It also needs the Router and a Retriever. Before this decision
`build_services` kept its engine and Router private, so the MCP server opened a second
engine for its retriever (ADR-0082 point 3) and any agent the API hosted would have
built a second Router with a second tracer. The tracer was never flushed by the API.

## Decision
1. `Services` gains `retriever`, `router` and `delivery_log`, all built once in
   `ripple.api.wiring.build_services` over the one engine. They default to None so
   tests that do not need them build `Services` from fakes as before.
2. `app_from_env` turns the channel on when TELEGRAM_BOT_TOKEN is set. It requires
   TELEGRAM_WEBHOOK_SECRET at start-up (a ConfigurationError, not a 503 on Telegram's
   first delivery). The route is mounted at build time (`mount_telegram_route`); the
   channel is attached in the app's lifespan (`attach_telegram_webhook`), where the
   checkpointer, the Conversation agent over the API's own Services, and the bot client
   are opened on an AsyncExitStack and closed in reverse order. Until attached, the
   route answers 503.
3. The lifespan flushes the Router's tracer on shutdown (LangfuseTracer.shutdown), the
   same as the worker's on_shutdown (ADR-0028).
4. `ripple.mcp_server.wiring.production_services` returns `Services.retriever`.

## Alternatives considered
- A separate bot process (like the worker): one more container, one more checkpointer
  connection pool, and the webhook would still need an HTTP server; the API already
  is one and owns the same Services.
- Mount the route inside the lifespan: FastAPI 0.146 mounts routers lazily and the
  route table is not meant to change after start-up; mounting early with a 503 until
  the channel exists is explicit.
- Leave the retriever outside Services: two engines per process and two places that
  decide which search backend production uses.

## Consequences
- One uvicorn process hosts the API and the bot. The update ledger and the bot's rate
  limiter remain in memory (ADR-0077 consequences; Postgres ledger is migration 0008).
- tests/api/test_wiring_c3.py covers settings, the start-up refusal, mounting, the DSN
  conversion and the tracer flush; the lifespan with a real checkpointer is covered only
  once a database exists (slow suite).
