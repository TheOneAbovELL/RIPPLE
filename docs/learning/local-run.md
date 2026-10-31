# Running the whole product locally (tools/local_run.py, ripple.worker.run_once)
Written 2026-10-31 for workstream WS-20 (docs/plans/final-delivery.md).

## 1. What it does
`uv run python -m tools.local_run` starts everything a student or a reviewer needs on
one machine, with no Docker and no Redis: embedded Postgres with pgvector, migrations,
the dashboard export, the API, and a fresh user whose token it prints. The dashboard is
at `http://127.0.0.1:8765/`, the API at `/api` on the same origin, as behind Caddy.
`--seed-demo` adds a demo student so the first page already shows a ripple.
`uv run python -m ripple.worker.run_once <job>` runs one of the worker's scheduled jobs
once against the same database and prints what a digest or alert would have said.

## 2. Why it exists
The author's machine has no Docker (ADR-0115), and every reviewer of the thesis needs
"one command, open the browser". Before this, a local run took five manual steps and two
origins with CORS, which did not exercise the static export or the CSP production
serves. ADR-0132 (local run), ADR-0133 (demo seed), ADR-0134 (one worker job).

## 3. How it works
- **Postgres.** `tools.embedded_pg.start` attaches to (or starts) a server in
  `~/.ripple/pgdata`; `--fresh` uses a temporary directory pgserver deletes at exit.
- **Migrations.** `alembic upgrade head` in a subprocess with that DATABASE_URL.
- **Dashboard.** `apps/web/out` is reused when `out/index.html` is newer than every file
  under `apps/web/src` plus `openapi.json`, `package.json`, `package-lock.json` and
  `next.config.ts`; otherwise `npm ci` (only without `node_modules`) and
  `npm run build`. `NEXT_PUBLIC_RIPPLE_API_BASE` is removed from the build's
  environment so the export calls `/api` on its own origin.
- **One origin.** `build_site` is a Starlette app: `Mount("/api", api)` strips the
  prefix like Caddy's `handle_path`; `ExportFiles` answers `{path}`, then
  `{path}/index.html`, then `/index.html` (Caddy's `try_files`), and refuses paths that
  climb out of the export. `SecurityHeaders` adds the Caddyfile's headers and CSP (not
  HSTS on plain HTTP). The API's own lifespan is entered inside the site's, because
  Starlette does not start a mounted app's lifespan.
- **API.** The production wiring unchanged: `Settings.from_env`, `build_services`,
  `create_app` with the in-process rate limiter and the Postgres readiness probe. The
  Telegram webhook is not mounted (`webhook_secret=None`); the bot runs by long-poll.
- **One event loop.** The user creation, the seed and uvicorn all run inside one
  `asyncio.run`: the engine's pooled connections belong to the loop that opened them,
  and `loop="none"` makes uvicorn use the selector loop the run set (ADR-0115 point 3).
- **Demo seed.** `seed_demo(store, clock, user_id)` uses production's components with
  the three model seams replaced: the resolver falls back to `AskTheStudent` (asks,
  never guesses), the prose linker is `RuleLinker`, and the change detector refuses
  anything but permanent structured facts. It
  writes seven profile facts through `Intake.ingest` (`profile_statement`, the same
  builder the bot uses), three openings through `OpeningRecorderAdapter.record` from
  realistic JD texts with exact spans, then two changes:
  1. CGPA 8.1 → 8.6: Beta Analytics (cutoff 8.5) goes from not eligible to eligible,
     Acme (7.0) is recomputed, the search criteria update;
  2. "My college reports CGPA on a 4-point scale": the eligibility rule cannot compare a
     4-point CGPA with ten-point cutoffs (ADR-0034), so Acme's and Beta's eligibility are
     asked and wait on the Questions page; Gamma, with no cutoff, is kept.
- **run_once.** Builds a `JobContext` like `job_context_from_env` with an
  `InMemoryLease` and no scout enqueue; reuses the arq wrappers in `settings.py` for
  the summary. Without `TELEGRAM_BOT_TOKEN` it uses `PrintingTransport` and an
  in-memory delivery log, so a preview never marks a digest as sent.

## 4. Trade-offs
- Production wiring over an "offline mode" for the server: a keyless local run is the
  same product as production, and fails the same way (503) where the model is needed.
  Only the seed uses a deterministic fallback, so the demo is identical with or without
  a key and free.
- Each run creates a new user, because a token is printed only once (ADR-0040).
- Starlette's static serving is close to Caddy's for the try-files order and headers;
  compression, TLS and request-size limits are not reproduced.
- The seed ends with an inconsistent profile on purpose (8.6 on a 4-point scale): it is
  the case the system is designed to ask about rather than guess.

## 5. Failure modes and tests
| Failure | Test |
|---|---|
| The seed bypasses the engine or writes a state change without a ChangeEvent | tests/tools/test_local_run.py `test_seed_demo_every_state_change_has_a_change_event` |
| The CGPA ripple does not reach the eligibility it crosses | `test_seed_demo_cgpa_change_makes_beta_eligible_through_the_ripple` |
| The rules' decline turns into a guess instead of a question | `test_seed_demo_scale_correction_parks_questions_instead_of_guessing` |
| A demo span does not quote the JD's exact words (FR-2) | `test_demo_openings_quote_the_exact_words_they_were_read_from` |
| Deep links 404, or `/api` is not stripped | `test_site_serves_files_then_folder_index_then_the_root_index`, `test_site_strips_the_api_prefix_like_caddy` |
| Missing CSP or headers locally | `test_site_sends_caddys_security_headers_on_static_and_api_responses` |
| Path traversal out of the export | `test_export_files_never_serves_outside_the_export` |
| A stale export served after a source change, or a dev API base baked in | `test_export_is_current_only_when_index_is_newer_than_every_source`, `test_build_dashboard_installs_then_builds_when_forced` |
| The banner hides what needs a key | `test_banner_lists_what_needs_the_model_key_when_it_is_missing` |
| A dry run sends a message or records a delivery | tests/worker/test_run_once.py `test_run_once_daily_digest_without_token_prints_the_message_instead_of_sending`, `test_local_job_without_token_is_a_dry_run_that_records_nothing_in_postgres` |
| A failed user is hidden | `test_run_once_exits_1_and_names_the_users_whose_work_failed` |

Not covered offline: the embedded Postgres start, npm and uvicorn themselves; they are
exercised by running the command (WS-20 handover shows a real run).

## 6. Interview questions
1. *Why not run `next dev` and uvicorn side by side?* Two origins need CORS, and neither
   the static export nor the production CSP would be exercised; a bug in either would
   first appear on the server.
2. *Why does the seed not just insert rows?* Rows inserted directly would have no
   ChangeEvents (I2) and would show beliefs the engine never derived; the demo would
   prove nothing about the engine.
3. *Is the AskTheStudent fallback cheating?* It is used only by the seed, and it can
   only ask; it never updates or retires. Production's LLM fallback may also ask. The
   decisions before the fallback are the real jobs rules.
4. *Why one `asyncio.run` for everything?* SQLAlchemy's async pool keeps connections
   bound to the loop that opened them; a second loop would inherit dead connections.
5. *Why does run_once use an in-memory delivery log without a bot token?* The Postgres
   log is what stops a second digest on the same day; recording a printed preview there
   would suppress the real send later.

## 7. Exercise
Run `uv run python -m tools.local_run --seed-demo --fresh`, sign in, open Questions and
answer one eligibility question with "Still holds". Then open Home: the ripple your
answer started is the newest one, and the restored belief is no longer flagged on
Recommendations. Run
`uv run python -m ripple.worker.run_once daily_digest` with the printed DATABASE_URL
and read the digest it would send (link Telegram first, or it says no chat is linked).
