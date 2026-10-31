# Round 2 plan — from "built offline" to "used daily"
Written 2026-10-24 by the coordinator. Status: **ready to execute**; starts when the
author has done the three prerequisites below, or in parallel with them where marked.

## Where the project stands against the original idea (checked 2026-10-24)
| Claim / goal | State | Evidence |
|---|---|---|
| Thesis: deterministic code decides *which*, LLM decides *how* | Core built: wave runner, resolver chain, rule-first resolution, versioning, forget, expiry, answers. The engine body is the author's ([human]) and is still a stub. | 893 tests pass, 31 xfail wait on the engine and the metric functions |
| C1 learned link induction | Baselines only: rule linker and LLM linker. Training data, the encoder and the pre-filter are Phase 4 (not started). | ADR-0009, proposal 0002 |
| C2 action-level evaluation | RippleBench v0 generator (35 scenarios), 4 strategies, TTC replay harness, metric interfaces. No Ripple numbers yet (engine). Baseline runs exist in results/. | ADR-0060..0063 |
| C3 real pilot | Product exists as code: API with identity, parsers, jobs rules, agents, retrieval, worker, digest. **Never run against Postgres, Redis, a real model or Telegram.** No channel for the student to talk to the agent yet. | docs/plans/parallel-execution/*.md |
| C4 cost | Resolver call counting, usage accounting and config-only prices in place. | Router, CountingResolver |
| Timeline | Code is ahead of the roadmap (Phase 2 and most of Phase 3 built in week 1 of Phase 0). Verification is behind: nothing committed, no CI run, no Docker. | docs/05-roadmap.md ticks |

The gap that matters most is not features. It is that no path has been exercised for
real, and every headline number waits on the engine. Round 2 is therefore ordered
"verify, then land the engine, then the two missing product pieces, then Phase 4 seeds".

## Prerequisites (author, before or alongside round 2)
1. **First commit** of the whole tree. Until then results/ carry sha "uncommitted",
   worktrees are impossible, and nothing is recoverable.
2. **GitHub remote and a push**: CI runs the slow suite against Postgres and Redis and
   builds the image; that is the only verification of migrations 0003 and 0004 we have.
3. **Docker Desktop** locally, or accept CI as the only live environment.
4. **ANTHROPIC_API_KEY** in .env for the first real model calls (a few cents).
5. **WaveEngine** ([human], docs/learning/ripple-engine.md) and, when ready, the
   **metric functions** (docs/learning/bench.md section 4). Neither blocks the
   workstreams below; both gate the first Ripple numbers.

## Workstreams (dependency order, then value)

### WS-0 Coordinator: live verification and engine landing (sequential-only)
- With Docker: `compose up`, `alembic upgrade head`, `pytest -m slow` (users, candidates,
  Postgres search, drift tests). Fix what breaks. Record real output in DEVLOG.
- With a key: one real resolver call and one real JD parse on scripted inputs, logged
  through LoggingTracer; record prompt behaviour notes, not numbers.
- When the engine lands: review it against tests/core/test_engine.py, remove the xfail
  markers (engine and scenarios), run `bench.run --suite smoke` and `--suite v0
  --strategy ripple`, compare resolver_calls with check_everything, write the first
  results/ run that answers "does the ripple strategy pass gold", DEVLOG and roadmap.
- Acceptance: slow suite green somewhere (CI or local); smoke 11/11 once the engine exists.

### WS-9 Scout agent (Phase 3; parallel-ready)
Owns src/ripple/agents/scout.py, src/ripple/domains/jobs/sources/**, tests/agents/test_scout*.py,
tests/domains/jobs_sources/**, docs/adr/0070-0074, docs/learning/scout.md, the cron slot in
src/ripple/worker/jobs.py (`scout_run`) and docs/plans/parallel-execution/ws-9.md.
- Allowed-sources registry (ADR-0008): a YAML registry of sources with terms note,
  robots policy, rate limit and fetch kind (public API, career page with permission,
  forwarded email); fetcher over httpx with per-source rate limiting and ETag caching;
  dedupe by canonical URL and title+company; parse through WS-2's parse_jd; record via
  WS-1's record_opening + derive_for_opening; search criteria read from `criteria`
  memories; re-run when a criteria memory changes (hook in the runner's completion or a
  worker job triggered by the ChangeEvent).
- Tests with httpx.MockTransport and fixture pages; no network. I6 named test: the Scout
  only GETs allowed sources, never POSTs, never logs in.
- Acceptance: scout_run job replaces its NotImplementedError; a fixture career page
  yields recorded openings and recommendations in the digest.

### WS-10 Telegram inbound: the student's channel (Phase 2 exit; parallel-ready)
Owns src/ripple/notify/inbound.py, src/ripple/notify/bot.py, src/ripple/worker/telegram_poll.py,
tests/notify/test_inbound*.py, docs/adr/0075-0079, docs/learning/telegram-bot.md, ws-10.md.
- Long-polling `getUpdates` (no public webhook needed for the pilot VPS) in an arq job
  or a dedicated loop; `/link <code>` → `ripple.storage.users.link_telegram`; any other
  message from a linked chat → ConversationAgent.turn with the user id; pending
  questions rendered with reply keyboards mapping to answers (still_holds /
  no_longer_holds / correction); forwarded placement emails (text) → openings.
- Rate limit per chat; never act on unlinked chats; never send to anyone but the chat
  that wrote (I6).
- Acceptance: a scripted update sequence (link, tell, ask, answer) drives the agent end
  to end offline; the daily digest and alerts already use the same transport.

### WS-11 MCP server (Phase 4, ADR-0006; parallel-ready, small)
Owns src/ripple/mcp_server/**, tests/mcp_server/**, docs/adr/0080-0084, docs/learning/mcp.md,
ws-11.md. Needs the `mcp` dependency: the coordinator adds it with an ADR before launch.
- Tools: search (Retriever), save (Intake), update (Intake.edit), forget, explain
  (parents, latest versions, events for a memory); auth by bearer token mapped to a
  user (reuse ripple.api.auth); invariants enforced at the boundary (I1, I7).
- Acceptance: an MCP client test (in-process) exercises all five tools offline.

### WS-12 Dashboard: memory inspector and map (Phase 2 "inspector page", Phase 4 map; parallel-ready)
Owns apps/web/**, docs/adr/0085-0089, docs/learning/dashboard.md, ws-12.md.
- Next.js + TypeScript strict, API client generated from the FastAPI OpenAPI schema
  (.claude/rules/frontend.md); pages: memories list with flags and colour + text label,
  memory detail (why, history, edit, forget), questions (answer), openings map with
  React Flow (openings, skills, applications as one graph via links); token login.
- Acceptance: `npm run build` and component tests pass offline against a mocked API;
  no business logic in the frontend.

### WS-13 Hardening follow-ups from round 1 (parallel-ready, Tier A)
Owns the files named per item; small, test-first:
- Postgres DeliveryLog (table + migration 0005) and a per-ChangeEvent lease in
  `RippleRunner.resume` (IDEAS 8).
- Atomic candidate confirm (conditional update in CandidateStore).
- Persist uploaded resume text (`resume_uploads` table, migration 0006) so span refs
  resolve; GET /memories/{id} shows the quoted line.
- Eligibility honours CGPA_SCALE (IDEAS 9).
- API: DELETE /me test asserts ChangeEvent erasure against Postgres (slow).
- Acceptance: each item has a test that failed before it.

### WS-14 Phase 4 seed: link-finder training data design (contract-dependent, docs first)
Owns training/**, docs/adr/0090-0094, docs/plans/parallel-execution/ws-14.md.
- From proposal 0002: silver labels from structure, LLM labels for hidden links, the
  300-pair hand-check protocol, split by persona/template, label provenance recorded;
  a generator that emits pairs from RippleBench v0 scenarios without leaking the test
  split (eval-auditor checklist). No model training yet ([human] loop).
- Acceptance: a labelled pair file with provenance and a leakage test.

## Coordination
- Same rules as round 1 (docs/plans/parallel-execution.md): shared checkout, file
  ownership, own-path verification, ADR ranges above, handover files, no commits.
- Run at most five sessions at once: seven hit the account session limit in round 1.
- Coordinator adds dependencies before launch: `mcp` (WS-11), Node toolchain is the
  author's install (WS-12). Contract changes requested in handovers are applied by the
  coordinator at checkpoints C3 (mid-round) and C4 (close), each with the full suite.
- Round 2 closes with the A..G hand-over, roadmap ticks only where acceptance passed,
  and a docs/04 update if the first Ripple numbers exist.

## What this round does not do
- No training of the encoder (needs labelled data first; Phase 4).
- No pilot recruitment; the self-use milestone (2027-02-01) needs WS-0 and WS-10 done.
- No claims: every number quoted comes from a results/ folder (I8).
