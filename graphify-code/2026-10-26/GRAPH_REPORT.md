# Graph Report - RIPPLE  (2026-10-23)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 3165 nodes · 12090 edges · 127 communities (86 shown, 41 thin omitted)
- Extraction: 82% EXTRACTED · 18% INFERRED · 0% AMBIGUOUS · INFERRED: 2197 edges (avg confidence: 0.93)
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
- FakeLLM
- router.py
- record_opening
- ConfigurationError
- postgres.py
- DecisionAction
- test_jobs.py
- Store
- FakeClock
- recommendation
- Memory
- test_bench_generate.py
- generate.py
- Resolution
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
- test_migrations_match_table_metadata
- test_migration_0003_matches_users_tables
- entrypoint.sh
- results_dir
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
- `test_on_startup_refuses_to_run_without_a_database_url()` --uses--> `ConfigurationError`  [INFERRED]
  tests/worker/test_settings.py → src/ripple/core/errors.py
- `test_on_startup_refuses_to_run_without_redis_url()` --uses--> `ConfigurationError`  [INFERRED]
  tests/worker/test_settings.py → src/ripple/core/errors.py
- `test_unparseable_resume_error_is_a_ripple_error()` --uses--> `RippleError`  [INFERRED]
  tests/domains/jobs_parsers/test_resume_parser.py → src/ripple/core/errors.py
- `test_system_clock_returns_aware_utc()` --uses--> `SystemClock`  [INFERRED]
  tests/core/test_clock.py → src/ripple/core/clock.py
- `FailingResolver` --uses--> `LLMUnavailableError`  [INFERRED]
  tests/api/fakes.py → src/ripple/core/errors.py

## Import Cycles
- None detected.

## Communities (127 total, 41 thin omitted)

### Community 0 - "API Test Harness"
Cohesion: 0.04
Nodes (63): candidate_fact(), FailingResolver, RecordingOpeningRecorder, ScriptedDetector, ScriptedOpeningParser, ScriptedRecommendations, ScriptedResumeParser, SimpleCandidateStatements (+55 more)

### Community 1 - "Ripple Runner & Nightly Sweep"
Cohesion: 0.05
Nodes (68): answer_no_longer_holds(), answer_with_correction(), confirm_still_holds(), NotPendingError, _pending(), _restore_parked(), Decision, TriggerKind (+60 more)

### Community 2 - "Core Domain Models & Intake"
Cohesion: 0.06
Nodes (8): retrieved_block(), Clock, AnswerVerdict, Claim, IntentVerdict, test_intent_verdict_accepts_structured_on_a_corrected_answer(), test_intent_verdict_rejects_payload_that_does_not_match_the_intent(), ScriptedEngine

### Community 3 - "Scenario Benchmarks & Replay"
Cohesion: 0.06
Nodes (37): EventSpec, load_scenario(), ResolutionSpec, ScenarioOutcome, ScenarioRunner, ScenarioSpec, validate_scenario(), AppendOnlyStrategy (+29 more)

### Community 4 - "In-Memory Retrieval & Indexing"
Cohesion: 0.05
Nodes (30): Embedder, SearchBackend, embed_memory(), index_memory(), cosine_similarity(), _Document, InMemorySearchBackend, searchable_text() (+22 more)

### Community 5 - "Change Detection & Statement Intake"
Cohesion: 0.07
Nodes (35): ChangeClassification, ChangeDetector, ChangeKind, detect_structured_update(), Intake, IntakeResult, Statement, Linker (+27 more)

### Community 6 - "API Wiring & LLM Services"
Cohesion: 0.06
Nodes (28): OpeningParserAdapter, ResumeParserAdapter, create_app(), create_production_app(), ResumeParser, ResumeUnparseableError, app_from_env(), build_services() (+20 more)

### Community 7 - "Hybrid Retrieval & Fusion"
Cohesion: 0.10
Nodes (44): RetrievalPath, RetrievedMemory, FusedHit, candidate_count(), _Collected, _Frontier, HybridRetriever, _source_evidence() (+36 more)

### Community 8 - "Conversation & Tailor Agents"
Cohesion: 0.06
Nodes (22): Capability, Citation, _compose_answer(), ConversationAgent, ConversationReply, ConversationState, _numbers(), PendingQuestion (+14 more)

### Community 9 - "Benchmark Metrics & Gold State"
Cohesion: 0.08
Nodes (31): ConvergenceRecord, correct_updates(), cost_per_ripple(), questions_asked(), stale_kept(), stale_recommendation_rate(), stale_retrieval_rate(), target_outcomes() (+23 more)

### Community 10 - "Postgres Store"
Cohesion: 0.06
Nodes (10): ForgetEvent, _event(), _forget_row(), _link(), _link_row(), _memory(), _memory_row(), PostgresStore (+2 more)

### Community 11 - "Search Backends (Postgres & In-Memory)"
Cohesion: 0.10
Nodes (35): SearchHit, PostgresSearchBackend, test_list_hides_retired_and_flags_suspect_and_pending(), run(), memory(), _indexed(), test_dense_orders_by_cosine_similarity(), test_dense_respects_k() (+27 more)

### Community 12 - "Telegram Notifications"
Cohesion: 0.07
Nodes (26): MessageTooLongError, NotifyError, TelegramSendError, _mapping(), _optional_int(), _parse_body(), _RedactToken, TelegramTransport (+18 more)

### Community 13 - "Alert Rendering & Digests"
Cohesion: 0.09
Nodes (35): AlertKind, Thresholds, Alert, alert_kinds(), _alert_reason(), alerts_for(), _deadline(), _hours() (+27 more)

### Community 14 - "InMemoryStore"
Cohesion: 0.10
Nodes (23): forget(), MemoryNotFoundError, _seed(), test_forget_deletes_whole_version_chain_and_depends_on_cascade(), test_forget_from_a_newer_version_deletes_the_older_ones_too(), test_forget_leaves_no_dangling_links(), test_forget_leaves_unrelated_memories_and_links_alone(), test_forget_removes_snapshot_link_but_keeps_the_dependent() (+15 more)

### Community 15 - "FakeLLM"
Cohesion: 0.10
Nodes (33): UnparseableResumeError, parse_jd(), extract_text(), build_pdf(), pdf_with_lines(), resume_reply(), router_for(), text_stream() (+25 more)

### Community 16 - "router.py"
Cohesion: 0.08
Nodes (11): CompletionRequest, CompletionResult, LLMClient, OpenAIClient, Completion, _summarise(), _Usage, NoopTracer (+3 more)

### Community 17 - "record_opening"
Cohesion: 0.10
Nodes (28): record_opening(), make_runner(), __init__(), parsed_acme(), RefusingResolver, rules_runner(), test_cgpa_rise_updates_eligibility_and_criteria_through_the_rules_without_an_llm(), test_deadline_extension_updates_the_reminder_and_leaves_eligibility_alone() (+20 more)

### Community 18 - "ConfigurationError"
Cohesion: 0.08
Nodes (24): _postgres_user_store(), Settings, ConfigurationError, LoggingTracer, database_url(), engine_from_url(), job_context_from_env(), router_from_env() (+16 more)

### Community 19 - "postgres.py"
Cohesion: 0.08
Nodes (5): upgrade(), upgrade(), Base, content_tsvector(), _extend_metadata()

### Community 20 - "DecisionAction"
Cohesion: 0.16
Nodes (36): DecisionAction, compute_eligibility(), EligibilityRule, OpeningFieldRule, belief_memory(), context(), opening_fact(), _owned_contexts() (+28 more)

### Community 21 - "test_jobs.py"
Cohesion: 0.11
Nodes (26): JobContext, daily_digest(), DeliveryReport, hourly_alerts(), JobFailedForUsersError, nightly_sweep(), scout_run(), SweepReport (+18 more)

### Community 22 - "Store"
Cohesion: 0.10
Nodes (18): Store, Transaction, StoreContract, duplicate(), dangling(), complete(), write(), delete() (+10 more)

### Community 23 - "FakeClock"
Cohesion: 0.17
Nodes (33): memory_saver(), test_answer_question_answered_meanwhile_replies_instead_of_raising(), test_answer_question_corrected_updates_the_structured_value(), test_answer_question_corrected_writes_a_new_version_and_ripples(), test_answer_question_for_an_unknown_question_writes_nothing(), test_answer_question_no_longer_holds_retires_and_ripples(), test_answer_question_still_holds_restores_the_memory(), test_ask_answers_from_retrieved_evidence_with_citations() (+25 more)

### Community 24 - "recommendation"
Cohesion: 0.12
Nodes (23): InMemoryDeliveryLog, test_fake_clock_advance_moves_now(), test_fake_clock_set_jumps_to_moment(), failing_transport(), recommendation(), _service(), test_send_alerts_does_not_record_when_the_transport_fails(), test_send_alerts_does_not_repeat_an_alert_within_the_cooldown() (+15 more)

### Community 25 - "Memory"
Cohesion: 0.08
Nodes (11): _why(), Link, Memory, StoreReader, _derive(), DerivedBeliefs, _existing(), _write() (+3 more)

### Community 26 - "test_bench_generate.py"
Cohesion: 0.10
Nodes (26): check_data(), data_hash(), generate(), Generated, load_jobs_v0(), main(), make_personas(), ManifestEntry (+18 more)

### Community 27 - "generate.py"
Cohesion: 0.18
Nodes (23): accepted_offer(), build_scenario(), _cgpa_memory(), cgpa_rise(), cutoff_unknown(), deadline_moved(), exam_block(), forget_cgpa() (+15 more)

### Community 28 - "Resolution"
Cohesion: 0.09
Nodes (13): AliasResolver, Resolution, ResolutionContext, RuleResolver, FitRule, jobs_rules(), _opening_belief(), ReminderRule (+5 more)

### Community 29 - "pytest"
Cohesion: 0.09
Nodes (31): test_inmemory_store_refuses_nested_transactions(), test_inmemory_store_refuses_writes_outside_a_transaction(), test_decision_keep_forbids_new_version_id(), test_decision_update_requires_new_version_id(), test_fact_builder_sets_structured_fields(), test_link_rejects_self_dependency(), test_memory_cannot_supersede_itself(), test_memory_is_immutable() (+23 more)

### Community 30 - "test_invariants_agents.py"
Cohesion: 0.13
Nodes (25): _forbidden(), _imports(), test_invariant_I4_agent_rejects_invalid_llm_output(), test_invariant_I4_conversation_rejects_invalid_answer_output(), test_invariant_I4_tailor_rejects_invalid_output(), test_invariant_I5_tailor_cites_only_existing_memories(), test_invariant_I6_agents_expose_no_submit_or_browser_tool(), test_invariant_I6_import_check_detects_a_breach() (+17 more)

### Community 31 - "digest.py"
Cohesion: 0.10
Nodes (7): RecommendationSource, DeliveryLog, MessageReceipt, Transport, UserDirectory, DigestService, Lease

### Community 32 - "api/schemas.py"
Cohesion: 0.11
Nodes (19): post_statement(), CandidatesOut, ConfirmOut, EditIn, ExportOut, ForgetOut, HistoryOut, IntakeOut (+11 more)

### Community 33 - "User"
Cohesion: 0.09
Nodes (9): _open_event_ids(), PostgresUserStore, User, _user(), TestPostgresCandidateStore, migrated(), TestPostgresUserStore, truncate_owned() (+1 more)

### Community 34 - "DependencyGraph"
Cohesion: 0.16
Nodes (20): DependencyGraph, WaveEngine, WaveOutcome, _chain(), test_engine_changed_outcome_seeds_the_next_wave(), test_engine_first_wave_is_direct_dependents_of_seeds(), test_engine_first_wave_never_includes_a_seed(), test_engine_first_wave_returns_none_when_seeds_have_no_dependents() (+12 more)

### Community 35 - "profile.py"
Cohesion: 0.10
Nodes (22): Sensitivity, _live_profile_facts(), profile_content(), profile_fact(), profile_memory(), profile_statement(), record_profile_fact(), _rule_links() (+14 more)

### Community 36 - "link"
Cohesion: 0.10
Nodes (25): _ids(), test_detail_explains_why_skipping_history_links_and_keeping_snapshots(), run(), test_edit_writes_a_user_edit_version_that_ripples(), run(), test_forget_cascades_and_is_the_only_deletion_path(), run(), run() (+17 more)

### Community 37 - "RouterConfig"
Cohesion: 0.10
Nodes (18): router_from_settings(), ModelPrice, ModelSpec, RouterConfig, router(), test_models_for_empty_list_raises_configuration_error(), test_models_for_returns_primary_then_fallbacks_in_order(), test_models_for_unknown_task_raises_configuration_error() (+10 more)

### Community 38 - "InMemoryUserStore"
Cohesion: 0.08
Nodes (6): ApiToken, _require_aware(), TelegramLinkCode, InMemoryUserStore, TestInMemoryCandidateStore, TestInMemoryUserStore

### Community 39 - "InMemoryLease"
Cohesion: 0.10
Nodes (13): InMemoryLease, leased(), RedisLease, test_lease_acquire_succeeds_after_release(), test_lease_expires_by_the_clock_so_a_crashed_holder_does_not_block_forever(), test_lease_keys_are_independent_per_user(), test_lease_second_acquire_fails_while_held(), test_leased_context_releases_on_exception() (+5 more)

### Community 40 - "ChangeEvent"
Cohesion: 0.08
Nodes (5): RippleStrategy, ChangeEvent, ChangeEventNotFoundError, _event_row(), PostgresTransaction

### Community 41 - "anthropic.py"
Cohesion: 0.12
Nodes (14): AnthropicClient, AnthropicLike, _default_factory(), _Messages, _tool_input(), FakeMessages, FakeSDK, _request() (+6 more)

### Community 42 - "auth.py"
Cohesion: 0.10
Nodes (11): current_user(), not_found(), owned_memory(), _unauthorized(), answer_question(), list_questions(), AnswerIn, AnswerOut (+3 more)

### Community 43 - "RippleRunner"
Cohesion: 0.13
Nodes (5): one_shot_engine(), first_wave(), Wave, RippleRunner, first_wave()

### Community 44 - "routers/resume.py"
Cohesion: 0.12
Nodes (10): candidate_from_fact(), fact_of(), confirm_candidate(), list_candidates(), _pending_candidate(), reject_candidate(), _source_ref(), upload_resume() (+2 more)

### Community 45 - "jobs/openings.py"
Cohesion: 0.12
Nodes (13): InvalidObjectError, field_memory(), find_opening(), OpeningAlreadyRecordedError, _validate(), _validate_opening(), anchor_structured(), _facts() (+5 more)

### Community 46 - "OpeningAttribute"
Cohesion: 0.22
Nodes (25): _summary(), OpeningAttribute, jd_reply(), _field(), _parse(), test_parse_jd_adds_deadline_from_regex_when_model_missed_it(), test_parse_jd_builds_summary_from_title_and_company_not_from_the_model(), test_parse_jd_coerces_cutoff_to_float_and_batch_to_int() (+17 more)

### Community 47 - "fact"
Cohesion: 0.14
Nodes (26): run(), test_invariant_I1_api_never_returns_retired(), run(), test_invariant_I7_api_deletes_only_through_forget_with_a_forget_event(), run(), test_edit_of_a_pending_memory_is_refused_and_points_at_answers(), run(), test_list_filters_by_kind_and_status() (+18 more)

### Community 48 - "run"
Cohesion: 0.21
Nodes (21): derive_for_opening(), run(), _parent_ids(), _setup(), test_derive_criteria_from_profile_facts_links_criteria_from(), test_derive_criteria_is_none_for_an_empty_profile(), test_derive_each_belief_opens_its_own_completed_change_event(), test_derive_eligibility_is_false_when_cgpa_is_below_the_cutoff() (+13 more)

### Community 49 - "UserStore"
Cohesion: 0.20
Nodes (5): link_telegram(), UserStore, _code(), _user(), UserStoreContract

### Community 50 - "LinkTypeRegistry"
Cohesion: 0.16
Nodes (16): _cascade(), _forget(), ForgetBehaviour, LinkPolicy, LinkTypeRegistry, policy_for(), UnknownLinkTypeError, LinkClass (+8 more)

### Community 51 - "run.py"
Cohesion: 0.19
Nodes (16): load_manifest(), _data_description(), _display(), main(), _report(), run_dir_for(), run_suite(), RunConfig (+8 more)

### Community 52 - "Recommendation"
Cohesion: 0.14
Nodes (9): VisibleMemory, fit_reasons(), _belief(), JobsRecommender, _Ranked, _spread_by_company(), _value(), opening_key() (+1 more)

### Community 53 - "jobs/rules.py"
Cohesion: 0.14
Nodes (7): Belief, compute_fit(), compute_reminder(), _unique(), _compare(), OpeningView, DerivedAttribute

### Community 54 - "fakes/clock.py"
Cohesion: 0.11
Nodes (10): test_fake_clock_rejects_naive_datetimes(), test_fake_clock_satisfies_clock_protocol(), test_system_clock_returns_aware_utc(), SentMessage, FakeUserDirectory, _imports(), _sources(), test_i6_checker_detects_a_foreign_url_and_a_forbidden_import() (+2 more)

### Community 55 - "dates.py"
Cohesion: 0.14
Nodes (14): DateMatch, find_dates(), _moment_of(), normalise_deadline(), _zone_of(), _regex_deadline(), test_find_dates_does_not_read_a_word_starting_with_am_as_a_time(), test_find_dates_ignores_version_numbers_and_stray_numbers() (+6 more)

### Community 56 - "manifest.json"
Cohesion: 0.08
Nodes (23): accepted_offer, cgpa_rise, cutoff_unknown, deadline_moved, exam_block, forget_cgpa, resume_update, data_sha256 (+15 more)

### Community 57 - "replay.py"
Cohesion: 0.14
Nodes (9): ActionLayer, _company_of(), _deadline_of(), memories_below(), _memory_snapshot(), MemorySnapshot, snapshot_after_event(), _state() (+1 more)

### Community 58 - "core/errors.py"
Cohesion: 0.12
Nodes (8): OpeningUnparseableError, _handler(), handle(), install_error_handlers(), InvariantViolationError, LLMOutputInvalidError, LLMUnavailableError, RippleError

### Community 59 - "ProfileView"
Cohesion: 0.13
Nodes (11): compute_criteria(), _num(), derive_criteria(), CriteriaRule, _in_doubt(), _owns(), ProfileView, _criteria() (+3 more)

### Community 60 - "jobs/test_openings.py"
Cohesion: 0.13
Nodes (16): opening_memories(), _by_value(), _latest(), one(), opening_subject(), field(), span(), _record() (+8 more)

### Community 61 - "ResumeCandidate"
Cohesion: 0.15
Nodes (6): _candidate(), CandidateStatus, PostgresCandidateStore, ResumeCandidate, _row(), InMemoryCandidateStore

### Community 62 - "test_ranking.py"
Cohesion: 0.27
Nodes (15): Board, test_recommender_does_not_spread_openings_without_a_company_as_one_employer(), test_recommender_fills_title_company_deadline_and_cited_fit_reasons(), test_recommender_flags_an_opening_whose_belief_or_field_is_suspect_or_pending(), test_recommender_is_not_flagged_by_a_belief_it_does_not_use(), test_recommender_keeps_a_flagged_deadline_for_ordering_and_display(), test_recommender_leaves_out_openings_whose_deadline_has_passed(), test_recommender_never_returns_an_opening_whose_anchor_is_retired() (+7 more)

### Community 63 - "ParsedOpening"
Cohesion: 0.14
Nodes (9): OpeningRecorderAdapter, OpeningParser, OpeningRecorder, OpeningWritten, ParsedField, ParsedOpening, _opening(), field() (+1 more)

### Community 64 - "parsers/jd.py"
Cohesion: 0.16
Nodes (13): _agree(), _coerce(), _cross_check(), _dropped(), _fence_safe(), _reconcile(), _regex_cgpa(), _role_type() (+5 more)

### Community 65 - "Resolver"
Cohesion: 0.13
Nodes (5): CheckEverythingStrategy, CountingResolver, _NoPropagation, MemoryIndexer, Resolver

### Community 66 - "settings.py"
Cohesion: 0.16
Nodes (10): daily_digest_job(), hourly_alerts_job(), job_context(), nightly_sweep_job(), on_shutdown(), on_startup(), redis_settings_from_env(), scout_run_job() (+2 more)

### Community 67 - "test_migration_0004.py"
Cohesion: 0.14
Nodes (8): Vector, process(), vector_literal(), _load_migration(), test_migration_0004_chains_after_0003_users(), test_migration_0004_dimension_matches_the_backend_constant(), test_vector_type_binds_sequences_as_the_pgvector_text_literal(), test_vector_type_parses_the_pgvector_text_literal()

### Community 68 - "users.py"
Cohesion: 0.17
Nodes (7): create_user(), main(), hash_token(), new_link_code(), new_raw_token(), test_create_user_prints_the_token_once_and_stores_only_its_hash(), test_create_user_without_a_database_url_fails_clearly()

### Community 69 - "parsers/resume.py"
Cohesion: 0.18
Nodes (8): cgpa_value(), first_number(), graduation_year(), _coerce(), _dropped(), parse_resume(), ResumeCandidate, ResumeParse

### Community 70 - "strip_email_envelope"
Cohesion: 0.18
Nodes (14): _cut_disclaimer(), _cut_signature(), _drop_headers(), strip_email_envelope(), test_strip_email_envelope_cuts_a_signature_followed_by_a_long_disclaimer(), test_strip_email_envelope_cuts_disclaimer_and_closing(), test_strip_email_envelope_keeps_a_date_line_inside_the_jd_body(), test_strip_email_envelope_keeps_a_double_dash_divider_above_long_content() (+6 more)

### Community 71 - "json"
Cohesion: 0.29
Nodes (14): _detector(), test_llm_detector_classifies_temporary_with_valid_to(), test_llm_detector_rejects_temporary_with_past_valid_to(), test_llm_detector_retries_temporary_without_valid_to(), test_llm_detector_update_with_known_id_is_kept(), test_llm_detector_update_with_unknown_id_becomes_new(), _context(), _resolver() (+6 more)

### Community 72 - "CandidateFact"
Cohesion: 0.16
Nodes (9): CandidateStatementsAdapter, CandidateStatements, _candidate(), candidate_to_statement(), CandidateFact, test_candidate_statements_adapter_marks_the_statement_as_an_inspector_edit(), candidate(), test_candidate_to_statement_builds_a_profile_fact_statement() (+1 more)

### Community 73 - "edit_memory"
Cohesion: 0.18
Nodes (5): edit_memory(), forget_memory(), get_memory(), list_memories(), _mentions()

### Community 74 - "new_id"
Cohesion: 0.19
Nodes (7): post_opening(), OpeningIn, OpeningOut, ParsedFieldOut, new_id(), test_new_id_is_a_uuid4_string(), test_new_id_is_unique_across_calls()

### Community 75 - "CandidateStore"
Cohesion: 0.25
Nodes (3): CandidateStore, _candidate(), CandidateStoreContract

### Community 76 - "test_settings.py"
Cohesion: 0.15
Nodes (6): _cron_by_name(), test_job_context_is_read_from_arq_ctx_and_missing_context_is_a_configuration_error(), test_on_startup_refuses_to_run_without_a_database_url(), test_on_startup_refuses_to_run_without_redis_url(), test_worker_settings_register_sweep_digest_alerts_and_scout_slots(), test_worker_settings_schedule_is_utc_and_ordered_scout_sweep_digest()

### Community 77 - "test_boundaries.py"
Cohesion: 0.25
Nodes (9): _clock_reads(), _core_sources(), _imported_modules(), _is_allowed(), test_boundary_check_detects_a_forbidden_import(), test_clock_check_allows_injected_clock(), test_clock_check_detects_disguised_now_calls(), test_core_never_reads_the_wall_clock_outside_clock_module() (+1 more)

### Community 78 - "write_new_version"
Cohesion: 0.15
Nodes (4): decision(), write_new_version(), go(), go()

### Community 79 - "me.py"
Cohesion: 0.22
Nodes (5): create_telegram_link_code(), delete_me(), export_me(), get_me(), MeOut

### Community 80 - "test_runner.py"
Cohesion: 0.22
Nodes (11): _recommend(), _store_with(), test_stub_ignores_retired_openings_and_non_openings(), _scripted(), __init__(), _spec(), test_runner_forget_and_deleted_expectation(), test_runner_records_a_snapshot_after_seeding_and_after_every_event() (+3 more)

### Community 81 - "checkpoints.py"
Cohesion: 0.20
Nodes (3): postgres_saver(), test_memory_saver_is_a_fresh_checkpointer_each_time(), test_postgres_saver_is_an_async_context_manager_that_does_not_connect_on_creation()

### Community 83 - "Status"
Cohesion: 0.31
Nodes (8): Status, visible_for_retrieval(), test_invariant_I1_retrieval_never_returns_retired_and_flags_suspect(), test_memory_defaults_to_valid_version_one(), test_visible_for_retrieval_hides_flagged_without_opt_in(), test_visible_for_retrieval_keeps_input_order(), test_visible_for_retrieval_never_shows_retired_even_with_opt_in(), SearchCall

### Community 84 - "env.py"
Cohesion: 0.31
Nodes (4): run_migrations_offline(), run_migrations_online(), _run_sync(), _url()

### Community 85 - "re"
Cohesion: 0.36
Nodes (5): locate_span(), test_locate_span_falls_back_to_case_insensitive_match(), test_locate_span_finds_exact_substring_with_offsets(), test_locate_span_returns_none_when_quote_is_absent(), test_locate_span_tolerates_line_breaks_the_model_read_as_spaces()

### Community 87 - "reciprocal_rank_fusion"
Cohesion: 0.44
Nodes (7): reciprocal_rank_fusion(), _hits(), test_fusion_equal_scores_break_ties_by_memory_id(), test_fusion_item_in_both_lists_beats_single_list_leaders(), test_fusion_of_nothing_is_nothing(), test_fusion_single_list_preserves_rank_order(), test_fusion_via_is_the_path_that_ranked_the_item_best()

## Knowledge Gaps
- **1 isolated node(s):** `ripple`
  These have ≤1 connection - possible missing edges. (Counts symbols only; 841 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **41 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Memory` connect `Memory` to `API Test Harness`, `Ripple Runner & Nightly Sweep`, `Core Domain Models & Intake`, `Scenario Benchmarks & Replay`, `In-Memory Retrieval & Indexing`, `Change Detection & Statement Intake`, `API Wiring & LLM Services`, `Hybrid Retrieval & Fusion`, `Conversation & Tailor Agents`, `Postgres Store`, `Search Backends (Postgres & In-Memory)`, `InMemoryStore`, `record_opening`, `postgres.py`, `DecisionAction`, `Store`, `FakeClock`, `Resolution`, `pytest`, `test_invariants_agents.py`, `api/schemas.py`, `profile.py`, `link`, `ChangeEvent`, `auth.py`, `RippleRunner`, `jobs/openings.py`, `fact`, `Recommendation`, `jobs/rules.py`, `replay.py`, `ProfileView`, `jobs/test_openings.py`, `Resolver`, `write_new_version`, `Status`, `_require_aware`, `StalePendingStore`?**
  _High betweenness centrality (0.094) - this node is a cross-community bridge._
- **Are the 37 inferred relationships involving `InMemoryStore` (e.g. with `ScenarioRunner` and `test_tailor_refuses_an_unusable_opening()`) actually correct?**
  _`InMemoryStore` has 37 INFERRED edges - model-reasoned connections that need verification._
- **What connects `ripple` to the rest of the system?**
  _1 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `API Test Harness` be split into smaller, more focused modules?**
  _Cohesion score 0.044438114228742345 - nodes in this community are weakly interconnected._
- **Why does `Status` connect `Status` to `API Test Harness`, `Ripple Runner & Nightly Sweep`, `Core Domain Models & Intake`, `Scenario Benchmarks & Replay`, `Change Detection & Statement Intake`, `Hybrid Retrieval & Fusion`, `Conversation & Tailor Agents`, `Postgres Store`, `Search Backends (Postgres & In-Memory)`, `InMemoryStore`, `record_opening`, `postgres.py`, `DecisionAction`, `Store`, `FakeClock`, `Memory`, `generate.py`, `Resolution`, `pytest`, `test_invariants_agents.py`, `api/schemas.py`, `profile.py`, `link`, `auth.py`, `RippleRunner`, `jobs/openings.py`, `fact`, `run`, `jobs/rules.py`, `replay.py`, `ProfileView`, `jobs/test_openings.py`, `test_ranking.py`, `ParsedOpening`, `Resolver`, `edit_memory`, `write_new_version`, `test_runner.py`, `StalePendingStore`?**
  _High betweenness centrality (0.057) - this node is a cross-community bridge._
- **Are the 114 inferred relationships involving `Memory` (e.g. with `_company_of()` and `_deadline_of()`) actually correct?**
  _`Memory` has 114 INFERRED edges - model-reasoned connections that need verification._
- **Should `Ripple Runner & Nightly Sweep` be split into smaller, more focused modules?**
  _Cohesion score 0.05126945126945127 - nodes in this community are weakly interconnected._