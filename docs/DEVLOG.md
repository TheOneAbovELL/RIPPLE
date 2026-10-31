# Devlog
Newest first. One entry per session.

## Template
### YYYY-MM-DD — Phase N, task
- Changed: what and why
- Decisions: ADR links
- Learned: one or two lines
- Open problems:
- Next step:

---

### 2026-10-31 — Final delivery, integration (coordinator, in progress)
- Changed: the author asked (2026-10-31) for the whole project to be delivered today and for
  the [human] pieces (WaveEngine, metric functions, training loop) to be implemented. Built:
  WaveEngine; embedded Postgres slow suite (ADR-0115); structured facts link and derive with
  no model (ADR-0116); Anthropic adapter fix, temperature removed (ADR-0117); GET /events,
  profile vocabulary, prose-deadline fix, duplicate-opening 409, run_once on the worker
  wiring, RIPPLE_LINKER wired, image without torch by default (ADR-0118). Integrated WS-18
  (metrics + 82-run grid, ADR-0120..0123), WS-19 (trained link finder, ADR-0125..0128) and
  WS-20 (dashboard flows, local run, ADR-0130..0134). README rewritten. WS-21 (paper and
  thesis drafts, ADR-0135..0139) running.
- Learned: the ANTHROPIC_API_KEY on this machine is invalid (401), so no real-LLM numbers.
  Any edit under src/ripple/{core,domains,retrieval} or bench/ changes the bench digest,
  so the grid must be re-run after the last such edit.
- Open: re-run bench.matrix + bench.summary; full verification (fast, slow, lint, types,
  dashboard); code review; graphify update; H3 and the pilot need a key and a season.

---

### 2026-10-31 — Wave B and checkpoint C4 (coordinator session)
- Changed: wrote docs/plans/wave-b.md and contract C5 (bench/linkpairs.py, labelled link
  pairs) before launching four sessions in the shared checkout. WS-14 built link-pair
  generation from RippleBench v0, a leakage test, the 300-pair hand-check protocol and
  a linker evaluation harness, with the training loop left [human]. WS-15 built news
  and finance adapters, synthetic news_v1 and finance_v1 tracks, test-only finance
  pairs for H4 and a STALE loader for a local copy. WS-16 built pilot feedback
  (migration 0009), the weekly pilot report, the incident runbook and refined pilot
  drafts. WS-17 built the paper and thesis outlines, numbers rendered only from
  results/, and the I8 check. At C4 the coordinator wired feedback into the API,
  export, deletion, the Telegram question card and the dashboard, fixed two
  training-data seams the WS-15 auditor found, and fixed the seven I8 violations.
- Decisions: ADR-0090..0094, 0100..0107, 0110, 0111 (all under the mandate).
- Verified: `pytest -m "not slow"` 1786 passed, 73 deselected, 33 xfailed, then two
  more feedback tests passing; ruff, format, pyright clean; apps/web 145 tests, lint and
  build pass; alembic 0001..0009 renders offline. The code-reviewer subagent could not
  run (network certificate error, twice); the seams were reviewed by hand.
- Learned: a session can end its turn while its own review subagent is still running;
  check the handover's status line, not the turn note. An I8 scanner finds the hand
  estimates in status documents first; write progress as counts with a source.
- Open problems: every results/ folder says "uncommitted", so paper.numbers refuses all
  macros until the first commit and a re-run; news and finance tracks are synthetic;
  STALE needs the dataset on disk; the hand-check labels, the training loop, the
  WaveEngine and the metric functions are the author's; feedback buttons on digests
  need the outbound transport to carry keyboards (IDEAS 16); producers must write what
  paper/registry.py reads (IDEAS 17).
- Next step: author makes the first commit and adds a GitHub remote (CI runs the slow
  suite and builds the image), then implements WaveEngine; after that the baselines
  and ripple runs are re-run so the paper numbers can render.

---

### 2026-10-26 — Status analysis and checkpoint C3 (coordinator session)
- Changed: wrote docs/plans/status-2026-10-26.md (done vs left against the roadmap and
  the production plan, from measured runs). Closed wave A: reconciled the Scout's
  review-pass drift (6 failing tests, docs, ADR-0073); fixed a vacuous rate-limit test
  (FastAPI 0.146 mounts routers lazily); replaced the worker's Scout stub tests;
  applied the MCP and dashboard contract requests (public inspector helpers,
  Services.retriever/router/delivery_log/vocabulary, GET /graph, GET /vocabulary,
  EditIn.valid_to with 422/409 instead of 500, required output fields, dev CORS,
  OpenAPI snapshot test); hosted the Telegram channel in the API lifespan; added
  EventObserver to RippleRunner and the criteria-change Scout trigger with a merged,
  time-bounded scout_user_job that skips deleted users and shares one parse cache per
  run; per-ChangeEvent lease in worker and API; CGPA scale in derivation, rule and
  criteria; DELETE /me erases delivery records; Postgres delivery log in the worker;
  middleware order so a 413 carries security headers; trace id on statements and
  edits; no slash redirects behind Caddy; Redis pools shared, locked and closed; prod
  compose mcp service, proxy trust, env anchor; only `migrate` migrates, with a
  rollback message; ruff no longer formats Markdown.
- Decisions: ADR-0034, 0073, 0078, 0079, 0088, 0095..0099 (all under the mandate).
  Accepted ADRs are not edited in place: two inline amendments I made (0072, 0082) and
  one a subagent made (0031) were moved into new ADRs.
- Verified: `pytest -m "not slow"` 1346 passed, 62 deselected, 31 xfailed; ruff check
  and format clean; pyright 0 errors; apps/web lint, 128 tests and static build pass;
  alembic 0001..0006 renders offline. Code review: 0 blockers, 7 majors, 14 minors; all
  majors and 13 minors fixed, with tests that fail without the fix where it applies.
- Learned: FastAPI 0.146's lazy router inclusion makes route-walking tests pass
  vacuously; test behaviour through the OpenAPI document instead. A Scout parse cache
  that is never passed silently multiplies LLM cost by the number of users.
- Open problems: nothing here ran against Postgres, Redis, a real bot or Docker; the
  API depends on ripple.worker.lease (move the lease adapters to a shared module if it
  grows); Telegram update ledger and Scout ledger are in memory (migrations 0007, 0008
  reserved; IDEAS 11); the JD parser reads "3.0/4" as ten-point (IDEAS 10); 4-point
  students get no eligibility verdict for openings recorded after their scale fact.
- Next step: author makes the first commit and adds a GitHub remote so CI runs the slow
  suite and builds the image; then wave B (WS-14..WS-17) per production-plan.md.

---

### 2026-10-24 — Production plan and wave A launch (coordinator session)
- Changed: docs/plans/round-2.md (next-session plan) then docs/plans/production-plan.md
  (one-pass production completion: definition of done, decisions fixed up front,
  waves, ownership, ADR ranges). ADR-0028 (Langfuse now), ADR-0029 (deployment
  topology). Dependencies: mcp, langfuse. WS-0 deployment layer: prod compose with
  Caddy TLS, migrate job, backup sidecar and restore script, CI image publish to GHCR
  with compose validation and a dashboard job, docs/ops (deploy, runbook), docs/pilot
  (consent draft, onboarding), LangfuseTracer behind the Tracer protocol wired into the
  API and worker routers with a shutdown flush.
- Launched wave A: WS-9 Scout, WS-10 Telegram inbound, WS-11 MCP server, WS-12
  dashboard, WS-13 hardening; the first run was interrupted and resumed from disk.
- Verified: tests/llm 47 passed with the tracer; tests/worker and API wiring green;
  full suite before the wave: 893 passed, 43 skipped, 31 xfailed; ruff and pyright
  clean. Compose files unvalidated locally (no Docker); CI validates them.
- Open problems: still no commit, remote, Docker or API key on the author's machine;
  engine and metric functions remain the author's; API lifespan flush for the tracer
  is applied at checkpoint C3 after WS-13 lands its app.py lines.
- Next step: checkpoint C3 when wave A reports (full suite, wiring of Scout and bot
  into worker and API, contract requests), then wave B.

---

### 2026-10-19 — Parallel round 1 closed at checkpoint C2 (coordinator session)
- Changed: WS-2, WS-3 and WS-7 finished after the limit reset. Integration done here:
  API adapters (src/ripple/api/adapters.py) wire WS-2 parsers and WS-1 recorder,
  derivation and recommender into the app factory; worker wiring builds the full
  JobContext from the environment; Store gained per-user event reads and deletes,
  Intake gained edit(); the API's EventLog stop-gap is gone and DELETE /me erases the
  user's ChangeEvents (ForgetEvents stay as audit); ripple.storage imports every table
  module so autogenerate and the drift test see migrations 0003 and 0004; RippleDriver
  protocol lets the bench swap strategies without casts. WS-7's doc requests applied.
- Decisions: ADR-0040..0044 (WS-3), ADR-0060..0063 (WS-7) indexed; docs/04 lists
  time-to-consistency and the stale-action window; H1 "accuracy" reading recorded as
  the collaborator's proposal pending the Phase 3 baseline ADR.
- Verified: ruff, ruff format, pyright clean; `pytest` 818 passed, 38 skipped
  (database), 31 xfailed (10 engine, 11 scenarios, 10 metric functions, all [human]).
  Baseline bench runs written to results/ (append_only, newest_wins, check_everything)
  with honest failures against gold; ripple strategy not runnable until the engine
  exists. Docker, Redis, CI, real LLM and Telegram remain unverified locally.
- Open problems: Scout agent (Phase 3) not started; MCP server and React Flow dashboard
  (Phase 4) not started; Postgres DeliveryLog and per-event lease (IDEAS 8); confirm
  endpoint not atomic under concurrent confirms (WS-3 handover); uploaded resume text
  not persisted so span refs do not resolve yet; Embedder model decision waits for v0
  numbers (ADR-0026); repo still uncommitted, so results carry sha "uncommitted".
- Next step: author implements WaveEngine and the metric functions; then remove the
  xfail markers, rerun smoke and v0 with the ripple strategy, and compare resolver_calls
  with check_everything for H1. Next build round: Scout agent, MCP server, dashboard.

---

### 2026-10-19 — Parallel round 1: seven workstreams on one checkout (coordinator session)
- Changed: parallel-execution directive. Wrote contracts C1 (jobs vocabulary) and C2
  (retrieval), ADR-0022..0027 (API stack, LangGraph checkpointer, pypdf resume parsing,
  Telegram over httpx, lexical-first retrieval, Anthropic adapter), added the
  dependencies, the tracker docs/plans/parallel-execution.md, and launched sessions
  WS-1..WS-7 with file ownership (no git commits exist, so no worktrees). Did WS-8
  here: Anthropic adapter with forced tool use, transport retries with backoff, TOML
  router config with config-only prices, tracing spans, Dockerfile + entrypoint,
  compose app profile, CI image and bench jobs.
- Workstreams (their handovers in docs/plans/parallel-execution/): WS-1 jobs adapter
  (ADR-0030..0032, 94 tests), WS-2 parsers (ADR-0035, 60 tests), WS-3 API and identity
  (ADR-0040..0044, migration 0003, 56 tests; handover pending), WS-4 agents
  (ADR-0045, 0046, 29 tests), WS-5 retrieval (ADR-0050, migration 0004, 54 tests),
  WS-6 worker and digest (ADR-0055, 0056), WS-7 bench (strategies, generator with 35
  scenarios, metric interfaces for the author's [human] task; records pending). All
  seven hit the account session limit once; WS-3, WS-7, WS-2 were resumed by message.
- Decisions: ADR-0022..0027 plus the workstream ADRs above; contract requests applied
  in core: Decision.question, answers.pending_questions, adapter-declared multi-valued
  attributes in change detection, MemoryIndexer post-commit hook (Intake, runner,
  forget), DerivedAttribute moved into the vocabulary, hours_until_deadline(now).
- Verified at checkpoint C1: ruff, ruff format, pyright clean on the combined
  checkout; `pytest` 566 passed, 37 skipped (database), 31 xfailed (engine + metric
  functions) before contract changes; after them and the worker wiring the
  coordinator's paths are green and the only failures are files WS-2, WS-3 and WS-7
  are editing. `alembic upgrade head --sql` renders 0001..0004 (23 DDL statements).
- Learned: a python patch script read under the Windows code page corrupts "·" and
  "→"; run patch scripts with `-X utf8`. Session names for SendMessage are the session
  titles with their [ref], not the short names.
- Open problems: Docker and CI still unverified locally; Postgres DeliveryLog and a
  per-ChangeEvent lease are follow-ups (WS-6); API wiring default_adapters is WS-3's
  to fill (message sent); the Embedder model decision waits for RippleBench v0
  numbers (ADR-0026); the engine and metric functions remain the author's.
- Next step: checkpoint C2 when WS-2/3/7 report: full suite, API wiring verified,
  roadmap ticks, hand-over A..G.

---

### 2026-10-19 — Phase 1 built under the autonomous mandate (third session of the day)
- Changed: author issued the autonomous-engineering mandate (recorded in CLAUDE.md
  "Working mode"). Wrote docs/plans/phase-1.md and built Phase 1: core models and link
  policy (two classes, registry); Store protocol with InMemoryStore and a shared
  contract test; DependencyGraph plus the human-owned WaveEngine stub with 10 contract
  tests (xfail strict); Resolver protocols with the rule-first chain; versioning with
  incoming/outgoing link copies; write flow (record/update with ChangeEvent in the same
  transaction); RippleRunner with two commits per wave, ask-subtree marking, crash
  recovery and resume; forget API with chain + cascade; NightlySweep (expiry, resume);
  user answers (still holds / no longer / correction); visibility rule for I1; Linker
  protocol with RuleLinker and LLMLinker; two-stage change detection; Intake; LLM
  resolver and change detector with versioned prompts v1 and strict schemas;
  PostgresStore, tables, migration 0002 with a schema-drift test; scenario runner, 11
  YAML scenarios, bench smoke runner writing results/. ADR-0019, 0020, 0021.
  Learning docs: ripple-engine, ripple-runner-and-writes, linking-and-intake, storage.
- Decisions: ADR-0019 rule-first resolution (chain built; jobs rules Phase 2),
  ADR-0020 change-detection policy, ADR-0021 PyYAML for scenarios. Spec clarification
  recorded in docs/03: the event whose trigger supersedes a version covers that
  version's retirement (I2).
- Verified: ruff, ruff format, pyright (strict core) clean. `pytest`: 146 passed,
  16 skipped (Postgres contract and migration tests, no database locally), 21 xfailed
  (10 engine + 11 scenarios, waiting on the human engine). `python -m bench.run --suite
  smoke`: runs, writes results/2026-10-18_smoke_uncommitted/, reports 0/11 "not
  runnable" until the engine exists (honest number, I8).
- Review (code-reviewer, 1 blocker + 5 majors + minors), all fixed and tested in
  tests/core/test_ripple_runner_recovery.py: resume could drop a wave after a crash
  because history ids were recorded as affected (now only SUSPECT ids are, and
  resume resolves exactly the outstanding ones); parked subtrees are now recorded on
  the event (`parked`) and answers restore exactly that set with wave-0 decisions;
  resolver updates carry valid_to and structured forward; a same-value structured
  statement is UNCHANGED and writes nothing; commit two re-reads rows and skips
  members changed meanwhile; Statement.origin decides the trigger kind; evidence
  refs are filtered to shown ids; verdict schemas forbid extra fields; a past
  valid_to is invalid output; links have a unique (parent, dependent, type)
  constraint mirrored by the in-memory store; InvalidObjectError replaces bare
  ValueError in core dataclasses. After fixes: 160 passed, 21 xfailed.
- Learned: copying incoming links must skip retired dependents and dedupe outgoing
  copies by (latest parent, type), or chains of updates duplicate edges. The boundary
  test must allow an injected clock's `.now()`. A ripple cannot be one transaction.
  Only ids actually flipped to SUSPECT may count as affected, or resume cannot tell
  history from outstanding work.
- Open problems: the engine is yours; until then Phase 1's exit ("scenarios pass
  offline") is not met. Postgres tests unverified locally (Docker). Rule resolvers are
  an empty list until the jobs adapter (Phase 2). Ask-user queue listing is Phase 2 API
  work. No transport retries in the Router yet. The sweep resumes open events by age
  and could double-resolve one that is legitimately still running under a slow LLM;
  acceptable single-process in Phase 1, to be guarded by a lease when the arq worker
  arrives (Phase 3).
- Next step: author implements WaveEngine (docs/learning/ripple-engine.md has the
  recipe); collaborator reviews it, then Phase 2 (jobs adapter, parsers, conversation
  agent, API, Telegram digest).

---

### 2026-10-19 — Phase 0, tasks 0.1–0.7 built (second session of the day)
- Changed: author approved ADR-0013/0014/0015 and the plan, then gave blanket
  authorization for Phase 0. Ran `git init`, installed uv 0.13.1. Built: pyproject
  (exact pins: pydantic 2.14.1, sqlalchemy[asyncio] 2.1.5, alembic 1.20.0,
  psycopg[binary] 3.3.6; dev: pytest 9.1.1, ruff 0.17.1, pyright 1.1.414), package
  skeleton; core clock/ids/errors + FakeClock + AST boundary tests; llm Router with
  validation, retry-with-error, fallback, usage accumulation, per-attempt logging, and
  FakeLLM; storage package (base, engine factory); Alembic with migration 0001
  (pgvector extension); docker-compose (postgres pgvector, redis); GitHub Actions CI
  (checks job + services job); learning docs for core and llm.
- Decisions: ADR-0016 (SQLAlchemy async + Alembic in src/ripple/storage), ADR-0017
  (arq on Redis), ADR-0018 (Langfuse over OTel, stdlib logging until Phase 2), all
  Accepted under the blanket authorization; revisit on request.
- Verified: `uv run ruff check .` clean; `ruff format --check` clean; `pyright`
  0 errors (strict on core); `pytest -m "not slow"` 32 passed; slow tests skip without
  a database; `alembic upgrade head --sql` emits the expected SQL, also from another
  working directory. Code-reviewer: no blockers, 2 majors + 13 minors, all fixed
  except the pgvector image-tag pin (needs a Docker pull to confirm).
- Learned: SQLAlchemy's async engine needs the `[asyncio]` extra (greenlet). With
  pydantic v2, non-JSON text raises ValidationError, so a separate ValueError branch
  is dead code. A provider call that raises mid-retry must still count as an attempt
  or fallback usage under-reports cost.
- Open problems: Docker not installed, so compose and the live migration are
  unverified locally; no GitHub remote, so CI is unverified; repo still under OneDrive.
  Not ticked on the roadmap for those reasons. Known gap: no transport retries with
  backoff in the Router (TODO, Phase 1).
- Next step: author installs Docker Desktop and pushes to a remote (CI, compose and
  migration ticks); then /plan-phase 1.

---

### 2026-10-19 — Phase 0, kickoff session (docs only, no code)
- Changed: ran the kickoff brief. Summarised intent, claims, invariants and phase;
  listed 13 gaps; proposed 5 innovation candidates. Interviewed the author on 4 of
  them (wave-by-wave ripple; versions as rows with link copy; core link classes with
  domain mapping; trigger = memory write with valid_to self-expiry). Rewrote
  docs/03-data-model.md; updated docs/01, 02, 04, 05 and CLAUDE.md (workflow step 5
  review, innovation tiers, I1/I2/I7 wording, pending-ADR list). Created docs/IDEAS.md,
  docs/proposals/ (0001 rule-first resolution, 0002 silver labels + pre-filter,
  0003 time-to-consistency) and docs/plans/phase-0.md. Two architecture-guardian
  passes (18 then 9 findings) fixed before hand-over; see the plan's review section.
- Decisions: ADR-0013, 0014, 0015 written as Proposed; they amend 0003, 0004, 0007
  (marked in the index). Interview question 5 (ChangeEvent trigger kinds) was not
  answered: the collaborator's recommended option is in ADR-0015 points 3–4, flagged.
- Learned: "copy links to the new version" only works with an explicit seed set and
  no status filter in the engine, otherwise expiry and retire ripples find nothing.
  One transaction per ripple is impossible once a wave waits on a user.
- Open problems: not a git repo; uv and Docker not installed; repo lives under
  OneDrive (sync risk). Assumptions marked *(assumed)* in docs/03 need confirming:
  link direction notation, ask marks its subtree SUSPECT, FR-16 added from the
  proposal. Identity/auth model, email digest scheduling, FR-7 thresholds, and the
  metric definitions in docs/04 "Open" remain undecided. Questions 6–10 of the
  interview were not asked.
- Next step: author approves ADR-0013/0014/0015 and docs/plans/phase-0.md, runs
  git init and installs uv; then task 0.1.

---

### 2026-10-19 — Phase 0, project definition
- Changed: wrote vision, requirements, architecture, data model, evaluation, roadmap,
  related work; ADRs 0001–0012 accepted.
- Decisions: ADR-0001 to ADR-0012.
- Learned: cascading invalidation itself is published (PACMI, Oct 2026); our novelty is
  learned edge induction, action-level evaluation and a real pilot.
- Open problems: confirm guide's approval; check departmental rules on pilot consent.
- Next step: run the kickoff prompt; /plan-phase 0.
