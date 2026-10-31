# Parallel execution tracker
Started 2026-10-19 under the parallel-phase directive. The coordinator session owns
this file; workstreams report through their handover files in
docs/plans/parallel-execution/. Updated at every integration checkpoint.

## Environment limits (checked 2026-10-19)
- The repository has no commits, so git worktrees cannot be created and commits are
  forbidden. All workstreams share one checkout and are isolated by **file ownership**
  only. A session edits nothing outside its owned paths.
- No Docker and no GitHub remote on the author's machine: Postgres, Redis, CI and real
  services are verified only through offline fakes or later in CI.
- `src/ripple/core/engine.py` WaveEngine is the author's learning task. Nobody but the
  author edits it or removes its xfail markers. Everything downstream uses the
  documented interface and `tests/fakes/engine.ScriptedEngine`.

## Shared contracts (coordinator-owned)
| Id | Contract | File | Consumers |
|---|---|---|---|
| C1 | Jobs vocabulary: kinds, attributes, link types, `Recommendation`, `RecommendationSource` | src/ripple/domains/jobs/vocabulary.py | WS-1, WS-2, WS-3, WS-4, WS-6, WS-7 |
| C2 | Retrieval: `Retriever`, `RetrievedMemory`, `Embedder` | src/ripple/core/retrieval_contract.py | WS-4, WS-5 |
| C3 | Core engine interface, Store, Intake, Resolver, Linker protocols | src/ripple/core/* (frozen for this round) | all |
| C4 | Router, prompts loader, FakeLLM | src/ripple/llm/{router,client,config,prompts/__init__}.py, tests/fakes/* | all |
A workstream that needs a change to a contract writes the request in its handover
file; the coordinator applies it and tells dependents.

## Coordinator-owned files (workstreams must not edit)
pyproject.toml, uv.lock, CLAUDE.md, README.md, docs/DEVLOG.md, docs/05-roadmap.md,
docs/adr/README.md, docs/IDEAS.md, docs/03-data-model.md, docs/02-architecture.md,
this file, tests/conftest.py, tests/builders/__init__.py, tests/fakes/{clock,llm,store,
engine,resolver}.py, src/ripple/core/**, src/ripple/llm/{router,client,config,
evidence,resolver,change_detector}.py, src/ripple/llm/prompts/__init__.py,
src/ripple/storage/{base,engine,tables,postgres}.py, infra/migrations/versions/0001,0002.
New files in shared directories are fine when listed under a workstream's ownership.

## Workstreams
| WS | Name | Owns (create/edit) | Depends on | ADR range | Migration | Class |
|---|---|---|---|---|---|---|
| WS-1 | Jobs adapter: schemas, rules, ranking | src/ripple/domains/jobs/** except vocabulary.py and parsers/; tests/domains/jobs/** | C1, core | 0030–0034 | — | Parallel-ready |
| WS-2 | Resume and JD parsers | src/ripple/domains/jobs/parsers/**, src/ripple/llm/schemas/{resume,jd}.py, src/ripple/llm/prompts/{resume_parser,jd_parser}.v*.md, tests/domains/jobs_parsers/** | C1, C4, ADR-0024 | 0035–0039 | — | Parallel-ready |
| WS-3 | API, identity, inspector, confirmation flow | src/ripple/api/**, src/ripple/storage/users*.py, tests/api/**, tests/storage/test_users*.py | C1, core, storage, WS-2 schemas (contract-dependent) | 0040–0044 | 0003_users (down_revision "0002") | Parallel-ready |
| WS-4 | Conversation + Tailor agents (LangGraph) | src/ripple/agents/**, src/ripple/llm/prompts/{conversation,tailor}.v*.md, src/ripple/llm/schemas/{conversation,tailor}.py, tests/agents/**, tests/fakes/retriever.py | C2 (contract-dependent on WS-5), C4, Intake, ADR-0023 | 0045–0049 | — | Contract-dependent |
| WS-5 | Retrieval: lexical, graph expansion, evidence, Embedder wiring | src/ripple/retrieval/**, src/ripple/storage/search*.py, infra/migrations/versions/0004_embeddings.py (down_revision "0003"), tests/retrieval/**, tests/fakes/embedder.py | C2, storage, ADR-0026 | 0050–0054 | 0004_embeddings | Parallel-ready |
| WS-6 | Worker, scheduler, notifications, digest | src/ripple/worker/**, src/ripple/notify/**, tests/worker/**, tests/notify/**, tests/fakes/transport.py | C1 `RecommendationSource` (contract-dependent on WS-1), core sweep, ADR-0017, ADR-0025 | 0055–0059 | — | Contract-dependent |
| WS-7 | Bench: baselines, RippleBench v0 generator, metrics interfaces ([human] metric functions), TTC harness | bench/**, tests/scenarios/** (new files; runner.py edits allowed), results/README.md, docs/proposals/0003 follow-up | engine (integration-blocked for numbers), C1 | 0060–0064 | — | Parallel-ready to build, integration-blocked to run |
| WS-8 | Deploy, CI, observability | infra/docker-compose.yml, infra/Dockerfile*, .github/**, src/ripple/llm/tracing.py, src/ripple/llm/router.py (tracing hook only), docs/learning/deploy.md | ADR-0018 | 0065–0069 | — | Parallel-ready (coordinator runs it) |
| WS-0 | Coordinator: contracts, integration, records, engine review | the coordinator-owned list above | — | 0022–0029 | — | — |

## Dependency graph (build order only where arrows exist)
C1 → WS-1, WS-2, WS-3, WS-6, WS-7 · C2 → WS-5 → WS-4 · WS-2 schemas → WS-3 confirmation
flow (build against the schema module name; WS-2 ships it first) · WS-1 ranking →
WS-6 digest (build against `RecommendationSource` with a fake) · author's WaveEngine →
scenario and bench numbers (integration-blocked only).

## Rules for every workstream session
1. Read CLAUDE.md, docs/00–05, the ADRs, docs/learning/*.md and this file first.
2. Edit only your owned paths; create new files only there. Never touch the
   coordinator-owned list; request changes in your handover file.
3. Lint, format, type-check and test **your paths only**:
   `uv run ruff check <paths>`, `uv run ruff format <paths>`,
   `uv run pyright <paths>`, `uv run pytest <your test dirs> -q`. The full suite runs at
   the coordinator's checkpoints.
4. Offline only: FakeLLM, FakeClock, InMemoryStore, ScriptedEngine; no network, no real
   LLM, no real Telegram. New fakes go in new files under tests/fakes/.
5. Decisions get an ADR in your range, Status "Accepted under the autonomous mandate",
   not added to docs/adr/README.md (the coordinator indexes it).
6. Write docs/learning/<module>.md for each module you finish (the /explain format).
7. Hand over in docs/plans/parallel-execution/<ws>.md: status, files, verification
   output, contract change requests, open problems, suggested commit message. Never
   commit, push, merge, rebase, reset, tag or run gh.
8. uv is at ~/.local/bin; run `export PATH="$HOME/.local/bin:$PATH"` first in bash.
   Do not run `uv add`; dependencies you need beyond pyproject go in the handover.

## Status board
| WS | Status | Last update | Notes |
|---|---|---|---|
| WS-0 | In progress | 2026-10-19 | contracts C1, C2 written; ADR-0022–0026; deps added; 7 sessions launched |
| WS-1 | Locally verified | 2026-10-19 | 94 tests; ADR-0030..0032; DerivedAttribute moved to vocabulary by coordinator |
| WS-2 | Locally verified | 2026-10-19 | 86 tests; ADR-0035; handover refreshed |
| WS-3 | Integrated and verified | 2026-10-19 | 61 tests; ADR-0040..0044; migration 0003; adapters wired by coordinator (api/adapters.py); Store gained per-user event reads/deletes and Intake.edit on request |
| WS-4 | Locally verified | 2026-10-19 | 29 tests; ADR-0045, 0046; Decision.question + pending_questions added by coordinator on request |
| WS-5 | Locally verified | 2026-10-19 | 54 tests (+6 slow skipped); ADR-0050; migration 0004; indexer hook added by coordinator on request |
| WS-6 | Integrated and verified | 2026-10-19 | ADR-0055, 0056; worker wiring filled (job_context_from_env) and tested |
| WS-7 | Locally verified (ripple numbers integration-blocked) | 2026-10-19 | ADR-0060..0063; 4 strategies, 35 v0 scenarios with split manifest, metric interfaces [human], TTC harness; baselines run and write results/ |
| WS-8 | Locally verified | 2026-10-19 | Anthropic adapter (ADR-0027), transport backoff, config TOML + prices, tracing spans, Dockerfile + entrypoint, compose app profile, CI image/bench jobs; tests/llm 49 passed; Docker/CI unverified locally |
| WS-9 | Integrated and verified (offline) | 2026-10-26 | Scout, sources registry, dedupe; review-pass drift reconciled by the coordinator (ADR-0073); capability declaration; criteria-change trigger wired at C3 |
| WS-10 | Integrated and verified (offline) | 2026-10-26 | Telegram inbound channel; hosted in the API lifespan (ADR-0078); handover completed by the coordinator; no real bot used |
| WS-11 | Integrated and verified (offline) | 2026-10-26 | MCP server; Services.retriever, public inspector helpers, mcp compose service and Caddy /mcp route applied at C3 |
| WS-12 | Integrated and verified (offline) | 2026-10-26 | Dashboard; API requests applied (ADR-0088), OpenAPI snapshot test added; dashboard adopts the new endpoints at C3 |
| WS-13 | Integrated and verified (offline) | 2026-10-26 | Hardening code by WS-13; records (ADR-0095..0098, learning doc, handover) written at C3; per-event lease ADR-0099 and CGPA scale by the coordinator |
| WS-14 | Integrated and verified (offline) | 2026-10-31 | link pairs, leakage test, hand-check protocol, evaluation harness; training loop [human]; ADR-0090..0094 |
| WS-15 | Integrated and verified (offline) | 2026-10-31 | news_v1 and finance_v1 (synthetic), finance pairs for H4, STALE loader; ADR-0100..0104 |
| WS-16 | Integrated and verified (offline) | 2026-10-31 | pilot feedback (migration 0009, API, bot and dashboard controls at C4), weekly report, incident runbook; ADR-0105..0107 |
| WS-17 | Integrated and verified (offline) | 2026-10-31 | paper and thesis outlines, numbers from results/, I8 check (violations fixed at C4); ADR-0110, 0111 |

Statuses: Not started · In progress · Implemented · Locally verified ·
Integration blocked · Integrated and verified · Failed or needs redesign.

## Checkpoint log
- 2026-10-19 C0: baseline before launch: `pytest` 160 passed, 19 skipped (database),
  21 xfailed (human engine); ruff and pyright clean.
- 2026-10-19 C1: all seven sessions hit the account session limit (reset 10:20 IST)
  after writing their code; combined checkout: ruff, format, pyright clean; `pytest`
  566 passed, 37 skipped (database), 31 xfailed (engine + metric functions). Contract
  requests applied: Decision.question, answers.pending_questions, multi-valued
  attributes in change detection (adapter-declared), DerivedAttribute and
  MULTI_VALUED_PROFILE_ATTRIBUTES in vocabulary, hours_until_deadline(now) replaces the
  broken property, MemoryIndexer hook in Intake/RippleRunner/forget, drift test imports
  search_schema. Migration chain 0001..0004 renders offline (23 DDL statements).
  WS-3, WS-7, WS-2 resumed by message for their remaining items.
- 2026-10-19 C2 (partial, WS-7 outstanding): WS-2 and WS-3 verified; API adapters
  (api/adapters.py) wire WS-1 and WS-2 into the app factory; worker wiring built; Store
  gained change_events_for_user/forget_events_for_user and per-user deletes; Intake.edit;
  storage package imports every table module so autogenerate and the drift test see
  0003 and 0004. Full suite: 610 passed, 40 skipped (database), 31 xfailed; ruff and
  pyright clean. Left for later: swap the API's EventLog for the Store methods, a
  shared tests/storage/conftest.py, DELETE /me erasing ChangeEvents through the new
  Store method, Postgres DeliveryLog.
- 2026-10-19 C2 (closed): WS-7 verified. EventLog stop-gap removed from the API in
  favour of the Store methods; DELETE /me now erases the user's ChangeEvents and keeps
  ForgetEvents as audit (FR-15). RippleDriver protocol added for the bench strategies.
  WS-7 doc requests applied (docs/04, CLAUDE.md commands, IDEAS, ADR index). Full
  suite: 818 passed, 38 skipped (database), 31 xfailed; ruff and pyright clean.
  Baseline bench runs exist in results/ (append_only, newest_wins, check_everything);
  the ripple strategy reports not runnable until the author's WaveEngine lands.
- 2026-10-19 C2 follow-ups from WS-2: the API uses WS-2's candidate_to_statement (a
  confirmed fact carries confidence 1.0; WS-1's statement_from_candidate stays for
  agent-side use); CGPA scale is recorded as ProfileAttribute.CGPA_SCALE (default 10)
  rather than guessed from magnitude; the eligibility rule compares within one scale
  (Tier A follow-up in the jobs adapter).
- 2026-10-24 Round 2 planned in docs/plans/round-2.md: live verification and engine
  landing (WS-0), Scout (WS-9), Telegram inbound channel (WS-10), MCP server (WS-11),
  dashboard (WS-12), hardening follow-ups (WS-13), link-finder data design (WS-14).
  State on 2026-10-24: 893 passed, 43 skipped, 31 xfailed; still no commit, Docker or
  remote; engine and metric functions still the author's.
- 2026-10-24 Production plan (docs/plans/production-plan.md) supersedes round-2 ordering.
  Wave A launched: WS-9 Scout, WS-10 Telegram inbound, WS-11 MCP, WS-12 Dashboard,
  WS-13 Hardening; coordinator WS-0 deployment layer (ADR-0028, ADR-0029). Dependencies
  added: mcp, langfuse. Ownership and ADR ranges: production-plan.md table.
- 2026-10-24 WS-0 deployment layer built: infra/docker-compose.prod.yml, Caddyfile,
  backup.sh/restore.sh, CI publish + compose validation + dashboard job, docs/ops,
  docs/pilot (consent draft, onboarding), LangfuseTracer wired into API and worker
  routers (tests/llm 47 passed). Wave A sessions were interrupted once and resumed:
  WS-12 by message; WS-9, WS-10, WS-11, WS-13 restarted from their on-disk state.
- 2026-10-26 C3 (closed, coordinator in this session; the wave-A sessions had stopped at
  the account session limit, so their open items were finished here after checking file
  times and session state). WS-9 review drift reconciled (ADR-0073); WS-10 and WS-13
  handovers and WS-13 records written (ADR-0095..0098); per-ChangeEvent lease
  (ADR-0099) and CGPA scale (ADR-0034) by a subagent, closed here; event observers and
  the criteria-change Scout trigger with scout_user_job (ADR-0079); Telegram channel in
  the API lifespan, Services carries router, retriever and delivery log (ADR-0078);
  dashboard API additions and adoption (ADR-0088); OpenAPI snapshot test; prod compose
  gains the mcp service, proxy trust, an env anchor, and only `migrate` migrates.
  Code review: 0 blockers, 7 majors and 14 minors, all majors and 13 minors fixed (the
  API importing ripple.worker.lease is noted, not moved). Full suite: 1346 passed,
  62 deselected (slow), 31 xfailed (engine and metric functions); ruff, format and
  pyright clean; dashboard 128 tests, lint and static build pass; migrations 0001..0006
  render offline. Postgres, Redis, a real bot, Docker and CI remain unverified.
- 2026-10-31 Wave B launched on the author's "Start wave B": docs/plans/wave-b.md
  (ownership, ADR ranges 0090-0094 / 0100-0104 / 0105-0109 / 0110-0114, migration 0009,
  acceptance per workstream). Contract C5 added before launch: bench/linkpairs.py with
  tests/scenarios/test_linkpairs_contract.py (5 passed). `paper` added to the ruff and
  pyright paths. Four sessions started in the shared checkout.
- 2026-10-31 C4 (closed): WS-14, WS-15, WS-16 and WS-17 handed over; WS-17 was asked to
  finish after its turn ended mid-review. Applied: feedback table registration (R0),
  /feedback router in the app with the rate limit, Services.feedback_store wired to
  Postgres, DELETE /me erases and the export includes feedback (R1-R3); Telegram
  feedback buttons (p: callbacks, question usefulness row) through the same
  record_feedback; dashboard feedback controls (subagent, 145 dashboard tests); leakage
  persona prefixes for every track and an empty-training-set refusal in training/;
  the seven I8 violations fixed at their source; ADR index 0090-0094, 0100-0107,
  0110-0111; CLAUDE.md commands; docs/03, docs/04, roadmap and IDEAS updates. Code
  review subagent failed twice on a network certificate error; the coordinator
  reviewed the seams instead and added two tests. Full suite: 1786 passed (before the
  two added tests), 73 deselected (slow), 33 xfailed (engine, metric functions and the
  [human] training loop); ruff, format and pyright clean; migrations 0001..0009 render
  offline. Postgres, Redis, a real bot, Docker and CI remain unverified.
