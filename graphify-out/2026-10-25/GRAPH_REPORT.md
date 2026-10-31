# Graph Report - RIPPLE  (2026-10-23)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 4005 nodes · 14011 edges · 182 communities (135 shown, 47 thin omitted)
- Extraction: 83% EXTRACTED · 17% INFERRED · 0% AMBIGUOUS · INFERRED: 2397 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- API Test Harness
- Ripple Runner & Nightly Sweep
- Core Domain Models & Intake
- Scenario Benchmarks & Replay
- In-Memory Retrieval & Indexing
- Change Detection & Statement Intake
- API Wiring & LLM Services
- Hybrid Retrieval & Fusion
- Conversation & Tailor Agents
- Benchmark Metrics & Gold State
- Postgres Store
- Search Backends (Postgres & In-Memory)
- Telegram Notifications
- Alert Rendering & Digests
- InMemoryStore
- Bench Data Generation
- Resume Candidate Store
- Scenario Runner & Resolution Specs
- ConfigurationError
- Conversation Agent & Evidence
- Resolver Decisions & Runner Recovery
- API Routers, Auth & Services
- Store
- Resume Parsing & Candidate Facts
- Service Wiring & LLM Resolver
- Worker Wiring, Settings & Leases
- Store Contract & Transactions
- Conversation Agent Tests & Fakes
- Agent Wiring & Tailor Tests
- pytest
- test_invariants_agents.py
- digest.py
- api/schemas.py
- User
- DependencyGraph
- profile.py
- link
- RouterConfig
- InMemoryUserStore
- InMemoryLease
- ChangeEvent
- anthropic.py
- auth.py
- RippleRunner
- routers/resume.py
- jobs/openings.py
- OpeningAttribute
- fact
- run
- UserStore
- LinkTypeRegistry
- run.py
- Recommendation
- jobs/rules.py
- fakes/clock.py
- dates.py
- manifest.json
- replay.py
- core/errors.py
- ProfileView
- jobs/test_openings.py
- ResumeCandidate
- test_ranking.py
- ParsedOpening
- parsers/jd.py
- Resolver
- settings.py
- test_migration_0004.py
- users.py
- parsers/resume.py
- strip_email_envelope
- json
- CandidateFact
- edit_memory
- new_id
- CandidateStore
- test_settings.py
- test_boundaries.py
- write_new_version
- me.py
- test_runner.py
- checkpoints.py
- test_directory.py
- Status
- env.py
- re
- _require_aware
- reciprocal_rank_fusion
- prompts/__init__.py
- list_recommendations
- StalePendingStore
- git_short_sha
- ripple/__init__.py
- test_migrations_match_table_metadata
- test_migration_0003_matches_users_tables
- 0001_initial.py
- bench/__init__.py
- entrypoint.sh
- ripple/api/__init__.py
- ripple/domains/__init__.py
- ripple/domains/jobs/__init__.py
- ripple/linking/__init__.py
- ripple/llm/__init__.py
- providers/__init__.py
- ._check
- schemas/__init__.py
- mcp_server/__init__.py
- tests/agents/__init__.py
- tests/conftest.py
- fakes/__init__.py
- tests/__init__.py
- scenarios/__init__.py
- results_dir
- ripple
- tests/api/__init__.py
- tests/core/__init__.py
- tests/domains/__init__.py
- tests/domains/jobs/__init__.py
- jobs_parsers/__init__.py
- infra/__init__.py
- tests/linking/__init__.py
- tests/llm/__init__.py
- tests/notify/__init__.py
- Writes memories and links to the store and indexes the memories in the backend.
- tests/retrieval/__init__.py
- tests/storage/__init__.py
- tests/worker/__init__.py
- ADR-0030: An opening is one anchor memory plus one structured fact per field
- WS-2 handover: resume and JD parsers
- _require_aware
- ripple.storage PostgresStore, tables and migrations
- prompts/__init__.py
- test_migration_0004.py
- migrated
- list_recommendations
- EventSnapshot
- AliasResolver
- DecisionAction
- FailingSecondCommitStore
- schemas/links.py
- ADR-0009: A trained small model for link finding
- test_migrations_match_table_metadata
- test_migration_0003_matches_users_tables
- Decision: record decisions as ADRs
- test_invariant_I4_invalid_llm_output_is_never_applied
- ADR-0000 template
- ADR-0001 Record decisions as ADRs
- ADR-0002 Job hunting is the primary domain
- ADR-0003 Graph decides scope; LLM decides action
- ADR-0004 PostgreSQL + pgvector
- ADR-0005 LangGraph for agents
- ADR-0006 Expose memory tools over MCP
- ripple

## God Nodes (most connected - your core abstractions)
1. `InMemoryStore` - 210 edges
2. `Memory` - 210 edges
3. `FakeClock` - 183 edges
4. `Status` - 181 edges
5. `fact()` - 149 edges
6. `FakeLLM` - 146 edges
7. `derived()` - 120 edges
8. `link()` - 105 edges
9. `memory()` - 100 edges
10. `ChangeEvent` - 98 edges

## Surprising Connections (you probably didn't know these)
- `RippleBench jobs_v0 track` --semantically_similar_to--> `Scenario tests (YAML timelines)`  [INFERRED] [semantically similar]
  bench/data/jobs_v0/accepted_offer__p0_jay.yaml → CLAUDE.md
- `test_unparseable_resume_error_is_a_ripple_error()` --uses--> `RippleError`  [INFERRED]
  tests/domains/jobs_parsers/test_resume_parser.py → src/ripple/core/errors.py
- `test_intent_verdict_accepts_structured_on_a_corrected_answer()` --uses--> `IntentVerdict`  [INFERRED]
  tests/agents/test_schemas.py → src/ripple/llm/schemas/conversation.py
- `test_system_clock_returns_aware_utc()` --uses--> `SystemClock`  [INFERRED]
  tests/core/test_clock.py → src/ripple/core/clock.py
- `DigestService.send_daily and send_alerts` --references--> `RecommendationSource`  [EXTRACTED]
  docs/learning/worker-and-notify.md → src/ripple/domains/jobs/vocabulary.py

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

## Communities (182 total, 47 thin omitted)

### Community 0 - "API Test Harness"
Cohesion: 0.05
Nodes (64): candidate_fact(), RecordingOpeningRecorder, ScriptedDetector, ScriptedOpeningParser, ScriptedRecommendations, ScriptedResumeParser, SimpleCandidateStatements, span() (+56 more)

### Community 1 - "Ripple Runner & Nightly Sweep"
Cohesion: 0.07
Nodes (28): derive_for_opening and derive_criteria, candidate_to_statement, Clock, MemoryIndexer, Link, Sensitivity, TriggerKind, record_memory() (+20 more)

### Community 2 - "Core Domain Models & Intake"
Cohesion: 0.05
Nodes (29): Embedder, RetrievedMemory, SearchBackend, SearchHit, FusedHit, reciprocal_rank_fusion(), candidate_count(), _Collected (+21 more)

### Community 3 - "Scenario Benchmarks & Replay"
Cohesion: 0.06
Nodes (33): not_found(), owned_memory(), edit_memory(), forget_memory(), get_memory(), list_memories(), _mentions(), post_opening() (+25 more)

### Community 4 - "In-Memory Retrieval & Indexing"
Cohesion: 0.07
Nodes (24): Recommendation, RecommendationSource, AlertKind, DeliveryLog, MessageReceipt, Thresholds, Transport, UserDirectory (+16 more)

### Community 5 - "Change Detection & Statement Intake"
Cohesion: 0.06
Nodes (62): Scenario accepted_offer__p0_jay, Scenario accepted_offer__p1_dev, Scenario accepted_offer__p2_harsh, Scenario accepted_offer__p3_esha, Scenario accepted_offer__p4_bharat, Scenario cgpa_rise__p0_jay, Scenario cgpa_rise__p1_dev, RippleBench jobs_v0 track (+54 more)

### Community 6 - "API Wiring & LLM Services"
Cohesion: 0.05
Nodes (15): main(), UserDirectoryAdapter, PostgresUserStore, _require_aware(), TelegramLinkCode, User, _user(), InMemoryUserStore (+7 more)

### Community 7 - "Hybrid Retrieval & Fusion"
Cohesion: 0.06
Nodes (25): InvalidObjectError, Memory, DerivedBeliefs, field_memory(), find_opening(), opening_memories(), OpeningAlreadyRecordedError, record_opening() (+17 more)

### Community 8 - "Conversation & Tailor Agents"
Cohesion: 0.12
Nodes (53): RetrievalPath, HybridRetriever, run(), run(), run(), test_detail_explains_why_skipping_history_links_and_keeping_snapshots(), run(), run() (+45 more)

### Community 9 - "Benchmark Metrics & Gold State"
Cohesion: 0.08
Nodes (31): daily_digest(), DeliveryReport, hourly_alerts(), JobFailedForUsersError, nightly_sweep(), scout_run(), SweepReport, sweep_lease_key() (+23 more)

### Community 10 - "Postgres Store"
Cohesion: 0.11
Nodes (55): Scenario cgpa_rise__p2_harsh, Scenario cgpa_rise__p3_esha, Scenario cgpa_rise__p4_bharat, Scenario cutoff_unknown__p0_jay, Scenario cutoff_unknown__p1_dev, Scenario cutoff_unknown__p2_harsh, Scenario cutoff_unknown__p3_esha, Scenario cutoff_unknown__p4_bharat (+47 more)

### Community 11 - "Search Backends (Postgres & In-Memory)"
Cohesion: 0.06
Nodes (43): jobs_rules() RuleResolver chain (field, eligibility, fit, reminder, criteria), Deterministic rule links for facts recorded later (fit_of, criteria_from), JobsRecommender (RecommendationSource implementation), Tier ordering and company-variety rebuild, One-time Telegram link code (8 hex, 15 min), POST /memories/{id}/edit as user_edit via update_memory, Declared Capability set checked for I6, AnswerVerdict claims with evidence_ids filtering (+35 more)

### Community 12 - "Telegram Notifications"
Cohesion: 0.07
Nodes (26): MessageTooLongError, NotifyError, TelegramSendError, _mapping(), _optional_int(), _parse_body(), _RedactToken, TelegramTransport (+18 more)

### Community 13 - "Alert Rendering & Digests"
Cohesion: 0.10
Nodes (28): ChangeClassification, ChangeDetector, ChangeKind, detect_structured_update(), Intake, IntakeResult, Statement, Linker (+20 more)

### Community 14 - "InMemoryStore"
Cohesion: 0.10
Nodes (39): visible_for_retrieval(), run(), change_event(), decision(), memory(), test_inmemory_store_refuses_nested_transactions(), test_inmemory_store_refuses_writes_outside_a_transaction(), test_invariant_I1_retrieval_never_returns_retired_and_flags_suspect() (+31 more)

### Community 15 - "Bench Data Generation"
Cohesion: 0.09
Nodes (31): build_scenario(), check_data(), data_hash(), generate(), Generated, load_jobs_v0(), load_manifest(), main() (+23 more)

### Community 16 - "Resume Candidate Store"
Cohesion: 0.08
Nodes (10): _candidate(), CandidateStatus, CandidateStore, PostgresCandidateStore, ResumeCandidate, _row(), InMemoryCandidateStore, _candidate() (+2 more)

### Community 17 - "Scenario Runner & Resolution Specs"
Cohesion: 0.09
Nodes (23): _retire(), load_scenario(), ResolutionSpec, ScenarioOutcome, ScenarioRunner, test_scenario_files_on_disk_load_with_the_shared_loader(), _cgpa_spec(), _scripted() (+15 more)

### Community 18 - "ConfigurationError"
Cohesion: 0.09
Nodes (26): InMemoryDeliveryLog, test_fake_clock_advance_moves_now(), test_fake_clock_rejects_naive_datetimes(), test_fake_clock_set_jumps_to_moment(), test_system_clock_returns_aware_utc(), test_profile_view_takes_the_latest_recorded_single_valued_fact(), failing_transport(), SentMessage (+18 more)

### Community 19 - "Conversation Agent & Evidence"
Cohesion: 0.09
Nodes (16): Citation, _compose_answer(), ConversationAgent, ConversationReply, ConversationState, _numbers(), PendingQuestion, _recent() (+8 more)

### Community 20 - "Resolver Decisions & Runner Recovery"
Cohesion: 0.14
Nodes (36): Status, test_edit_writes_a_user_edit_version_that_ripples(), run(), _runner(), _seed(), test_ask_records_parked_ids_on_the_event(), test_confirming_one_ask_does_not_restore_a_child_still_parked_by_another_question(), test_failed_commit_two_leaves_wave_suspect_and_no_new_version() (+28 more)

### Community 21 - "API Routers, Auth & Services"
Cohesion: 0.07
Nodes (17): STATUS_FOR exception-to-HTTP table, Services frozen dataclass, Known erasure gap: ChangeEvents survive DELETE /me, Learning page: ripple.api identity, inspector, confirmation, export, delete, owned_memory single dereference point (404 across users), Invariant I7: hard deletion only through the forget API, current_user(), _unauthorized() (+9 more)

### Community 22 - "Store"
Cohesion: 0.12
Nodes (9): create_user(), ApiToken, hash_token(), link_telegram(), new_raw_token(), UserStore, _code(), _user() (+1 more)

### Community 23 - "Resume Parsing & Candidate Facts"
Cohesion: 0.07
Nodes (18): CandidateStatements, ResumeParser, UnparseableResumeError, cgpa_value(), first_number(), graduation_year(), _candidate(), candidate_to_statement() (+10 more)

### Community 24 - "Service Wiring & LLM Resolver"
Cohesion: 0.10
Nodes (17): CandidateStatementsAdapter, OpeningParserAdapter, build_services(), default_adapters(), DomainAdapters, router_from_settings(), SystemClock, LLMLinker (+9 more)

### Community 25 - "Worker Wiring, Settings & Leases"
Cohesion: 0.08
Nodes (20): JobContext, Lease, RedisLease, daily_digest_job(), hourly_alerts_job(), job_context(), nightly_sweep_job(), on_shutdown() (+12 more)

### Community 26 - "Store Contract & Transactions"
Cohesion: 0.09
Nodes (18): OpeningRecorderAdapter, Store, Transaction, StoreContract, duplicate(), dangling(), complete(), write() (+10 more)

### Community 27 - "Conversation Agent Tests & Fakes"
Cohesion: 0.17
Nodes (34): test_answer_question_answered_meanwhile_replies_instead_of_raising(), test_answer_question_corrected_updates_the_structured_value(), test_answer_question_corrected_writes_a_new_version_and_ripples(), test_answer_question_for_an_unknown_question_writes_nothing(), test_answer_question_no_longer_holds_retires_and_ripples(), test_answer_question_still_holds_restores_the_memory(), test_ask_answers_from_retrieved_evidence_with_citations(), test_ask_renders_flagged_evidence_as_unconfirmed() (+26 more)

### Community 28 - "Agent Wiring & Tailor Tests"
Cohesion: 0.12
Nodes (26): _forbidden(), _imports(), test_invariant_I4_agent_rejects_invalid_llm_output(), test_invariant_I4_tailor_rejects_invalid_output(), test_invariant_I5_tailor_cites_only_existing_memories(), test_invariant_I6_agents_expose_no_submit_or_browser_tool(), test_invariant_I6_import_check_detects_a_breach(), _candidates_shown() (+18 more)

### Community 29 - "pytest"
Cohesion: 0.08
Nodes (42): C3 Real-world pilot, C4 Cost of graph-scoped resolution, Success criteria by May 2028, FR-13 Map dashboard, FR-14 MCP server, NFR-2 Cost and latency logged per step, docs/04-evaluation.md, Baseline: Append-only (+34 more)

### Community 30 - "test_invariants_agents.py"
Cohesion: 0.09
Nodes (20): forget(), StalePendingStore, _seed(), test_forget_deletes_whole_version_chain_and_depends_on_cascade(), test_forget_from_a_newer_version_deletes_the_older_ones_too(), test_forget_leaves_no_dangling_links(), test_forget_leaves_unrelated_memories_and_links_alone(), test_forget_removes_snapshot_link_but_keeps_the_dependent() (+12 more)

### Community 31 - "digest.py"
Cohesion: 0.10
Nodes (33): extract_text(), build_pdf(), candidate(), pdf_with_lines(), resume_reply(), router_for(), text_stream(), test_invariant_I4_parsers_reject_output_that_never_matches_the_schema() (+25 more)

### Community 32 - "api/schemas.py"
Cohesion: 0.17
Nodes (26): accepted_offer(), _cgpa_memory(), cgpa_rise(), cutoff_unknown(), deadline_moved(), exam_block(), forget_cgpa(), _keep() (+18 more)

### Community 33 - "User"
Cohesion: 0.08
Nodes (17): NightlySweep, test_intent_verdict_accepts_structured_on_a_corrected_answer(), test_intent_verdict_rejects_payload_that_does_not_match_the_intent(), _router(), test_opening_parser_adapter_strips_email_envelopes_only_for_email_sources(), test_opening_recorder_records_anchor_fields_and_derived_beliefs(), _availability_graph(), _pending_graph() (+9 more)

### Community 34 - "DependencyGraph"
Cohesion: 0.08
Nodes (32): tests/fakes FakeLLM and FakeClock, Invariants I1-I8, Scenario tests (YAML timelines), Testing policy, ADR-0002, ADR-0003, ADR-0019, ADR-0030 (+24 more)

### Community 35 - "profile.py"
Cohesion: 0.14
Nodes (21): one_shot_engine(), DependencyGraph, WaveEngine, WaveOutcome, _chain(), test_engine_changed_outcome_seeds_the_next_wave(), test_engine_first_wave_is_direct_dependents_of_seeds(), test_engine_first_wave_never_includes_a_seed() (+13 more)

### Community 36 - "link"
Cohesion: 0.10
Nodes (7): ChangeEvent, ChangeEventNotFoundError, _event(), _event_row(), _link(), _link_row(), _Reads

### Community 37 - "RouterConfig"
Cohesion: 0.10
Nodes (23): Hand-written deadline normaliser (dates.normalise_deadline), Forwarded email envelope stripping (strip_email_envelope), Model quotes, code locates (locate_span), Regex cross-checks for cgpa_cutoff and deadline, DateMatch, _agree(), _coerce(), _cross_check() (+15 more)

### Community 38 - "InMemoryUserStore"
Cohesion: 0.09
Nodes (19): ModelPrice, ModelSpec, RouterConfig, LoggingTracer, router_from_env(), test_models_for_empty_list_raises_configuration_error(), test_models_for_returns_primary_then_fallbacks_in_order(), test_models_for_unknown_task_raises_configuration_error() (+11 more)

### Community 39 - "InMemoryLease"
Cohesion: 0.09
Nodes (12): Capability, _about_the_student(), OpeningUnavailableError, Suggestion, TailorAgent, TailorState, TailorSuggestions, Retriever (+4 more)

### Community 40 - "ChangeEvent"
Cohesion: 0.10
Nodes (13): answer_no_longer_holds(), answer_with_correction(), confirm_still_holds(), NotPendingError, _pending(), pending_questions(), PendingQuestion, _restore_parked() (+5 more)

### Community 41 - "anthropic.py"
Cohesion: 0.13
Nodes (19): _data_description(), _display(), git_short_sha(), main(), _report(), run_dir_for(), run_suite(), RunConfig (+11 more)

### Community 42 - "auth.py"
Cohesion: 0.10
Nodes (15): LLMOutputInvalidError, AnthropicClient, AnthropicLike, _default_factory(), _Messages, _tool_input(), FakeMessages, FakeSDK (+7 more)

### Community 43 - "RippleRunner"
Cohesion: 0.11
Nodes (35): ADR-0040, ADR-0041, ADR-0042, ADR-0043, ADR-0044, Parallel execution tracker, C1 Jobs vocabulary contract, C2 Retrieval contract (+27 more)

### Community 44 - "routers/resume.py"
Cohesion: 0.10
Nodes (16): cosine_similarity(), InMemorySearchBackend, DeterministicFakeEmbedder, backend(), dense_seeder(), embedder(), Seeder, seeder() (+8 more)

### Community 45 - "jobs/openings.py"
Cohesion: 0.18
Nodes (29): compute_eligibility(), EligibilityRule, belief_memory(), context(), opening_fact(), profile(), test_eligibility_rule_batch_mismatch_makes_it_not_eligible_despite_the_cgpa(), test_eligibility_rule_defers_when_an_opening_field_is_pending_user() (+21 more)

### Community 46 - "OpeningAttribute"
Cohesion: 0.11
Nodes (26): run(), run(), run(), test_answering_a_memory_without_a_question_is_a_conflict(), run(), test_correction_writes_a_new_version(), test_no_longer_holds_retires_the_memory(), test_questions_list_pending_memories_with_the_ask_question_and_reason() (+18 more)

### Community 47 - "fact"
Cohesion: 0.12
Nodes (12): Resolution, ResolutionContext, _compare(), _in_doubt(), _opening_belief(), _owns(), ReminderRule, _retire_closed() (+4 more)

### Community 48 - "run"
Cohesion: 0.11
Nodes (18): PostgresSearchBackend, backend(), embedder(), engine(), _seed_graph(), store(), test_postgres_dense_skips_rows_without_an_embedding(), test_postgres_hybrid_retriever_end_to_end_respects_I1() (+10 more)

### Community 49 - "UserStore"
Cohesion: 0.13
Nodes (18): ConvergenceRecord, correct_updates(), cost_per_ripple(), questions_asked(), stale_kept(), stale_retrieval_rate(), target_outcomes(), TargetOutcome (+10 more)

### Community 50 - "LinkTypeRegistry"
Cohesion: 0.12
Nodes (8): CompletionRequest, CompletionResult, LLMClient, OpenAIClient, Completion, _summarise(), _Usage, test_openai_client_is_not_built_yet()

### Community 52 - "Recommendation"
Cohesion: 0.12
Nodes (5): upgrade(), upgrade(), Base, content_tsvector(), _extend_metadata()

### Community 53 - "jobs/rules.py"
Cohesion: 0.09
Nodes (5): ForgetEvent, MemoryNotFoundError, _forget_row(), _memory_row(), PostgresTransaction

### Community 54 - "fakes/clock.py"
Cohesion: 0.21
Nodes (21): derive_for_opening(), run(), _parent_ids(), _setup(), test_derive_criteria_from_profile_facts_links_criteria_from(), test_derive_criteria_is_none_for_an_empty_profile(), test_derive_each_belief_opens_its_own_completed_change_event(), test_derive_eligibility_is_false_when_cgpa_is_below_the_cutoff() (+13 more)

### Community 55 - "dates.py"
Cohesion: 0.13
Nodes (9): AppendOnlyStrategy, build_strategy(), CheckEverythingStrategy, CountingResolver, MemoryStrategy, NewestWinsStrategy, _NoPropagation, RippleStrategy (+1 more)

### Community 56 - "manifest.json"
Cohesion: 0.10
Nodes (10): OpeningParser, OpeningRecorder, OpeningWritten, _fence_safe(), parse_jd(), _summary(), ParsedField, ParsedOpening (+2 more)

### Community 57 - "replay.py"
Cohesion: 0.16
Nodes (16): _cascade(), _forget(), ForgetBehaviour, LinkPolicy, LinkTypeRegistry, policy_for(), UnknownLinkTypeError, LinkClass (+8 more)

### Community 58 - "core/errors.py"
Cohesion: 0.25
Nodes (24): OpeningAttribute, jd_reply(), _field(), _parse(), test_parse_jd_adds_deadline_from_regex_when_model_missed_it(), test_parse_jd_builds_summary_from_title_and_company_not_from_the_model(), test_parse_jd_coerces_cutoff_to_float_and_batch_to_int(), test_parse_jd_does_not_take_a_date_from_the_next_sentence_as_deadline() (+16 more)

### Community 59 - "ProfileView"
Cohesion: 0.15
Nodes (21): render_digest(), write(), write(), recommendation(), test_alert_kinds_deadline_just_beyond_48h_is_outside_the_window(), test_alert_kinds_never_alert_on_flagged_openings(), test_alert_kinds_never_alert_on_ineligible_openings(), test_alert_kinds_no_high_fit_just_below_threshold() (+13 more)

### Community 60 - "jobs/test_openings.py"
Cohesion: 0.16
Nodes (19): field(), make_runner(), parsed_acme(), span(), _record(), test_opening_view_ignores_retired_fields(), test_opening_view_reads_typed_values_from_the_field_facts(), test_record_opening_accepts_the_same_source_again_once_the_first_is_retired() (+11 more)

### Community 61 - "ResumeCandidate"
Cohesion: 0.09
Nodes (22): architecture-guardian subagent, code-reviewer subagent, adr skill, plan-phase skill, ADR requirement policy, Human-owned [human] tasks, Innovation tiers A and B, Job-hunt agent for engineering students (+14 more)

### Community 62 - "test_ranking.py"
Cohesion: 0.13
Nodes (10): ActionLayer, _company_of(), _deadline_of(), memories_below(), _memory_snapshot(), RecommendationSnapshot, snapshot_after_event(), _state() (+2 more)

### Community 63 - "ParsedOpening"
Cohesion: 0.15
Nodes (4): first_wave(), Wave, RippleRunner, ScriptedEngine

### Community 64 - "parsers/jd.py"
Cohesion: 0.13
Nodes (22): ADR-0014, ADR-0026, ADR-0050, ripple.retrieval hybrid search, graph expansion, I1 filtering, Graph expansion along depends_on and snapshot_of, HybridRetriever.search, index_memory and DeterministicFakeEmbedder, InMemorySearchBackend (BM25, cosine) (+14 more)

### Community 65 - "Resolver"
Cohesion: 0.12
Nodes (26): FR-16 Link verification, FR-7 Ask the user, NFR-4 Reliability, Read flow, Principle: graph decides scope, LLM decides action; core domain-agnostic, Validity-aware, graph-expanded, evidence-cited RAG, docs/03-data-model.md, Ask parks memory in PENDING_USER; subtree marked SUSPECT (+18 more)

### Community 66 - "settings.py"
Cohesion: 0.12
Nodes (13): _postgres_user_store(), create_app(), create_production_app(), app_from_env(), Settings, ConfigurationError, engine_from_url(), test_build_services_wires_an_app_without_touching_the_database() (+5 more)

### Community 67 - "test_migration_0004.py"
Cohesion: 0.11
Nodes (12): config/llm.default.toml, ADR-0018, ADR-0027, Tracing spans per LLM attempt, ripple.llm provider adapter, transport retries, prices, tracing, Anthropic provider adapter (forced tool use), RouterConfig.from_toml and prices, Tracer protocol (Noop, Logging, planned Langfuse) (+4 more)

### Community 68 - "users.py"
Cohesion: 0.08
Nodes (23): accepted_offer, cgpa_rise, cutoff_unknown, deadline_moved, exam_block, forget_cgpa, resume_update, data_sha256 (+15 more)

### Community 69 - "parsers/resume.py"
Cohesion: 0.14
Nodes (3): compute_criteria(), _num(), ProfileView

### Community 71 - "json"
Cohesion: 0.13
Nodes (22): eval-auditor subagent, ADR-0016 SQLAlchemy 2 async + Alembic, ADR-0017 arq on Redis job queue, ADR-0018 Langfuse over OpenTelemetry, Project commands, Pending ADRs: embeddings BGE-M3, LangGraph checkpointer, resume PDF parser, Technology stack, CI workflow (+14 more)

### Community 72 - "CandidateFact"
Cohesion: 0.15
Nodes (10): InMemoryLease, leased(), test_lease_acquire_succeeds_after_release(), test_lease_expires_by_the_clock_so_a_crashed_holder_does_not_block_forever(), test_lease_keys_are_independent_per_user(), test_lease_second_acquire_fails_while_held(), test_leased_context_releases_on_exception(), crash() (+2 more)

### Community 73 - "edit_memory"
Cohesion: 0.27
Nodes (15): Board, test_recommender_does_not_spread_openings_without_a_company_as_one_employer(), test_recommender_fills_title_company_deadline_and_cited_fit_reasons(), test_recommender_flags_an_opening_whose_belief_or_field_is_suspect_or_pending(), test_recommender_is_not_flagged_by_a_belief_it_does_not_use(), test_recommender_keeps_a_flagged_deadline_for_ordering_and_display(), test_recommender_leaves_out_openings_whose_deadline_has_passed(), test_recommender_never_returns_an_opening_whose_anchor_is_retired() (+7 more)

### Community 74 - "new_id"
Cohesion: 0.16
Nodes (21): ADR-0025, ADR-0055, ADR-0056, ripple.worker and ripple.notify scheduled jobs, digest and alerts, DigestService.send_daily and send_alerts, Lease (InMemoryLease, RedisLease), Transport, UserDirectory, DeliveryLog, Thresholds, render_digest, alert_kinds, render_alert (+13 more)

### Community 75 - "CandidateStore"
Cohesion: 0.22
Nodes (22): docs/02-architecture.md, Conversation agent, Curator agent, Scout agent, Tailor agent, How core stays domain-agnostic: link classes + Linker/Resolver protocols, Deployment: Docker Compose on one VPS, Ripple flow (wave by wave) (+14 more)

### Community 76 - "test_settings.py"
Cohesion: 0.14
Nodes (8): candidate_from_fact(), fact_of(), confirm_candidate(), list_candidates(), _pending_candidate(), reject_candidate(), _source_ref(), upload_resume()

### Community 77 - "test_boundaries.py"
Cohesion: 0.17
Nodes (12): find_dates(), _moment_of(), normalise_deadline(), _zone_of(), test_find_dates_does_not_read_a_word_starting_with_am_as_a_time(), test_find_dates_ignores_version_numbers_and_stray_numbers(), test_find_dates_keeps_source_offsets(), test_normalise_deadline_keeps_the_date_when_the_time_is_impossible() (+4 more)

### Community 78 - "write_new_version"
Cohesion: 0.16
Nodes (4): _require_database(), _scalar(), test_migrations_upgrade_head_on_empty_db(), test_services_postgres_is_reachable_with_pgvector_available()

### Community 79 - "me.py"
Cohesion: 0.22
Nodes (16): ChangeEvent, DPDP Act, Forget API, Invariant I7: forget cascades along dependency links, depends_on link class, Domain-adapter link-type mapping, Invariant I1: retrieval flags SUSPECT memories, Invariant I3: engine never calls an LLM (+8 more)

### Community 80 - "test_runner.py"
Cohesion: 0.17
Nodes (15): strip_email_envelope, _cut_disclaimer(), _cut_signature(), _drop_headers(), strip_email_envelope(), test_strip_email_envelope_cuts_a_signature_followed_by_a_long_disclaimer(), test_strip_email_envelope_cuts_disclaimer_and_closing(), test_strip_email_envelope_keeps_a_date_line_inside_the_jd_body() (+7 more)

### Community 81 - "checkpoints.py"
Cohesion: 0.18
Nodes (10): GoldState, VersionState, _recommend(), _store_with(), test_gold_state_reports_each_mismatch_with_the_runner_wording(), test_stub_flags_a_recommendation_built_on_a_suspect_belief(), test_stub_ignores_retired_openings_and_non_openings(), test_stub_recommends_valid_openings_and_skips_negative_eligibility() (+2 more)

### Community 82 - "test_directory.py"
Cohesion: 0.16
Nodes (19): docs/01-requirements.md, FR-10 Conversation (validity-aware RAG), FR-11 Tailor, FR-12 Memory inspector, FR-15 Export and delete all user data, FR-1 Profile setup from resume, FR-2 Openings intake with source spans, FR-3 Application tracking (+11 more)

### Community 83 - "Status"
Cohesion: 0.18
Nodes (16): FakeLLM, Invariant I4: LLM outputs schema-validated by Router, Pydantic schema validation, ripple.llm.Router, BGE-M3, Embedder contract, Hypothesis H2 (stale retrieval rate), pgvector column (migration 0004) (+8 more)

### Community 84 - "env.py"
Cohesion: 0.17
Nodes (6): LinkProposal, proposals_to_links(), LinkCreator, _mentions(), RuleLinker, _same_fact()

### Community 85 - "re"
Cohesion: 0.19
Nodes (18): explain skill, session-end skill, Seed set, docs/DEVLOG.md, Devlog 2026-10-19 Phase 0 kickoff session, Devlog 2026-10-19 Parallel round 1: seven workstreams, Devlog 2026-10-19 Phase 0 tasks 0.1-0.7 built, Devlog 2026-10-19 Phase 1 built under autonomous mandate (+10 more)

### Community 86 - "_require_aware"
Cohesion: 0.18
Nodes (8): create_telegram_link_code(), delete_me(), export_me(), get_me(), ExportOut, LinkCodeOut, MeOut, new_link_code()

### Community 87 - "reciprocal_rank_fusion"
Cohesion: 0.15
Nodes (8): Core import boundary test (ast allowlist), Injected Clock protocol (FakeClock, SystemClock), Learning page: ripple.core foundations (clock, ids, errors, boundaries), new_id(), write_new_version(), test_new_id_is_a_uuid4_string(), test_new_id_is_unique_across_calls(), go()

### Community 88 - "prompts/__init__.py"
Cohesion: 0.20
Nodes (7): VisibleMemory, fit_reasons(), _belief(), JobsRecommender, _Ranked, _spread_by_company(), _value()

### Community 89 - "list_recommendations"
Cohesion: 0.19
Nodes (17): ADR-0007, ADR-0013, ripple.core.engine the ripple engine, DependencyGraph.from_links, WaveEngine.first_wave, WaveEngine.next_wave, Visited set and depth limit, WaveEngine (human-owned learning task) (+9 more)

### Community 90 - "StalePendingStore"
Cohesion: 0.21
Nodes (17): ADR-0010, ADR-0011, ADR-0015, Phase 0 plan: Foundation, Architecture-guardian review (two passes), Deferred: embeddings (Phase 3), checkpointer (Phase 2), resume PDF parser (Phase 2), Phase 0 exit: CI green, offline tests pass, services start, Risk: no Docker locally (+9 more)

### Community 91 - "git_short_sha"
Cohesion: 0.15
Nodes (14): pyright, pytest, Python 3.12+, ruff, uv, Memory version row (supersedes_id), Alembic, psycopg 3 (+6 more)

### Community 92 - "ripple/__init__.py"
Cohesion: 0.21
Nodes (17): ADR-0060, ADR-0061, ADR-0062, ADR-0063, bench learning doc, WS-7 handover: bench, baselines, RippleBench v0, metrics, TTC harness, Baseline results table, Baseline memory strategies (ADR-0060) (+9 more)

### Community 93 - "test_migrations_match_table_metadata"
Cohesion: 0.20
Nodes (16): docs/00-vision.md, C1 Learned dependency induction, C2 Action-level evaluation, Domain scope: jobs primary, news secondary, finance generalization, What Ripple does not claim, Ripple (system), Problem: agents act on stale dependent knowledge, Thesis: explicit dependencies; code decides WHICH, LLM decides HOW (+8 more)

### Community 94 - "test_migration_0003_matches_users_tables"
Cohesion: 0.33
Nodes (13): _detector(), test_llm_detector_classifies_temporary_with_valid_to(), test_llm_detector_rejects_temporary_with_past_valid_to(), test_llm_detector_retries_temporary_without_valid_to(), test_llm_detector_update_with_known_id_is_kept(), test_llm_detector_update_with_unknown_id_becomes_new(), _context(), _resolver() (+5 more)

### Community 95 - "0001_initial.py"
Cohesion: 0.23
Nodes (9): _clock_reads(), _core_sources(), _imported_modules(), _is_allowed(), test_boundary_check_detects_a_forbidden_import(), test_clock_check_allows_injected_clock(), test_clock_check_detects_disguised_now_calls(), test_core_never_reads_the_wall_clock_outside_clock_module() (+1 more)

### Community 96 - "bench/__init__.py"
Cohesion: 0.21
Nodes (10): rules_runner(), _profile_and_opening(), test_a_skill_learned_later_reaches_fit_and_criteria_through_rule_links(), test_an_unrelated_skill_gets_no_fit_link(), test_closing_an_opening_retires_its_fields_and_beliefs_without_the_fallback(), close(), test_inspector_edit_of_the_anchor_keeps_fields_and_beliefs_attached(), test_record_opening_wave_one_keeps_every_field_without_the_fallback() (+2 more)

### Community 97 - "entrypoint.sh"
Cohesion: 0.15
Nodes (6): _cron_by_name(), test_job_context_is_read_from_arq_ctx_and_missing_context_is_a_configuration_error(), test_on_startup_refuses_to_run_without_a_database_url(), test_on_startup_refuses_to_run_without_redis_url(), test_worker_settings_register_sweep_digest_alerts_and_scout_slots(), test_worker_settings_schedule_is_utc_and_ordered_scout_sweep_digest()

### Community 98 - "ripple/api/__init__.py"
Cohesion: 0.42
Nodes (15): forget_cgpa scenario (p4_bharat, forget family), resume_update scenario (p0_jay, snapshot family), resume_update scenario (p1_dev, snapshot family), resume_update scenario (p2_harsh, snapshot family), resume_update scenario (p3_esha, snapshot family), resume_update scenario (p4_bharat, snapshot family), ForgetEvent, Invariant I7: forget deletes whole version chain and cascades (+7 more)

### Community 99 - "ripple/domains/__init__.py"
Cohesion: 0.20
Nodes (13): ADR-0045, ADR-0046, WS-4 handover: Conversation and Tailor agents, Evidence blocks with retrieval flag, Capability enum (closed list, I6), memory_saver and postgres_saver checkpoints, Code review: stale structured value blocker, tailor leaking openings, unbounded checkpoint, Contract requests: Decision.question, pending_questions, forget deletes agent thread (+5 more)

### Community 100 - "ripple/domains/jobs/__init__.py"
Cohesion: 0.18
Nodes (4): memory_saver(), postgres_saver(), test_memory_saver_is_a_fresh_checkpointer_each_time(), test_postgres_saver_is_an_async_context_manager_that_does_not_connect_on_creation()

### Community 101 - "ripple/linking/__init__.py"
Cohesion: 0.16
Nodes (6): ResolverChain, RuleResolver, __init__(), RefusingResolver, test_resolver_chain_falls_back_when_no_jobs_rule_applies(), test_resolver_chain_with_jobs_rules_never_reaches_the_fallback_for_a_rule_case()

### Community 102 - "ripple/llm/__init__.py"
Cohesion: 0.19
Nodes (4): compute_fit(), compute_reminder(), _unique(), OpeningView

### Community 103 - "providers/__init__.py"
Cohesion: 0.25
Nodes (13): _router(), test_fake_llm_records_calls(), test_router_accumulates_tokens_across_attempts(), test_router_counts_tokens_from_failed_provider_before_fallback(), test_router_falls_back_when_provider_raises(), test_router_logs_every_attempt_without_content(), test_router_raises_unavailable_when_every_provider_fails(), test_router_rejects_invalid_output_after_n_retries() (+5 more)

### Community 104 - "._check"
Cohesion: 0.24
Nodes (6): FakeUserDirectory, _imports(), _sources(), test_i6_checker_detects_a_foreign_url_and_a_forbidden_import(), test_invariant_I6_worker_and_notify_never_act_on_external_sites(), _url_literals()

### Community 105 - "schemas/__init__.py"
Cohesion: 0.21
Nodes (8): availability derived memory (available for interviews; v2 on exams, v3 after expiry), exams temporary fact (busy with exams, valid_to_days 30), looking fact memory (actively looking for internships, v1 stays VALID), reminder derived memory (Globex interview slot; resolution keep), Scenario: temporary unavailability (temporary fact ripples in, expires, ripples out, no permanent change), cgpa fact memory (7.6 -> 7.9 -> 8.1, v3 at end), eligibility derived memory (not eligible for Acme; v2 then v3 VALID), Scenario: two CGPA changes (second change must reach already-updated eligibility)

### Community 106 - "mcp_server/__init__.py"
Cohesion: 0.17
Nodes (10): graphify skill pointer (/graphify), apps/web dashboard, Code map, graphify knowledge-graph usage rules, Module src/ripple/agents, Module src/ripple/{api,mcp_server,notify,worker}, Module src/ripple/domains, Module src/ripple/linking (+2 more)

### Community 107 - "tests/agents/__init__.py"
Cohesion: 0.27
Nodes (13): ADR-0024, ADR-0035, ripple.domains.jobs.parsers resume and JD parsers, find_dates and normalise_deadline, extract_text via pypdf, spans.locate_span, cgpa_value and graduation_year, parse_jd with span-checked extraction (+5 more)

### Community 108 - "tests/conftest.py"
Cohesion: 0.23
Nodes (9): CriteriaRule, FitRule, jobs_rules(), _criteria(), _owned_contexts(), test_criteria_rule_defers_when_a_profile_parent_is_in_doubt(), test_criteria_rule_returns_none_when_every_profile_parent_is_gone(), test_criteria_rule_updates_the_cutoff_clause_when_the_cgpa_changes() (+1 more)

### Community 109 - "fakes/__init__.py"
Cohesion: 0.21
Nodes (7): MemorySnapshot, _event(), _mem(), test_target_outcomes_flattens_every_event_target_pair_in_order(), test_time_to_consistency_counts_events_and_days_until_the_state_matches_gold(), _v(), worked_trace()

### Community 110 - "tests/__init__.py"
Cohesion: 0.24
Nodes (5): Vector, process(), vector_literal(), test_vector_type_binds_sequences_as_the_pgvector_text_literal(), test_vector_type_parses_the_pgvector_text_literal()

### Community 111 - "scenarios/__init__.py"
Cohesion: 0.23
Nodes (11): ADR-0004, ADR-0017, ADR-0022, Deployment, CI and observability (WS-8), Bench smoke step informational in CI, CI pipeline: checks, services, image jobs, Docker compose with app profile, Single container image for api or worker (+3 more)

### Community 112 - "results_dir"
Cohesion: 0.26
Nodes (9): Bench smoke suite, eval-auditor, Invariant I8: results traceable to files with config and commit, results/ directory, Langfuse, OpenTelemetry, Structured stdlib logging, PyYAML (safe_load) (+1 more)

### Community 113 - "ripple"
Cohesion: 0.41
Nodes (12): WS-1 handover: jobs adapter, Pure belief computations, CGPA scale mismatch risk (4-point vs 10-point), Code review round 2 (2 blockers, 7 majors), Contract requests: OPENING_KEY, CGPA scale, batch ranges, Derivation writers, Open problems: closing an opening, re-recording a changed JD, hidden links on Intake path, eligibility with no profile fact, Profile builders and record_profile_fact (+4 more)

### Community 114 - "tests/api/__init__.py"
Cohesion: 0.35
Nodes (12): Phase 1 plan: Core engine, Phase 1 exit: scenarios pass offline, invariants tested, smoke suite runs, Risks: human-owned engine blocks scenarios; Postgres store unverified locally, Task 1.1 Core models and link policy, Task 1.2 Store protocol and in-memory store, Task 1.3 [human] Ripple engine, Task 1.4 Resolver protocol, rule-first stage, ripple runner, Task 1.5 Versioning, forget, expiry, user answers (+4 more)

### Community 115 - "tests/core/__init__.py"
Cohesion: 0.21
Nodes (5): ResumeParserAdapter, ResumeUnparseableError, LLMUnavailableError, RippleError, test_resume_parser_adapter_maps_unparseable_pdf_to_the_api_error()

### Community 116 - "tests/domains/__init__.py"
Cohesion: 0.25
Nodes (9): Invariant I6: agent never submits applications, robots.txt and rate-limit compliance, Scout, Source registry, Nightly sweep (Curator), arq, Job idempotency, Redis 7.4 (+1 more)

### Community 117 - "tests/domains/jobs/__init__.py"
Cohesion: 0.33
Nodes (11): ADR-0009, ADR-0020, Linkers, change detection and intake, Two-stage change detection, Intake.ingest flow, Linker.propose and proposals_to_links, LLM change detector (prose), LLMLinker (prompt linker.v1) (+3 more)

### Community 118 - "jobs_parsers/__init__.py"
Cohesion: 0.44
Nodes (8): _graph(), test_new_version_copies_incoming_depends_on_links(), test_new_version_copies_outgoing_links_repointed_at_latest_parent(), test_new_version_increments_and_retires_the_old_row(), test_new_version_inherits_sensitivity_confidence_and_source(), test_second_change_to_parent_reaches_the_updated_dependent(), test_snapshot_links_stay_on_the_old_version(), _update()

### Community 119 - "infra/__init__.py"
Cohesion: 0.29
Nodes (8): API layer, FastAPI, httpx, python-multipart, uvicorn, Digest renderer, Telegram Bot API, Transport protocol

### Community 120 - "tests/linking/__init__.py"
Cohesion: 0.20
Nodes (6): database_url(), migrated(), test_database_url_is_none_when_blank(), test_database_url_is_none_when_unset(), migrated(), _url()

### Community 121 - "tests/llm/__init__.py"
Cohesion: 0.36
Nodes (7): _assert_only_parent_values(), _parents(), _seed(), test_invariant_I1_recommender_never_returns_retired_and_flags_suspect_or_pending(), test_invariant_I5_derived_beliefs_cite_only_values_held_by_their_parents(), test_invariant_I5_rule_updates_cite_only_values_held_by_their_parents(), test_invariant_I5_the_adapter_never_writes_a_profile_fact_on_its_own()

### Community 122 - "tests/notify/__init__.py"
Cohesion: 0.38
Nodes (8): _scripted(), __init__(), _spec(), test_runner_forget_and_deleted_expectation(), test_runner_records_a_snapshot_after_seeding_and_after_every_event(), test_runner_rejects_an_unknown_strategy(), test_runner_reports_a_wrong_expectation_with_detail(), test_runner_reports_passing_expectations()

### Community 123 - "Writes memories and links to the store and indexes the memories in the backend."
Cohesion: 0.31
Nodes (4): run_migrations_offline(), run_migrations_online(), _run_sync(), _url()

### Community 124 - "tests/retrieval/__init__.py"
Cohesion: 0.36
Nodes (9): NFR-1 Offline tests, llm-router learning doc, FakeLLM scripted client, Fallback to next model on provider error, LLMClient protocol, Router.complete (only door to any LLM), RouterConfig and ModelSpec, Validate-and-retry loop with error feedback (+1 more)

### Community 125 - "tests/storage/__init__.py"
Cohesion: 0.39
Nodes (8): Resolver, Ablation: without rules, Invariant I2: every decision cites evidence, Jobs domain rules, LLM resolver, ResolverChain (ripple.core.resolver), RuleResolver, OpeningFieldRule (ADR-0031)

### Community 126 - "tests/worker/__init__.py"
Cohesion: 0.28
Nodes (7): valid_to field, ripple.llm.change_detector (prompt change_detector.v1), ripple.core.intake, Pending candidate facts, Invariant I5: nothing stored without confirmation, pypdf, ripple.llm.schemas.resume

### Community 127 - "ADR-0030: An opening is one anchor memory plus one structured fact per field"
Cohesion: 0.44
Nodes (8): Opening anchor memory, depends_on_fact link type, Opening field fact, InvalidObjectError, Stable opening key, OpeningAlreadyRecordedError, ParsedOpening (contract C1), record_opening

### Community 128 - "WS-2 handover: resume and JD parsers"
Cohesion: 0.47
Nodes (9): WS-2 handover: resume and JD parsers, Two candidate-to-Statement builders, CGPA scale decision: 3.8/4.0 resume becomes cgpa=3.8, Code review: year-less deadline blocker, cgpa regex reading stipend or percent, envelope, dates, numbers, spans helpers, JD/resume schemas and v1 prompts, parse_jd, parse_resume, extract_text, candidate_to_statement (+1 more)

### Community 130 - "ripple.storage PostgresStore, tables and migrations"
Cohesion: 0.39
Nodes (8): ADR-0016, ripple.storage PostgresStore, tables and migrations, Migration 0002 and drift test, PostgresStore and PostgresTransaction, Shared Store contract tests (in-memory and Postgres), Four sa.Tables (memories, links, events), version_chain walk, NFR-4 transactional commits

### Community 132 - "test_migration_0004.py"
Cohesion: 0.32
Nodes (3): _load_migration(), test_migration_0004_chains_after_0003_users(), test_migration_0004_dimension_matches_the_backend_constant()

### Community 133 - "migrated"
Cohesion: 0.25
Nodes (3): migrated(), TestPostgresStore, _url()

### Community 135 - "EventSnapshot"
Cohesion: 0.40
Nodes (3): stale_recommendation_rate(), EventSnapshot, test_stale_recommendation_rate_counts_unflagged_recommendations_on_stale_beliefs()

### Community 137 - "DecisionAction"
Cohesion: 0.53
Nodes (5): DecisionAction, OpeningFieldRule, test_opening_field_rule_follows_a_new_version_of_the_anchor(), test_opening_field_rule_keeps_a_field_while_its_anchor_is_valid(), test_opening_field_rule_retires_a_field_when_its_anchor_is_retired()

### Community 141 - "ADR-0009: A trained small model for link finding"
Cohesion: 0.67
Nodes (3): Hypothesis H3 (trained linker quality), Linker interface (rules, LLM, trained), ModernBERT / DeBERTa-v3 pair classifier

### Community 145 - "Decision: record decisions as ADRs"
Cohesion: 0.67
Nodes (3): Design freeze 2027-02-28, ADR template (Context, Decision, Alternatives, Consequences, Revisit if), Decision: record decisions as ADRs

### Community 147 - "test_invariant_I4_invalid_llm_output_is_never_applied"
Cohesion: 0.67
Nodes (3): test_invariant_I4_invalid_llm_output_is_never_applied(), __init__(), write()

## Knowledge Gaps
- **143 isolated node(s):** `ripple`, `Family type ask`, `Family type changed`, `Family type forget`, `Family type temporary` (+138 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 987 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **47 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Memory` connect `Hybrid Retrieval & Fusion` to `API Test Harness`, `Ripple Runner & Nightly Sweep`, `_require_aware`, `Scenario Benchmarks & Replay`, `Core Domain Models & Intake`, `Conversation & Tailor Agents`, `Alert Rendering & Digests`, `InMemoryStore`, `Scenario Runner & Resolution Specs`, `Conversation Agent & Evidence`, `API Routers, Auth & Services`, `Service Wiring & LLM Resolver`, `Store Contract & Transactions`, `Conversation Agent Tests & Fakes`, `Agent Wiring & Tailor Tests`, `test_invariants_agents.py`, `api/schemas.py`, `link`, `InMemoryLease`, `ChangeEvent`, `routers/resume.py`, `jobs/openings.py`, `OpeningAttribute`, `fact`, `run`, `run.py`, `Recommendation`, `jobs/rules.py`, `test_ranking.py`, `ParsedOpening`, `parsers/resume.py`, `strip_email_envelope`, `env.py`, `_require_aware`, `reciprocal_rank_fusion`, `prompts/__init__.py`, `ripple/llm/__init__.py`, `tests/conftest.py`, `tests/llm/__init__.py`?**
  _High betweenness centrality (0.113) - this node is a cross-community bridge._
- **Are the 37 inferred relationships involving `InMemoryStore` (e.g. with `ScenarioRunner` and `test_tailor_refuses_an_unusable_opening()`) actually correct?**
  _`InMemoryStore` has 37 INFERRED edges - model-reasoned connections that need verification._
- **What connects `ripple`, `Family type ask`, `Family type changed` to the rest of the system?**
  _143 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `API Test Harness` be split into smaller, more focused modules?**
  _Cohesion score 0.0540045766590389 - nodes in this community are weakly interconnected._
- **Why does `docs/03-data-model.md` connect `Resolver` to `DependencyGraph`, `ripple/api/__init__.py`, `Change Detection & Statement Intake`, `me.py`, `test_directory.py`, `ResumeCandidate`, `re`, `test_migrations_match_table_metadata`?**
  _High betweenness centrality (0.091) - this node is a cross-community bridge._
- **Are the 114 inferred relationships involving `Memory` (e.g. with `_company_of()` and `_deadline_of()`) actually correct?**
  _`Memory` has 114 INFERRED edges - model-reasoned connections that need verification._
- **Should `Ripple Runner & Nightly Sweep` be split into smaller, more focused modules?**
  _Cohesion score 0.06771929824561404 - nodes in this community are weakly interconnected._