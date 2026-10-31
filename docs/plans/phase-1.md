# Phase 1 plan — Core engine
Written 2026-10-19 under the autonomous mandate. Status: **built on 2026-10-19 except the human-owned engine**; see docs/DEVLOG.md.

## Goal and exit criteria (docs/05-roadmap.md)
Phase 1, 2026-11-09 → 2026-12-31 (started early, 2026-10-19).
Exit: scenarios pass offline; invariants tested; smoke suite runs.

## Starting state
Phase 0 complete except Docker/CI verification. Core has clock, ids, errors; llm has the
Router and FakeLLM; storage has the base and engine factory; migration 0001 enables
pgvector. ADR-0013 (wave-by-wave, two link classes), 0014 (versions as rows, links
copied), 0015 (memory-write trigger, self-expiry) are Accepted and are the spec for
this phase, together with docs/03-data-model.md.

## Ordered tasks

### 1.1 Core models and link policy
Files: src/ripple/core/models.py (Memory, Link, ChangeEvent, Decision, ForgetEvent,
enums Status, LinkClass, DecisionAction, TriggerKind), src/ripple/core/links.py
(LinkPolicy table per class; LinkTypeRegistry that a domain adapter fills: type → class).
Tests: tests/core/test_models.py (validation: aware datetimes, confidence bounds,
version/supersedes consistency), tests/core/test_links.py (policy table, unknown type
rejected). tests/builders for every model.
Acceptance: pyright strict clean; fast tests pass.

### 1.2 Store protocol and in-memory store
Files: src/ripple/core/store.py (async Store protocol: memories, links, change events,
forget events; transactional unit of work), tests/fakes/store.py (InMemoryStore),
tests/core/store_contract.py (shared contract tests parameterised over implementations).
Acceptance: contract tests pass for InMemoryStore.

### 1.3 [human] Ripple engine
Files: src/ripple/core/engine.py: `WaveEngine` with `first_wave(seeds)` and
`next_wave(decisions)`; traversal over depends_on links, visited set, depth limit.
The collaborator writes the class, the docstring contract, the tests
(tests/core/test_engine.py, marked xfail strict until implemented) and
docs/learning/ripple-engine.md; the body raises NotImplementedError with TODO(human).
Acceptance: the author's implementation turns the xfails into passes.

### 1.4 Resolver protocol, rule-first stage, ripple runner
Files: src/ripple/core/resolver.py (Resolver protocol; RuleResolver protocol;
ResolverChain that tries rules then the LLM resolver), src/ripple/core/ripple.py
(RippleRunner: seeds from a write, two commits per wave, ChangeEvent lifecycle with
completed_at, ask → PENDING_USER + subtree SUSPECT, depth limit, I3 by construction).
ADR-0019 records rule-first resolution (proposal 0001).
Tests: runner tests with a scripted engine (so they do not depend on the human task),
FakeClock and InMemoryStore; invariant tests I2 and I3.
Acceptance: fast tests pass.

### 1.5 Versioning, forget, expiry, user answers
Files: src/ripple/core/versioning.py (update = new row + link copy, transactional),
src/ripple/core/forget.py (forget API: whole chain + depends_on cascade + ForgetEvent),
src/ripple/core/sweep.py (expiry of valid_to with trigger_kind=expiry; resume of open
ChangeEvents), src/ripple/core/answers.py (user answer → new ripple or deterministic
restore). Invariant tests I1 (retrieval helper on the Store) and I7.
Acceptance: fast tests pass; FR-5's FakeClock scenario passes once the engine exists.

### 1.6 Linkers
Files: src/ripple/core/linking.py (Linker protocol: propose links for a new memory
against candidates), src/ripple/linking/rules.py (structured subject/attribute match
→ depends_on_fact), src/ripple/linking/llm.py (LLMLinker through the Router; schema
in llm/schemas/links.py; prompt llm/prompts/linker.v1.md).
Tests: rule linker unit tests; LLM linker with FakeLLM; I4 invariant test on the
linker schema path.

### 1.7 Change detector
Files: src/ripple/core/change_detection.py (deterministic: same subject+attribute →
update; valid_to from structured input), src/ripple/llm/schemas/change.py and
prompts/change_detector.v1.md (LLM classification for prose: new | update-of <id> |
temporary-until <date>), src/ripple/linking or agents glue later.
Tests: FakeLLM-driven; temporary classification sets valid_to.

### 1.8 Postgres store
Files: src/ripple/storage/tables.py, src/ripple/storage/postgres.py (PostgresStore),
infra/migrations/versions/0002_core_tables.py. Contract tests run against Postgres
when TEST_DATABASE_URL is set (slow).
Acceptance: slow contract tests pass in CI.

### 1.9 Scenario runner and bench smoke
Files: tests/scenarios/*.yaml (cgpa_change, two_cgpa_changes, accepted_offer,
temporary_unavailability, ask_unanswered_subtree, resume_version_snapshot),
tests/scenarios/runner.py, bench/run.py --suite smoke writing results/<date>_smoke_<sha>/.
Scenario tests are xfail until the human engine exists; the runner itself is tested.

## Decisions recorded in this phase
ADR-0019 rule-first resolution. ADR-0020 change-detection policy (deterministic path
first, LLM for prose). Others as they arise.

## Risks
- The engine is human-owned: every end-to-end scenario waits on it. Everything around
  it is built and tested with a scripted engine so the author's job is one file.
- Postgres store unverifiable locally without Docker; CI covers it.
- No jobs-domain rules yet (Phase 2); RuleResolver has only generic rules (none) in
  Phase 1, so the LLM path is exercised through FakeLLM.
