# Graph Report - RIPPLE  (2026-10-25)

## Corpus Check
- 817 files · ~910,274 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 17 file(s) not represented in the graph (top: (none) 8, .graphify-bak 1, .example 1)

## Summary
- 7277 nodes · 21863 edges · 437 communities (385 shown, 52 thin omitted)
- Extraction: 84% EXTRACTED · 16% INFERRED · 0% AMBIGUOUS · INFERRED: 3474 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- API Test Harness
- Memory
- models.py
- Scenario Benchmarks & Replay
- In-Memory Retrieval & Indexing
- Change Detection & Statement Intake
- API Wiring & LLM Services
- jobs/openings.py
- Conversation & Tailor Agents
- test_jobs.py
- Postgres Store
- Search Backends (Postgres & In-Memory)
- Telegram Notifications
- test_intake.py
- InMemoryStore
- Bench Data Generation
- routers/resume.py
- Scenario Runner & Resolution Specs
- ConfigurationError
- Conversation Agent & Evidence
- FakeClock
- app.py
- Store
- parsers/resume.py
- Service Wiring & LLM Resolver
- pytest
- Store
- FakeLLM
- RetrievedMemory
- docs/04-evaluation.md
- make_runner
- digest.py
- api/schemas.py
- build
- DependencyGraph
- profile.py
- ChangeEvent
- RouterConfig
- InMemoryUserStore
- tools.py
- McpHarness
- anthropic.py
- auth.py
- RippleRunner
- routers/resume.py
- DecisionAction
- Communities (127 total, 41 thin omitted)
- Communities (127 total, 41 thin omitted)
- PostgresSearchBackend
- UserStore
- ._complete_with
- run.py
- users.py
- channel.py
- fakes/clock.py
- fixture
- ParsedOpening
- core/errors.py
- core/errors.py
- MemoryDetailView.tsx
- jobs/test_openings.py
- ResumeCandidate
- test_ranking.py
- helpers.tsx
- parsers/jd.py
- Ripple semantics (wave by wave, two commits per wave)
- api/wiring.py
- LangfuseTracer
- users.py
- TelegramBotApi
- dedupe.py
- json
- context
- edit_memory
- new_id
- CandidateStore
- adapters.py
- test_boundaries.py
- types.ts
- me.py
- test_runner.py
- checkpoints.py
- test_directory.py
- Status
- test_hardening_ratelimit.py
- re
- _require_aware
- fetcher.py
- keyboards.py
- list_recommendations
- StalePendingStore
- git_short_sha
- ripple/__init__.py
- test_migrations_match_table_metadata
- InboundDispatcher
- 0001_initial.py
- bench/__init__.py
- ConfigurationError
- ripple/api/__init__.py
- router.py
- ripple/domains/jobs/__init__.py
- package.json
- test_fetcher.py
- test_scout.py
- ._check
- schemas/__init__.py
- ResumeUpload
- tests/agents/__init__.py
- sources/__init__.py
- worked_trace
- test_telegram_webhook.py
- scenarios/__init__.py
- results_dir
- Parallel execution tracker
- DroppedUpdates
- ScoutCriteria
- tests/domains/__init__.py
- tests/domains/jobs/__init__.py
- AccountView.tsx
- infra/__init__.py
- test_hardening_health.py
- tests/llm/__init__.py
- tests/notify/__init__.py
- test_hardening_logging.py
- llm-router learning doc
- tests/storage/__init__.py
- tests/worker/__init__.py
- ADR-0030: An opening is one anchor memory plus one structured fact per field
- AlertKind
- _require_aware
- ripple.storage PostgresStore, tables and migrations
- test_inbound_telegram_api.py
- Shell
- build_server
- auth.py
- EventSnapshot
- MemoriesView.tsx
- compilerOptions
- Services
- record_opening
- ADR-0009: A trained small model for link finding
- test_migrations_match_table_metadata
- test_migration_0003_matches_users_tables
- Decision: record decisions as ADRs
- SessionProvider.tsx
- identity.py
- http.py
- ADR-0000 template
- ADR-0001 Record decisions as ADRs
- ADR-0002 Job hunting is the primary domain
- ADR-0003 Graph decides scope; LLM decides action
- ADR-0004 PostgreSQL + pgvector
- ADR-0005 LangGraph for agents
- ADR-0006 Expose memory tools over MCP
- ripple
- Learning page: bench strategies, generator, replay harness, metrics
- main
- RobotsPolicy
- DeliveryLog
- CandidateStore
- devDependencies
- test_inbound_render.py
- docs/05-roadmap.md
- Kind
- Workstreams (dependency order, then value)
- Bot
- .search
- test_inbound_ratelimit.py
- schema.d.ts
- open_scout
- reciprocal_rank_fusion
- docs/IDEAS.md and docs/proposals/
- Production plan — build the whole product once, deploy-ready
- 2026-10-23/manifest.json
- graphify-code/manifest.json
- runner.py
- ripple.agents.scout and ripple.domains.jobs.sources: the Scout
- Deploying Ripple (ADR-0029)
- Pilot consent (draft for departmental review)
- Rule-first resolution
- RedisLease
- locate_span
- no-business-logic.test.ts
- ADR-0029: Deployment topology: one VPS, Compose, Caddy TLS, GHCR images, pg_dump backups
- ADR-0086: Dashboard pages, token session in sessionStorage, query-string routing
- ADR-0087: Openings map built from the inspector's `why` links, laid out by kind
- ripple.mcp_server — Ripple's memory as MCP tools
- Operations runbook
- Graph Report - RIPPLE  (2026-10-23)
- Graph Report - RIPPLE  (2026-10-23)
- current_user
- Ripple dashboard (apps/web)
- ADR-0070: Allowed-sources registry: a YAML file validated into Pydantic, terms note required
- ADR-0075: Telegram inbound: a strict subset of the Update type, private chats only, drops counted
- ADR-0080: MCP server on the SDK's low-level `Server`, explicit Pydantic tool schemas, seven tools
- ADR-0081: MCP identity: one bearer token per connection, hashed through ADR-0040, bound per request
- WS-11 handover: MCP server
- .claude/settings.json
- .claude/settings.json
- parse_resume_ref
- .prettierrc.json
- bench/data/jobs_v0/manifest.json
- bench/generate.py
- bench/__init__.py
- bench/metrics.py
- bench/replay.py
- bench/run.py
- bench/scenario.py
- bench/strategies.py
- infra/entrypoint.sh
- infra/migrations/env.py
- infra/migrations/versions/0001_initial.py
- infra/migrations/versions/0002_core_tables.py
- infra/migrations/versions/0003_users.py
- infra/migrations/versions/0004_embeddings.py
- pyproject.toml
- src/ripple/agents/capabilities.py
- src/ripple/agents/conversation.py
- src/ripple/agents/evidence.py
- src/ripple/agents/__init__.py
- src/ripple/agents/tailor.py
- src/ripple/api/adapters.py
- src/ripple/api/admin.py
- src/ripple/api/app.py
- src/ripple/api/auth.py
- src/ripple/api/candidates.py
- src/ripple/api/contracts.py
- src/ripple/api/directory.py
- src/ripple/api/errors.py
- src/ripple/api/__init__.py
- src/ripple/api/routers/__init__.py
- src/ripple/api/routers/me.py
- src/ripple/api/routers/memories.py
- src/ripple/api/routers/openings.py
- src/ripple/api/routers/questions.py
- src/ripple/api/routers/recommendations.py
- src/ripple/api/routers/resume.py
- src/ripple/api/routers/statements.py
- src/ripple/api/schemas.py
- src/ripple/api/services.py
- src/ripple/api/wiring.py
- src/ripple/core/answers.py
- src/ripple/core/change_detection.py
- src/ripple/core/clock.py
- src/ripple/core/engine.py
- src/ripple/core/errors.py
- src/ripple/core/forget.py
- src/ripple/core/ids.py
- src/ripple/core/indexing.py
- src/ripple/core/__init__.py
- src/ripple/core/intake.py
- src/ripple/core/linking.py
- src/ripple/core/links.py
- src/ripple/core/models.py
- src/ripple/core/resolver.py
- src/ripple/core/retrieval_contract.py
- src/ripple/core/ripple.py
- src/ripple/core/store.py
- src/ripple/core/sweep.py
- src/ripple/core/versioning.py
- src/ripple/core/visibility.py
- src/ripple/core/writes.py
- src/ripple/domains/__init__.py
- src/ripple/domains/jobs/beliefs.py
- src/ripple/domains/jobs/derive.py
- src/ripple/domains/jobs/__init__.py
- src/ripple/domains/jobs/openings.py
- src/ripple/domains/jobs/parsers/dates.py
- src/ripple/domains/jobs/parsers/envelope.py
- src/ripple/domains/jobs/parsers/errors.py
- src/ripple/domains/jobs/parsers/__init__.py
- src/ripple/domains/jobs/parsers/jd.py
- src/ripple/domains/jobs/parsers/numbers.py
- src/ripple/domains/jobs/parsers/resume.py
- src/ripple/domains/jobs/parsers/spans.py
- src/ripple/domains/jobs/profile.py
- src/ripple/domains/jobs/ranking.py
- src/ripple/domains/jobs/rules.py
- src/ripple/domains/jobs/schemas.py
- src/ripple/domains/jobs/vocabulary.py
- src/ripple/__init__.py
- src/ripple/linking/__init__.py
- src/ripple/linking/llm.py
- src/ripple/linking/rules.py
- src/ripple/llm/change_detector.py
- src/ripple/llm/client.py
- src/ripple/llm/config.py
- src/ripple/llm/evidence.py
- src/ripple/llm/__init__.py
- src/ripple/llm/prompts/__init__.py
- src/ripple/llm/providers/anthropic.py
- src/ripple/llm/providers/__init__.py
- src/ripple/llm/providers/openai.py
- src/ripple/llm/resolver.py
- src/ripple/llm/router.py
- src/ripple/llm/schemas/change.py
- src/ripple/llm/schemas/conversation.py
- src/ripple/llm/schemas/__init__.py
- bench/data/jobs_v0/manifest.json
- bench/generate.py
- bench/__init__.py
- bench/metrics.py
- bench/replay.py
- bench/run.py
- bench/scenario.py
- bench/strategies.py
- infra/entrypoint.sh
- infra/migrations/env.py
- infra/migrations/versions/0001_initial.py
- infra/migrations/versions/0002_core_tables.py
- infra/migrations/versions/0003_users.py
- infra/migrations/versions/0004_embeddings.py
- pyproject.toml
- src/ripple/agents/capabilities.py
- src/ripple/agents/conversation.py
- src/ripple/agents/evidence.py
- src/ripple/agents/__init__.py
- src/ripple/agents/tailor.py
- src/ripple/api/adapters.py
- src/ripple/api/admin.py
- src/ripple/api/app.py
- src/ripple/api/auth.py
- src/ripple/api/candidates.py
- src/ripple/api/contracts.py
- src/ripple/api/directory.py
- src/ripple/api/errors.py
- src/ripple/api/__init__.py
- src/ripple/api/routers/__init__.py
- src/ripple/api/routers/me.py
- src/ripple/api/routers/memories.py
- src/ripple/api/routers/openings.py
- src/ripple/api/routers/questions.py
- src/ripple/api/routers/recommendations.py
- src/ripple/api/routers/resume.py
- src/ripple/api/routers/statements.py
- src/ripple/api/schemas.py
- src/ripple/api/services.py
- src/ripple/api/wiring.py
- src/ripple/core/answers.py
- src/ripple/core/change_detection.py
- src/ripple/core/clock.py
- src/ripple/core/engine.py
- src/ripple/core/errors.py
- src/ripple/core/forget.py
- src/ripple/core/ids.py
- src/ripple/core/indexing.py
- src/ripple/core/__init__.py
- src/ripple/core/intake.py
- src/ripple/core/linking.py
- src/ripple/core/links.py
- src/ripple/core/models.py
- src/ripple/core/resolver.py
- src/ripple/core/retrieval_contract.py
- src/ripple/core/ripple.py
- src/ripple/core/store.py
- src/ripple/core/sweep.py
- src/ripple/core/versioning.py
- src/ripple/core/visibility.py
- src/ripple/core/writes.py
- src/ripple/domains/__init__.py
- src/ripple/domains/jobs/beliefs.py
- src/ripple/domains/jobs/derive.py
- src/ripple/domains/jobs/__init__.py
- src/ripple/domains/jobs/openings.py
- src/ripple/domains/jobs/parsers/dates.py
- src/ripple/domains/jobs/parsers/envelope.py
- src/ripple/domains/jobs/parsers/errors.py
- src/ripple/domains/jobs/parsers/__init__.py
- src/ripple/domains/jobs/parsers/jd.py
- src/ripple/domains/jobs/parsers/numbers.py
- src/ripple/domains/jobs/parsers/resume.py
- src/ripple/domains/jobs/parsers/spans.py
- src/ripple/domains/jobs/profile.py
- src/ripple/domains/jobs/ranking.py
- src/ripple/domains/jobs/rules.py
- src/ripple/domains/jobs/schemas.py
- src/ripple/domains/jobs/vocabulary.py
- src/ripple/__init__.py
- src/ripple/linking/__init__.py
- src/ripple/linking/llm.py
- src/ripple/linking/rules.py
- src/ripple/llm/change_detector.py
- src/ripple/llm/client.py
- src/ripple/llm/config.py
- src/ripple/llm/evidence.py
- src/ripple/llm/__init__.py
- src/ripple/llm/prompts/__init__.py
- src/ripple/llm/providers/anthropic.py
- src/ripple/llm/providers/__init__.py
- src/ripple/llm/providers/openai.py
- src/ripple/llm/resolver.py
- src/ripple/llm/router.py
- src/ripple/llm/schemas/change.py
- src/ripple/llm/schemas/conversation.py
- src/ripple/llm/schemas/__init__.py
- quote
- .user
- ResizeObserverStub
- hashlib
- serve_stdio
- test_migration_0005_matches_delivery_tables
- backup.sh
- redis_settings_from_env
- onboarding.md
- restore.sh

## God Nodes (most connected - your core abstractions)
1. `FakeClock` - 257 edges
2. `Memory` - 240 edges
3. `InMemoryStore` - 238 edges
4. `Status` - 218 edges
5. `fact()` - 188 edges
6. `FakeLLM` - 175 edges
7. `memory()` - 145 edges
8. `derived()` - 139 edges
9. `link()` - 121 edges
10. `Harness` - 106 edges

## Surprising Connections (you probably didn't know these)
- `Alternatives considered` --references--> `answer_question()`  [INFERRED]
  docs/adr/0076-telegram-dispatcher.md → src/ripple/api/routers/questions.py
- `2. Why it exists` --references--> `Services`  [INFERRED]
  docs/learning/mcp.md → src/ripple/api/services.py
- `WS-10 Telegram inbound: the student's channel (Phase 2 exit; parallel-ready)` --references--> `link_telegram()`  [INFERRED]
  docs/plans/round-2.md → src/ripple/storage/users.py
- `Incidents` --references--> `daily_digest()`  [INFERRED]
  docs/ops/runbook.md → src/ripple/worker/jobs.py
- `Ownership and ADR ranges for wave A` --references--> `scout_run()`  [INFERRED]
  docs/plans/production-plan.md → src/ripple/worker/jobs.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Rule-first resolution chain** — docs_adr_0013_wave_by_wave_ripple_link_classes_resolver, docs_adr_0019_rule_first_resolution_resolverchain, docs_adr_0019_rule_first_resolution_ruleresolver, docs_adr_0019_rule_first_resolution_llm_resolver, docs_adr_0019_rule_first_resolution_jobs_rules [EXTRACTED 1.00]
- **Ripple write, version and wave model decisions** — docs_adr_0007_retire_not_delete_decision, docs_adr_0013_wave_by_wave_ripple_link_classes_decision, docs_adr_0014_memory_versions_copy_links_decision, docs_adr_0015_change_is_memory_write_self_expiry_decision, docs_adr_0030_opening_representation_decision [EXTRACTED 1.00]
- **API boundary user-data lifecycle (identity, inspector, candidates, export/delete)** — docs_adr_0040_identity_bearer_tokens_telegram_link_decision, docs_adr_0042_inspector_endpoints_i1_at_the_boundary_decision, docs_adr_0043_resume_candidates_table_and_confirmation_flow_decision, docs_adr_0044_export_and_delete_dpdp_decision [EXTRACTED 1.00]
- **cutoff_unknown ask-and-reply scenarios** — bench_data_jobs_v0_cutoff_unknown_p0_jay, bench_data_jobs_v0_cutoff_unknown_p1_dev, bench_data_jobs_v0_cutoff_unknown_p2_harsh, bench_data_jobs_v0_cutoff_unknown_p3_esha, bench_data_jobs_v0_cutoff_unknown_p4_bharat [EXTRACTED 1.00]
- **deadline_moved precision scenarios** — bench_data_jobs_v0_deadline_moved_p0_jay, bench_data_jobs_v0_deadline_moved_p1_dev, bench_data_jobs_v0_deadline_moved_p2_harsh, bench_data_jobs_v0_deadline_moved_p3_esha, bench_data_jobs_v0_deadline_moved_p4_bharat [EXTRACTED 1.00]
- **exam_block temporary-validity scenarios** — bench_data_jobs_v0_exam_block_p0_jay, bench_data_jobs_v0_exam_block_p1_dev, bench_data_jobs_v0_exam_block_p2_harsh, bench_data_jobs_v0_exam_block_p3_esha, bench_data_jobs_v0_exam_block_p4_bharat [EXTRACTED 1.00]
- **jobs_v0 scenario fixtures** — bench_data_jobs_v0_accepted_offer__p0_jay_scenario, bench_data_jobs_v0_accepted_offer__p1_dev_scenario, bench_data_jobs_v0_accepted_offer__p2_harsh_scenario, bench_data_jobs_v0_accepted_offer__p3_esha_scenario, bench_data_jobs_v0_accepted_offer__p4_bharat_scenario, bench_data_jobs_v0_cgpa_rise__p0_jay_scenario, bench_data_jobs_v0_cgpa_rise__p1_dev_scenario [EXTRACTED 1.00]
- **Ripple LangGraph agents (Conversation, Scout, Curator, Tailor)** — docs_02_architecture_agent_conversation, docs_02_architecture_agent_scout, docs_02_architecture_agent_curator, docs_02_architecture_agent_tailor [EXTRACTED 1.00]
- **Parallel execution round-one workstreams WS-1..WS-8** — docs_plans_parallel_execution_ws_1_workstream, docs_plans_parallel_execution_ws_2_workstream, docs_plans_parallel_execution_ws_3_workstream, docs_plans_parallel_execution_ws_4_workstream, docs_plans_parallel_execution_ws_5_workstream, docs_plans_parallel_execution_ws_6_workstream, docs_plans_parallel_execution_ws_7_workstream, docs_plans_parallel_execution_ws_8_workstream [EXTRACTED 1.00]
- **resume_update snapshot-family scenarios (5 personas)** — bench_data_jobs_v0_resume_update__p0_jay_scenario, bench_data_jobs_v0_resume_update__p1_dev_scenario, bench_data_jobs_v0_resume_update__p2_harsh_scenario, bench_data_jobs_v0_resume_update__p3_esha_scenario, bench_data_jobs_v0_resume_update__p4_bharat_scenario [EXTRACTED 1.00]
- **Compose app stack: api and worker depend on healthy postgres and redis** — infra_docker_compose_api, infra_docker_compose_worker, infra_docker_compose_postgres, infra_docker_compose_redis [EXTRACTED 1.00]
- **Ripple invariants I1-I8** — claude_invariant_i1, claude_invariant_i2, claude_invariant_i3, claude_invariant_i4, claude_invariant_i5, claude_invariant_i6, claude_invariant_i7, claude_invariant_i8 [EXTRACTED 1.00]
- **Ripple wave protocol: seed set, wave, decision, ChangeEvent** — docs_03_data_model_ripple_semantics, docs_03_data_model_seed_set, docs_03_data_model_wave, docs_03_data_model_decision, docs_03_data_model_changeevent [EXTRACTED 1.00]
- **RippleBench v0 evaluation stack (strategies, generator, replay, metrics)** — docs_adr_0060_baseline_memory_strategies_decision, docs_adr_0061_ripplebench_v0_generator_and_split_decision, docs_adr_0062_ttc_replay_harness_decision, docs_adr_0063_ripplebench_metric_definitions_decision [EXTRACTED 1.00]
- **Temporary unavailability dependency chain (looking, availability, reminder, exams)** — tests_scenarios_temporary_unavailability_looking_fact, tests_scenarios_temporary_unavailability_availability_derived, tests_scenarios_temporary_unavailability_reminder_derived, tests_scenarios_temporary_unavailability_exams_event [EXTRACTED 1.00]
- **Two CGPA changes ripple flow (cgpa, eligibility, ADR-0014 outgoing copies)** — tests_scenarios_two_cgpa_changes_cgpa_fact, tests_scenarios_two_cgpa_changes_eligibility_derived, tests_scenarios_two_cgpa_changes_adr_0014_outgoing_copies, tests_scenarios_two_cgpa_changes_repeated_update_ripple [EXTRACTED 1.00]
- **Scenarios exercising resolver actions and ask/answer lifecycle** — tests_scenarios_ask_confirmed, tests_scenarios_ask_unanswered_subtree, tests_scenarios_keep_stops_propagation, tests_scenarios_accepted_offer_chain [INFERRED 0.75]
- **LLM Router, FakeLLM, provider adapter and config** — docs_adr_0010_llm_router_router, docs_adr_0010_llm_router_fakellm, docs_adr_0027_anthropic_first_provider_adapter_anthropicclient, docs_adr_0027_anthropic_first_provider_adapter_routerconfig, docs_adr_0010_llm_router_invariant_i4 [INFERRED 0.85]
- **Review subagents guarding architecture, code and evaluation** — _claude_agents_architecture_guardian, _claude_agents_code_reviewer, _claude_agents_eval_auditor [INFERRED 0.85]
- **Jobs belief derivation, ranking and digest pipeline** — docs_adr_0031_jobs_rule_resolvers_decision, docs_adr_0032_jobs_ranking_decision, docs_adr_0055_digest_thresholds_and_rendering_decision, docs_adr_0056_worker_idempotency_leases_schedule_decision [INFERRED 0.85]
- **Jobs rule resolvers recompute from the same belief functions** — docs_learning_jobs_adapter_eligibility_rule, docs_learning_jobs_adapter_fit_rule, docs_learning_jobs_adapter_reminder_rule, docs_learning_jobs_adapter_criteria_rule, docs_learning_jobs_adapter_opening_field_rule [INFERRED 0.85]
- **Versioned LLM prompts sharing JSON-schema and data-not-instructions convention** — src_ripple_llm_prompts_change_detector_v1, src_ripple_llm_prompts_conversation_v1, src_ripple_llm_prompts_intent_v1, src_ripple_llm_prompts_jd_parser_v1, src_ripple_llm_prompts_linker_v1, src_ripple_llm_prompts_resolver_v1, src_ripple_llm_prompts_resume_parser_v1, src_ripple_llm_prompts_tailor_v1, src_ripple_llm_prompts_readme [INFERRED 0.85]
- **Core write-to-ripple pipeline** — docs_learning_ripple_runner_and_writes_record_update_memory, docs_learning_ripple_runner_and_writes_write_new_version, docs_learning_ripple_runner_and_writes_ripplerunner, docs_learning_ripple_engine_waveengine, docs_learning_ripple_runner_and_writes_answers_flow, docs_learning_ripple_runner_and_writes_nightly_sweep_core [INFERRED 0.85]

## Communities (437 total, 52 thin omitted)

### Community 0 - "API Test Harness"
Cohesion: 0.03
Nodes (109): candidate_fact(), InMemoryCandidateStore, _rebase_spans(), RecordingOpeningRecorder, ScriptedOpeningParser, ScriptedRecommendations, ScriptedResumeParser, SimpleCandidateStatements (+101 more)

### Community 1 - "Memory"
Cohesion: 0.04
Nodes (37): one_shot_engine(), first_wave(), candidate_to_statement, ChangeDetector, detect_structured_update(), Wave, MemoryIndexer, Intake (+29 more)

### Community 2 - "models.py"
Cohesion: 0.04
Nodes (23): derive_for_opening and derive_criteria, Open problems, Task 1.5 Versioning, forget, expiry, user answers, ScoutAgent, Embedder, ScoutError, SourceCount, SearchBackend (+15 more)

### Community 3 - "Scenario Benchmarks & Replay"
Cohesion: 0.08
Nodes (26): description, not_found(), owned_memory(), edit_memory(), forget_memory(), get_memory(), list_memories(), answer_question() (+18 more)

### Community 4 - "In-Memory Retrieval & Indexing"
Cohesion: 0.06
Nodes (39): Recommendation, RecommendationSource, Thresholds, Transport, UserDirectory, DigestService, Alert, alert_kinds() (+31 more)

### Community 5 - "Change Detection & Statement Intake"
Cohesion: 0.06
Nodes (62): Scenario accepted_offer__p0_jay, Scenario accepted_offer__p1_dev, Scenario accepted_offer__p2_harsh, Scenario accepted_offer__p3_esha, Scenario accepted_offer__p4_bharat, Scenario cgpa_rise__p0_jay, Scenario cgpa_rise__p1_dev, RippleBench jobs_v0 track (+54 more)

### Community 6 - "API Wiring & LLM Services"
Cohesion: 0.04
Nodes (19): ADR-0076: Telegram dispatcher: commands, link flow, keyboards for answers, two-step forget, agent for the rest, Alternatives considered, Consequences, Revisit if, main(), UserDirectoryAdapter, ChatDirectory, ScanningChatDirectory (+11 more)

### Community 7 - "jobs/openings.py"
Cohesion: 0.04
Nodes (45): 7. Exercise, Pure belief computations (eligibility, fit, reminder, criteria), JobsRecommender ranking, wiring.default_adapters integration, InvalidObjectError, VisibleMemory, compute_criteria(), fit_reasons() (+37 more)

### Community 8 - "Conversation & Tailor Agents"
Cohesion: 0.08
Nodes (68): RetrievalPath, HybridRetriever, run(), run(), run(), run(), run(), run() (+60 more)

### Community 9 - "test_jobs.py"
Cohesion: 0.07
Nodes (21): daily_digest(), DeliveryReport, hourly_alerts(), RecordingTransport, SentMessage, FakeRecommendationSource, scripted_runner(), user_with_expiry_and_stranded_ripple() (+13 more)

### Community 10 - "Postgres Store"
Cohesion: 0.11
Nodes (55): Scenario cgpa_rise__p2_harsh, Scenario cgpa_rise__p3_esha, Scenario cgpa_rise__p4_bharat, Scenario cutoff_unknown__p0_jay, Scenario cutoff_unknown__p1_dev, Scenario cutoff_unknown__p2_harsh, Scenario cutoff_unknown__p3_esha, Scenario cutoff_unknown__p4_bharat (+47 more)

### Community 11 - "Search Backends (Postgres & In-Memory)"
Cohesion: 0.07
Nodes (32): jobs_rules() RuleResolver chain (field, eligibility, fit, reminder, criteria), Deterministic rule links for facts recorded later (fit_of, criteria_from), JobsRecommender (RecommendationSource implementation), Tier ordering and company-variety rebuild, One-time Telegram link code (8 hex, 15 min), STATUS_FOR exception-to-HTTP table, Services frozen dataclass, POST /memories/{id}/edit as user_edit via update_memory (+24 more)

### Community 12 - "Telegram Notifications"
Cohesion: 0.13
Nodes (19): TelegramSendError, _ok(), handler(), test_telegram_transport_from_env_reads_the_token(), handler(), test_telegram_transport_from_env_refuses_a_missing_token(), test_telegram_transport_never_logs_token_or_text_at_info_on_any_logger(), test_telegram_transport_posts_send_message_with_chat_id_and_text() (+11 more)

### Community 13 - "test_intake.py"
Cohesion: 0.21
Nodes (18): ChangeClassification, ChangeKind, __init__(), ScriptedDetector, _intake(), __init__(), _proposal(), ScriptedDetector (+10 more)

### Community 14 - "InMemoryStore"
Cohesion: 0.06
Nodes (63): index_memory(), run(), run(), decision(), memory(), test_decision_keep_forbids_new_version_id(), test_decision_update_requires_new_version_id(), test_fact_builder_sets_structured_fields() (+55 more)

### Community 15 - "Bench Data Generation"
Cohesion: 0.09
Nodes (28): check_data(), generate(), Generated, load_jobs_v0(), load_manifest(), main(), make_personas(), ManifestEntry (+20 more)

### Community 16 - "routers/resume.py"
Cohesion: 0.07
Nodes (21): fact_of(), _already(), _claim(), confirm_candidate(), list_candidates(), _pending_candidate(), reject_candidate(), upload_resume() (+13 more)

### Community 17 - "Scenario Runner & Resolution Specs"
Cohesion: 0.10
Nodes (20): load_scenario(), ScenarioRunner, AppendOnlyStrategy, as_runner(), MemoryStrategy, _cgpa_spec(), _scripted(), __init__() (+12 more)

### Community 18 - "ConfigurationError"
Cohesion: 0.19
Nodes (22): test_fake_clock_advance_moves_now(), test_fake_clock_set_jumps_to_moment(), failing_transport(), recommendation(), _service(), test_send_alerts_does_not_record_when_the_transport_fails(), test_send_alerts_does_not_repeat_an_alert_within_the_cooldown(), test_send_alerts_fires_a_deadline_alert_when_the_opening_enters_the_48h_window() (+14 more)

### Community 19 - "Conversation Agent & Evidence"
Cohesion: 0.04
Nodes (31): BM25 in-memory and ts_rank_cd Postgres lexical scoring, ADR-0072: The Scout is a plain loop over injected parts, fetching only through the sources package, Alternatives considered, Consequences, Context, Revisit if, Reciprocal rank fusion (k=60), Capability (+23 more)

### Community 20 - "FakeClock"
Cohesion: 0.05
Nodes (90): God Nodes (most connected - your core abstractions), Suggested Questions, God Nodes (most connected - your core abstractions), Suggested Questions, Status, TriggerKind, NightlySweep, update_memory() (+82 more)

### Community 21 - "app.py"
Cohesion: 0.07
Nodes (12): create_app(), create_production_app(), install_error_handlers(), RequestIdMiddleware, BodySizeLimitMiddleware, counting_receive(), BodyTooLargeError, _content_length() (+4 more)

### Community 22 - "Store"
Cohesion: 0.14
Nodes (12): Decision, create_user(), _postgres_user_store(), resolve_user(), ApiToken, hash_token(), link_telegram(), new_raw_token() (+4 more)

### Community 23 - "parsers/resume.py"
Cohesion: 0.12
Nodes (11): Hand-written deadline normaliser (dates.normalise_deadline), Forwarded email envelope stripping (strip_email_envelope), Model quotes, code locates (locate_span), Regex cross-checks for cgpa_cutoff and deadline, UnparseableResumeError, _candidate(), _coerce(), _dropped() (+3 more)

### Community 24 - "Service Wiring & LLM Resolver"
Cohesion: 0.07
Nodes (18): Suggestion, TailorAgent, TailorSuggestions, LLMOutputInvalidError, LLMLinker, LLMChangeDetector, Message, memories_block() (+10 more)

### Community 25 - "pytest"
Cohesion: 0.07
Nodes (26): TokenBucket, database_url(), job_context_from_env(), test_intent_verdict_rejects_payload_that_does_not_match_the_intent(), test_fake_clock_rejects_naive_datetimes(), advancing_sleeper(), test_token_bucket_default_burst_of_one_never_lets_two_requests_through_at_once(), test_token_bucket_does_not_wait_when_enough_time_has_passed() (+18 more)

### Community 26 - "Store"
Cohesion: 0.04
Nodes (39): build_strategy(), CheckEverythingStrategy, CountingResolver, NewestWinsStrategy, _NoPropagation, RippleStrategy, Decision, answer_no_longer_holds() (+31 more)

### Community 27 - "FakeLLM"
Cohesion: 0.05
Nodes (93): jd_reply(), test_answer_question_answered_meanwhile_replies_instead_of_raising(), test_answer_question_corrected_updates_the_structured_value(), test_answer_question_corrected_writes_a_new_version_and_ripples(), test_answer_question_for_an_unknown_question_writes_nothing(), test_answer_question_no_longer_holds_retires_and_ripples(), test_answer_question_still_holds_restores_the_memory(), test_ask_answers_from_retrieved_evidence_with_citations() (+85 more)

### Community 28 - "RetrievedMemory"
Cohesion: 0.20
Nodes (5): stale_retrieval_rate(), RetrievedMemory, SearchCall, LeakyRetriever, test_stale_retrieval_rate_counts_unflagged_hits_on_gold_stale_rows()

### Community 29 - "docs/04-evaluation.md"
Cohesion: 0.18
Nodes (19): C4 Cost of graph-scoped resolution, Success criteria by May 2028, docs/04-evaluation.md, Baseline: Append-only, Baseline: Check-everything, Baseline: Mem0-style, Baseline: Newest-wins, External benchmark STALE (+11 more)

### Community 30 - "make_runner"
Cohesion: 0.13
Nodes (16): record_profile_fact(), profile(), write(), test_criteria_for_returns_the_valid_criteria_memory_and_ignores_a_questioned_one(), test_event_changed_criteria_is_true_for_a_criteria_derivation_and_false_for_an_opening(), test_scout_records_a_fixture_career_page_as_openings_and_recommendations(), test_scout_reparses_a_filtered_opening_once_the_criteria_change(), test_scout_second_run_counts_duplicates_and_filtered_without_a_model_call() (+8 more)

### Community 31 - "digest.py"
Cohesion: 0.11
Nodes (31): extract_text(), build_pdf(), candidate(), pdf_with_lines(), resume_reply(), router_for(), text_stream(), test_invariant_I4_parsers_reject_output_that_never_matches_the_schema() (+23 more)

### Community 32 - "api/schemas.py"
Cohesion: 0.17
Nodes (28): accepted_offer(), build_scenario(), _cgpa_memory(), cgpa_rise(), cutoff_unknown(), deadline_moved(), exam_block(), forget_cgpa() (+20 more)

### Community 33 - "build"
Cohesion: 0.03
Nodes (78): ReceiveResult, answer_data(), test_channel_answers_the_callback_before_sending_replies(), run(), test_channel_drops_an_update_it_does_not_handle_and_counts_the_reason(), test_channel_failure_is_recorded_in_the_ledger_so_a_retry_is_not_reprocessed(), run(), test_channel_handles_a_text_update_and_sends_the_reply_to_that_chat() (+70 more)

### Community 34 - "DependencyGraph"
Cohesion: 0.10
Nodes (21): tests/fakes FakeLLM and FakeClock, Invariants I1-I8, Scenario tests (YAML timelines), Testing policy, ADR-0002, ADR-0019, ADR-0030, ADR-0031 (+13 more)

### Community 35 - "profile.py"
Cohesion: 0.10
Nodes (30): DependencyGraph, WaveEngine, WaveOutcome, run(), run(), run(), link(), _chain() (+22 more)

### Community 36 - "ChangeEvent"
Cohesion: 0.04
Nodes (15): event_changed_criteria(), ChangeEvent, ChangeEventNotFoundError, MemoryNotFoundError, _event(), _event_row(), _forget_row(), _link() (+7 more)

### Community 37 - "RouterConfig"
Cohesion: 0.11
Nodes (23): DateMatch, _agree(), _coerce(), _cross_check(), _dropped(), _fence_safe(), parse_jd(), _reconcile() (+15 more)

### Community 38 - "InMemoryUserStore"
Cohesion: 0.12
Nodes (17): router_from_settings(), ModelPrice, ModelSpec, RouterConfig, test_models_for_empty_list_raises_configuration_error(), test_models_for_returns_primary_then_fallbacks_in_order(), test_models_for_unknown_task_raises_configuration_error(), RecordingSleeper (+9 more)

### Community 39 - "tools.py"
Cohesion: 0.10
Nodes (35): Decision, 3. How it works, What was built, _mentions(), pending_questions(), PendingQuestion, forget(), Retriever (+27 more)

### Community 40 - "McpHarness"
Cohesion: 0.05
Nodes (49): run(), change_event(), snapshot_link(), write(), error(), McpHarness, out(), TokenHolder (+41 more)

### Community 41 - "anthropic.py"
Cohesion: 0.12
Nodes (19): _data_description(), _display(), git_short_sha(), main(), _report(), run_dir_for(), run_suite(), RunConfig (+11 more)

### Community 42 - "auth.py"
Cohesion: 0.08
Nodes (20): Anthropic provider adapter (forced tool use), CompletionRequest, CompletionResult, LLMClient, AnthropicClient, AnthropicLike, _default_factory(), _Messages (+12 more)

### Community 43 - "RippleRunner"
Cohesion: 0.19
Nodes (18): ADR-0040, ADR-0041, ADR-0042, ADR-0043, ADR-0044, WS-3 handover: API, identity, inspector, confirmation flow, Bearer token identity (ADR-0040), Contract requests: per-user event reads, Intake.edit, per-user event deletion, shared metadata import (+10 more)

### Community 44 - "routers/resume.py"
Cohesion: 0.09
Nodes (17): cosine_similarity(), InMemorySearchBackend, DeterministicFakeEmbedder, BackendIndexer, backend(), dense_seeder(), embedder(), Seeder (+9 more)

### Community 45 - "DecisionAction"
Cohesion: 0.06
Nodes (58): AliasResolver, DecisionAction, Resolution, ResolutionContext, ResolverChain, RuleResolver, compute_eligibility(), compute_fit() (+50 more)

### Community 46 - "Communities (127 total, 41 thin omitted)"
Cohesion: 0.02
Nodes (87): Communities (127 total, 41 thin omitted), Community 0 - "Harness", Community 10 - "PostgresStore", Community 11 - "asyncio", Community 12 - "telegram.py", Community 13 - "test_render.py", Community 14 - "InMemoryStore", Community 15 - "FakeLLM" (+79 more)

### Community 47 - "Communities (127 total, 41 thin omitted)"
Cohesion: 0.02
Nodes (87): Communities (127 total, 41 thin omitted), Community 0 - "API Test Harness", Community 10 - "Postgres Store", Community 11 - "Search Backends (Postgres & In-Memory)", Community 12 - "Telegram Notifications", Community 13 - "Alert Rendering & Digests", Community 14 - "InMemoryStore", Community 15 - "FakeLLM" (+79 more)

### Community 48 - "PostgresSearchBackend"
Cohesion: 0.09
Nodes (9): PostgresSearchBackend, Vector, process(), vector_literal(), _load_migration(), test_migration_0004_chains_after_0003_users(), test_migration_0004_dimension_matches_the_backend_constant(), test_vector_type_binds_sequences_as_the_pgvector_text_literal() (+1 more)

### Community 49 - "UserStore"
Cohesion: 0.20
Nodes (10): ConvergenceRecord, cost_per_ripple(), questions_asked(), time_to_consistency(), TTCReport, ReplayTrace, test_cost_per_ripple_divides_resolver_calls_by_change_events(), test_questions_asked_counts_ask_decisions_across_events() (+2 more)

### Community 50 - "._complete_with"
Cohesion: 0.18
Nodes (3): Completion, _summarise(), _Usage

### Community 51 - "run.py"
Cohesion: 0.11
Nodes (3): _why(), ForgetEvent, StoreReader

### Community 52 - "users.py"
Cohesion: 0.04
Nodes (25): run_migrations_offline(), run_migrations_online(), _run_sync(), _url(), upgrade(), upgrade(), upgrade(), upgrade() (+17 more)

### Community 53 - "channel.py"
Cohesion: 0.05
Nodes (21): ChannelStats, TelegramChannel, _update_id(), Conversation, InMemoryUpdateLedger, UpdateLedger, InMemoryRateLimiter, RateLimiter (+13 more)

### Community 54 - "fakes/clock.py"
Cohesion: 0.21
Nodes (21): derive_for_opening(), run(), _parent_ids(), _setup(), test_derive_criteria_from_profile_facts_links_criteria_from(), test_derive_criteria_is_none_for_an_empty_profile(), test_derive_each_belief_opens_its_own_completed_change_event(), test_derive_eligibility_is_false_when_cgpa_is_below_the_cutoff() (+13 more)

### Community 55 - "fixture"
Cohesion: 0.07
Nodes (39): What was built, Candidate, _collect_text(), _descendants(), _Element, extract_candidates(), _first_href(), html_candidates() (+31 more)

### Community 56 - "ParsedOpening"
Cohesion: 0.19
Nodes (3): OpeningWritten, ParsedOpening, test_scout_criteria_admits_by_cutoff_and_batch_and_passes_a_silent_jd()

### Community 57 - "core/errors.py"
Cohesion: 0.08
Nodes (23): Core import boundary test (ast allowlist), Injected Clock protocol (FakeClock, SystemClock), Learning page: ripple.core foundations (clock, ids, errors, boundaries), OpeningUnparseableError, ResumeUnparseableError, LLMUnavailableError, RippleError, _cascade() (+15 more)

### Community 58 - "core/errors.py"
Cohesion: 0.25
Nodes (24): OpeningAttribute, jd_reply(), _field(), _parse(), test_parse_jd_adds_deadline_from_regex_when_model_missed_it(), test_parse_jd_builds_summary_from_title_and_company_not_from_the_model(), test_parse_jd_coerces_cutoff_to_float_and_batch_to_int(), test_parse_jd_does_not_take_a_date_from_the_next_sentence_as_deadline() (+16 more)

### Community 59 - "MemoryDetailView.tsx"
Cohesion: 0.10
Nodes (49): AnswerOut, ChangeEvent, Link, Memory, MemoryStatus, QuestionOut, Empty(), ErrorBox() (+41 more)

### Community 60 - "jobs/test_openings.py"
Cohesion: 0.18
Nodes (17): field(), parsed_acme(), span(), _record(), test_opening_view_ignores_retired_fields(), test_opening_view_reads_typed_values_from_the_field_facts(), test_record_opening_accepts_the_same_source_again_once_the_first_is_retired(), test_record_opening_anchor_carries_a_stable_opening_key() (+9 more)

### Community 61 - "ResumeCandidate"
Cohesion: 0.10
Nodes (20): architecture-guardian subagent, code-reviewer subagent, eval-auditor subagent, adr skill, explain skill, plan-phase skill, session-end skill, ADR requirement policy (+12 more)

### Community 62 - "test_ranking.py"
Cohesion: 0.15
Nodes (8): ActionLayer, _company_of(), _deadline_of(), memories_below(), _memory_snapshot(), snapshot_after_event(), _state(), StubActionLayer

### Community 63 - "helpers.tsx"
Cohesion: 0.11
Nodes (40): ApiError, ClientOptions, request(), encodeQuery(), messageFor(), Query, readDetail(), ADR-0029 (+32 more)

### Community 64 - "parsers/jd.py"
Cohesion: 0.14
Nodes (22): ADR-0014, ADR-0026, ADR-0050, ripple.retrieval hybrid search, graph expansion, I1 filtering, Graph expansion along depends_on and snapshot_of, index_memory and DeterministicFakeEmbedder, InMemorySearchBackend (BM25, cosine), Migration 0004_embeddings (HNSW, GIN) (+14 more)

### Community 65 - "Ripple semantics (wave by wave, two commits per wave)"
Cohesion: 0.20
Nodes (10): FR-7 Ask the user, NFR-4 Reliability, Principle: graph decides scope, LLM decides action; core domain-agnostic, Decision record (keep|update|retire|ask), Invariant I3: deterministic scope; engine never calls an LLM, Ripple semantics (wave by wave, two commits per wave), Wave (set of dependents resolved together), Worked example: cgpa 7.6 -> 7.9 ripple (+2 more)

### Community 66 - "api/wiring.py"
Cohesion: 0.09
Nodes (21): Contract change requests (coordinator), OpeningParserAdapter, OpeningRecorderAdapter, ResumeParserAdapter, configure_logging(), RateLimiter, app_from_env(), build_services() (+13 more)

### Community 67 - "LangfuseTracer"
Cohesion: 0.07
Nodes (16): ADR-0028: Langfuse tracer implemented now behind the Tracer protocol, Alternatives considered, Consequences, Context, Decision, Revisit if, LangfuseLike, LangfuseObservationLike (+8 more)

### Community 68 - "users.py"
Cohesion: 0.08
Nodes (23): accepted_offer, cgpa_rise, cutoff_unknown, deadline_moved, exam_block, forget_cgpa, resume_update, data_sha256 (+15 more)

### Community 69 - "TelegramBotApi"
Cohesion: 0.07
Nodes (15): Plan (written before implementation, CLAUDE.md "How we work" step 2), WS-10 handover: Telegram inbound channel, MessageReceipt, MessageTooLongError, TelegramCallError, register(), _mapping(), _optional_int() (+7 more)

### Community 70 - "dedupe.py"
Cohesion: 0.07
Nodes (23): Decision, 3. How it works, _candidate_url(), _not_a_jd_key(), canonical_url(), fingerprint(), _is_tracking(), _normalise() (+15 more)

### Community 71 - "json"
Cohesion: 0.11
Nodes (21): graphify skill pointer (/graphify), apps/web dashboard, ADR-0016 SQLAlchemy 2 async + Alembic, ADR-0017 arq on Redis job queue, ADR-0018 Langfuse over OpenTelemetry, Code map, Project commands, graphify knowledge-graph usage rules (+13 more)

### Community 72 - "context"
Cohesion: 0.07
Nodes (35): Coordinator actions requested, scout_lease_key(), JobFailedForUsersError, nightly_sweep(), scout_run(), SweepReport, InMemoryLease, leased() (+27 more)

### Community 73 - "edit_memory"
Cohesion: 0.27
Nodes (15): Board, test_recommender_does_not_spread_openings_without_a_company_as_one_employer(), test_recommender_fills_title_company_deadline_and_cited_fit_reasons(), test_recommender_flags_an_opening_whose_belief_or_field_is_suspect_or_pending(), test_recommender_is_not_flagged_by_a_belief_it_does_not_use(), test_recommender_keeps_a_flagged_deadline_for_ordering_and_display(), test_recommender_leaves_out_openings_whose_deadline_has_passed(), test_recommender_never_returns_an_opening_whose_anchor_is_retired() (+7 more)

### Community 74 - "new_id"
Cohesion: 0.17
Nodes (21): ADR-0025, ADR-0055, ADR-0056, ripple.worker and ripple.notify scheduled jobs, digest and alerts, DigestService.send_daily and send_alerts, Lease (InMemoryLease, RedisLease), Transport, UserDirectory, DeliveryLog, Thresholds, render_digest, alert_kinds, render_alert (+13 more)

### Community 75 - "CandidateStore"
Cohesion: 0.19
Nodes (24): docs/02-architecture.md, Conversation agent, Curator agent, Scout agent, Tailor agent, How core stays domain-agnostic: link classes + Linker/Resolver protocols, Deployment: Docker Compose on one VPS, Read flow (+16 more)

### Community 76 - "adapters.py"
Cohesion: 0.10
Nodes (13): CandidateStatementsAdapter, candidate_from_fact(), CandidateStatements, ResumeParse, Statement, candidate_to_statement(), statement_from_candidate(), CandidateFact (+5 more)

### Community 77 - "test_boundaries.py"
Cohesion: 0.17
Nodes (12): find_dates(), _moment_of(), normalise_deadline(), _zone_of(), test_find_dates_does_not_read_a_word_starting_with_am_as_a_time(), test_find_dates_ignores_version_numbers_and_stray_numbers(), test_find_dates_keeps_source_offsets(), test_normalise_deadline_keeps_the_date_when_the_time_is_impossible() (+4 more)

### Community 78 - "types.ts"
Cohesion: 0.05
Nodes (34): RippleApi, AnswerIn, Decision, EditIn, ExportOut, ForgetEvent, ForgetOut, HistoryOut (+26 more)

### Community 79 - "me.py"
Cohesion: 0.22
Nodes (16): ChangeEvent, DPDP Act, Forget API, Invariant I7: forget cascades along dependency links, depends_on link class, Domain-adapter link-type mapping, Invariant I1: retrieval flags SUSPECT memories, Invariant I3: engine never calls an LLM (+8 more)

### Community 80 - "test_runner.py"
Cohesion: 0.16
Nodes (15): strip_email_envelope, _cut_disclaimer(), _cut_signature(), _drop_headers(), strip_email_envelope(), test_strip_email_envelope_cuts_a_signature_followed_by_a_long_disclaimer(), test_strip_email_envelope_cuts_disclaimer_and_closing(), test_strip_email_envelope_keeps_a_date_line_inside_the_jd_body() (+7 more)

### Community 81 - "checkpoints.py"
Cohesion: 0.18
Nodes (6): GoldState, MemorySnapshot, VersionState, _mem(), test_gold_state_reports_each_mismatch_with_the_runner_wording(), test_trace_records_recommendations_with_the_beliefs_they_rest_on()

### Community 82 - "test_directory.py"
Cohesion: 0.16
Nodes (19): docs/01-requirements.md, FR-10 Conversation (validity-aware RAG), FR-11 Tailor, FR-12 Memory inspector, FR-15 Export and delete all user data, FR-1 Profile setup from resume, FR-2 Openings intake with source spans, FR-3 Application tracking (+11 more)

### Community 83 - "Status"
Cohesion: 0.15
Nodes (19): FakeLLM, Invariant I4: LLM outputs schema-validated by Router, Pydantic schema validation, ripple.llm.Router, Langfuse, OpenTelemetry, Structured stdlib logging, BGE-M3 (+11 more)

### Community 84 - "test_hardening_ratelimit.py"
Cohesion: 0.08
Nodes (18): Bucket, InMemoryRateLimiter, RateDecision, RateLimitGuard, RateLimits, RedisRateLimiter, _refill(), _guarded() (+10 more)

### Community 85 - "re"
Cohesion: 0.25
Nodes (15): Seed set, docs/DEVLOG.md, Devlog 2026-10-19 Phase 0 kickoff session, Devlog 2026-10-19 Parallel round 1: seven workstreams, Devlog 2026-10-19 Phase 0 tasks 0.1-0.7 built, Devlog 2026-10-19 Phase 1 built under autonomous mandate, Devlog 2026-10-19 Phase 0 project definition, WS-1 Jobs adapter (+7 more)

### Community 86 - "_require_aware"
Cohesion: 0.19
Nodes (6): create_telegram_link_code(), delete_me(), export_me(), get_me(), ExportOut, MeOut

### Community 87 - "fetcher.py"
Cohesion: 0.08
Nodes (7): CachedPage, FetchCache, InMemoryFetchCache, FetchResult, SourceFetcher, SourceSpec, open_fetcher()

### Community 88 - "keyboards.py"
Cohesion: 0.08
Nodes (20): NotifyError, BotSender, CallbackDataError, AnswerAction, Button, decode_callback(), forget_data(), forget_keyboard() (+12 more)

### Community 89 - "list_recommendations"
Cohesion: 0.12
Nodes (30): ADR-0003, ADR-0007, ADR-0013, ADR-0015, ripple.core.engine the ripple engine, DependencyGraph.from_links, WaveEngine.first_wave, WaveEngine.next_wave (+22 more)

### Community 90 - "StalePendingStore"
Cohesion: 0.25
Nodes (15): ADR-0011, Phase 0 plan: Foundation, Architecture-guardian review (two passes), Deferred: embeddings (Phase 3), checkpointer (Phase 2), resume PDF parser (Phase 2), Phase 0 exit: CI green, offline tests pass, services start, Risk: no Docker locally, Risk: repo inside OneDrive, Task 0.1 Project skeleton and tooling (+7 more)

### Community 91 - "git_short_sha"
Cohesion: 0.15
Nodes (14): pyright, pytest, Python 3.12+, ruff, uv, Memory version row (supersedes_id), Alembic, psycopg 3 (+6 more)

### Community 92 - "ripple/__init__.py"
Cohesion: 0.21
Nodes (17): ADR-0060, ADR-0061, ADR-0062, ADR-0063, bench learning doc, WS-7 handover: bench, baselines, RippleBench v0, metrics, TTC harness, Baseline results table, Baseline memory strategies (ADR-0060) (+9 more)

### Community 93 - "test_migrations_match_table_metadata"
Cohesion: 0.13
Nodes (22): docs/00-vision.md, C1 Learned dependency induction, C2 Action-level evaluation, Domain scope: jobs primary, news secondary, finance generalization, What Ripple does not claim, Ripple (system), Problem: agents act on stale dependent knowledge, Thesis: explicit dependencies; code decides WHICH, LLM decides HOW (+14 more)

### Community 94 - "InboundDispatcher"
Cohesion: 0.14
Nodes (13): Decision, CallbackAck, InboundDispatcher, looks_like_opening(), Outcome, parse_command(), _Pending, Reply (+5 more)

### Community 95 - "0001_initial.py"
Cohesion: 0.27
Nodes (9): _clock_reads(), _core_sources(), _imported_modules(), _is_allowed(), test_boundary_check_detects_a_forbidden_import(), test_clock_check_allows_injected_clock(), test_clock_check_detects_disguised_now_calls(), test_core_never_reads_the_wall_clock_outside_clock_module() (+1 more)

### Community 96 - "bench/__init__.py"
Cohesion: 0.23
Nodes (9): rules_runner(), _profile_and_opening(), test_a_skill_learned_later_reaches_fit_and_criteria_through_rule_links(), test_an_unrelated_skill_gets_no_fit_link(), test_closing_an_opening_retires_its_fields_and_beliefs_without_the_fallback(), close(), test_inspector_edit_of_the_anchor_keeps_fields_and_beliefs_attached(), test_record_opening_wave_one_keeps_every_field_without_the_fallback() (+1 more)

### Community 97 - "ConfigurationError"
Cohesion: 0.11
Nodes (19): Surprising Connections (you probably didn't know these), Surprising Connections (you probably didn't know these), SystemClock, ConfigurationError, build_parser(), _default_api(), main(), test_system_clock_returns_aware_utc() (+11 more)

### Community 98 - "ripple/api/__init__.py"
Cohesion: 0.19
Nodes (28): forget_cgpa scenario (p4_bharat, forget family), resume_update scenario (p0_jay, snapshot family), resume_update scenario (p1_dev, snapshot family), resume_update scenario (p2_harsh, snapshot family), resume_update scenario (p3_esha, snapshot family), resume_update scenario (p4_bharat, snapshot family), FR-16 Link verification, docs/03-data-model.md (+20 more)

### Community 99 - "router.py"
Cohesion: 0.09
Nodes (23): ADR-0045, ADR-0046, Tracing spans per LLM attempt, HybridRetriever.search, C2 Retrieval contract, C4 Router, prompts loader, FakeLLM, WS-4 handover: Conversation and Tailor agents, Evidence blocks with retrieval flag (+15 more)

### Community 100 - "ripple/domains/jobs/__init__.py"
Cohesion: 0.18
Nodes (4): memory_saver(), postgres_saver(), test_memory_saver_is_a_fresh_checkpointer_each_time(), test_postgres_saver_is_an_async_context_manager_that_does_not_connect_on_creation()

### Community 101 - "package.json"
Cohesion: 0.05
Nodes (36): config, dependencies, next, react, react-dom, @xyflow/react, engines, node (+28 more)

### Community 102 - "test_fetcher.py"
Cohesion: 0.16
Nodes (28): FetchFailedError, FetchRefusedError, acme_routes(), client(), fetcher(), _fetch(), test_fetch_result_decodes_the_charset_from_the_content_type(), test_fetcher_canonicalises_the_url_it_requests() (+20 more)

### Community 103 - "test_scout.py"
Cohesion: 0.12
Nodes (22): scout(), test_invariant_I5_scout_records_only_parsed_fields_with_spans_into_the_page_text(), test_invariant_I6_scout_only_gets_allowed_sources(), test_scout_caps_the_candidates_parsed_per_source(), test_scout_counts_a_failing_source_and_continues_with_the_next(), test_scout_does_not_fetch_a_disabled_source(), test_scout_openings_reach_the_daily_digest(), test_scout_reads_a_public_api_source_and_identifies_items_without_a_url_by_their_text() (+14 more)

### Community 104 - "._check"
Cohesion: 0.24
Nodes (6): FakeUserDirectory, _imports(), _sources(), test_i6_checker_detects_a_foreign_url_and_a_forbidden_import(), test_invariant_I6_worker_and_notify_never_act_on_external_sites(), _url_literals()

### Community 105 - "schemas/__init__.py"
Cohesion: 0.21
Nodes (8): availability derived memory (available for interviews; v2 on exams, v3 after expiry), exams temporary fact (busy with exams, valid_to_days 30), looking fact memory (actively looking for internships, v1 stays VALID), reminder derived memory (Globex interview slot; resolution keep), Scenario: temporary unavailability (temporary fact ripples in, expires, ripples out, no permanent change), cgpa fact memory (7.6 -> 7.9 -> 8.1, v3 at end), eligibility derived memory (not eligible for Acme; v2 then v3 VALID), Scenario: two CGPA changes (second change must reach already-updated eligibility)

### Community 106 - "ResumeUpload"
Cohesion: 0.09
Nodes (10): InMemoryUploadStore, PostgresUploadStore, ResumeUpload, UploadStore, test_resume_upload_refuses_naive_timestamps_and_oversized_text(), TestInMemoryUploadStore, upload(), UploadStoreContract (+2 more)

### Community 107 - "tests/agents/__init__.py"
Cohesion: 0.18
Nodes (22): ADR-0024, ADR-0035, ripple.domains.jobs.parsers resume and JD parsers, find_dates and normalise_deadline, extract_text via pypdf, spans.locate_span, cgpa_value and graduation_year, parse_jd with span-checked extraction (+14 more)

### Community 108 - "sources/__init__.py"
Cohesion: 0.13
Nodes (23): Decision, load_registry(), parse_registry(), registry_from_env(), SourceKind, SourceRegistry, SourceRegistryError, forwarded_email() (+15 more)

### Community 109 - "worked_trace"
Cohesion: 0.18
Nodes (11): correct_updates(), stale_kept(), target_outcomes(), TargetOutcome, wrongful_changes(), test_correct_updates_counts_should_change_targets_that_match_gold(), test_stale_kept_counts_should_change_targets_that_did_not_move(), test_target_outcomes_flattens_every_event_target_pair_in_order() (+3 more)

### Community 110 - "test_telegram_webhook.py"
Cohesion: 0.09
Nodes (22): install_telegram_webhook(), receive_update(), TelegramWebhook, _webhook_of(), webhook_secret_from_env(), test_install_telegram_webhook_twice_mounts_the_route_once(), test_telegram_webhook_answers_200_for_a_body_that_is_not_json(), test_telegram_webhook_answers_200_when_processing_times_out() (+14 more)

### Community 111 - "scenarios/__init__.py"
Cohesion: 0.21
Nodes (15): ADR-0017, ADR-0022, Deployment, CI and observability (WS-8), Bench smoke step informational in CI, CI pipeline: checks, services, image jobs, Docker compose with app profile, Single container image for api or worker, Migrate on container start (+7 more)

### Community 112 - "results_dir"
Cohesion: 0.39
Nodes (6): Bench smoke suite, eval-auditor, Invariant I8: results traceable to files with config and commit, results/ directory, PyYAML (safe_load), Scenario YAML files (tests/scenarios)

### Community 113 - "Parallel execution tracker"
Cohesion: 0.17
Nodes (25): Parallel execution tracker, C1 Jobs vocabulary contract, C3 Core engine/Store/Intake/Resolver/Linker protocols, Checkpoint C0 baseline (160 passed), Checkpoint C1 combined checkout (566 passed), Checkpoint C2 closed (818 passed), Checkpoint C2 partial (610 passed), File-ownership isolation (no commits, no worktrees) (+17 more)

### Community 114 - "DroppedUpdates"
Cohesion: 0.13
Nodes (22): _callback(), DroppedUpdates, parse_update(), TelegramCallbackQuery, TelegramChat, TelegramMessage, TelegramUpdate, TelegramUser (+14 more)

### Community 115 - "ScoutCriteria"
Cohesion: 0.08
Nodes (13): Decision, criteria_for(), EnqueueingScoutTrigger, _filtered_key(), ImmediateScoutTrigger, ScoutCriteria, ScoutTrigger, ScoutReport (+5 more)

### Community 116 - "tests/domains/__init__.py"
Cohesion: 0.25
Nodes (9): Invariant I6: agent never submits applications, robots.txt and rate-limit compliance, Scout, Source registry, Nightly sweep (Curator), arq, Job idempotency, Redis 7.4 (+1 more)

### Community 117 - "tests/domains/jobs/__init__.py"
Cohesion: 0.33
Nodes (11): ADR-0009, ADR-0020, Linkers, change detection and intake, Two-stage change detection, Intake.ingest flow, Linker.propose and proposals_to_links, LLM change detector (prose), LLMLinker (prompt linker.v1) (+3 more)

### Community 118 - "AccountView.tsx"
Cohesion: 0.12
Nodes (24): LoginPage(), useApi(), useSession(), ConfirmDialog(), cancel(), ConfirmDialogProps, AccountView(), DELETE_PHRASE (+16 more)

### Community 119 - "infra/__init__.py"
Cohesion: 0.29
Nodes (8): API layer, FastAPI, httpx, python-multipart, uvicorn, Digest renderer, Telegram Bot API, Transport protocol

### Community 120 - "test_hardening_health.py"
Cohesion: 0.11
Nodes (17): healthz(), postgres_probe(), probe(), Readiness, readyz(), redis_probe(), _app(), _broken() (+9 more)

### Community 121 - "tests/llm/__init__.py"
Cohesion: 0.33
Nodes (8): _assert_only_parent_values(), _parents(), _seed(), test_invariant_I1_recommender_never_returns_retired_and_flags_suspect_or_pending(), test_invariant_I5_derived_beliefs_cite_only_values_held_by_their_parents(), test_invariant_I5_rule_updates_cite_only_values_held_by_their_parents(), test_invariant_I5_the_adapter_never_writes_a_profile_fact_on_its_own(), test_jobs_rules_cgpa_change_never_calls_the_fallback()

### Community 122 - "tests/notify/__init__.py"
Cohesion: 0.38
Nodes (8): _scripted(), __init__(), _spec(), test_runner_forget_and_deleted_expectation(), test_runner_records_a_snapshot_after_seeding_and_after_every_event(), test_runner_rejects_an_unknown_strategy(), test_runner_reports_a_wrong_expectation_with_detail(), test_runner_reports_passing_expectations()

### Community 123 - "test_hardening_logging.py"
Cohesion: 0.08
Nodes (20): accept_trace_id(), bind_trace_id(), current_trace_id(), _header(), JsonFormatter, logging_config(), new_trace_id(), reset_trace_id() (+12 more)

### Community 124 - "llm-router learning doc"
Cohesion: 0.14
Nodes (19): config/llm.default.toml, NFR-1 Offline tests, ADR-0010, ADR-0018, ADR-0027, ripple.llm provider adapter, transport retries, prices, tracing, RouterConfig.from_toml and prices, Tracer protocol (Noop, Logging, planned Langfuse) (+11 more)

### Community 125 - "tests/storage/__init__.py"
Cohesion: 0.39
Nodes (8): Resolver, Ablation: without rules, Invariant I2: every decision cites evidence, Jobs domain rules, LLM resolver, ResolverChain (ripple.core.resolver), RuleResolver, OpeningFieldRule (ADR-0031)

### Community 126 - "tests/worker/__init__.py"
Cohesion: 0.28
Nodes (7): valid_to field, ripple.llm.change_detector (prompt change_detector.v1), ripple.core.intake, Pending candidate facts, Invariant I5: nothing stored without confirmation, pypdf, ripple.llm.schemas.resume

### Community 127 - "ADR-0030: An opening is one anchor memory plus one structured fact per field"
Cohesion: 0.44
Nodes (8): Opening anchor memory, depends_on_fact link type, Opening field fact, InvalidObjectError, Stable opening key, OpeningAlreadyRecordedError, ParsedOpening (contract C1), record_opening

### Community 128 - "AlertKind"
Cohesion: 0.12
Nodes (8): AlertKind, _day_start(), InMemoryDeliveryLog, PostgresDeliveryLog, test_digest_day_is_a_date_not_a_datetime(), TestInMemoryDeliveryLog, test_delivery_log_survives_a_new_instance_over_the_same_database(), TestPostgresDeliveryLog

### Community 130 - "ripple.storage PostgresStore, tables and migrations"
Cohesion: 0.33
Nodes (9): ADR-0004, ADR-0016, ripple.storage PostgresStore, tables and migrations, Migration 0002 and drift test, PostgresStore and PostgresTransaction, Shared Store contract tests (in-memory and Postgres), Four sa.Tables (memories, links, events), version_chain walk (+1 more)

### Community 131 - "test_inbound_telegram_api.py"
Cohesion: 0.15
Nodes (16): api(), Recorder, test_bot_api_answer_callback_query_posts_the_id_and_truncated_text(), test_bot_api_get_updates_posts_offset_timeout_and_allowed_updates(), test_bot_api_get_updates_rejects_a_result_that_is_not_a_list(), test_bot_api_get_updates_without_an_offset_omits_it(), test_bot_api_raises_call_error_with_method_and_description_never_the_token(), test_bot_api_rejects_non_json_and_non_object_bodies() (+8 more)

### Community 132 - "Shell"
Cohesion: 0.12
Nodes (18): nextConfig, ADR-0029, ADR-0086, AccountPage(), MapPage(), DetailFromQuery(), MemoryDetailPage(), ADR-0086 (+10 more)

### Community 133 - "build_server"
Cohesion: 0.11
Nodes (8): current_user(), build_server(), call_tool(), _describe(), _failure(), _success(), not_found(), ToolCallError

### Community 134 - "auth.py"
Cohesion: 0.08
Nodes (9): _unauthorized(), post_opening(), list_recommendations(), post_statement(), OpeningIn, OpeningOut, ParsedFieldOut, RecommendationOut (+1 more)

### Community 135 - "EventSnapshot"
Cohesion: 0.25
Nodes (5): stale_recommendation_rate(), EventSnapshot, RecommendationSnapshot, _event(), test_stale_recommendation_rate_counts_unflagged_recommendations_on_stale_beliefs()

### Community 136 - "MemoriesView.tsx"
Cohesion: 0.11
Nodes (22): MemoryOut, ParentOut, VisibleStatus, KINDS, KnownKind, SKILL_ATTRIBUTE, buildGraph(), addNode() (+14 more)

### Community 137 - "compilerOptions"
Cohesion: 0.08
Nodes (23): compilerOptions, allowJs, esModuleInterop, exactOptionalPropertyTypes, incremental, isolatedModules, jsx, lib (+15 more)

### Community 138 - "Services"
Cohesion: 0.12
Nodes (15): Context, ADR-0082: MCP transports: stdio for local clients, stateless streamable HTTP for the VPS, one wiring, Alternatives considered, Consequences, Context, Decision, Revisit if, OpeningParser (+7 more)

### Community 140 - "record_opening"
Cohesion: 0.15
Nodes (17): ADR-0071: Scout dedupe by canonical URL, then (company, title) fingerprint, with a seen ledger, Alternatives considered, Consequences, Context, Revisit if, record_opening(), scout_source_ref(), _dedupe() (+9 more)

### Community 141 - "ADR-0009: A trained small model for link finding"
Cohesion: 0.67
Nodes (3): Hypothesis H3 (trained linker quality), Linker interface (rules, LLM, trained), ModernBERT / DeBERTa-v3 pair classifier

### Community 145 - "Decision: record decisions as ADRs"
Cohesion: 0.67
Nodes (3): Design freeze 2027-02-28, ADR template (Context, Decision, Alternatives, Consequences, Revisit if), Decision: record decisions as ADRs

### Community 146 - "SessionProvider.tsx"
Cohesion: 0.17
Nodes (15): createClient(), API_BASE_URL, metadata, RootLayout(), noSubscription(), SessionContext, SessionProvider(), ADR-0086 (+7 more)

### Community 147 - "identity.py"
Cohesion: 0.12
Nodes (3): BearerIdentity, env_token_source(), header_token_source()

### Community 155 - "http.py"
Cohesion: 0.09
Nodes (3): BearerGate, streamable_http_app(), bearer_token()

### Community 182 - "Learning page: bench strategies, generator, replay harness, metrics"
Cohesion: 0.17
Nodes (16): append_only and newest_wins baselines, check_everything baseline (one-shot all-VALID wave), manifest.json persona/template split with sha256, Seven gold-behaviour template families, stale_retrieval_rate and stale_recommendation_rate, time_to_consistency metric, correct_updates, stale_kept, wrongful_changes, AliasResolver trigger-scoped scripted oracle (+8 more)

### Community 183 - "main"
Cohesion: 0.15
Nodes (8): main(), serve_http(), McpSettings, _fakes(), test_main_serves_http_from_flags_over_environment(), test_main_serves_stdio_only_with_a_token_in_the_environment(), test_settings_default_to_stdio_on_loopback(), test_settings_read_the_environment_and_name_a_bad_value()

### Community 184 - "RobotsPolicy"
Cohesion: 0.21
Nodes (8): RobotsPolicy, ScriptedRobots, test_robots_policy_allows_everything_when_robots_txt_is_missing(), test_robots_policy_applies_rules_for_a_named_agent(), test_robots_policy_closes_the_host_when_robots_txt_cannot_be_read(), test_robots_policy_fetches_robots_txt_once_per_host_per_run(), test_robots_policy_reads_the_crawl_delay_for_our_agent(), test_robots_policy_refuses_a_disallowed_path_and_allows_the_rest()

### Community 185 - "DeliveryLog"
Cohesion: 0.23
Nodes (3): DeliveryLog, DeliveryLogContract, _service()

### Community 186 - "CandidateStore"
Cohesion: 0.27
Nodes (5): CandidateStore, _candidate(), CandidateStoreContract, ConditionalReplaceContract, _decided()

### Community 187 - "devDependencies"
Cohesion: 0.11
Nodes (18): devDependencies, eslint, eslint-config-next, eslint-config-prettier, eslint-plugin-jsx-a11y, jsdom, openapi-typescript, prettier (+10 more)

### Community 188 - "test_inbound_render.py"
Cohesion: 0.20
Nodes (12): Citation, render_reply(), split_text(), test_dispatcher_renders_agent_citations_as_a_numbered_footer(), test_render_reply_marks_flagged_citations_unconfirmed(), test_render_reply_numbers_citations_in_a_footer_with_memory_ids(), test_render_reply_without_citations_is_the_agent_text_alone(), test_split_text_cuts_at_line_breaks_when_it_can() (+4 more)

### Community 189 - "docs/05-roadmap.md"
Cohesion: 0.20
Nodes (16): C3 Real-world pilot, FR-13 Map dashboard, FR-14 MCP server, Pilot metrics, docs/05-roadmap.md, [human] Metric functions, [human] WaveEngine (author-implemented ripple engine), Phase 0 Foundation (2026-10-20 to 2026-11-08) (+8 more)

### Community 190 - "Kind"
Cohesion: 0.22
Nodes (10): profile_content(), profile_fact(), profile_memory(), profile_statement(), Kind, ProfileAttribute, test_profile_fact_accepts_only_a_4_or_10_point_cgpa_scale(), test_profile_fact_types_cgpa_as_float_and_batch_as_int() (+2 more)

### Community 191 - "Workstreams (dependency order, then value)"
Cohesion: 0.14
Nodes (13): Coordination, Prerequisites (author, before or alongside round 2), Round 2 plan — from "built offline" to "used daily", What this round does not do, Where the project stands against the original idea (checked 2026-10-24), Workstreams (dependency order, then value), WS-0 Coordinator: live verification and engine landing (sequential-only), WS-10 Telegram inbound: the student's channel (Phase 2 exit; parallel-ready) (+5 more)

### Community 192 - "Bot"
Cohesion: 0.17
Nodes (3): new_link_code(), Bot, incoming_callback()

### Community 193 - ".search"
Cohesion: 0.22
Nodes (5): candidate_count(), _Collected, _Frontier, _source_evidence(), _visible()

### Community 194 - "test_inbound_ratelimit.py"
Cohesion: 0.17
Nodes (5): test_rate_limiter_allows_up_to_the_limit_then_refuses(), test_rate_limiter_forget_idle_drops_keys_older_than_the_window(), test_rate_limiter_keys_are_independent(), test_rate_limiter_refused_attempts_do_not_extend_the_lockout(), test_rate_limiter_releases_once_the_window_has_passed()

### Community 195 - "schema.d.ts"
Cohesion: 0.18
Nodes (10): components, $defs, operations, paths, ADR-0013, ADR-0015, ADR-0042, webhooks (+2 more)

### Community 196 - "open_scout"
Cohesion: 0.18
Nodes (7): Follow-ups (specified, not built), How consumers call it, Suggested commit message, Verification (WS-9 paths only), WS-9 handover: Scout agent, open_scout(), process_ledger()

### Community 197 - "reciprocal_rank_fusion"
Cohesion: 0.35
Nodes (8): FusedHit, reciprocal_rank_fusion(), _hits(), test_fusion_equal_scores_break_ties_by_memory_id(), test_fusion_item_in_both_lists_beats_single_list_leaders(), test_fusion_of_nothing_is_nothing(), test_fusion_single_list_preserves_rank_order(), test_fusion_via_is_the_path_that_ranked_the_item_best()

### Community 198 - "docs/IDEAS.md and docs/proposals/"
Cohesion: 0.20
Nodes (10): Time-to-consistency and stale-action window, docs/IDEAS.md and docs/proposals/, Idea 1 Wave-by-wave ripple with early stopping, Idea 2 Rule-first resolution, Idea 3 Self-expiring memories via valid_to, Idea 4 Structure-derived silver labels + candidate pre-filter, Idea 5 Time-to-consistency metric with replay harness, Idea 7 RippleBench v1 generator: missing-link scenarios, multi-parent cases, prose fields (+2 more)

### Community 199 - "Production plan — build the whole product once, deploy-ready"
Cohesion: 0.20
Nodes (9): Acceptance for the plan as a whole, Author-owned, in parallel with both waves, Decisions fixed now, so nothing is rebuilt later, Definition of production-ready (what "done once" means), Ownership and ADR ranges for wave A, Production plan — build the whole product once, deploy-ready, Wave A — product completion and hardening (now), Wave B — evaluation and research completion (after C3) (+1 more)

### Community 200 - "2026-10-23/manifest.json"
Cohesion: 0.20
Nodes (9): src/ripple/agents/checkpoints.py, ast_hash, mtime, seen, semantic_hash, src/ripple/llm/schemas/jd.py, ast_hash, mtime (+1 more)

### Community 201 - "graphify-code/manifest.json"
Cohesion: 0.20
Nodes (9): src/ripple/agents/checkpoints.py, ast_hash, mtime, seen, semantic_hash, src/ripple/llm/schemas/jd.py, ast_hash, mtime (+1 more)

### Community 202 - "runner.py"
Cohesion: 0.24
Nodes (3): scenario_paths(), test_every_scenario_file_loads_and_declares_expectations(), test_scenario()

### Community 203 - "ripple.agents.scout and ripple.domains.jobs.sources: the Scout"
Cohesion: 0.25
Nodes (7): 1. What it does, 2. Why it exists, 4. Trade-offs, 5. Failure modes and tests, 6. Interview questions, 7. Exercise, ripple.agents.scout and ripple.domains.jobs.sources: the Scout

### Community 204 - "Deploying Ripple (ADR-0029)"
Cohesion: 0.25
Nodes (7): Backups, Deploying Ripple (ADR-0029), First deploy, Prerequisites (once), Rollback, Secrets, Upgrade

### Community 205 - "Pilot consent (draft for departmental review)"
Cohesion: 0.25
Nodes (7): Contact, How it is used, Pilot consent (draft for departmental review), What Ripple is, What we collect, Where it lives, Your rights

### Community 206 - "Rule-first resolution"
Cohesion: 0.46
Nodes (8): Proposal 0001: Rule-first resolution, Alternatives: LLM-only, calculator tool, rules in the Linker, Measurement: LLM calls per ripple and eligibility accuracy with flag on vs off, Rule-first resolution, Problem: eligibility arithmetic sent to the LLM, Recommendation: protocol in Phase 1, jobs rules in Phase 2, Risk: wrong rules are confidently wrong, Rationale: fewer LLM calls and deterministic testable decisions

### Community 207 - "RedisLease"
Cohesion: 0.29
Nodes (3): RedisLease, test_redis_lease_acquire_release_expiry_and_foreign_release(), scenario()

### Community 208 - "locate_span"
Cohesion: 0.39
Nodes (5): locate_span(), test_locate_span_falls_back_to_case_insensitive_match(), test_locate_span_finds_exact_substring_with_offsets(), test_locate_span_returns_none_when_quote_is_absent(), test_locate_span_tolerates_line_breaks_the_model_read_as_spaces()

### Community 209 - "no-business-logic.test.ts"
Cohesion: 0.29
Nodes (3): FORBIDDEN, sourceFiles(), SRC

### Community 210 - "ADR-0029: Deployment topology: one VPS, Compose, Caddy TLS, GHCR images, pg_dump backups"
Cohesion: 0.29
Nodes (6): ADR-0029: Deployment topology: one VPS, Compose, Caddy TLS, GHCR images, pg_dump backups, Alternatives considered, Consequences, Context, Decision, Revisit if

### Community 211 - "ADR-0086: Dashboard pages, token session in sessionStorage, query-string routing"
Cohesion: 0.29
Nodes (6): ADR-0086: Dashboard pages, token session in sessionStorage, query-string routing, Alternatives considered, Consequences, Context, Decision, Revisit if

### Community 212 - "ADR-0087: Openings map built from the inspector's `why` links, laid out by kind"
Cohesion: 0.29
Nodes (6): ADR-0087: Openings map built from the inspector's `why` links, laid out by kind, Alternatives considered, Consequences, Context, Decision, Revisit if

### Community 213 - "ripple.mcp_server — Ripple's memory as MCP tools"
Cohesion: 0.29
Nodes (7): 1. What it does, 2. Why it exists, 4. Trade-offs, 5. Failure modes and tests, 6. Interview questions, 7. Exercise, ripple.mcp_server — Ripple's memory as MCP tools

### Community 214 - "Operations runbook"
Cohesion: 0.29
Nodes (6): Data requests (DPDP, FR-15), Health, Incidents, Key rotation, Operations runbook, Rollback and restore

### Community 215 - "Graph Report - RIPPLE  (2026-10-23)"
Cohesion: 0.29
Nodes (6): Community Hubs (Navigation), Corpus Check, Graph Report - RIPPLE  (2026-10-23), Import Cycles, Knowledge Gaps, Summary

### Community 216 - "Graph Report - RIPPLE  (2026-10-23)"
Cohesion: 0.29
Nodes (6): Community Hubs (Navigation), Corpus Check, Graph Report - RIPPLE  (2026-10-23), Import Cycles, Knowledge Gaps, Summary

### Community 218 - "Ripple dashboard (apps/web)"
Cohesion: 0.33
Nodes (5): Commands (run inside apps/web), Deploy, Regenerating the API client, Ripple dashboard (apps/web), Rules

### Community 219 - "ADR-0070: Allowed-sources registry: a YAML file validated into Pydantic, terms note required"
Cohesion: 0.33
Nodes (5): ADR-0070: Allowed-sources registry: a YAML file validated into Pydantic, terms note required, Alternatives considered, Consequences, Context, Revisit if

### Community 220 - "ADR-0075: Telegram inbound: a strict subset of the Update type, private chats only, drops counted"
Cohesion: 0.33
Nodes (5): ADR-0075: Telegram inbound: a strict subset of the Update type, private chats only, drops counted, Alternatives considered, Consequences, Context, Revisit if

### Community 221 - "ADR-0080: MCP server on the SDK's low-level `Server`, explicit Pydantic tool schemas, seven tools"
Cohesion: 0.33
Nodes (5): ADR-0080: MCP server on the SDK's low-level `Server`, explicit Pydantic tool schemas, seven tools, Alternatives considered, Consequences, Context, Revisit if

### Community 222 - "ADR-0081: MCP identity: one bearer token per connection, hashed through ADR-0040, bound per request"
Cohesion: 0.33
Nodes (5): ADR-0081: MCP identity: one bearer token per connection, hashed through ADR-0040, bound per request, Alternatives considered, Consequences, Context, Revisit if

### Community 223 - "WS-11 handover: MCP server"
Cohesion: 0.33
Nodes (5): Open problems, Suggested commit message, Tool surface, Verification (run 2026-10-25, after the code-review pass), WS-11 handover: MCP server

### Community 224 - ".claude/settings.json"
Cohesion: 0.33
Nodes (6): .claude/settings.json, ast_empty, ast_hash, mtime, seen, semantic_hash

### Community 225 - ".claude/settings.json"
Cohesion: 0.33
Nodes (6): .claude/settings.json, ast_empty, ast_hash, mtime, seen, semantic_hash

### Community 226 - "parse_resume_ref"
Cohesion: 0.40
Nodes (4): parse_resume_ref(), ResumeRef, test_parse_resume_ref_reads_upload_id_and_span(), test_parse_resume_ref_rejects_anything_else()

### Community 227 - ".prettierrc.json"
Cohesion: 0.40
Nodes (4): printWidth, semi, singleQuote, trailingComma

### Community 228 - "bench/data/jobs_v0/manifest.json"
Cohesion: 0.40
Nodes (5): bench/data/jobs_v0/manifest.json, ast_hash, mtime, seen, semantic_hash

### Community 229 - "bench/generate.py"
Cohesion: 0.40
Nodes (5): bench/generate.py, ast_hash, mtime, seen, semantic_hash

### Community 230 - "bench/__init__.py"
Cohesion: 0.40
Nodes (5): bench/__init__.py, ast_hash, mtime, seen, semantic_hash

### Community 231 - "bench/metrics.py"
Cohesion: 0.40
Nodes (5): bench/metrics.py, ast_hash, mtime, seen, semantic_hash

### Community 232 - "bench/replay.py"
Cohesion: 0.40
Nodes (5): bench/replay.py, ast_hash, mtime, seen, semantic_hash

### Community 233 - "bench/run.py"
Cohesion: 0.40
Nodes (5): bench/run.py, ast_hash, mtime, seen, semantic_hash

### Community 234 - "bench/scenario.py"
Cohesion: 0.40
Nodes (5): bench/scenario.py, ast_hash, mtime, seen, semantic_hash

### Community 235 - "bench/strategies.py"
Cohesion: 0.40
Nodes (5): bench/strategies.py, ast_hash, mtime, seen, semantic_hash

### Community 236 - "infra/entrypoint.sh"
Cohesion: 0.40
Nodes (5): infra/entrypoint.sh, ast_hash, mtime, seen, semantic_hash

### Community 237 - "infra/migrations/env.py"
Cohesion: 0.40
Nodes (5): infra/migrations/env.py, ast_hash, mtime, seen, semantic_hash

### Community 238 - "infra/migrations/versions/0001_initial.py"
Cohesion: 0.40
Nodes (5): infra/migrations/versions/0001_initial.py, ast_hash, mtime, seen, semantic_hash

### Community 239 - "infra/migrations/versions/0002_core_tables.py"
Cohesion: 0.40
Nodes (5): infra/migrations/versions/0002_core_tables.py, ast_hash, mtime, seen, semantic_hash

### Community 240 - "infra/migrations/versions/0003_users.py"
Cohesion: 0.40
Nodes (5): infra/migrations/versions/0003_users.py, ast_hash, mtime, seen, semantic_hash

### Community 241 - "infra/migrations/versions/0004_embeddings.py"
Cohesion: 0.40
Nodes (5): infra/migrations/versions/0004_embeddings.py, ast_hash, mtime, seen, semantic_hash

### Community 242 - "pyproject.toml"
Cohesion: 0.40
Nodes (5): pyproject.toml, ast_hash, mtime, seen, semantic_hash

### Community 243 - "src/ripple/agents/capabilities.py"
Cohesion: 0.40
Nodes (5): src/ripple/agents/capabilities.py, ast_hash, mtime, seen, semantic_hash

### Community 244 - "src/ripple/agents/conversation.py"
Cohesion: 0.40
Nodes (5): src/ripple/agents/conversation.py, ast_hash, mtime, seen, semantic_hash

### Community 245 - "src/ripple/agents/evidence.py"
Cohesion: 0.40
Nodes (5): src/ripple/agents/evidence.py, ast_hash, mtime, seen, semantic_hash

### Community 246 - "src/ripple/agents/__init__.py"
Cohesion: 0.40
Nodes (5): src/ripple/agents/__init__.py, ast_hash, mtime, seen, semantic_hash

### Community 247 - "src/ripple/agents/tailor.py"
Cohesion: 0.40
Nodes (5): src/ripple/agents/tailor.py, ast_hash, mtime, seen, semantic_hash

### Community 248 - "src/ripple/api/adapters.py"
Cohesion: 0.40
Nodes (5): src/ripple/api/adapters.py, ast_hash, mtime, seen, semantic_hash

### Community 249 - "src/ripple/api/admin.py"
Cohesion: 0.40
Nodes (5): src/ripple/api/admin.py, ast_hash, mtime, seen, semantic_hash

### Community 250 - "src/ripple/api/app.py"
Cohesion: 0.40
Nodes (5): src/ripple/api/app.py, ast_hash, mtime, seen, semantic_hash

### Community 251 - "src/ripple/api/auth.py"
Cohesion: 0.40
Nodes (5): src/ripple/api/auth.py, ast_hash, mtime, seen, semantic_hash

### Community 252 - "src/ripple/api/candidates.py"
Cohesion: 0.40
Nodes (5): src/ripple/api/candidates.py, ast_hash, mtime, seen, semantic_hash

### Community 253 - "src/ripple/api/contracts.py"
Cohesion: 0.40
Nodes (5): src/ripple/api/contracts.py, ast_hash, mtime, seen, semantic_hash

### Community 254 - "src/ripple/api/directory.py"
Cohesion: 0.40
Nodes (5): src/ripple/api/directory.py, ast_hash, mtime, seen, semantic_hash

### Community 255 - "src/ripple/api/errors.py"
Cohesion: 0.40
Nodes (5): src/ripple/api/errors.py, ast_hash, mtime, seen, semantic_hash

### Community 256 - "src/ripple/api/__init__.py"
Cohesion: 0.40
Nodes (5): src/ripple/api/__init__.py, ast_hash, mtime, seen, semantic_hash

### Community 257 - "src/ripple/api/routers/__init__.py"
Cohesion: 0.40
Nodes (5): src/ripple/api/routers/__init__.py, ast_hash, mtime, seen, semantic_hash

### Community 258 - "src/ripple/api/routers/me.py"
Cohesion: 0.40
Nodes (5): src/ripple/api/routers/me.py, ast_hash, mtime, seen, semantic_hash

### Community 259 - "src/ripple/api/routers/memories.py"
Cohesion: 0.40
Nodes (5): src/ripple/api/routers/memories.py, ast_hash, mtime, seen, semantic_hash

### Community 260 - "src/ripple/api/routers/openings.py"
Cohesion: 0.40
Nodes (5): src/ripple/api/routers/openings.py, ast_hash, mtime, seen, semantic_hash

### Community 261 - "src/ripple/api/routers/questions.py"
Cohesion: 0.40
Nodes (5): src/ripple/api/routers/questions.py, ast_hash, mtime, seen, semantic_hash

### Community 262 - "src/ripple/api/routers/recommendations.py"
Cohesion: 0.40
Nodes (5): src/ripple/api/routers/recommendations.py, ast_hash, mtime, seen, semantic_hash

### Community 263 - "src/ripple/api/routers/resume.py"
Cohesion: 0.40
Nodes (5): src/ripple/api/routers/resume.py, ast_hash, mtime, seen, semantic_hash

### Community 264 - "src/ripple/api/routers/statements.py"
Cohesion: 0.40
Nodes (5): src/ripple/api/routers/statements.py, ast_hash, mtime, seen, semantic_hash

### Community 265 - "src/ripple/api/schemas.py"
Cohesion: 0.40
Nodes (5): src/ripple/api/schemas.py, ast_hash, mtime, seen, semantic_hash

### Community 266 - "src/ripple/api/services.py"
Cohesion: 0.40
Nodes (5): src/ripple/api/services.py, ast_hash, mtime, seen, semantic_hash

### Community 267 - "src/ripple/api/wiring.py"
Cohesion: 0.40
Nodes (5): src/ripple/api/wiring.py, ast_hash, mtime, seen, semantic_hash

### Community 268 - "src/ripple/core/answers.py"
Cohesion: 0.40
Nodes (5): src/ripple/core/answers.py, ast_hash, mtime, seen, semantic_hash

### Community 269 - "src/ripple/core/change_detection.py"
Cohesion: 0.40
Nodes (5): src/ripple/core/change_detection.py, ast_hash, mtime, seen, semantic_hash

### Community 270 - "src/ripple/core/clock.py"
Cohesion: 0.40
Nodes (5): src/ripple/core/clock.py, ast_hash, mtime, seen, semantic_hash

### Community 271 - "src/ripple/core/engine.py"
Cohesion: 0.40
Nodes (5): src/ripple/core/engine.py, ast_hash, mtime, seen, semantic_hash

### Community 272 - "src/ripple/core/errors.py"
Cohesion: 0.40
Nodes (5): src/ripple/core/errors.py, ast_hash, mtime, seen, semantic_hash

### Community 273 - "src/ripple/core/forget.py"
Cohesion: 0.40
Nodes (5): src/ripple/core/forget.py, ast_hash, mtime, seen, semantic_hash

### Community 274 - "src/ripple/core/ids.py"
Cohesion: 0.40
Nodes (5): src/ripple/core/ids.py, ast_hash, mtime, seen, semantic_hash

### Community 275 - "src/ripple/core/indexing.py"
Cohesion: 0.40
Nodes (5): src/ripple/core/indexing.py, ast_hash, mtime, seen, semantic_hash

### Community 276 - "src/ripple/core/__init__.py"
Cohesion: 0.40
Nodes (5): src/ripple/core/__init__.py, ast_hash, mtime, seen, semantic_hash

### Community 277 - "src/ripple/core/intake.py"
Cohesion: 0.40
Nodes (5): src/ripple/core/intake.py, ast_hash, mtime, seen, semantic_hash

### Community 278 - "src/ripple/core/linking.py"
Cohesion: 0.40
Nodes (5): src/ripple/core/linking.py, ast_hash, mtime, seen, semantic_hash

### Community 279 - "src/ripple/core/links.py"
Cohesion: 0.40
Nodes (5): src/ripple/core/links.py, ast_hash, mtime, seen, semantic_hash

### Community 280 - "src/ripple/core/models.py"
Cohesion: 0.40
Nodes (5): src/ripple/core/models.py, ast_hash, mtime, seen, semantic_hash

### Community 281 - "src/ripple/core/resolver.py"
Cohesion: 0.40
Nodes (5): src/ripple/core/resolver.py, ast_hash, mtime, seen, semantic_hash

### Community 282 - "src/ripple/core/retrieval_contract.py"
Cohesion: 0.40
Nodes (5): src/ripple/core/retrieval_contract.py, ast_hash, mtime, seen, semantic_hash

### Community 283 - "src/ripple/core/ripple.py"
Cohesion: 0.40
Nodes (5): src/ripple/core/ripple.py, ast_hash, mtime, seen, semantic_hash

### Community 284 - "src/ripple/core/store.py"
Cohesion: 0.40
Nodes (5): src/ripple/core/store.py, ast_hash, mtime, seen, semantic_hash

### Community 285 - "src/ripple/core/sweep.py"
Cohesion: 0.40
Nodes (5): src/ripple/core/sweep.py, ast_hash, mtime, seen, semantic_hash

### Community 286 - "src/ripple/core/versioning.py"
Cohesion: 0.40
Nodes (5): src/ripple/core/versioning.py, ast_hash, mtime, seen, semantic_hash

### Community 287 - "src/ripple/core/visibility.py"
Cohesion: 0.40
Nodes (5): src/ripple/core/visibility.py, ast_hash, mtime, seen, semantic_hash

### Community 288 - "src/ripple/core/writes.py"
Cohesion: 0.40
Nodes (5): src/ripple/core/writes.py, ast_hash, mtime, seen, semantic_hash

### Community 289 - "src/ripple/domains/__init__.py"
Cohesion: 0.40
Nodes (5): src/ripple/domains/__init__.py, ast_hash, mtime, seen, semantic_hash

### Community 290 - "src/ripple/domains/jobs/beliefs.py"
Cohesion: 0.40
Nodes (5): src/ripple/domains/jobs/beliefs.py, ast_hash, mtime, seen, semantic_hash

### Community 291 - "src/ripple/domains/jobs/derive.py"
Cohesion: 0.40
Nodes (5): src/ripple/domains/jobs/derive.py, ast_hash, mtime, seen, semantic_hash

### Community 292 - "src/ripple/domains/jobs/__init__.py"
Cohesion: 0.40
Nodes (5): src/ripple/domains/jobs/__init__.py, ast_hash, mtime, seen, semantic_hash

### Community 293 - "src/ripple/domains/jobs/openings.py"
Cohesion: 0.40
Nodes (5): src/ripple/domains/jobs/openings.py, ast_hash, mtime, seen, semantic_hash

### Community 294 - "src/ripple/domains/jobs/parsers/dates.py"
Cohesion: 0.40
Nodes (5): src/ripple/domains/jobs/parsers/dates.py, ast_hash, mtime, seen, semantic_hash

### Community 295 - "src/ripple/domains/jobs/parsers/envelope.py"
Cohesion: 0.40
Nodes (5): src/ripple/domains/jobs/parsers/envelope.py, ast_hash, mtime, seen, semantic_hash

### Community 296 - "src/ripple/domains/jobs/parsers/errors.py"
Cohesion: 0.40
Nodes (5): src/ripple/domains/jobs/parsers/errors.py, ast_hash, mtime, seen, semantic_hash

### Community 297 - "src/ripple/domains/jobs/parsers/__init__.py"
Cohesion: 0.40
Nodes (5): src/ripple/domains/jobs/parsers/__init__.py, ast_hash, mtime, seen, semantic_hash

### Community 298 - "src/ripple/domains/jobs/parsers/jd.py"
Cohesion: 0.40
Nodes (5): src/ripple/domains/jobs/parsers/jd.py, ast_hash, mtime, seen, semantic_hash

### Community 299 - "src/ripple/domains/jobs/parsers/numbers.py"
Cohesion: 0.40
Nodes (5): src/ripple/domains/jobs/parsers/numbers.py, ast_hash, mtime, seen, semantic_hash

### Community 300 - "src/ripple/domains/jobs/parsers/resume.py"
Cohesion: 0.40
Nodes (5): src/ripple/domains/jobs/parsers/resume.py, ast_hash, mtime, seen, semantic_hash

### Community 301 - "src/ripple/domains/jobs/parsers/spans.py"
Cohesion: 0.40
Nodes (5): src/ripple/domains/jobs/parsers/spans.py, ast_hash, mtime, seen, semantic_hash

### Community 302 - "src/ripple/domains/jobs/profile.py"
Cohesion: 0.40
Nodes (5): src/ripple/domains/jobs/profile.py, ast_hash, mtime, seen, semantic_hash

### Community 303 - "src/ripple/domains/jobs/ranking.py"
Cohesion: 0.40
Nodes (5): src/ripple/domains/jobs/ranking.py, ast_hash, mtime, seen, semantic_hash

### Community 304 - "src/ripple/domains/jobs/rules.py"
Cohesion: 0.40
Nodes (5): src/ripple/domains/jobs/rules.py, ast_hash, mtime, seen, semantic_hash

### Community 305 - "src/ripple/domains/jobs/schemas.py"
Cohesion: 0.40
Nodes (5): src/ripple/domains/jobs/schemas.py, ast_hash, mtime, seen, semantic_hash

### Community 306 - "src/ripple/domains/jobs/vocabulary.py"
Cohesion: 0.40
Nodes (5): src/ripple/domains/jobs/vocabulary.py, ast_hash, mtime, seen, semantic_hash

### Community 307 - "src/ripple/__init__.py"
Cohesion: 0.40
Nodes (5): src/ripple/__init__.py, ast_hash, mtime, seen, semantic_hash

### Community 308 - "src/ripple/linking/__init__.py"
Cohesion: 0.40
Nodes (5): src/ripple/linking/__init__.py, ast_hash, mtime, seen, semantic_hash

### Community 309 - "src/ripple/linking/llm.py"
Cohesion: 0.40
Nodes (5): src/ripple/linking/llm.py, ast_hash, mtime, seen, semantic_hash

### Community 310 - "src/ripple/linking/rules.py"
Cohesion: 0.40
Nodes (5): src/ripple/linking/rules.py, ast_hash, mtime, seen, semantic_hash

### Community 311 - "src/ripple/llm/change_detector.py"
Cohesion: 0.40
Nodes (5): src/ripple/llm/change_detector.py, ast_hash, mtime, seen, semantic_hash

### Community 312 - "src/ripple/llm/client.py"
Cohesion: 0.40
Nodes (5): src/ripple/llm/client.py, ast_hash, mtime, seen, semantic_hash

### Community 313 - "src/ripple/llm/config.py"
Cohesion: 0.40
Nodes (5): src/ripple/llm/config.py, ast_hash, mtime, seen, semantic_hash

### Community 314 - "src/ripple/llm/evidence.py"
Cohesion: 0.40
Nodes (5): src/ripple/llm/evidence.py, ast_hash, mtime, seen, semantic_hash

### Community 315 - "src/ripple/llm/__init__.py"
Cohesion: 0.40
Nodes (5): src/ripple/llm/__init__.py, ast_hash, mtime, seen, semantic_hash

### Community 316 - "src/ripple/llm/prompts/__init__.py"
Cohesion: 0.40
Nodes (5): src/ripple/llm/prompts/__init__.py, ast_hash, mtime, seen, semantic_hash

### Community 317 - "src/ripple/llm/providers/anthropic.py"
Cohesion: 0.40
Nodes (5): src/ripple/llm/providers/anthropic.py, ast_hash, mtime, seen, semantic_hash

### Community 318 - "src/ripple/llm/providers/__init__.py"
Cohesion: 0.40
Nodes (5): src/ripple/llm/providers/__init__.py, ast_hash, mtime, seen, semantic_hash

### Community 319 - "src/ripple/llm/providers/openai.py"
Cohesion: 0.40
Nodes (5): src/ripple/llm/providers/openai.py, ast_hash, mtime, seen, semantic_hash

### Community 320 - "src/ripple/llm/resolver.py"
Cohesion: 0.40
Nodes (5): src/ripple/llm/resolver.py, ast_hash, mtime, seen, semantic_hash

### Community 321 - "src/ripple/llm/router.py"
Cohesion: 0.40
Nodes (5): src/ripple/llm/router.py, ast_hash, mtime, seen, semantic_hash

### Community 322 - "src/ripple/llm/schemas/change.py"
Cohesion: 0.40
Nodes (5): src/ripple/llm/schemas/change.py, ast_hash, mtime, seen, semantic_hash

### Community 323 - "src/ripple/llm/schemas/conversation.py"
Cohesion: 0.40
Nodes (5): src/ripple/llm/schemas/conversation.py, ast_hash, mtime, seen, semantic_hash

### Community 324 - "src/ripple/llm/schemas/__init__.py"
Cohesion: 0.40
Nodes (5): src/ripple/llm/schemas/__init__.py, ast_hash, mtime, seen, semantic_hash

### Community 325 - "bench/data/jobs_v0/manifest.json"
Cohesion: 0.40
Nodes (5): bench/data/jobs_v0/manifest.json, ast_hash, mtime, seen, semantic_hash

### Community 326 - "bench/generate.py"
Cohesion: 0.40
Nodes (5): bench/generate.py, ast_hash, mtime, seen, semantic_hash

### Community 327 - "bench/__init__.py"
Cohesion: 0.40
Nodes (5): bench/__init__.py, ast_hash, mtime, seen, semantic_hash

### Community 328 - "bench/metrics.py"
Cohesion: 0.40
Nodes (5): bench/metrics.py, ast_hash, mtime, seen, semantic_hash

### Community 329 - "bench/replay.py"
Cohesion: 0.40
Nodes (5): bench/replay.py, ast_hash, mtime, seen, semantic_hash

### Community 330 - "bench/run.py"
Cohesion: 0.40
Nodes (5): bench/run.py, ast_hash, mtime, seen, semantic_hash

### Community 331 - "bench/scenario.py"
Cohesion: 0.40
Nodes (5): bench/scenario.py, ast_hash, mtime, seen, semantic_hash

### Community 332 - "bench/strategies.py"
Cohesion: 0.40
Nodes (5): bench/strategies.py, ast_hash, mtime, seen, semantic_hash

### Community 333 - "infra/entrypoint.sh"
Cohesion: 0.40
Nodes (5): infra/entrypoint.sh, ast_hash, mtime, seen, semantic_hash

### Community 334 - "infra/migrations/env.py"
Cohesion: 0.40
Nodes (5): infra/migrations/env.py, ast_hash, mtime, seen, semantic_hash

### Community 335 - "infra/migrations/versions/0001_initial.py"
Cohesion: 0.40
Nodes (5): infra/migrations/versions/0001_initial.py, ast_hash, mtime, seen, semantic_hash

### Community 336 - "infra/migrations/versions/0002_core_tables.py"
Cohesion: 0.40
Nodes (5): infra/migrations/versions/0002_core_tables.py, ast_hash, mtime, seen, semantic_hash

### Community 337 - "infra/migrations/versions/0003_users.py"
Cohesion: 0.40
Nodes (5): infra/migrations/versions/0003_users.py, ast_hash, mtime, seen, semantic_hash

### Community 338 - "infra/migrations/versions/0004_embeddings.py"
Cohesion: 0.40
Nodes (5): infra/migrations/versions/0004_embeddings.py, ast_hash, mtime, seen, semantic_hash

### Community 339 - "pyproject.toml"
Cohesion: 0.40
Nodes (5): pyproject.toml, ast_hash, mtime, seen, semantic_hash

### Community 340 - "src/ripple/agents/capabilities.py"
Cohesion: 0.40
Nodes (5): src/ripple/agents/capabilities.py, ast_hash, mtime, seen, semantic_hash

### Community 341 - "src/ripple/agents/conversation.py"
Cohesion: 0.40
Nodes (5): src/ripple/agents/conversation.py, ast_hash, mtime, seen, semantic_hash

### Community 342 - "src/ripple/agents/evidence.py"
Cohesion: 0.40
Nodes (5): src/ripple/agents/evidence.py, ast_hash, mtime, seen, semantic_hash

### Community 343 - "src/ripple/agents/__init__.py"
Cohesion: 0.40
Nodes (5): src/ripple/agents/__init__.py, ast_hash, mtime, seen, semantic_hash

### Community 344 - "src/ripple/agents/tailor.py"
Cohesion: 0.40
Nodes (5): src/ripple/agents/tailor.py, ast_hash, mtime, seen, semantic_hash

### Community 345 - "src/ripple/api/adapters.py"
Cohesion: 0.40
Nodes (5): src/ripple/api/adapters.py, ast_hash, mtime, seen, semantic_hash

### Community 346 - "src/ripple/api/admin.py"
Cohesion: 0.40
Nodes (5): src/ripple/api/admin.py, ast_hash, mtime, seen, semantic_hash

### Community 347 - "src/ripple/api/app.py"
Cohesion: 0.40
Nodes (5): src/ripple/api/app.py, ast_hash, mtime, seen, semantic_hash

### Community 348 - "src/ripple/api/auth.py"
Cohesion: 0.40
Nodes (5): src/ripple/api/auth.py, ast_hash, mtime, seen, semantic_hash

### Community 349 - "src/ripple/api/candidates.py"
Cohesion: 0.40
Nodes (5): src/ripple/api/candidates.py, ast_hash, mtime, seen, semantic_hash

### Community 350 - "src/ripple/api/contracts.py"
Cohesion: 0.40
Nodes (5): src/ripple/api/contracts.py, ast_hash, mtime, seen, semantic_hash

### Community 351 - "src/ripple/api/directory.py"
Cohesion: 0.40
Nodes (5): src/ripple/api/directory.py, ast_hash, mtime, seen, semantic_hash

### Community 352 - "src/ripple/api/errors.py"
Cohesion: 0.40
Nodes (5): src/ripple/api/errors.py, ast_hash, mtime, seen, semantic_hash

### Community 353 - "src/ripple/api/__init__.py"
Cohesion: 0.40
Nodes (5): src/ripple/api/__init__.py, ast_hash, mtime, seen, semantic_hash

### Community 354 - "src/ripple/api/routers/__init__.py"
Cohesion: 0.40
Nodes (5): src/ripple/api/routers/__init__.py, ast_hash, mtime, seen, semantic_hash

### Community 355 - "src/ripple/api/routers/me.py"
Cohesion: 0.40
Nodes (5): src/ripple/api/routers/me.py, ast_hash, mtime, seen, semantic_hash

### Community 356 - "src/ripple/api/routers/memories.py"
Cohesion: 0.40
Nodes (5): src/ripple/api/routers/memories.py, ast_hash, mtime, seen, semantic_hash

### Community 357 - "src/ripple/api/routers/openings.py"
Cohesion: 0.40
Nodes (5): src/ripple/api/routers/openings.py, ast_hash, mtime, seen, semantic_hash

### Community 358 - "src/ripple/api/routers/questions.py"
Cohesion: 0.40
Nodes (5): src/ripple/api/routers/questions.py, ast_hash, mtime, seen, semantic_hash

### Community 359 - "src/ripple/api/routers/recommendations.py"
Cohesion: 0.40
Nodes (5): src/ripple/api/routers/recommendations.py, ast_hash, mtime, seen, semantic_hash

### Community 360 - "src/ripple/api/routers/resume.py"
Cohesion: 0.40
Nodes (5): src/ripple/api/routers/resume.py, ast_hash, mtime, seen, semantic_hash

### Community 361 - "src/ripple/api/routers/statements.py"
Cohesion: 0.40
Nodes (5): src/ripple/api/routers/statements.py, ast_hash, mtime, seen, semantic_hash

### Community 362 - "src/ripple/api/schemas.py"
Cohesion: 0.40
Nodes (5): src/ripple/api/schemas.py, ast_hash, mtime, seen, semantic_hash

### Community 363 - "src/ripple/api/services.py"
Cohesion: 0.40
Nodes (5): src/ripple/api/services.py, ast_hash, mtime, seen, semantic_hash

### Community 364 - "src/ripple/api/wiring.py"
Cohesion: 0.40
Nodes (5): src/ripple/api/wiring.py, ast_hash, mtime, seen, semantic_hash

### Community 365 - "src/ripple/core/answers.py"
Cohesion: 0.40
Nodes (5): src/ripple/core/answers.py, ast_hash, mtime, seen, semantic_hash

### Community 366 - "src/ripple/core/change_detection.py"
Cohesion: 0.40
Nodes (5): src/ripple/core/change_detection.py, ast_hash, mtime, seen, semantic_hash

### Community 367 - "src/ripple/core/clock.py"
Cohesion: 0.40
Nodes (5): src/ripple/core/clock.py, ast_hash, mtime, seen, semantic_hash

### Community 368 - "src/ripple/core/engine.py"
Cohesion: 0.40
Nodes (5): src/ripple/core/engine.py, ast_hash, mtime, seen, semantic_hash

### Community 369 - "src/ripple/core/errors.py"
Cohesion: 0.40
Nodes (5): src/ripple/core/errors.py, ast_hash, mtime, seen, semantic_hash

### Community 370 - "src/ripple/core/forget.py"
Cohesion: 0.40
Nodes (5): src/ripple/core/forget.py, ast_hash, mtime, seen, semantic_hash

### Community 371 - "src/ripple/core/ids.py"
Cohesion: 0.40
Nodes (5): src/ripple/core/ids.py, ast_hash, mtime, seen, semantic_hash

### Community 372 - "src/ripple/core/indexing.py"
Cohesion: 0.40
Nodes (5): src/ripple/core/indexing.py, ast_hash, mtime, seen, semantic_hash

### Community 373 - "src/ripple/core/__init__.py"
Cohesion: 0.40
Nodes (5): src/ripple/core/__init__.py, ast_hash, mtime, seen, semantic_hash

### Community 374 - "src/ripple/core/intake.py"
Cohesion: 0.40
Nodes (5): src/ripple/core/intake.py, ast_hash, mtime, seen, semantic_hash

### Community 375 - "src/ripple/core/linking.py"
Cohesion: 0.40
Nodes (5): src/ripple/core/linking.py, ast_hash, mtime, seen, semantic_hash

### Community 376 - "src/ripple/core/links.py"
Cohesion: 0.40
Nodes (5): src/ripple/core/links.py, ast_hash, mtime, seen, semantic_hash

### Community 377 - "src/ripple/core/models.py"
Cohesion: 0.40
Nodes (5): src/ripple/core/models.py, ast_hash, mtime, seen, semantic_hash

### Community 378 - "src/ripple/core/resolver.py"
Cohesion: 0.40
Nodes (5): src/ripple/core/resolver.py, ast_hash, mtime, seen, semantic_hash

### Community 379 - "src/ripple/core/retrieval_contract.py"
Cohesion: 0.40
Nodes (5): src/ripple/core/retrieval_contract.py, ast_hash, mtime, seen, semantic_hash

### Community 380 - "src/ripple/core/ripple.py"
Cohesion: 0.40
Nodes (5): src/ripple/core/ripple.py, ast_hash, mtime, seen, semantic_hash

### Community 381 - "src/ripple/core/store.py"
Cohesion: 0.40
Nodes (5): src/ripple/core/store.py, ast_hash, mtime, seen, semantic_hash

### Community 382 - "src/ripple/core/sweep.py"
Cohesion: 0.40
Nodes (5): src/ripple/core/sweep.py, ast_hash, mtime, seen, semantic_hash

### Community 383 - "src/ripple/core/versioning.py"
Cohesion: 0.40
Nodes (5): src/ripple/core/versioning.py, ast_hash, mtime, seen, semantic_hash

### Community 384 - "src/ripple/core/visibility.py"
Cohesion: 0.40
Nodes (5): src/ripple/core/visibility.py, ast_hash, mtime, seen, semantic_hash

### Community 385 - "src/ripple/core/writes.py"
Cohesion: 0.40
Nodes (5): src/ripple/core/writes.py, ast_hash, mtime, seen, semantic_hash

### Community 386 - "src/ripple/domains/__init__.py"
Cohesion: 0.40
Nodes (5): src/ripple/domains/__init__.py, ast_hash, mtime, seen, semantic_hash

### Community 387 - "src/ripple/domains/jobs/beliefs.py"
Cohesion: 0.40
Nodes (5): src/ripple/domains/jobs/beliefs.py, ast_hash, mtime, seen, semantic_hash

### Community 388 - "src/ripple/domains/jobs/derive.py"
Cohesion: 0.40
Nodes (5): src/ripple/domains/jobs/derive.py, ast_hash, mtime, seen, semantic_hash

### Community 389 - "src/ripple/domains/jobs/__init__.py"
Cohesion: 0.40
Nodes (5): src/ripple/domains/jobs/__init__.py, ast_hash, mtime, seen, semantic_hash

### Community 390 - "src/ripple/domains/jobs/openings.py"
Cohesion: 0.40
Nodes (5): src/ripple/domains/jobs/openings.py, ast_hash, mtime, seen, semantic_hash

### Community 391 - "src/ripple/domains/jobs/parsers/dates.py"
Cohesion: 0.40
Nodes (5): src/ripple/domains/jobs/parsers/dates.py, ast_hash, mtime, seen, semantic_hash

### Community 392 - "src/ripple/domains/jobs/parsers/envelope.py"
Cohesion: 0.40
Nodes (5): src/ripple/domains/jobs/parsers/envelope.py, ast_hash, mtime, seen, semantic_hash

### Community 393 - "src/ripple/domains/jobs/parsers/errors.py"
Cohesion: 0.40
Nodes (5): src/ripple/domains/jobs/parsers/errors.py, ast_hash, mtime, seen, semantic_hash

### Community 394 - "src/ripple/domains/jobs/parsers/__init__.py"
Cohesion: 0.40
Nodes (5): src/ripple/domains/jobs/parsers/__init__.py, ast_hash, mtime, seen, semantic_hash

### Community 395 - "src/ripple/domains/jobs/parsers/jd.py"
Cohesion: 0.40
Nodes (5): src/ripple/domains/jobs/parsers/jd.py, ast_hash, mtime, seen, semantic_hash

### Community 396 - "src/ripple/domains/jobs/parsers/numbers.py"
Cohesion: 0.40
Nodes (5): src/ripple/domains/jobs/parsers/numbers.py, ast_hash, mtime, seen, semantic_hash

### Community 397 - "src/ripple/domains/jobs/parsers/resume.py"
Cohesion: 0.40
Nodes (5): src/ripple/domains/jobs/parsers/resume.py, ast_hash, mtime, seen, semantic_hash

### Community 398 - "src/ripple/domains/jobs/parsers/spans.py"
Cohesion: 0.40
Nodes (5): src/ripple/domains/jobs/parsers/spans.py, ast_hash, mtime, seen, semantic_hash

### Community 399 - "src/ripple/domains/jobs/profile.py"
Cohesion: 0.40
Nodes (5): src/ripple/domains/jobs/profile.py, ast_hash, mtime, seen, semantic_hash

### Community 400 - "src/ripple/domains/jobs/ranking.py"
Cohesion: 0.40
Nodes (5): src/ripple/domains/jobs/ranking.py, ast_hash, mtime, seen, semantic_hash

### Community 401 - "src/ripple/domains/jobs/rules.py"
Cohesion: 0.40
Nodes (5): src/ripple/domains/jobs/rules.py, ast_hash, mtime, seen, semantic_hash

### Community 402 - "src/ripple/domains/jobs/schemas.py"
Cohesion: 0.40
Nodes (5): src/ripple/domains/jobs/schemas.py, ast_hash, mtime, seen, semantic_hash

### Community 403 - "src/ripple/domains/jobs/vocabulary.py"
Cohesion: 0.40
Nodes (5): src/ripple/domains/jobs/vocabulary.py, ast_hash, mtime, seen, semantic_hash

### Community 404 - "src/ripple/__init__.py"
Cohesion: 0.40
Nodes (5): src/ripple/__init__.py, ast_hash, mtime, seen, semantic_hash

### Community 405 - "src/ripple/linking/__init__.py"
Cohesion: 0.40
Nodes (5): src/ripple/linking/__init__.py, ast_hash, mtime, seen, semantic_hash

### Community 406 - "src/ripple/linking/llm.py"
Cohesion: 0.40
Nodes (5): src/ripple/linking/llm.py, ast_hash, mtime, seen, semantic_hash

### Community 407 - "src/ripple/linking/rules.py"
Cohesion: 0.40
Nodes (5): src/ripple/linking/rules.py, ast_hash, mtime, seen, semantic_hash

### Community 408 - "src/ripple/llm/change_detector.py"
Cohesion: 0.40
Nodes (5): src/ripple/llm/change_detector.py, ast_hash, mtime, seen, semantic_hash

### Community 409 - "src/ripple/llm/client.py"
Cohesion: 0.40
Nodes (5): src/ripple/llm/client.py, ast_hash, mtime, seen, semantic_hash

### Community 410 - "src/ripple/llm/config.py"
Cohesion: 0.40
Nodes (5): src/ripple/llm/config.py, ast_hash, mtime, seen, semantic_hash

### Community 411 - "src/ripple/llm/evidence.py"
Cohesion: 0.40
Nodes (5): src/ripple/llm/evidence.py, ast_hash, mtime, seen, semantic_hash

### Community 412 - "src/ripple/llm/__init__.py"
Cohesion: 0.40
Nodes (5): src/ripple/llm/__init__.py, ast_hash, mtime, seen, semantic_hash

### Community 413 - "src/ripple/llm/prompts/__init__.py"
Cohesion: 0.40
Nodes (5): src/ripple/llm/prompts/__init__.py, ast_hash, mtime, seen, semantic_hash

### Community 414 - "src/ripple/llm/providers/anthropic.py"
Cohesion: 0.40
Nodes (5): src/ripple/llm/providers/anthropic.py, ast_hash, mtime, seen, semantic_hash

### Community 415 - "src/ripple/llm/providers/__init__.py"
Cohesion: 0.40
Nodes (5): src/ripple/llm/providers/__init__.py, ast_hash, mtime, seen, semantic_hash

### Community 416 - "src/ripple/llm/providers/openai.py"
Cohesion: 0.40
Nodes (5): src/ripple/llm/providers/openai.py, ast_hash, mtime, seen, semantic_hash

### Community 417 - "src/ripple/llm/resolver.py"
Cohesion: 0.40
Nodes (5): src/ripple/llm/resolver.py, ast_hash, mtime, seen, semantic_hash

### Community 418 - "src/ripple/llm/router.py"
Cohesion: 0.40
Nodes (5): src/ripple/llm/router.py, ast_hash, mtime, seen, semantic_hash

### Community 419 - "src/ripple/llm/schemas/change.py"
Cohesion: 0.40
Nodes (5): src/ripple/llm/schemas/change.py, ast_hash, mtime, seen, semantic_hash

### Community 420 - "src/ripple/llm/schemas/conversation.py"
Cohesion: 0.40
Nodes (5): src/ripple/llm/schemas/conversation.py, ast_hash, mtime, seen, semantic_hash

### Community 421 - "src/ripple/llm/schemas/__init__.py"
Cohesion: 0.40
Nodes (5): src/ripple/llm/schemas/__init__.py, ast_hash, mtime, seen, semantic_hash

### Community 422 - "quote"
Cohesion: 0.40
Nodes (5): Quote, quote(), test_quote_handles_the_first_and_last_lines_without_newlines(), test_quote_is_none_outside_the_text(), test_quote_returns_the_span_and_its_whole_line()

### Community 425 - "hashlib"
Cohesion: 0.67
Nodes (3): data_hash(), sha256_of(), test_sha256_of_is_the_hex_digest_of_the_bytes()

## Knowledge Gaps
- **177 isolated node(s):** `ADR-0029`, `ADR-0086`, `react-dom`, `@testing-library/dom`, `@types/node` (+172 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 2693 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **52 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Status` connect `FakeClock` to `API Test Harness`, `Memory`, `models.py`, `Scenario Benchmarks & Replay`, `jobs/openings.py`, `Conversation & Tailor Agents`, `test_jobs.py`, `record_opening`, `test_intake.py`, `InMemoryStore`, `Scenario Runner & Resolution Specs`, `Conversation Agent & Evidence`, `Service Wiring & LLM Resolver`, `Store`, `FakeLLM`, `make_runner`, `api/schemas.py`, `build`, `ChangeEvent`, `tools.py`, `McpHarness`, `DecisionAction`, `run.py`, `users.py`, `fakes/clock.py`, `jobs/test_openings.py`, `test_ranking.py`, `Bot`, `edit_memory`, `types.ts`, `InboundDispatcher`, `bench/__init__.py`, `ScoutCriteria`, `tests/llm/__init__.py`, `tests/notify/__init__.py`?**
  _High betweenness centrality (0.113) - this node is a cross-community bridge._
- **Are the 23 inferred relationships involving `FakeClock` (e.g. with `ScenarioRunner` and `God Nodes (most connected - your core abstractions)`) actually correct?**
  _`FakeClock` has 23 INFERRED edges - model-reasoned connections that need verification._
- **What connects `ADR-0029`, `ADR-0086`, `react-dom` to the rest of the system?**
  _177 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `API Test Harness` be split into smaller, more focused modules?**
  _Cohesion score 0.030560447529265514 - nodes in this community are weakly interconnected._
- **Why does `3. How it works` connect `types.ts` to `Shell`, `SessionProvider.tsx`, `FakeClock`, `AccountView.tsx`, `MemoryDetailView.tsx`, `helpers.tsx`?**
  _High betweenness centrality (0.066) - this node is a cross-community bridge._
- **Are the 131 inferred relationships involving `Memory` (e.g. with `_company_of()` and `_deadline_of()`) actually correct?**
  _`Memory` has 131 INFERRED edges - model-reasoned connections that need verification._
- **Should `Memory` be split into smaller, more focused modules?**
  _Cohesion score 0.03643178410794603 - nodes in this community are weakly interconnected._