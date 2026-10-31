# Roadmap
Design freeze: 2027-02-28. After it, ADRs need an explicit "why now".

## Phase 0 — Foundation (2026-10-20 → 2026-11-08)
- [x] Repo, uv, ruff, pyright, pytest config
- [ ] CI green on GitHub Actions (workflow written 2026-10-19; needs a remote and a push)
- [x] ADRs: observability; ORM + migrations (sync vs async); job queue (Redis vs Postgres-backed)
- [ ] infra/docker-compose.yml: postgres+pgvector, redis (written 2026-10-19; Docker not installed locally, verify there or in CI)
- [x] Alembic set up; initial migration enables pgvector (live upgrade to head verified 2026-10-31 on embedded Postgres 16 + pgvector, ADR-0115)
- [x] llm router skeleton + FakeLLM; FakeClock; tests/fakes
- [x] Author approves ADR-0013, 0014, 0015 (ripple semantics, versioning, triggers)
Exit: CI green; offline tests pass; services start.

## Phase 1 — Core engine (2026-11-09 → 2026-12-31)
- [x] Models + tables + migration (Memory, Link, ChangeEvent, Decision, ForgetEvent); migration 0002 verified offline, live run needs Docker/CI
- [x] Store interface; Postgres and in-memory implementations; tests/builders (Postgres contract tests run in CI)
- [x] Versioning: new row + depends_on link copy in one transaction; mid-update rollback test (ADR-0014)
- [x] [human] Ripple engine: wave iterator over link classes, cycle safety, depth limit (ADR-0013) — implemented 2026-10-31 on the author's request; 10 contract tests pass
- [x] Rule linker (baseline) + LLM linker behind Linker interface
- [x] Change detector (permanent vs temporary): deterministic for structured facts, LLM for prose (ADR-0020)
- [x] Resolver (rule-first chain, ADR-0019) + ask handling; per-wave transactional commit; ChangeEvent per trigger kind (ADR-0015). Ask-user *queue* (listing pending questions) lands with the API in Phase 2
- [x] Expiry sweep (deterministic, FakeClock) and forget API with ForgetEvent cascade
- [x] Invariant tests I1–I4, I7 (tests/core/test_invariants.py, tests/llm/test_invariants_llm.py)
- [x] Scenario tests: 11 YAML scenarios (CGPA change, two consecutive changes, accepted-offer chain, temporary unavailability, ask unanswered/confirmed, snapshot, hidden link, forget, deadline, keep halts) pass against the engine
- [x] Bench smoke suite: runner and results/ writing done (`uv run python -m bench.run --suite smoke`); the ripple strategy runs every scenario (tests/scenarios/test_bench_run.py)
Exit: scenarios pass offline; invariants tested; smoke suite runs.

## Phase 2 — Job-hunt MVP (2027-01-01 → 2027-01-31)
- [x] Jobs adapter: schemas, link types, eligibility rules, fit with cited JD lines (WS-1, ADR-0030..0032; offline tests)
- [x] Resume parsing with confirmation; JD parser with spans (WS-2 parsers + WS-3 candidates flow; offline tests)
- [x] Conversation agent (LangGraph); FastAPI endpoints (WS-4, WS-3; offline tests; live run needs Postgres + key)
- [x] Telegram daily digest (WS-6 digest + worker; offline tests; no real message sent yet)
- [x] Basic memory inspector page (WS-12 dashboard: list, detail, edit incl. valid_to, questions, account; offline tests and static build, checkpoint C3)
Exit: author uses it daily from 2027-02-01.

## Phase 3 — Scout, RAG, first results (2027-02-01–2027-04-30)
- [x] Allowed-sources registry; Scout agent; dedupe; ranking (WS-1 ranking; WS-9 Scout, ADR-0070..0073; daily and criteria-change triggers, ADR-0079; offline fixtures only, every real source ships disabled until its site agrees)
- [x] Validity-aware retrieval + graph expansion + evidence (WS-5, ADR-0050; Postgres path verified only in CI)
- [x] Curator worker + nightly sweep (WS-6 arq jobs + coordinator wiring; Redis path unverified locally)
- [x] RippleBench v0 (jobs, ~30 scenarios) + baselines (2026-10-31: engine built, 82-run seeded grid over v0, news_v1, finance_v1 and smoke with the scripted oracle; docs/results/benchmark.md, ADR-0120..0123; re-run after the first commit for citable numbers)
- [x] [human] Metric functions (implemented by the collaborator at the author's request, 2026-10-31; ADR-0120, 0123)
- [ ] Small pilot (10–15 classmates) with consent
Exit: first results report in results/ answering H1 and H2 at v0 scale.

## Phase 4 — Link finder + RippleBench v1 (2027-05-01 → 2027-07-31)
- [ ] Training data generation; 300 pairs hand-checked (generator, leakage test, hand-check protocol and evaluation harness built in wave B, ADR-0090..0094; the 300 hand labels are the author's; v1 and LLM-labelled pairs still to come)
- [x] [human] Training loop and evaluation (implemented at the author's request, 2026-10-31: ModernBERT-base on CPU, three seeds, rule vs trained on the jobs test split and the finance transfer; docs/results/link-finder.md, ADR-0125..0127. The LLM-linker comparison waits for a valid API key)
- [ ] Serve the model inside the Linker; compare with LLM linker (served: `ripple.linking.trained.TrainedLinker`, selected by RIPPLE_LINKER, wired in the API, ADR-0128/0118; the comparison with the LLM linker (H3) needs a valid key)
- [ ] RippleBench v1: full jobs track + news track; STALE runner (news_v1 and finance_v1 generated and synthetic, ADR-0100..0103; STALE loader only, mapping open; full jobs v1 not started)
- [x] MCP server; React Flow map dashboard (WS-11, WS-12; done early in wave A, integrated at C3; production paths unverified without Postgres)
Exit: link finder report (H3).

## Phase 5 — Main pilot (2027-08-01 → 2027-10-31)
- [ ] Consent form, onboarding, monitoring (consent and onboarding drafts in docs/pilot need department sign-off; monitoring and weekly reports are wave B, WS-16)
- [ ] Weekly pilot reports; corrections fed back to training (feedback capture and the weekly report generator built in wave B, ADR-0105..0107; corrections-to-training not started)
Exit: pilot report.

## Phase 6 — Final evaluation and write-up (2027-11-01–2028-05-31)
- [ ] Finance transfer test (H4); full ablations; final seeded runs (2026-10-31: H4 transfer run, three seeds, not supported on this evidence; offline ablations no_graph and no_ask_user run; model-backed ablations and the committed re-run remain)
- [ ] Paper draft; thesis; demo video; open-source release
Exit: thesis submitted.
