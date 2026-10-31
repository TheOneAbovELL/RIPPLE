# ADR-0098: API boundary hardening: token-bucket write limits, health probes, request ids with JSON logs, security headers and a body cap
Status: Accepted under the autonomous mandate · Date: 2026-10-26

## Context
The production plan (WS-13) lists, for the API: Redis-backed per-user limits,
`/healthz` and `/readyz`, JSON structured logs with request ids end to end, and the
boundary limits that ADR-0029 puts partly in Caddy. ADR-0018 chose stdlib structured
logging until Langfuse; ADR-0017 put Redis behind arq; ADR-0041 says `create_app`
is the only way to build the app and reads no settings. Write endpoints can cost a
model call and a ripple each, so a stuck retry loop or a leaked token must not be
able to spend the pilot's LLM budget. Tests must stay offline (FakeClock, no Redis).

## Decision
1. **Rate limiting** (`ripple.api.ratelimit`). A token bucket per key: `Bucket(capacity,
   refill_per_second)`. Pilot defaults in `RateLimits`: per user 30 burst refilling at
   0.5 per second (30 per minute), per client address 60 burst at 1.0 per second. Every
   POST, PUT, PATCH and DELETE on the product routers takes one token from the address
   bucket and, when a bearer token is present, one from the user bucket; reads are not
   limited. A refusal is 429 `"rate limit exceeded"` with `Retry-After` in whole
   seconds (at least 1). The user key is `user:` plus the first 16 hex characters of
   the token's SHA-256, so no store lookup happens before the limit and an invalid
   token still burns a bucket. The address is the socket peer, or the first
   `X-Forwarded-For` entry only when `RIPPLE_TRUST_PROXY` is true (behind Caddy).
   - `RateLimiter.take(key, bucket, now)` is a protocol. `InMemoryRateLimiter` serves
     tests and one process. `RedisRateLimiter` runs one Lua script per call (refill,
     take, store `{tokens, updated_ms}`, expire an idle bucket once it would be full),
     so several uvicorn workers share buckets atomically. It reaches Redis through the
     arq client (ADR-0017: no second Redis library). Time comes from the injected Clock.
   - `RateLimitGuard` lives on `app.state.rate_limit`; `enforce_rate_limit` is added
     as a router dependency to every product router in `create_app`. `None` (the
     default) means no limiting.
2. **Health** (`ripple.api.health`). `GET /healthz` answers `{"status": "ok"}` with no
   checks. `GET /readyz` runs every configured probe concurrently, each under a
   2-second timeout, and answers 200 `ready` or 503 `not ready` with a `checks` map
   whose values are `ok`, `timeout` or `error: <exception type>` (never the message).
   Probes are injected callables: `postgres_probe(engine)` (`SELECT 1`) always, and
   `redis_probe(...)` (`PING`) when `REDIS_URL` is set. Both routes are
   unauthenticated, never rate limited, and excluded from the OpenAPI document.
3. **Request ids and logs** (`ripple.api.logging`). `RequestIdMiddleware` takes the
   client's `X-Request-ID` if it matches `^[A-Za-z0-9._:-]{1,128}$`, mints a uuid4 hex
   otherwise, binds it to a context variable for the request, echoes it on every
   response and logs one `request` access line (method, path, status).
   `TraceIdFilter` stamps that id as `trace_id` on every record that has none of its
   own; `JsonFormatter` writes one JSON object per line (ts, level, logger, message,
   trace_id, the caller's extras, exception). `configure_logging` routes the root and
   uvicorn loggers through one stderr handler; `RIPPLE_LOG_LEVEL` and
   `RIPPLE_LOG_JSON` (default true) select level and format. The resume confirm passes
   `current_trace_id()` to Intake, so the ChangeEvent carries the request's id.
4. **Security headers and body cap** (`ripple.api.middleware`), both pure ASGI.
   `SecurityHeadersMiddleware` adds `X-Content-Type-Options: nosniff`,
   `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Cache-Control: no-store`,
   a `Permissions-Policy` denying camera, microphone and geolocation, and
   `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'` except under
   `/docs` and `/redoc`; it never overrides a header the app already set. No HSTS:
   Caddy sets it (ADR-0029). `BodySizeLimitMiddleware` refuses a declared
   `Content-Length` over the cap with 413 before reading, and counts a streamed body
   as it arrives, answering 413 once it crosses the cap. Default cap 8 MiB, above the
   5 MiB resume limit plus multipart framing, matching Caddy's `max_size 8MB`.
5. **Wiring.** `create_app(services, *, rate_limit=None, readiness=None,
   max_body_bytes=DEFAULT_MAX_BODY_BYTES)`; middleware order, outermost first:
   request id, body cap, security headers. `ripple.api.wiring.app_from_env` reads
   `REDIS_URL`, `RIPPLE_LOG_LEVEL`, `RIPPLE_LOG_JSON`, `RIPPLE_TRUST_PROXY`, calls
   `configure_logging`, and passes a guard (Redis limiter when `REDIS_URL` is set,
   in-memory otherwise) and the probes.

## Alternatives considered
- slowapi or fastapi-limiter — a new dependency (CLAUDE.md asks an ADR and a reason
  for each); slowapi's in-process default is wrong for several workers, and both pull
  their own Redis client next to arq's. Thirty lines of Lua do the one thing needed.
  Lost.
- Rate limiting only in Caddy — Caddy's core has no rate limiter (it needs a third-party
  module and a custom build), and it cannot key on the bearer token's user. Lost.
- Fixed-window counters (`INCR` with `EXPIRE`) — simpler, but a client can send two
  windows' worth at a boundary; a token bucket gives a burst and a steady rate. Lost.
- Keying the user bucket by resolved user id — needs a database lookup before the
  limiter, so a flood of invalid tokens would reach Postgres. Lost; one token is one
  user in the pilot (ADR-0040).
- Limiting reads as well — the dashboard loads several reads per page and they cost no
  model call. Lost for now.
- structlog or python-json-logger — a dependency for what one `Formatter` subclass
  does; ADR-0018 keeps stdlib logging until Langfuse. Lost.
- Starlette's `BaseHTTPMiddleware` for the headers — runs after the app's response
  object exists and has known problems with streaming and context variables; pure ASGI
  wraps error responses and keeps the trace id bound. Lost.
- `/readyz` checking the LLM provider — a provider outage should degrade answers
  (ADR-0010 fallbacks), not take the API out of the load balancer. Lost.

## Consequences
- Behind Caddy, `RIPPLE_TRUST_PROXY` must be set to true, or every client shares
  Caddy's address bucket (60 writes per minute for the whole pilot). Neither
  `.env.example` nor `infra/docker-compose.prod.yml` sets it yet; the prod compose
  sets `LOG_FORMAT: json`, which the code does not read (the JSON default applies
  anyway). Both are handover items for the coordinator.
- `RedisRateLimiter`, `redis_probe`, `postgres_probe` and the env-to-guard wiring have
  no test that talks to a real Redis or Postgres; the Lua script is unverified until
  one runs.
- `rate_limit_guard` and `readiness_probes` each call `redis_factory`, so a process
  opens two arq pools, not the one shared pool the comment on `redis_factory` describes.
- The body-cap 413 is produced outside the security-headers middleware, so it carries
  `X-Request-ID` but none of the security headers (checked by hand on 2026-10-26).
  Its body is fixed JSON with no user content.
- Only the resume confirm passes the request id to Intake. `POST /statements` and the
  answer and forget routes write ChangeEvents with no `trace_id`; their log lines
  still carry it through the filter.
- The Telegram bot's limiter (`ripple.notify.inbound.ratelimit`, `allow(key, limit,
  window)`, ADR-0076) is a different protocol; no Redis implementation of it was
  built here, so the bot's link-code limit stays per process.
- The rate-limit dependency runs before authentication, so a 429 can be returned to a
  request that would have been 401.

## Revisit if
The pilot runs more than one API host (then the address bucket needs the real client
address from the proxy chain), a student hits 429 by hand, or Langfuse lands and the
request id should become the trace's id.
