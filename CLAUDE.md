# Ripple — instructions for Claude Code

## What this is
Ripple is a domain-agnostic consistency layer for agent memory: when a fact changes,
every belief that depended on it is updated. First product: a job-hunt agent for
engineering students. Final-year B.Tech project (Nov 2026 – May 2028).
The author, Omjee R Giri, owns every decision. You are a collaborator, not the author.

## Read before working
- docs/00-vision.md — why this exists, what we claim, what we do NOT claim
- docs/02-architecture.md + docs/03-data-model.md — before touching src/
- docs/04-evaluation.md — before touching bench/, training/ or results/
- docs/05-roadmap.md — current phase, its tasks and exit criteria
- docs/adr/README.md — decisions already made; never silently reverse one
- docs/IDEAS.md + docs/proposals/ — innovation backlog and Tier B proposals
- docs/DEVLOG.md — last 3 entries, to know where work stopped
Source of truth: docs/ > code > chat. If code and docs disagree, stop and ask.

## Working mode: autonomous (authorised by the author on 2026-10-19)
The collaborator decides and executes routine and project-level engineering decisions
without waiting: architecture refinements, data-model changes, dependencies, evaluation
methods. Each significant decision still gets an ADR (status "Accepted under the
autonomous mandate"), tests, docs and a DEVLOG line; earlier ADRs are superseded or
amended, never silently reversed. Questions to the author only when an assumption
risks data loss, security, irreversible external effects or the product's intent.
[human] tasks stay human-owned. Git write operations stay forbidden.

## How we work (every task)
1. Explore: read the relevant docs and code. Never guess file contents.
2. Plan: anything over ~30 lines or touching >1 module gets a written plan in
   docs/plans/; proceed into implementation once it is clear.
3. Implement in small steps; every step leaves tests passing.
4. Verify: run tests, lint, type check. Show real output. Never claim a pass you did not see.
5. Review: ask the code-reviewer subagent to review the diff; fix blockers.
6. Record: update docs, DEVLOG, roadmap checkboxes; ADR for any decision.
7. Never run git commit, push, merge, rebase, reset, tag or any GitHub CLI command. Leave
   all changes uncommitted. End with (1) changed files grouped by purpose, (2) a 3–6 line
   explanation, (3) a suggested commit message "<area>: <what> — <why>";
   the author commits manually.

## Innovation tiers
- Tier A (implement, then record in DEVLOG with evidence): in scope, no new dependency,
  no change to architecture, data model, validity states, invariants, evaluation
  protocol or prompt behaviour; fully tested.
- Tier B: everything else. Write docs/proposals/NNNN-<title>.md, add a line to
  docs/IDEAS.md, then (autonomous mode) decide, record the ADR, implement behind a
  config flag where sensible, and measure with the bench before and after.
- After the design freeze (2027-02-28) a Tier B proposal must also justify "why now".

## Decisions need ADRs (use /adr)
Required for: architecture or module boundaries; any new dependency or service;
the data model or validity states; prompt changes that alter behaviour; evaluation
protocol, metrics or datasets; reversing an earlier ADR.
Always list real alternatives and why they lost. If unsure whether it needs an ADR, it does.

## Invariants (each has a named test: test_invariant_I<n>_...)
- I1 Retrieval never returns RETIRED memories; SUSPECT and PENDING_USER ones only with a flag.
- I2 Every memory state change writes a ChangeEvent with reason and evidence refs,
     whatever its trigger kind (ripple, expiry, user_edit, user_answer).
- I3 The ripple engine (graph traversal) never calls an LLM.
- I4 LLM output is parsed into a Pydantic schema before use; invalid output is
     retried or rejected, never partially applied.
- I5 The agent never invents profile facts, experience or numbers.
- I6 The agent never submits an application or acts on an external site for the user.
- I7 Hard deletion only via the forget API, applied to the whole version chain and
     cascading along dependency links (class depends_on; docs/03-data-model.md).
- I8 Every number in README, docs or paper traces to a file in results/.

## Anti-slop rules
- No placeholder code that pretends to work. Unbuilt paths raise NotImplementedError
  with a TODO naming the roadmap task.
- No new dependency without asking + an ADR.
- No invented benchmarks, metrics, citations or results. Missing number → "TBD (pending run)".
- No drive-by rewrites. Stay in scope; note other issues in DEVLOG.
- Boring, readable code. Domain names (memory, link, ripple), not generic ones
  (data, handler, manager). Comments explain why, not what.
- Unsure? Ask one precise question instead of guessing.

## Human-owned work
Roadmap tasks tagged [human] are written by the author. For those: write the
interface, the tests and a short explanation, leave TODO(human), then review
the author's implementation. Do not implement them unless explicitly asked.

## Stack (reasons in ADRs)
Python 3.12+ with uv · FastAPI + Pydantic v2 · PostgreSQL + pgvector
(SQLAlchemy 2 + Alembic) · LangGraph · MCP Python SDK · Redis job queue ·
PyTorch + Hugging Face (link finder) · Next.js + React Flow (apps/web) ·
pytest, ruff, pyright. Pin exact versions when adding packages.
Decided: SQLAlchemy 2 async + Alembic in src/ripple/storage (ADR-0016) · arq on Redis
(ADR-0017) · Langfuse over OpenTelemetry, stdlib structured logging until Phase 2
(ADR-0018) · pypdf for resumes (ADR-0024) · torch + transformers (CPU) in the `linkfinder`
group (ADR-0125). Pending ADRs (do not import before one exists): embeddings (BGE-M3,
Phase 3), LangGraph checkpointer.

## Commands
- Install: uv sync
- Whole product locally, one command (ADR-0132/0133): uv run python -m tools.local_run [--seed-demo] [--fresh] [--port N]
- One worker job without Redis (ADR-0134): uv run python -m ripple.worker.run_once nightly_sweep|daily_digest|hourly_alerts|scout_run
- Fast offline tests: uv run pytest -m "not slow"
- All tests: uv run pytest
- Lint + format: uv run ruff check . && uv run ruff format .
- Types: uv run pyright
- Services: docker compose -f infra/docker-compose.yml up -d (infra only) · add `--profile app --build` for api + worker
- LLM config: config/llm.default.toml; set RIPPLE_LLM_CONFIG to an override file; prices only from config (I8)
- Migrations: uv run alembic upgrade head
- New migration: uv run alembic revision --rev-id 0002 -m "<slug>" (hand-numbered ids;
  autogenerate output is reviewed, never committed blind; ADR-0016)
- Benchmark smoke: uv run python -m bench.run --suite smoke (writes results/<date>_smoke_<sha>/)
- Benchmark v0: uv run python -m bench.run --suite v0 --strategy ripple|append_only|newest_wins|check_everything [--ablation no_graph|no_ask_user] [--generator-seeds N]
- Whole benchmark grid + summary (ADR-0120/0121): uv run python -m bench.matrix · uv run python -m bench.summary
- Regenerate/check RippleBench v0 data: uv run python -m bench.generate --check
- Slow tests (need a database): TEST_DATABASE_URL=postgresql+psycopg://ripple:change-me@localhost:5432/ripple uv run pytest -m slow
- Slow tests without Docker (embedded Postgres + pgvector, ADR-0115): uv run python -m tools.embedded_pg test · persistent local server: uv run python -m tools.embedded_pg serve
- MCP server: uv run python -m ripple.mcp_server (stdio, RIPPLE_MCP_TOKEN) · `--transport http` for streamable HTTP
- Telegram bot, development long-poll: uv run python -m ripple.worker.telegram_poll (production uses the webhook in the API when TELEGRAM_BOT_TOKEN is set)
- Telegram webhook registration: uv run python -m ripple.notify.inbound.register --url https://<domain>/telegram/webhook
- Link pairs (RippleBench v0 -> C5): uv run python -m training.jobs_pairs [--check] · evaluate a linker: uv run python -m training.evaluate --linker rule|fake_llm|llm|trained [--split test] [--transfer]
- Train the link finder (CPU, ADR-0125/0126): uv run python -m training.train --validation-persona p2_harsh --seed N · summarize seeded runs: uv run python -m training.summarize results/<runs>
- Serve the trained linker: RIPPLE_LINKER=trained RIPPLE_TRAINED_LINKER_MODEL=<artifact dir> (default llm, ADR-0128)
- Hand check: uv run python -m training.handcheck sample --out <csv> · report: uv run python -m training.handcheck report --sheet <csv>
- RippleBench v1: uv run python -m bench.generate_news --check · uv run python -m bench.generate_finance --check · uv run python -m bench.run --suite news_v1|finance_v1 --strategy <name>
- STALE (local copy only): RIPPLE_STALE_PATH=<path> uv run python -m bench.stale
- Pilot weekly report: uv run python -m ripple.pilot.report --week YYYY-Www (writes results/pilot/<week>/)
- Paper numbers from results/ (I8): uv run python -m paper.numbers [--check|--strict|--draft] · I8 scan: uv run python -m paper.i8 [--all]
- Dashboard (inside apps/web only): npm ci && npm run lint && npm test && npm run build · after an API change regenerate apps/web/openapi.json (apps/web/README.md) then `npm run gen:api`
(Keep this list current.)

## Code map
- src/ripple/core — models, Store protocol, ripple engine, Linker and Resolver protocols.
  Domain-agnostic. Must not import any other ripple package, an ORM or a framework.
- src/ripple/storage — SQLAlchemy tables, Alembic migrations, Postgres Store (ADR-0016).
- src/ripple/linking — link finders: rules, LLM, trained model.
- src/ripple/retrieval — validity-aware hybrid retrieval, graph expansion, evidence.
- src/ripple/llm — provider router, schemas, versioned prompts. ONLY place calling LLM APIs.
- src/ripple/agents — LangGraph: conversation, scout, curator, tailor.
- src/ripple/domains/<name> — adapters: schemas, link types, sources, rules.
- src/ripple/{api,mcp_server,notify,worker} — delivery.
- training/ bench/ results/ — link finder training, RippleBench, run outputs.
- apps/web — dashboard.
- paper/ — write-up numbers rendered from results/ and the I8 check; docs/paper — paper and thesis drafts and outlines.

## Testing
- Unit tests never hit the network or a real LLM: use tests/fakes (FakeLLM, FakeClock)
  and the in-memory store.
- Scenario tests (tests/scenarios/*.yaml) replay a user timeline and assert memory states.
- A bug fix starts with a failing test.

## End of session
Run /session-end. Leave changes uncommitted, with a clear summary for the author to commit.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- When graphify-out/graph.json exists, run `graphify query "<question>"` before your first grep, search or source-file read for a codebase question, and put this rule in every subagent prompt that explores code. Read raw files only for lines the graph or an earlier read already located. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
- A committed graphify-out/graph.json is rewritten whole on every build, so a large diff to it in a pull request is expected. Do not flag it as churn or suggest skipping the graph rebuild or its hooks.

### Graph layout for this project
- `graphify-out/` - full knowledge graph: code structure plus docs, ADRs, configs and images (semantic layer). This is the default target of `graphify query`, `graphify path` and `graphify explain`.
- `graphify-code/` - code-only relation graph (deterministic AST, no LLM, own cache). Use it for pure structure questions: `graphify query "<question>" --graph graphify-code/graph.json`. Rebuild after code changes with `GRAPHIFY_OUT=graphify-code graphify update .`.
- Both graphs are scoped to this project only; cross-project links live in the merged graph on the Desktop, not here.
