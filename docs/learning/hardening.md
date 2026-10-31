# Production hardening — delivery log, atomic confirm, resume text, API boundary
Written 2026-10-26 for workstream WS-13 (docs/plans/production-plan.md), ADR-0095 to
ADR-0098. The code was written by the WS-13 session; this note was written afterwards
from the code and its tests.

## 1. What it does
Closes four gaps between "works in a test" and "runs for a pilot":
- The worker remembers which digests and alerts it sent in Postgres, so a restart on
  digest day does not resend (`PostgresDeliveryLog`).
- Two clicks on "confirm" for the same resume candidate produce one decision: the
  second request gets 409 instead of overwriting the first (conditional replace).
- The text the resume parser read is stored, so a fact's `resume:<upload>#<start>-<end>`
  reference resolves and the inspector shows the exact line the belief came from.
- The API refuses runaway writes (429), answers `/healthz` and `/readyz` for the
  platform, tags every log line and response with one request id, writes JSON logs,
  sets security headers and refuses oversized bodies (413).

## 2. Why it exists
- ADR-0056 left the delivery log in memory and said so in its consequences.
- WS-3's handover listed the double-confirm race as open problem m6; ADR-0043 checked
  "pending" with a read, which two requests can both pass.
- FR-12 asks the inspector to show where a belief came from; I5 asks that no profile
  fact be invented. A span into text nobody kept proves nothing.
- The production plan (Observability, Idempotency, Rate limiting rows) and ADR-0029
  (health endpoints, request size limits) assign the rest to WS-13. ADR-0018 keeps
  logging on the standard library; ADR-0017 keeps Redis behind arq.

## 3. How it works
- **Delivery log** (`ripple.notify.delivery_log`, `ripple.storage.delivery_tables`,
  migration 0005; ADR-0095). Table `delivery_log(user_id, kind, key, sent_at)` with
  primary key `(user_id, kind, key)`. A digest is `kind="digest"`, key the ISO day,
  `sent_at` that day at midnight UTC; `record_digest` inserts with `ON CONFLICT DO
  NOTHING`, `last_digest_day` reads `max(sent_at)`. An alert is `kind=<AlertKind>`,
  key the opening memory id; `record_alert` upserts `sent_at` forward,
  `last_alert_at` reads the row. `InMemoryDeliveryLog` keeps the latest day so both
  agree on one contract test.
- **Atomic confirm** (`ripple.storage.candidates`, `ripple.api.routers.resume`;
  ADR-0096). `replace_candidate(candidate, expected_status=PENDING)` runs `UPDATE ...
  WHERE id = :id AND status = 'pending'`; `rowcount == 0` means someone else decided
  first, and the store raises `CandidateAlreadyDecidedError(candidate_id, actual)`.
  The router's `_claim` turns that into 409 `"candidate already <status>"` for both
  confirm and reject. Confirm runs Intake first; Intake writes nothing for an
  identical fact, so two racing confirms leave one memory.
- **Resume text** (`ripple.storage.uploads`, `uploads_tables`, migration 0006,
  `ripple.api.uploads`; ADR-0097). `POST /resume` makes a `ResumeUpload` id, parses
  with `source_ref=resume:<id>`, refuses text over 200,000 characters (413), stores
  the upload (filename, SHA-256 of the PDF, text), then the candidates.
  `parse_resume_ref` reads `resume:<id>` and `resume:<id>#<a>-<b>`; `quote(text, a, b)`
  returns `text[a:b]` and its whole line. `GET /memories/{id}` adds `source`
  (`SourceOut`) through `source_for`, which answers `None` for anything that is not
  the same user's upload or whose span falls outside the text. The export lists
  uploads; `DELETE /me` removes them; `users.id` cascades as a second guard.
- **Rate limits** (`ripple.api.ratelimit`; ADR-0098). `Bucket(capacity,
  refill_per_second)`; tokens refill by elapsed time from the injected Clock, capped
  at capacity. Unsafe methods on product routers take one token from `ip:<address>`
  and, with a bearer token, one from `user:<sha256(token)[:16]>`. Refusal: 429 with
  `Retry-After`. `InMemoryRateLimiter` keeps `(tokens, updated)` per key;
  `RedisRateLimiter` does the same in one Lua script over a Redis hash with an expiry,
  through arq's client. `X-Forwarded-For` is read only when `RIPPLE_TRUST_PROXY` is
  true.
- **Health** (`ripple.api.health`). `/healthz` always 200. `/readyz` runs the probes
  (Postgres `SELECT 1`; Redis `PING` when `REDIS_URL` is set) concurrently with a
  2-second timeout each; 200 `ready` or 503 `not ready` with per-probe verdicts that
  name an exception's type, never its message.
- **Request ids and JSON logs** (`ripple.api.logging`). `RequestIdMiddleware`
  accepts a well-formed `X-Request-ID` or mints one, binds it in a `ContextVar`,
  echoes it, and logs one access line. `TraceIdFilter` copies it onto every record
  without a `trace_id`; `JsonFormatter` prints one JSON object per line with the
  record's extras. The confirm handler passes `current_trace_id()` to Intake, so the
  ChangeEvent and the logs share the id.
- **Headers and body cap** (`ripple.api.middleware`). Pure ASGI wrappers. Security
  headers on every response (CSP relaxed only for `/docs` and `/redoc`; HSTS left to
  Caddy). Body cap 8 MiB: a declared `Content-Length` over it is 413 without reading;
  a streamed body raises inside `receive` once it crosses the cap and the middleware
  replaces whatever the app was about to answer with 413.
- **Wiring** (`ripple.api.app`, `ripple.api.wiring`). `create_app` takes the guard,
  readiness and cap as keyword arguments (all off by default for tests);
  `app_from_env` reads `REDIS_URL`, `RIPPLE_LOG_LEVEL`, `RIPPLE_LOG_JSON`,
  `RIPPLE_TRUST_PROXY`, configures logging and builds both.

## 4. Trade-offs
- The delivery log's primary key stops duplicate rows, not duplicate sends: the
  service sends, then records. Exactly-once would need insert-before-send plus a
  "send failed" path; for one worker process at-least-once with restart safety is
  enough.
- The atomic confirm runs Intake before claiming the row. Claim-first would need a
  fourth status and crash recovery; the price is that a confirm losing to a reject
  has already written its memory.
- The text, not the PDF, is stored: spans stay stable across pypdf versions and less
  personal data is kept, but the original file cannot be shown back.
- The user bucket is keyed by a token hash prefix, not the user id: no database read
  before the limiter, at the cost of one bucket per token rather than per person.
- Reads are not limited: the dashboard's page loads are reads and cost no model call.
- A hand-written Lua script instead of a rate-limit library: no new dependency, but
  the script is only checked by reading it until a Redis-backed test exists.
- Pure ASGI middleware is more code than `BaseHTTPMiddleware` but wraps FastAPI's own
  error responses and keeps the context variable bound for the whole request.

## 5. Failure modes and tests
| Failure | Test |
|---|---|
| A worker restart resends today's digest | test_digest_service_rebuilt_over_the_same_log_does_not_resend (contract, in-memory here; Postgres in tests/storage, slow) |
| Recording the same day twice adds a row or moves the day back | test_recording_the_same_day_twice_is_idempotent, test_last_digest_day_is_the_newest_day_recorded |
| Alert cooldown keyed wrongly or naive times returned | test_alert_is_none_until_recorded_then_keyed_by_user_opening_and_kind, test_alert_times_come_back_timezone_aware |
| Migration and table definition drift | test_migration_0005_matches_delivery_tables, test_migration_0006_matches_uploads_tables (slow) |
| Two confirms both write | test_two_concurrent_confirms_yield_one_success_one_409_and_one_memory |
| Confirm and reject both win | test_confirm_racing_a_reject_leaves_the_first_decision_standing |
| A stale read overwrites a decision | test_second_decision_on_a_stale_read_raises_and_changes_nothing |
| A span points at text nobody kept | test_upload_persists_the_parsed_text_under_the_returned_upload_id, test_confirmed_fact_detail_quotes_the_resume_line_its_span_points_at |
| Another user's upload is quoted, or a guess is shown | test_detail_source_is_none_for_non_upload_refs_and_other_users_uploads, test_quote_is_none_outside_the_text |
| Huge text stored half-way | test_upload_whose_text_exceeds_the_cap_is_refused_and_stores_nothing |
| Resume text survives account deletion | test_invariant_I7_delete_me_removes_uploads_and_candidates, test_delete_me_removes_the_uploads |
| Production silently uses the in-memory upload store | test_production_wiring_uses_the_postgres_upload_store |
| A loop of writes spends the budget | test_writes_over_the_user_limit_are_429_with_retry_after_and_reads_are_not |
| A write route escapes the limiter | test_every_product_write_route_is_rate_limited |
| A client picks its own bucket with X-Forwarded-For | test_forwarded_for_picks_the_bucket_only_when_the_proxy_is_trusted |
| Health checks get rate limited or need a token | test_health_endpoints_are_never_rate_limited, test_healthz_answers_without_a_token |
| A hanging database hangs /readyz | test_readyz_times_out_a_hanging_probe_instead_of_hanging_itself |
| /readyz leaks an error message | test_readyz_is_503_naming_the_failing_probe_by_exception_type_only |
| A header injects a forged request id | test_accept_trace_id_mints_a_fresh_id_for_anything_else |
| A log line or event loses the request id | test_log_records_during_a_request_carry_its_id, test_the_request_id_reaches_the_change_event_written_by_a_confirm |
| Error responses miss headers or ids | test_every_response_carries_the_security_headers_including_errors, test_error_responses_carry_the_request_id_too |
| An oversized body reaches a handler | test_a_declared_body_over_the_cap_is_413_before_the_handler_runs, test_a_streamed_body_over_the_cap_is_413_too |

Not covered by any test: `RedisRateLimiter` and its Lua script, `redis_probe`,
`postgres_probe`, and the environment-to-guard wiring in `app_from_env`.

## 6. Interview questions
1. *Why is the conditional update one SQL statement and not "read, check, write"?*
   Two transactions can both read "pending" before either writes. With `WHERE status
   = 'pending'` in the `UPDATE`, Postgres re-checks the condition on the row it locks,
   so the second writer finds zero rows.
2. *Does the delivery log make digests exactly-once?* No. It makes a retried or
   restarted job skip what was recorded. A crash between send and record resends, and
   two workers checking at the same moment can both send; the pilot runs one worker.
3. *Why key the user bucket by a hash of the token and not the user id?* So the
   limiter runs before any database lookup. A flood of invalid tokens is refused
   without reaching Postgres.
4. *Why is `X-Forwarded-For` ignored by default?* Without a trusted proxy in front,
   the header is whatever the client wrote, so a client could choose a fresh bucket
   for every request.
5. *Why store the parsed text instead of the PDF?* The spans index into the text the
   parser saw; re-extracting a stored PDF with another library version could shift
   every offset.
6. *Why does `/readyz` not check the LLM provider?* A provider outage should degrade
   answers through the router's fallbacks, not remove the API from service.

## 7. Exercise
Make the `Retry-After` header carry the exact fractional wait instead of whole
seconds. Predict which test in `tests/api/test_hardening_ratelimit.py` fails first and
why HTTP forces you back to integers, then run
`uv run pytest tests/api/test_hardening_ratelimit.py -q`.
