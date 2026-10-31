# Production plan — build the whole product once, deploy-ready
Written 2026-10-24 by the coordinator under the autonomous mandate. Supersedes the
ordering in docs/plans/round-2.md (its workstream briefs still apply). Status: **in
execution**. Tracker: docs/plans/parallel-execution.md.

## Definition of production-ready (what "done once" means)
A pilot student can, with no developer present: get a token from the admin, link
Telegram, upload a resume and confirm facts, receive a daily digest and 48-hour alerts,
talk to the agent in Telegram, paste or forward JDs, see and edit beliefs in the
dashboard, answer questions, export and delete everything. Operators can deploy to one
VPS from a tagged image with TLS, run migrations, back up and restore the database,
read traces and structured logs, and roll back. Every invariant has a named test,
every number in docs comes from results/, and nothing is a stub except the two
[human] bodies (WaveEngine, metric functions), which have complete tests waiting.

## Decisions fixed now, so nothing is rebuilt later
| Area | Decision | ADR |
|---|---|---|
| Deployment | One VPS, Docker Compose, images built in CI and published to GHCR by tag, Caddy for TLS and reverse proxy, migrations as a one-shot job before the app starts, nightly pg_dump to object storage, restore runbook | ADR-0029 |
| Telegram channel | Webhook into the API with Telegram's secret token header in production; long polling only for local development; one transport for digests and replies | ADR-0075 (WS-10) |
| Observability | Langfuse tracer implements the existing Tracer protocol now; JSON structured logs; request/trace ids end to end; /healthz and /readyz | ADR-0028, WS-13 |
| Idempotency and leases | Postgres DeliveryLog; per-ChangeEvent lease in resume; atomic candidate confirm | WS-13 |
| Rate limiting and abuse | Redis-backed per-user and per-chat limits at the API and bot boundary; upload size limits already in Services | WS-13 |
| Scout | Allowed-sources YAML registry with terms notes, robots and rate limits (ADR-0008); httpx fetch with ETag cache; dedupe by canonical URL and title+company | ADR-0070.. (WS-9) |
| MCP | Official `mcp` SDK, stdio and streamable HTTP, bearer auth mapped to a user, five tools | ADR-0080.. (WS-11) |
| Dashboard | Next.js (TypeScript strict), generated OpenAPI client, React Flow map, token login, deployed as a static export served by Caddy | ADR-0085.. (WS-12) |
| Link finder data | Silver labels from structure + LLM labels for hidden links, provenance recorded, split by persona/template, leakage test | ADR-0090.. (WS-14) |

## Waves (at most five sessions at once)
### Wave A — product completion and hardening (now)
WS-9 Scout · WS-10 Telegram inbound · WS-11 MCP server · WS-12 Dashboard ·
WS-13 Hardening (DeliveryLog, leases, atomic confirm, uploads table, CGPA scale,
rate limits, health endpoints, JSON logging, trace ids). Coordinator: WS-0 deployment
layer (prod compose + Caddy, backup/restore scripts, CI publish, Langfuse tracer, deploy
and operations runbook, consent and onboarding documents for the pilot).
Checkpoint C3: full suite, contract requests, wiring of Scout and bot into worker/API.

### Wave B — evaluation and research completion (after C3)
WS-14 Link-finder training data and evaluation harness (training loop stays [human]) ·
WS-15 RippleBench v1: news track, STALE runner, finance transfer harness (H4) ·
WS-16 Pilot operations: consent text, onboarding checklist, weekly report generator
from results/ and the store, incident runbook · WS-17 Paper and thesis plumbing:
docs/paper skeleton, a script that renders every number from results/ (I8), figure
generation from bench snapshots. Checkpoint C4: full suite, hand-over A..G.

### Author-owned, in parallel with both waves
First commit and GitHub remote (CI is the only live Postgres/Redis environment until
Docker exists locally) · Docker Desktop · ANTHROPIC_API_KEY in .env · WaveEngine ·
metric functions · GHCR token and a VPS when deploying for real · pilot consent sign-off
with the department.

## Ownership and ADR ranges for wave A
| WS | Owns | ADRs |
|---|---|---|
| WS-9 | src/ripple/agents/scout.py, src/ripple/domains/jobs/sources/**, src/ripple/worker/jobs.py `scout_run` body only, tests/agents/test_scout*.py, tests/domains/jobs_sources/**, docs/learning/scout.md, ws-9.md | 0070–0074 |
| WS-10 | src/ripple/notify/inbound/**, src/ripple/api/routers/telegram.py, src/ripple/worker/telegram_poll.py, tests/notify/test_inbound*.py, tests/api/test_telegram*.py, docs/learning/telegram-bot.md, ws-10.md | 0075–0079 |
| WS-11 | src/ripple/mcp_server/**, tests/mcp_server/**, docs/learning/mcp.md, ws-11.md | 0080–0084 |
| WS-12 | apps/web/**, docs/learning/dashboard.md, ws-12.md | 0085–0089 |
| WS-13 | src/ripple/notify/delivery_log.py (+ Postgres impl), src/ripple/storage/delivery_tables.py, src/ripple/storage/uploads*.py, infra/migrations/versions/0005_delivery_log.py, 0006_resume_uploads.py, src/ripple/core/ripple.py `resume` lease only (coordinate: send the diff in the handover, coordinator applies), src/ripple/storage/candidates.py conditional update, src/ripple/domains/jobs/rules.py CGPA scale, src/ripple/api/{ratelimit,health,logging}.py and their wiring lines in app.py, tests for each, docs/learning/hardening.md, ws-13.md | 0095–0099 |
| WS-0 | infra/** (prod compose, Caddyfile, backup/restore scripts), .github/** (publish job), src/ripple/llm/tracing.py (Langfuse), docs/ops/**, docs/pilot/**, coordinator-owned files | 0028–0029 |
Core (src/ripple/core/**) stays coordinator-owned; WS-13 sends core diffs through its
handover. Dependencies are added by the coordinator only: `mcp` and `langfuse` are in.
Node 22 is installed for WS-12; it runs `npm` inside apps/web only.

## Acceptance for the plan as a whole
- `uv run pytest` green; slow suite green in CI; `docker compose --profile app` boots
  api, worker, bot webhook, dashboard behind Caddy on a fresh VPS following docs/ops.
- A scripted end-to-end run (offline fakes) covers: link → resume → confirm → opening →
  ripple → digest → question → answer → export → delete.
- Smoke 11/11 and v0 ripple numbers in results/ once the engine lands.
- Learning docs for every module; ADRs for every decision above; DEVLOG per checkpoint.
