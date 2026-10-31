# Graph Report - RIPPLE  (2026-10-31)

## Corpus Check
- 742 files · ~419,763 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 26 file(s) not represented in the graph (top: (none) 7, .jsonl 3, .toml 3)

## Summary
- 8737 nodes · 29250 edges · 330 communities (255 shown, 75 thin omitted)
- Extraction: 82% EXTRACTED · 18% INFERRED · 0% AMBIGUOUS · INFERRED: 5381 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- QuestionsView.tsx
- FakeClock
- generate_finance.py
- ScenarioRunner
- Feedback
- Link
- test_telegram_webhook.py
- fact
- agents/conversation.py
- test_bench_metrics.py
- Postgres Store
- pytest
- ConfigurationError
- Alert Rendering & Digests
- InMemoryStore
- FakeLLM
- Router
- run
- test_handcheck.py
- sqlalchemy
- DecisionAction
- test_settings.py
- Store
- test_conversation.py
- recommendation
- scout.py
- test_bench_generate.py
- generate.py
- Resolution
- test_numbers.py
- build
- DeliveryLog
- api/schemas.py
- User
- RippleRunner
- types.ts
- asyncio
- RouterConfig
- raw_text_update
- job_context_from_env
- What was built
- anthropic.py
- TellView.tsx
- tools.py
- routers/resume.py
- record_opening
- OpeningAttribute
- models.py
- test_i8_detector.py
- users.py
- LinkTypeRegistry
- run.py
- jobs/schemas.py
- Harness
- evaluate.py
- dates.py
- manifest.json
- collections_abc
- answers.py
- Kind
- test_fetcher.py
- InMemorySearchBackend
- test_ranking.py
- pathlib
- parsers/jd.py
- jobs_pairs.py
- jobs.py
- test_migration_0004.py
- tracks.py
- parsers/resume.py
- strip_email_envelope
- json
- pilot/report.py
- api/wiring.py
- i8.py
- summary.py
- package.json
- test_boundaries.py
- test_hardening_ratelimit.py
- me.py
- test_stale.py
- checkpoints.py
- asyncio
- fixture
- logging.py
- TelegramChannel
- _require_aware
- Memory
- PairMemory
- User
- TelegramBotApi
- Services
- provenance_problems
- test_hardening_uploads_postgres.py
- FeedbackStore
- MemoryDetailView.tsx
- fetcher.py
- entrypoint.sh
- helpers.tsx
- test_run_once.py
- FeedbackKind
- MapView.tsx
- ripple
- sources/__init__.py
- useApi
- resolve_all
- keyboards.py
- load_scenario
- RedisLease
- tracing.py
- InMemoryDeliveryLog
- Linker
- Clock
- test_inbound_telegram_api.py
- compilerOptions
- test_inbound_render.py
- selectors.py
- ADR-0027: Anthropic SDK as the first provider adapter; structured output via forced tool use
- test_local_run.py
- storage/feedback.py
- .__call__
- derive_for_opening
- RobotsPolicy
- Ripple — instructions for Claude Code
- 2. The original plan, item by item
- test_report.py
- Ordered tasks (each one session; tests first; [human] marks author-owned work)
- LabelledPair
- Ordered tasks
- worker/wiring.py
- test_hardening_health.py
- 3. How it works
- test_run_v1.py
- finance_v1/manifest.json
- Workstreams (dependency order, then value)
- test_telegram_transport.py
- news_v1/manifest.json
- Data model
- build_site
- schema.d.ts
- Architecture
- Template
- paper/registry.py
- inbound/wiring.py
- ADR-0062: Time-to-consistency replay harness with per-event snapshots
- Evaluation
- test_finance_pairs.py
- SessionProvider.tsx
- Production plan — build the whole product once, deploy-ready
- Proposal 0001: Rule-first resolution
- Proposal 0002: Structure-derived silver labels and a candidate pre-filter for the link finder
- Proposal 0003: Time-to-consistency as an action-level metric
- Vision
- Roadmap
- WS-17 handover: paper and thesis plumbing, the I8 check
- bench: strategies, RippleBench v0 generator, replay harness, metric interfaces
- ripple.core.engine — the ripple engine (your module)
- Paper outline: Ripple — learned dependency links keep agent memory consistent
- identity.py
- StructuredFact
- test_trained_linker.py
- ripple.api — identity, inspector, confirmation flow, export and delete
- UserDirectoryAdapter
- jobs/vocabulary.py
- ScoutCriteria
- TokenBucket
- devDependencies
- ripple.core: writes, runner, versioning, forget, sweep, answers
- dedupe.py
- target_outcomes
- test_generators.py
- migrate
- Pilot consent (draft for departmental review)
- Ripple dashboard (apps/web)
- no-business-logic.test.ts
- ADR-NNNN: <title>
- ADR-0001: Record decisions as ADRs
- ADR-0002: Job hunting is the primary domain
- ADR-0003: The graph decides scope; the LLM decides action
- ADR-0004: PostgreSQL + pgvector with in-process traversal
- ADR-0005: LangGraph for agents; core stays framework-free
- ADR-0006: Expose memory tools over MCP
- ADR-0007: Retire, never silently delete
- ADR-0008: The human applies; allowed sources only
- ADR-0009: A trained small model for link finding
- ADR-0010: Provider-agnostic LLM router with structured outputs
- ADR-0011: Python tooling: uv, ruff, pyright, pytest
- ADR-0012: Evaluation-first development
- ADR-0013: Wave-by-wave ripple over core link classes
- ADR-0014: Memory versions are rows; dependency links are copied to the new version
- ADR-0015: Every change is a memory write; temporary facts self-expire
- ADR-0016: SQLAlchemy 2 (async, psycopg) + Alembic, in a storage package outside core
- ADR-0017: Background jobs with arq on Redis
- ADR-0018: Observability with Langfuse over OpenTelemetry; structured logging until then
- ADR-0020: Change detection: deterministic for structured facts, LLM for prose
- ADR-0021: Scenario files are YAML, parsed with PyYAML
- ADR-0022: Web API stack: FastAPI, uvicorn, httpx, python-multipart
- ADR-0023: LangGraph dependency and Postgres checkpointer
- ADR-0024: Resume parsing: pypdf text extraction, LLM structuring, user confirmation
- ADR-0025: Notifications: Telegram Bot API over httpx; email deferred
- new_id
- ADR-0044: Export everything, delete through forget, keep the deletion audit
- build_dashboard
- ADR-0063: Metric definitions for RippleBench v0 (interfaces; bodies are [human])
- ADR-0086: Dashboard pages, token session in sessionStorage, query-string routing
- Operations runbook
- main
- InlineKeyboard
- Contract requests (coordinator)
- bench/metrics.py
- Thesis outline: Ripple — a consistency layer for agent memory
- ADR-0042: Inspector endpoints: I1 at the boundary, history on request, edits go straight to versioning
- local_run.py
- Incident runbook (ADR-0107)
- ADR-0075: Telegram inbound: a strict subset of the Update type, private chats only, drops counted
- ADR-0080: MCP server on the SDK's low-level `Server`, explicit Pydantic tool schemas, seven tools
- current_user
- ADR-0088: API additions for the dashboard: /graph, /vocabulary, editable valid_to, required output fields
- WS-11 handover: MCP server
- embedded_pg.py
- .prettierrc.json
- Requirements
- ADR-0092: The 300-pair hand check is stratified, blind, keyed and re-drawn at report time
- ResizeObserverStub
- news_registry
- delivery_log.py
- comparable
- backup.sh
- ADR-0107: Three incident severities and a daily monitoring check for a one-operator pilot
- .claude/CLAUDE.md
- frontend.md
- prompts.md
- python.md
- tests.md
- 06-related-work.md
- IDEAS.md
- onboarding.md
- proposals/README.md
- restore.sh
- README.md
- prompts/README.md
- questions_needed
- Production hardening — delivery log, atomic confirm, resume text, API boundary
- paper: numbers from results/ and the I8 check
- stale_retrieval_rate
- RuleResolver
- Wave B — evaluation, pilot operations and write-up plumbing
- worked_trace
- ADR-0070: Allowed-sources registry: a YAML file validated into Pydantic, terms note required
- Decision
- ADR-0096: Candidate decisions are a compare-and-set on status, so a double confirm cannot write twice
- Pilot metrics: definitions, sources and what is still missing
- ripple.agents.scout and ripple.domains.jobs.sources: the Scout
- ripple.worker and ripple.notify — scheduled jobs, digest and alerts
- ADR-0091: Negatives at 3 per positive with every reversed link kept; train decontaminated against test
- ADR-0115: Embedded Postgres with pgvector for development and the local slow suite
- ADR-0125: The trained link finder fine-tunes ModernBERT-base on CPU; torch and transformers in a `linkfinder` group
- ADR-0127: Link-finder evaluation: a transfer mode for H4, CPU cost per call, and a three-seed summary folder
- ADR-0130: Dashboard information architecture and visual system
- ADR-0132: One-command local run of the whole product
- Running the whole product locally (tools/local_run.py, ripple.worker.run_once)
- ripple.mcp_server — Ripple's memory as MCP tools
- Pilot operations — feedback capture, the weekly report, incident handling
- ripple.notify.inbound — the Telegram bot the student talks to
- WS-18 handover: metric functions and the full benchmark
- ADR-0026: Retrieval is lexical-first behind an Embedder contract; dense model decided at integration
- ADR-0043: Resume candidates live in their own table until the user decides
- ADR-0094: The training loop is an interface with a fixed data view; the loop is the author's
- ADR-0126: Link-finder training recipe, artifact folder, and the served linker in ripple.linking.trained
- docs/paper — outlines and rendered numbers
- Final delivery — everything buildable, built and verified (2026-10-31)
- readyz
- .user
- next.config.ts

## God Nodes (most connected - your core abstractions)
1. `FakeClock` - 321 edges
2. `InMemoryStore` - 289 edges
3. `Memory` - 271 edges
4. `Status` - 246 edges
5. `fact()` - 226 edges
6. `FakeLLM` - 176 edges
7. `derived()` - 164 edges
8. `memory()` - 156 edges
9. `ChangeEvent` - 138 edges
10. `ConfigurationError` - 137 edges

## Surprising Connections (you probably didn't know these)
- `Decision` --references--> `setup()`  [INFERRED]
  docs/adr/0023-langgraph-checkpointer.md → apps/web/tests/questions.test.tsx
- `Consequences` --references--> `validate_scenario()`  [INFERRED]
  docs/adr/0100-news-and-finance-vocabularies.md → bench/scenario.py
- `Alternatives considered` --references--> `ImmediateScoutTrigger`  [INFERRED]
  docs/adr/0079-event-observers-and-criteria-change-scouting.md → src/ripple/agents/scout.py
- `Decision` --references--> `DomainVocabulary`  [INFERRED]
  docs/adr/0088-dashboard-api-additions.md → src/ripple/api/contracts.py
- `4. Trade-offs` --references--> `why()`  [INFERRED]
  docs/learning/mcp.md → src/ripple/api/inspector.py

## Import Cycles
- None detected.

## Communities (330 total, 75 thin omitted)

### Community 0 - "QuestionsView.tsx"
Cohesion: 0.08
Nodes (34): FeedbackKind, QuestionOut, RecommendationOut, DetailFromQuery(), MemoryDetailPage(), ADR-0086, ErrorBox(), ErrorBoxProps (+26 more)

### Community 1 - "FakeClock"
Cohesion: 0.05
Nodes (79): Status, TriggerKind, test_still_holds_restores_the_memory_and_what_it_parked(), _cgpa_edit(), CountingStore, FakeEventLease, _runner(), __init__() (+71 more)

### Community 2 - "generate_finance.py"
Cohesion: 0.08
Nodes (51): ceo_departure(), Company, _company_fact(), _floor(), forget_holding(), guidance_cut(), Investor, journal_entry() (+43 more)

### Community 3 - "ScenarioRunner"
Cohesion: 0.07
Nodes (40): load_scenario(), ResolutionSpec, ScenarioRunner, scenario_paths(), _cgpa_rise(), _spec(), test_probe_can_be_switched_off_and_the_trace_serialises_its_results(), test_probe_counts_do_not_depend_on_the_random_ids_of_new_versions() (+32 more)

### Community 4 - "Feedback"
Cohesion: 0.11
Nodes (24): Rendered numbers, DeliveryRecord, alerted_pairs(), _opening(), _ordered(), pending(), positive_pairs(), question_usefulness() (+16 more)

### Community 5 - "Link"
Cohesion: 0.04
Nodes (26): description, Decision, ADR-0087: Openings map built from the inspector's `why` links, laid out by kind, Alternatives considered, Consequences, Context, Decision, Revisit if (+18 more)

### Community 6 - "test_telegram_webhook.py"
Cohesion: 0.06
Nodes (33): Consequences, ADR-0078: The Telegram channel is hosted in the API's lifespan; Services carries the shared parts, Alternatives considered, Consequences, Context, Decision, Integration done at checkpoint C3 (coordinator), attach_telegram_webhook() (+25 more)

### Community 7 - "fact"
Cohesion: 0.05
Nodes (110): RetrievalPath, HybridRetriever, run(), test_invariant_I1_answer_receipt_never_carries_a_retired_memory(), run(), test_invariant_I1_api_never_returns_retired(), run(), test_invariant_I1_graph_never_returns_retired_nodes_or_links_to_them() (+102 more)

### Community 8 - "agents/conversation.py"
Cohesion: 0.04
Nodes (34): ADR-0045: Conversation agent: one LangGraph turn, strict intent, evidence-only answers, Alternatives considered, Consequences, Context, Decision, Revisit if, Decision, 6. Interview questions (+26 more)

### Community 9 - "test_bench_metrics.py"
Cohesion: 0.27
Nodes (17): ConvergenceRecord, time_to_consistency(), TTCReport, GoldState, ReplayTrace, _event(), _forget_trace(), _mem() (+9 more)

### Community 10 - "Postgres Store"
Cohesion: 0.04
Nodes (22): AppendOnlyStrategy, _NoPropagation, 3. How it works, event_changed_criteria(), ChangeEvent, ForgetEvent, EventObserver, ChangeEventNotFoundError (+14 more)

### Community 11 - "pytest"
Cohesion: 0.04
Nodes (71): index_memory(), test_intent_verdict_rejects_payload_that_does_not_match_the_intent(), RecordingTrigger, _seed(), test_observer_stays_quiet_for_an_event_that_left_the_criteria_alone(), test_observer_triggers_when_the_event_updated_a_criteria_memory(), test_observer_triggers_when_the_event_was_triggered_by_a_criteria_memory(), test_list_hides_retired_and_flags_suspect_and_pending() (+63 more)

### Community 12 - "ConfigurationError"
Cohesion: 0.04
Nodes (31): ADR-0050: Lexical scoring (BM25 / PostgreSQL FTS), reciprocal rank fusion and one-hop graph expansion for retrieval, Alternatives considered, Consequences, Context, Decision, Revisit if, run_migrations_offline(), run_migrations_online() (+23 more)

### Community 13 - "Alert Rendering & Digests"
Cohesion: 0.08
Nodes (24): What was built, Recommendation, AlertKind, Thresholds, Transport, UserDirectory, DigestService, Alert (+16 more)

### Community 14 - "InMemoryStore"
Cohesion: 0.07
Nodes (38): ChangeClassification, Statement, _seed(), test_forget_deletes_whole_version_chain_and_depends_on_cascade(), test_forget_from_a_newer_version_deletes_the_older_ones_too(), test_forget_leaves_no_dangling_links(), test_forget_leaves_unrelated_memories_and_links_alone(), test_forget_removes_snapshot_link_but_keeps_the_dependent() (+30 more)

### Community 15 - "FakeLLM"
Cohesion: 0.14
Nodes (24): build_pdf(), pdf_with_lines(), resume_reply(), text_stream(), _parse(), test_extract_text_joins_pages_with_a_blank_line(), test_extract_text_raises_when_pdf_has_no_text_layer(), test_extract_text_raises_when_pdf_is_password_protected() (+16 more)

### Community 16 - "Router"
Cohesion: 0.07
Nodes (25): ChangeKind, LLMOutputInvalidError, LLMLinker, LLMChangeDetector, Message, memories_block(), memory_block(), load_prompt() (+17 more)

### Community 17 - "run"
Cohesion: 0.05
Nodes (71): Decision, derive_criteria(), InMemoryScoutLedger, test_invariant_I5_scout_records_only_parsed_fields_with_spans_into_the_page_text(), test_invariant_I6_scout_declares_only_closed_capabilities_and_writes_only_openings(), test_invariant_I6_scout_only_gets_allowed_sources(), test_criteria_for_returns_the_valid_criteria_memory_and_ignores_a_questioned_one(), test_enqueueing_trigger_hands_the_user_id_to_the_queue() (+63 more)

### Community 18 - "test_handcheck.py"
Cohesion: 0.11
Nodes (37): _fill(), _rows(), _small_pair_file(), test_agreement_is_reported_overall_by_provenance_and_by_stratum(), test_allocate_gives_each_stratum_its_minimum_then_shares_the_rest_exactly(), test_allocate_keeps_the_minimums_when_they_exceed_the_total(), test_allocate_takes_everything_when_the_set_is_small(), test_gold_pairs_are_human_provenance_with_the_labeller_and_the_silver_label_kept() (+29 more)

### Community 19 - "sqlalchemy"
Cohesion: 0.09
Nodes (6): upgrade(), upgrade(), upgrade(), upgrade(), upgrade(), Base

### Community 20 - "DecisionAction"
Cohesion: 0.05
Nodes (76): Decision, Consequences, Decision, 1. What it does, 2. Why it exists, 3. How it works, 4. Trade-offs, 5. Failure modes and tests (+68 more)

### Community 21 - "test_settings.py"
Cohesion: 0.14
Nodes (7): _cron_by_name(), test_arq_wrappers_delegate_to_the_plain_jobs_and_summarise(), test_job_context_is_read_from_arq_ctx_and_missing_context_is_a_configuration_error(), test_on_startup_refuses_to_run_without_a_database_url(), test_on_startup_refuses_to_run_without_redis_url(), test_worker_settings_register_sweep_digest_alerts_and_scout_slots(), test_worker_settings_schedule_is_utc_and_ordered_scout_sweep_digest()

### Community 22 - "Store"
Cohesion: 0.05
Nodes (31): 1. What it does, 2. Why it exists, 4. Trade-offs, 5. Failure modes and tests, 6. Interview questions, 7. Exercise, ripple.storage — PostgresStore, tables and migrations, _cascade() (+23 more)

### Community 23 - "test_conversation.py"
Cohesion: 0.07
Nodes (67): memory_saver(), StalePendingStore, test_answer_question_answered_meanwhile_replies_instead_of_raising(), test_answer_question_corrected_updates_the_structured_value(), test_answer_question_corrected_writes_a_new_version_and_ripples(), test_answer_question_for_an_unknown_question_writes_nothing(), test_answer_question_no_longer_holds_retires_and_ripples(), test_answer_question_still_holds_restores_the_memory() (+59 more)

### Community 24 - "recommendation"
Cohesion: 0.06
Nodes (52): render_digest(), test_fake_clock_advance_moves_now(), failing_transport(), RecordingTransport, SentMessage, FakeRecommendationSource, FakeUserDirectory, recommendation() (+44 more)

### Community 25 - "scout.py"
Cohesion: 0.06
Nodes (30): Decision, 3. How it works, Follow-ups (specified, not built), How consumers call it, Suggested commit message, Verification (coordinator, 2026-10-26, after reconciling the review pass), What was built, WS-9 handover: Scout agent (+22 more)

### Community 26 - "test_bench_generate.py"
Cohesion: 0.12
Nodes (22): check_data(), generate(), Generated, load_jobs_v0(), main(), scenario_yaml(), write_data(), generated() (+14 more)

### Community 27 - "generate.py"
Cohesion: 0.16
Nodes (21): accepted_offer(), build_scenario(), _cgpa_memory(), cgpa_rise(), cutoff_unknown(), deadline_moved(), exam_block(), forget_cgpa() (+13 more)

### Community 28 - "Resolution"
Cohesion: 0.06
Nodes (23): AliasResolver, NoAskResolver, ADR-0122: Offline ablations, the `linker` and `ablation` keys, and counted LLM calls, Alternatives considered, Consequences, Context, Decision, Revisit if (+15 more)

### Community 29 - "test_numbers.py"
Cohesion: 0.14
Nodes (59): 5. Failure modes and tests (tests/paper), Refused, Rendered, resolve_all(), resolve(), resolve_macro(), bench_config(), complete() (+51 more)

### Community 30 - "build"
Cohesion: 0.04
Nodes (60): answer_data(), test_dispatcher_answer_tap_on_a_memory_that_is_no_longer_pending_is_refused(), run(), test_dispatcher_answer_tap_on_another_users_memory_changes_nothing(), run(), test_dispatcher_answer_tap_with_garbage_callback_data_is_refused(), test_dispatcher_applied_tap_says_nothing_was_applied_anywhere(), test_dispatcher_correction_tap_then_text_writes_a_new_version_without_the_agent() (+52 more)

### Community 31 - "DeliveryLog"
Cohesion: 0.21
Nodes (3): DeliveryLog, DeliveryLogContract, _service()

### Community 32 - "api/schemas.py"
Cohesion: 0.05
Nodes (29): get_graph(), post_opening(), list_recommendations(), post_statement(), get_vocabulary(), AnswerIn, CandidateOut, CandidatesOut (+21 more)

### Community 33 - "User"
Cohesion: 0.05
Nodes (15): main(), ScanningChatDirectory, PostgresUserStore, _require_aware(), TelegramLinkCode, User, _user(), InMemoryUserStore (+7 more)

### Community 34 - "RippleRunner"
Cohesion: 0.05
Nodes (38): CheckEverythingStrategy, one_shot_engine(), first_wave(), parents_first(), ADR-0060: Baseline memory strategies behind one MemoryStrategy protocol, Alternatives considered, Context, Decision (+30 more)

### Community 35 - "types.ts"
Cohesion: 0.03
Nodes (63): ClientOptions, send(), encodeQuery(), messageFor(), Query, readDetail(), RippleApi, ADR-0025 (+55 more)

### Community 36 - "asyncio"
Cohesion: 0.05
Nodes (44): error(), McpHarness, out(), TokenHolder, test_a_revoked_token_stops_working_on_the_next_call(), test_tool_calls_without_a_resolvable_token_are_refused(), test_users_cannot_see_or_touch_each_others_memories(), test_explain_reports_visibility_for_valid_and_retired_memories() (+36 more)

### Community 37 - "RouterConfig"
Cohesion: 0.05
Nodes (31): 1. What it does, 2. Why it exists, 3. How it works, 4. Trade-offs, 5. Failure modes and tests, 6. Interview questions, 7. Exercise, ripple.llm — the Router (+23 more)

### Community 38 - "raw_text_update"
Cohesion: 0.07
Nodes (43): ChannelStats, ReceiveResult, _callback(), DroppedUpdates, parse_update(), TelegramCallbackQuery, TelegramChat, TelegramMessage (+35 more)

### Community 39 - "job_context_from_env"
Cohesion: 0.09
Nodes (30): event_lease_key(), InMemoryLease, sweep_lease_key(), test_scout_run_with_the_default_registry_fetches_nothing(), context(), scripted_runner(), user_with_expiry_and_stranded_ripple(), write() (+22 more)

### Community 40 - "What was built"
Cohesion: 0.06
Nodes (30): ADR-0097: The text layer of every resume upload is stored so span references resolve, Alternatives considered, Consequences, Context, Decision, Revisit if, 3. How it works, SourceOut (+22 more)

### Community 41 - "anthropic.py"
Cohesion: 0.11
Nodes (15): CompletionRequest, CompletionResult, LLMClient, AnthropicClient, OpenAIClient, FakeMessages, FakeSDK, _request() (+7 more)

### Community 42 - "TellView.tsx"
Cohesion: 0.07
Nodes (37): IntakeOut, ResumeCandidate, Page(), Page(), ActionError(), ActionErrorProps, isModelUnavailable(), ADR-0131 (+29 more)

### Community 43 - "tools.py"
Cohesion: 0.09
Nodes (34): 3. How it works, What was built, AnswerIn, AnswerOut, DecisionOut, ErrorOut, EventOut, ExplainIn (+26 more)

### Community 44 - "routers/resume.py"
Cohesion: 0.05
Nodes (30): 6. Interview questions, candidate_from_fact(), fact_of(), current_trace_id(), _already(), _claim(), confirm_candidate(), list_candidates() (+22 more)

### Community 45 - "record_opening"
Cohesion: 0.05
Nodes (41): ADR-0030: An opening is one anchor memory plus one structured fact per field, Alternatives considered, Consequences, Context, Decision, Revisit if, ADR-0034: CGPA is compared with a cutoff only on one scale; otherwise the rules defer, Alternatives considered (+33 more)

### Community 46 - "OpeningAttribute"
Cohesion: 0.25
Nodes (24): OpeningAttribute, jd_reply(), _field(), _parse(), test_parse_jd_adds_deadline_from_regex_when_model_missed_it(), test_parse_jd_builds_summary_from_title_and_company_not_from_the_model(), test_parse_jd_coerces_cutoff_to_float_and_batch_to_int(), test_parse_jd_does_not_take_a_date_from_the_next_sentence_as_deadline() (+16 more)

### Community 47 - "models.py"
Cohesion: 0.04
Nodes (22): RecordingOpeningRecorder, ScriptedDetector, ScriptedRecommendations, SimpleCandidateStatements, _router(), test_opening_parser_adapter_strips_email_envelopes_only_for_email_sources(), test_opening_recorder_records_anchor_fields_and_derived_beliefs(), test_resume_parser_adapter_maps_unparseable_pdf_to_the_api_error() (+14 more)

### Community 48 - "test_i8_detector.py"
Cohesion: 0.11
Nodes (39): blocks(), Category, line_claims(), scan_text(), _cited(), claims(), _outcomes(), _run() (+31 more)

### Community 49 - "users.py"
Cohesion: 0.11
Nodes (10): create_user(), ApiToken, hash_token(), link_telegram(), new_link_code(), new_raw_token(), UserStore, _code() (+2 more)

### Community 50 - "LinkTypeRegistry"
Cohesion: 0.20
Nodes (15): _unknown_link_type(), ForgetBehaviour, LinkTypeRegistry, UnknownLinkTypeError, LinkClass, test_depends_on_propagates_copies_and_cascades(), test_every_link_class_has_a_policy(), test_registry_accepts_domain_types() (+7 more)

### Community 51 - "run.py"
Cohesion: 0.05
Nodes (58): load_manifest(), grid(), main(), _content_line(), _data_description(), display_path(), _engine(), main() (+50 more)

### Community 52 - "jobs/schemas.py"
Cohesion: 0.05
Nodes (36): ADR-0032: Ranking openings: eligible, then urgent, then fit, then variety; flagged, never retired, Alternatives considered, Consequences, Context, Decision, Revisit if, ADR-0046: Tailor agent: read-only, picks from id-validated candidates, Alternatives considered (+28 more)

### Community 53 - "Harness"
Cohesion: 0.03
Nodes (100): Consequences, candidate_fact(), _rebase_spans(), ScriptedOpeningParser, ScriptedResumeParser, span(), unparseable_opening(), unparseable_resume() (+92 more)

### Community 54 - "evaluate.py"
Cohesion: 0.10
Nodes (33): InvalidOutputLinker, _prediction(), test_confusion_counts_and_scores_detection_and_type(), test_confusion_for_an_untyped_linker_reports_no_typed_metrics(), test_confusion_reports_undefined_precision_as_none_and_f1_as_zero(), test_confusion_without_gold_negatives_reports_no_precision(), test_metrics_report_false_positives_per_negative_kind(), test_metrics_stratify_and_report_recall_only_per_gold_type() (+25 more)

### Community 55 - "dates.py"
Cohesion: 0.17
Nodes (12): find_dates(), _moment_of(), normalise_deadline(), _zone_of(), test_find_dates_does_not_read_a_word_starting_with_am_as_a_time(), test_find_dates_ignores_version_numbers_and_stray_numbers(), test_find_dates_keeps_source_offsets(), test_normalise_deadline_keeps_the_date_when_the_time_is_impossible() (+4 more)

### Community 56 - "manifest.json"
Cohesion: 0.08
Nodes (23): accepted_offer, cgpa_rise, cutoff_unknown, deadline_moved, exam_block, forget_cgpa, resume_update, data_sha256 (+15 more)

### Community 57 - "collections_abc"
Cohesion: 0.04
Nodes (24): domain_of(), registry_for(), retrieval_probe(), ActionLayer, _company_of(), _deadline_of(), memories_below(), _memory_snapshot() (+16 more)

### Community 58 - "answers.py"
Cohesion: 0.06
Nodes (32): ADR-0076: Telegram dispatcher: commands, link flow, keyboards for answers, two-step forget, agent for the rest, Alternatives considered, Consequences, Decision, Revisit if, 3. How it works, Verification (run 2026-10-19, after the code-review fixes), Code review (code-reviewer subagent, 2026-10-20) and what was done (+24 more)

### Community 59 - "Kind"
Cohesion: 0.08
Nodes (37): CandidateStatementsAdapter, Sensitivity, _link_beliefs_derived_since(), _live_profile_facts(), profile_content(), profile_fact(), profile_memory(), profile_statement() (+29 more)

### Community 60 - "test_fetcher.py"
Cohesion: 0.15
Nodes (30): acme_routes(), client(), fetcher(), forwarded_email(), html(), Recorder, _fetch(), test_fetch_result_decodes_the_charset_from_the_content_type() (+22 more)

### Community 61 - "InMemorySearchBackend"
Cohesion: 0.09
Nodes (17): cosine_similarity(), InMemorySearchBackend, DeterministicFakeEmbedder, BackendIndexer, backend(), dense_seeder(), embedder(), Seeder (+9 more)

### Community 62 - "test_ranking.py"
Cohesion: 0.27
Nodes (15): Board, test_recommender_does_not_spread_openings_without_a_company_as_one_employer(), test_recommender_fills_title_company_deadline_and_cited_fit_reasons(), test_recommender_flags_an_opening_whose_belief_or_field_is_suspect_or_pending(), test_recommender_is_not_flagged_by_a_belief_it_does_not_use(), test_recommender_keeps_a_flagged_deadline_for_ordering_and_display(), test_recommender_leaves_out_openings_whose_deadline_has_passed(), test_recommender_never_returns_an_opening_whose_anchor_is_retired() (+7 more)

### Community 63 - "pathlib"
Cohesion: 0.05
Nodes (62): ADR-0061: RippleBench v0 jobs track is generated from seeded personas and templates, Alternatives considered, Consequences, Context, Decision, Revisit if, Decision, Decision (+54 more)

### Community 64 - "parsers/jd.py"
Cohesion: 0.07
Nodes (33): 3. How it works, What was built, DateMatch, _agree(), _coerce(), _cross_check(), _dropped(), _fence_safe() (+25 more)

### Community 65 - "jobs_pairs.py"
Cohesion: 0.09
Nodes (42): Provenance, 6. Failure modes and tests (tests/training/), scenario(), _candidate(), test_every_test_split_scenario_link_of_the_seeded_state_is_a_positive(), test_jobs_pairs_build_is_deterministic(), test_jobs_pairs_carry_both_generated_provenances_and_no_other(), test_jobs_pairs_checked_in_files_equal_a_fresh_generation() (+34 more)

### Community 66 - "jobs.py"
Cohesion: 0.07
Nodes (34): Decision, ADR-0134: Run one worker job locally without Redis, Alternatives considered, Consequences, Context, Decision, Revisit if, 3. How it works (+26 more)

### Community 67 - "test_migration_0004.py"
Cohesion: 0.11
Nodes (11): 4. Trade-offs, content_tsvector(), _extend_metadata(), Vector, process(), vector_literal(), _load_migration(), test_migration_0004_chains_after_0003_users() (+3 more)

### Community 68 - "tracks.py"
Cohesion: 0.06
Nodes (42): data_hash(), generate(), main(), generate(), main(), assemble_track(), _build(), check_track() (+34 more)

### Community 69 - "parsers/resume.py"
Cohesion: 0.05
Nodes (38): ADR-0035: Parsers: LLM extraction with deterministic span, value and date validation, Alternatives considered, Consequences, Context, Decision, Revisit if, 1. What it does, 2. Why it exists (+30 more)

### Community 70 - "strip_email_envelope"
Cohesion: 0.15
Nodes (15): OpeningParserAdapter, _cut_disclaimer(), _cut_signature(), _drop_headers(), strip_email_envelope(), test_strip_email_envelope_cuts_a_signature_followed_by_a_long_disclaimer(), test_strip_email_envelope_cuts_disclaimer_and_closing(), test_strip_email_envelope_keeps_a_date_line_inside_the_jd_body() (+7 more)

### Community 71 - "json"
Cohesion: 0.09
Nodes (54): git_short_sha(), jd_reply(), test_git_short_sha_marks_a_dirty_tree(), _pair_file(), ScriptedLinker, test_fake_llm_run_is_labelled_a_plumbing_check(), test_rule_linker_run_on_the_checked_in_pairs_reports_held_out_cells(), test_run_never_overwrites_an_earlier_folder() (+46 more)

### Community 72 - "pilot/report.py"
Cohesion: 0.12
Nodes (19): collect(), FeedbackReader, first_versions(), generate(), git_short_sha(), main(), MemoryHistory, parse_args() (+11 more)

### Community 73 - "api/wiring.py"
Cohesion: 0.03
Nodes (65): ADR-0098: API boundary hardening: token-bucket write limits, health probes, request ids with JSON logs, security headers and a body cap, Alternatives considered, Consequences, Context, Decision, Revisit if, 5. Failure modes and tests, 3. How it works (+57 more)

### Community 74 - "i8.py"
Cohesion: 0.07
Nodes (45): _allowable(), _blank(), _blank_file_name(), _blank_pin(), CategoryRule, check(), _cited_run(), CitedRun (+37 more)

### Community 75 - "summary.py"
Cohesion: 0.13
Nodes (22): _by_seed(), Cell, cell(), _count(), count_cell(), _find(), _fmt(), _fmt_cell() (+14 more)

### Community 76 - "package.json"
Cohesion: 0.05
Nodes (36): config, dependencies, next, react, react-dom, @xyflow/react, engines, node (+28 more)

### Community 77 - "test_boundaries.py"
Cohesion: 0.31
Nodes (9): _clock_reads(), _core_sources(), _imported_modules(), _is_allowed(), test_boundary_check_detects_a_forbidden_import(), test_clock_check_allows_injected_clock(), test_clock_check_detects_disguised_now_calls(), test_core_never_reads_the_wall_clock_outside_clock_module() (+1 more)

### Community 78 - "test_hardening_ratelimit.py"
Cohesion: 0.07
Nodes (23): Done by the coordinator, not by WS-13, Bucket, InMemoryRateLimiter, RateDecision, RateLimiter, RateLimitGuard, RateLimits, RedisRateLimiter (+15 more)

### Community 79 - "me.py"
Cohesion: 0.23
Nodes (4): create_telegram_link_code(), delete_me(), export_me(), get_me()

### Community 80 - "test_stale.py"
Cohesion: 0.08
Nodes (32): iter_stale(), load_stale(), main(), stale_files(), stale_path_from_env(), StaleFormatError, StaleItem, StaleSession (+24 more)

### Community 81 - "checkpoints.py"
Cohesion: 0.18
Nodes (4): Open problems, postgres_saver(), test_memory_saver_is_a_fresh_checkpointer_each_time(), test_postgres_saver_is_an_async_context_manager_that_does_not_connect_on_creation()

### Community 82 - "asyncio"
Cohesion: 0.04
Nodes (80): asking(), feedback_harness(), opening(), seed_event(), test_delete_me_erases_feedback(), run(), test_export_includes_the_users_feedback(), run() (+72 more)

### Community 83 - "fixture"
Cohesion: 0.06
Nodes (36): _collect_text(), _descendants(), _Element, _element_children(), extract_candidates(), _first_href(), html_candidates(), json_candidates() (+28 more)

### Community 84 - "logging.py"
Cohesion: 0.09
Nodes (18): accept_trace_id(), bind_trace_id(), _header(), JsonFormatter, logging_config(), new_trace_id(), reset_trace_id(), TraceIdFilter (+10 more)

### Community 85 - "TelegramChannel"
Cohesion: 0.13
Nodes (14): 3. How it works, TelegramChannel, _update_id(), poll_forever(), poll_once(), FakeBotServer, test_poll_forever_backs_off_after_a_transport_error_and_continues(), fake_sleep() (+6 more)

### Community 87 - "Memory"
Cohesion: 0.05
Nodes (38): Decision, 1. What it does, 2. Why it exists, 3. How it works, 5. Failure modes and tests, 6. Interview questions, 7. Exercise, ripple.retrieval — hybrid search, graph expansion, I1 filtering (+30 more)

### Community 88 - "PairMemory"
Cohesion: 0.21
Nodes (17): PairMemory, _fact(), _opening(), test_an_application_is_a_snapshot_of_the_resume_version_it_names(), test_criteria_follow_the_cgpa_value(), test_eligibility_rests_on_cgpa_only_when_that_company_states_a_cutoff(), test_eligibility_rests_on_the_opening_whose_company_it_names(), test_opening_company_is_the_first_word_of_an_opening() (+9 more)

### Community 89 - "User"
Cohesion: 0.14
Nodes (13): Decision, CallbackAck, InboundDispatcher, Outcome, parse_command(), _Pending, Reply, question_keyboard() (+5 more)

### Community 90 - "TelegramBotApi"
Cohesion: 0.06
Nodes (25): ADR-0077: Telegram delivery: secret-token webhook into the API, at-most-once by update_id, long polling for development only, Alternatives considered, Context, Decision, Revisit if, _open_telegram_channel(), SystemClock, TelegramCallError (+17 more)

### Community 91 - "Services"
Cohesion: 0.03
Nodes (60): ADR-0041: API composition: `create_app(services)`, a `Services` object, environment-only wiring, Alternatives considered, Consequences, Context, Decision, Revisit if, Decision, Context (+52 more)

### Community 92 - "provenance_problems"
Cohesion: 0.13
Nodes (8): _all_filled(), discover_runs(), model_ids(), _not_runnable(), provenance_problems(), RunRecord, unpinned(), _when()

### Community 93 - "test_hardening_uploads_postgres.py"
Cohesion: 0.08
Nodes (12): engine(), owner(), test_migration_0006_matches_uploads_tables(), diff(), migrated(), _url(), migrated(), test_migration_0003_matches_users_tables() (+4 more)

### Community 94 - "FeedbackStore"
Cohesion: 0.11
Nodes (14): ADR-0105: Pilot feedback is one row per (student, memory, kind), first statement wins, Alternatives considered, Consequences, Context, Revisit if, FeedbackStore, race(), TestPostgresFeedbackStore (+6 more)

### Community 95 - "MemoryDetailView.tsx"
Cohesion: 0.11
Nodes (48): ChangeEvent, Link, Memory, FlaggedChip(), KindChip(), StatusChip(), RecentRipples, ADR-0130 (+40 more)

### Community 96 - "fetcher.py"
Cohesion: 0.08
Nodes (10): RippleError, CachedPage, FetchCache, InMemoryFetchCache, FetchFailedError, FetchRefusedError, FetchResult, SourceFetcher (+2 more)

### Community 104 - "helpers.tsx"
Cohesion: 0.10
Nodes (48): ApiError, FeedbackReceipt, ExportOut, Feedback, TOKEN_KEY, exportOut, me, editResult() (+40 more)

### Community 106 - "test_run_once.py"
Cohesion: 0.14
Nodes (18): LocalJob, main(), PrintingTransport, run_job(), RecordingSweep, __init__(), _factory(), _last_json() (+10 more)

### Community 108 - "FeedbackKind"
Cohesion: 0.16
Nodes (23): FeedbackKind, scenario(), alert(), at(), digest(), fb(), StaticDeliveries, metrics() (+15 more)

### Community 112 - "MapView.tsx"
Cohesion: 0.11
Nodes (26): MemoryStatus, VisibleStatus, LABELS, StatusChipProps, statusLabel(), kindLabel(), buildGraph(), edgeOf() (+18 more)

### Community 127 - "sources/__init__.py"
Cohesion: 0.15
Nodes (21): load_registry(), parse_registry(), registry_from_env(), SourceKind, SourceRegistry, SourceRegistryError, test_default_sources_file_lists_only_forwarded_email_and_a_disabled_example(), test_load_registry_reports_a_missing_file() (+13 more)

### Community 128 - "useApi"
Cohesion: 0.05
Nodes (69): AccountPage(), Page(), MapPage(), MemoriesPage(), Page(), LoginPage(), QuestionsPage(), RecommendationsPage() (+61 more)

### Community 129 - "resolve_all"
Cohesion: 0.10
Nodes (29): figure_cells(), format_value(), inconsistent_sources(), lookup(), main(), _markdown_value(), _numeric(), _plain() (+21 more)

### Community 130 - "keyboards.py"
Cohesion: 0.09
Nodes (26): NotifyError, CallbackDataError, AnswerAction, Button, decode_callback(), feedback_data(), FeedbackAction, forget_data() (+18 more)

### Community 131 - "load_scenario"
Cohesion: 0.14
Nodes (14): test_snapshots_drop_retired_expired_and_forgotten_memories(), _check_expectations(), _cutoff_unknown(), test_replay_agrees_with_every_v0_scenario_expectation(), test_replay_carries_structure_over_an_update_that_does_not_restate_it(), test_replay_refuses_an_event_on_a_forgotten_memory(), test_replay_refuses_two_links_on_one_pair(), test_replay_stops_a_branch_at_ask_as_the_engine_does() (+6 more)

### Community 132 - "RedisLease"
Cohesion: 0.08
Nodes (18): ADR-0056: Worker jobs are idempotent per user; sweeps hold a per-user lease; UTC schedule, Alternatives considered, Consequences, Revisit if, ADR-0099: The runner holds a per-ChangeEvent lease while it drives an event, Alternatives considered, Consequences, Context (+10 more)

### Community 133 - "tracing.py"
Cohesion: 0.04
Nodes (37): ADR-0028: Langfuse tracer implemented now behind the Tracer protocol, Alternatives considered, Consequences, Context, Decision, Revisit if, 1. What it does, 2. Why it exists (+29 more)

### Community 134 - "InMemoryDeliveryLog"
Cohesion: 0.07
Nodes (17): ADR-0095: A Postgres delivery log keyed by (user, kind, key) makes digests and alerts survive restarts, Alternatives considered, Consequences, Context, Decision, Revisit if, _day_start(), InMemoryDeliveryLog (+9 more)

### Community 135 - "Linker"
Cohesion: 0.03
Nodes (55): ADR-0093: Link finders are scored per pair with opaque ids, stratified by provenance and held-out cell, Alternatives considered, Consequences, Context, Decision, Revisit if, ADR-0102: Finance link pairs for H4 come from the finance_v1 scenarios, test split only, Alternatives considered (+47 more)

### Community 136 - "Clock"
Cohesion: 0.05
Nodes (30): CountingResolver, RippleStrategy, Context, Decision, 1. What it does, 2. Why it exists, 3. How it works, 4. Trade-offs (+22 more)

### Community 137 - "test_inbound_telegram_api.py"
Cohesion: 0.14
Nodes (17): run(), api(), Recorder, test_bot_api_answer_callback_query_posts_the_id_and_truncated_text(), test_bot_api_get_updates_posts_offset_timeout_and_allowed_updates(), test_bot_api_get_updates_rejects_a_result_that_is_not_a_list(), test_bot_api_get_updates_without_an_offset_omits_it(), test_bot_api_raises_call_error_with_method_and_description_never_the_token() (+9 more)

### Community 138 - "compilerOptions"
Cohesion: 0.08
Nodes (23): compilerOptions, allowJs, esModuleInterop, exactOptionalPropertyTypes, incremental, isolatedModules, jsx, lib (+15 more)

### Community 139 - "test_inbound_render.py"
Cohesion: 0.13
Nodes (17): 1. What it does, 2. Why it exists, 4. Trade-offs, 5. Failure modes and tests, 7. Exercise, ripple.agents — Conversation and Tailor, Citation, render_reply() (+9 more)

### Community 140 - "selectors.py"
Cohesion: 0.13
Nodes (7): _descendants(), parse_selector(), parse_simple(), select(), _select_parts(), SelectableNode, SimpleSelector

### Community 141 - "ADR-0027: Anthropic SDK as the first provider adapter; structured output via forced tool use"
Cohesion: 0.25
Nodes (7): ADR-0027: Anthropic SDK as the first provider adapter; structured output via forced tool use, Alternatives considered, Consequences, Context, Decision, Revisit if, input_schema()

### Community 142 - "test_local_run.py"
Cohesion: 0.13
Nodes (18): 5. Failure modes and tests, write(), _eligibility(), _live(), _site(), test_banner_lists_what_needs_the_model_key_when_it_is_missing(), test_banner_says_model_features_are_on_with_a_key_and_reports_the_seed(), test_export_files_never_serves_outside_the_export() (+10 more)

### Community 143 - "storage/feedback.py"
Cohesion: 0.06
Nodes (18): Decision, 3. How it works, Files by purpose, Requests to other workstreams (exact payloads), feedback_store_of(), FeedbackIn, FeedbackListOut, list_feedback() (+10 more)

### Community 144 - ".__call__"
Cohesion: 0.31
Nodes (4): counting_receive(), tracking_send(), _content_length(), _send_413()

### Community 145 - "derive_for_opening"
Cohesion: 0.19
Nodes (20): derive_for_opening(), JobsLinkType, _parent_ids(), _setup(), test_derive_criteria_from_profile_facts_links_criteria_from(), test_derive_each_belief_opens_its_own_completed_change_event(), test_derive_eligibility_is_false_when_cgpa_is_below_the_cutoff(), test_derive_eligibility_is_skipped_when_the_profile_lacks_the_cgpa() (+12 more)

### Community 146 - "RobotsPolicy"
Cohesion: 0.16
Nodes (8): RobotsPolicy, ScriptedRobots, test_robots_policy_allows_everything_when_robots_txt_is_missing(), test_robots_policy_applies_rules_for_a_named_agent(), test_robots_policy_closes_the_host_when_robots_txt_cannot_be_read(), test_robots_policy_fetches_robots_txt_once_per_host_per_run(), test_robots_policy_reads_the_crawl_delay_for_our_agent(), test_robots_policy_refuses_a_disallowed_path_and_allows_the_rest()

### Community 147 - "Ripple — instructions for Claude Code"
Cohesion: 0.11
Nodes (17): Anti-slop rules, Code map, Commands, Decisions need ADRs (use /adr), End of session, Graph layout for this project, graphify, How we work (every task) (+9 more)

### Community 148 - "2. The original plan, item by item"
Cohesion: 0.11
Nodes (18): 1. Measured state of the checkout (17:55 IST), 2. The original plan, item by item, 3. The production plan, wave by wave, 4. The honest totals, 5. What only the author can unblock (in order of leverage), 6. What the collaborator does next (no author input needed), 7. After checkpoint C3 (same day, later), Acceptance criteria of the production plan (+10 more)

### Community 149 - "test_report.py"
Cohesion: 0.20
Nodes (17): 5. Failure modes and tests, constructed_sources(), read_json(), run(), go(), test_generate_config_records_provenance(), test_generate_marks_a_partial_week_when_allowed(), test_generate_metrics_json_carries_the_computed_share() (+9 more)

### Community 150 - "Ordered tasks (each one session; tests first; [human] marks author-owned work)"
Cohesion: 0.12
Nodes (16): 0.1 Project skeleton and tooling, 0.2 CI on GitHub Actions, 0.3 Services: docker compose (after ADR-0017), 0.4 Migrations pipeline (after ADR-0016), 0.5 Clock, ids and errors in core, 0.6 LLM router skeleton and FakeLLM, 0.7 ADRs for pending dependencies (before 0.3 and 0.4), 0.8 Phase close (+8 more)

### Community 151 - "LabelledPair"
Cohesion: 0.08
Nodes (36): LabelledPair, read_pairs(), Split, split_for(), write_pairs(), ADR-0090: Jobs link pairs come from static scenario snapshots, with structure rules as a stratum, Alternatives considered, Consequences (+28 more)

### Community 152 - "Ordered tasks"
Cohesion: 0.12
Nodes (15): 1.1 Core models and link policy, 1.2 Store protocol and in-memory store, 1.3 [human] Ripple engine, 1.4 Resolver protocol, rule-first stage, ripple runner, 1.5 Versioning, forget, expiry, user answers, 1.6 Linkers, 1.7 Change detector, 1.8 Postgres store (+7 more)

### Community 153 - "worker/wiring.py"
Cohesion: 0.05
Nodes (28): Decision, Code review, Files by purpose, Not verified, Status, Suggested commit message, Verification (real output, 2026-10-31), WS-20: complete product (dashboard flows, design, local run): handover (+20 more)

### Community 154 - "test_hardening_health.py"
Cohesion: 0.35
Nodes (11): _app(), _broken(), _get(), _hangs(), _ok(), test_health_routes_stay_out_of_the_openapi_document(), test_healthz_answers_without_a_token(), test_readyz_is_200_when_every_probe_passes() (+3 more)

### Community 155 - "3. How it works"
Cohesion: 0.21
Nodes (5): cost_per_ripple(), VersionState, 3. How it works, test_cost_per_ripple_divides_resolver_calls_by_change_events(), test_gold_state_reports_each_mismatch_with_the_runner_wording()

### Community 156 - "test_run_v1.py"
Cohesion: 0.05
Nodes (38): validate_scenario(), 1. What it does, 2. Why it exists, 4. Adding curated real stories (your data work), 5. Trade-offs, 6. Failure modes and tests, 7. Interview questions, 8. Exercise (+30 more)

### Community 157 - "finance_v1/manifest.json"
Cohesion: 0.07
Nodes (29): ceo_departure, forget_holding, guidance_cut, journal_entry, peer_margin, rate_edge, trading_halt, content (+21 more)

### Community 158 - "Workstreams (dependency order, then value)"
Cohesion: 0.14
Nodes (13): Coordination, Prerequisites (author, before or alongside round 2), Round 2 plan — from "built offline" to "used daily", What this round does not do, Where the project stands against the original idea (checked 2026-10-24), Workstreams (dependency order, then value), WS-0 Coordinator: live verification and engine landing (sequential-only), WS-10 Telegram inbound: the student's channel (Phase 2 exit; parallel-ready) (+5 more)

### Community 159 - "test_telegram_transport.py"
Cohesion: 0.15
Nodes (18): TelegramSendError, _ok(), handler(), test_telegram_transport_from_env_reads_the_token(), handler(), test_telegram_transport_never_logs_token_or_text_at_info_on_any_logger(), test_telegram_transport_posts_send_message_with_chat_id_and_text(), handler() (+10 more)

### Community 160 - "news_v1/manifest.json"
Cohesion: 0.07
Nodes (28): attribution_retracted, conflicting_reports, figure_revised, forget_story, other_story_develops, road_closure, shared_note, content (+20 more)

### Community 161 - "Data model"
Cohesion: 0.15
Nodes (12): ChangeEvent (ADR-0015), Data model, Decision, ForgetEvent, Link classes (core) and link types (domains), Link (dependency edge), Memory, Ripple semantics (ADR-0013) (+4 more)

### Community 162 - "build_site"
Cohesion: 0.14
Nodes (4): build_site(), lifespan(), ExportFiles, SecurityHeaders

### Community 163 - "schema.d.ts"
Cohesion: 0.10
Nodes (18): components, $defs, operations, paths, ADR-0013, ADR-0015, ADR-0025, ADR-0042 (+10 more)

### Community 164 - "Architecture"
Cohesion: 0.18
Nodes (10): Agents, Architecture, Deployment, Flows, How core stays domain-agnostic (ADR-0013), Modules, Open (not yet decided; see docs/plans/phase-0.md), Principle (+2 more)

### Community 165 - "Template"
Cohesion: 0.17
Nodes (11): 2026-10-19 — Parallel round 1 closed at checkpoint C2 (coordinator session), 2026-10-19 — Parallel round 1: seven workstreams on one checkout (coordinator session), 2026-10-19 — Phase 0, kickoff session (docs only, no code), 2026-10-19 — Phase 0, project definition, 2026-10-19 — Phase 0, tasks 0.1–0.7 built (second session of the day), 2026-10-19 — Phase 1 built under the autonomous mandate (third session of the day), 2026-10-24 — Production plan and wave A launch (coordinator session), 2026-10-31 — Wave B and checkpoint C4 (coordinator session) (+3 more)

### Community 166 - "paper/registry.py"
Cohesion: 0.17
Nodes (21): Decision, 3. How it works, Adding a number, matches_config(), select_runs(), _ablations(), Aggregate, _build() (+13 more)

### Community 167 - "inbound/wiring.py"
Cohesion: 0.07
Nodes (14): Open problems, Plan (written before implementation, CLAUDE.md "How we work" step 2), Suggested commit message, Verification (coordinator, 2026-10-26), WS-10 handover: Telegram inbound channel, InMemoryUpdateLedger, UpdateLedger, InMemoryRateLimiter (+6 more)

### Community 168 - "ADR-0062: Time-to-consistency replay harness with per-event snapshots"
Cohesion: 0.20
Nodes (6): ADR-0062: Time-to-consistency replay harness with per-event snapshots, Alternatives considered, Consequences, Context, Decision, Revisit if

### Community 169 - "Evaluation"
Cohesion: 0.20
Nodes (9): Ablations, Baselines, Evaluation, Hypotheses (initial targets; revised after Phase 3 baselines, with an ADR), Metrics, Pilot metrics, Protocol, Questions (+1 more)

### Community 170 - "test_finance_pairs.py"
Cohesion: 0.08
Nodes (25): _pairs_file(), pairs_text(), _reachable(), _same_key(), scenario_pairs(), track_pairs(), ManifestEntry, company_subject() (+17 more)

### Community 171 - "SessionProvider.tsx"
Cohesion: 0.09
Nodes (28): createClient(), request(), API_BASE_URL, metadata, RootLayout(), noSubscription(), SessionContext, SessionProvider() (+20 more)

### Community 172 - "Production plan — build the whole product once, deploy-ready"
Cohesion: 0.20
Nodes (9): Acceptance for the plan as a whole, Author-owned, in parallel with both waves, Decisions fixed now, so nothing is rebuilt later, Definition of production-ready (what "done once" means), Ownership and ADR ranges for wave A, Production plan — build the whole product once, deploy-ready, Wave A — product completion and hardening (now), Wave B — evaluation and research completion (after C3) (+1 more)

### Community 173 - "Proposal 0001: Rule-first resolution"
Cohesion: 0.20
Nodes (9): Alternatives, Cost, How we measure it, Problem, Proposal 0001: Rule-first resolution, Proposed change, Rationale, Recommendation (+1 more)

### Community 174 - "Proposal 0002: Structure-derived silver labels and a candidate pre-filter for the link finder"
Cohesion: 0.20
Nodes (9): Alternatives, Cost, How we measure it, Problem, Proposal 0002: Structure-derived silver labels and a candidate pre-filter for the link finder, Proposed change, Rationale, Recommendation (+1 more)

### Community 175 - "Proposal 0003: Time-to-consistency as an action-level metric"
Cohesion: 0.20
Nodes (9): Alternatives, Cost, How we measure it, Problem, Proposal 0003: Time-to-consistency as an action-level metric, Proposed change, Rationale, Recommendation (+1 more)

### Community 176 - "Vision"
Cohesion: 0.22
Nodes (8): One line, Scope, Success by May 2028, The problem, Thesis, Vision, What we claim (contributions), What we do NOT claim

### Community 177 - "Roadmap"
Cohesion: 0.22
Nodes (8): Phase 0 — Foundation (2026-10-20 → 2026-11-08), Phase 1 — Core engine (2026-11-09 → 2026-12-31), Phase 2 — Job-hunt MVP (2027-01-01 → 2027-01-31), Phase 3 — Scout, RAG, first results (2027-02-01–2027-04-30), Phase 4 — Link finder + RippleBench v1 (2027-05-01 → 2027-07-31), Phase 5 — Main pilot (2027-08-01 → 2027-10-31), Phase 6 — Final evaluation and write-up (2027-11-01–2028-05-31), Roadmap

### Community 178 - "WS-17 handover: paper and thesis plumbing, the I8 check"
Cohesion: 0.12
Nodes (16): ADR-0110: Paper and thesis numbers are registered macros rendered from results/, Alternatives considered, Consequences, Context, Revisit if, Contract requests (coordinator / producers), Files by purpose, I8 violations today (paper/i8_known_violations.toml) — for the coordinator (+8 more)

### Community 179 - "bench: strategies, RippleBench v0 generator, replay harness, metric interfaces"
Cohesion: 0.17
Nodes (11): 1. What it does, 2. Why it exists, 4. The metrics, with a worked example (tests/scenarios/test_bench_metrics.py), 5. Trade-offs, 6. Failure modes and tests, 7. Interview questions, 8. Exercise, bench: strategies, RippleBench v0 generator, replay harness, metrics (+3 more)

### Community 180 - "ripple.core.engine — the ripple engine (your module)"
Cohesion: 0.22
Nodes (8): 1. What it does, 2. Why it exists, 3. How it works (what you implement), 4. Trade-offs you should be able to argue, 5. Failure modes and tests, 6. Interview questions, 7. Exercise, ripple.core.engine — the ripple engine

### Community 181 - "Paper outline: Ripple — learned dependency links keep agent memory consistent"
Cohesion: 0.08
Nodes (24): Ablations, Abstract, Action level: stale recommendations and time to consistency (C2), Asking the user, Conclusion, Cost (C4), Data model, Ethics (+16 more)

### Community 182 - "identity.py"
Cohesion: 0.06
Nodes (7): BearerGate, bearer_token(), BearerIdentity, current_user(), env_token_source(), header_token_source(), resolve_user()

### Community 183 - "StructuredFact"
Cohesion: 0.08
Nodes (18): ADR-0116: Structured facts are classified, linked and derived from without a model, Alternatives considered, Consequences, Context, Decision, LinkProposal, LinkCreator, StructuredFact (+10 more)

### Community 184 - "test_trained_linker.py"
Cohesion: 0.22
Nodes (11): TrainedLinker, _artifact(), ScriptedScorer, test_a_threshold_outside_zero_one_is_refused(), test_an_explicit_threshold_overrides_the_validated_one(), test_memory_text_spells_out_kind_content_and_structure(), test_propose_finds_a_hidden_link_from_the_new_fact_to_an_existing_belief(), test_propose_skips_itself_and_other_users_memories_without_scoring() (+3 more)

### Community 185 - "ripple.api — identity, inspector, confirmation flow, export and delete"
Cohesion: 0.25
Nodes (7): 1. What it does, 2. Why it exists, 4. Trade-offs, 5. Failure modes and tests, 6. Interview questions, 7. Exercise, ripple.api — identity, inspector, confirmation flow, export and delete

### Community 186 - "UserDirectoryAdapter"
Cohesion: 0.13
Nodes (12): ADR-0040: Identity for the pilot: admin-created users, hashed bearer tokens, one-time Telegram link codes, Alternatives considered, Consequences, Context, Decision, Revisit if, Contract change requests to the coordinator, Contracts (+4 more)

### Community 187 - "jobs/vocabulary.py"
Cohesion: 0.07
Nodes (24): _derive(), DerivedBeliefs, _existing(), rules_runner(), _assert_only_parent_values(), _parents(), _seed(), test_invariant_I1_recommender_never_returns_retired_and_flags_suspect_or_pending() (+16 more)

### Community 188 - "ScoutCriteria"
Cohesion: 0.17
Nodes (10): ADR-0073: Scout refusals are counted apart from errors; criteria parse only the gates, Alternatives considered, Consequences, Context, Decision, criteria_for(), _filtered_key(), ScoutCriteria (+2 more)

### Community 189 - "TokenBucket"
Cohesion: 0.25
Nodes (8): TokenBucket, advancing_sleeper(), test_token_bucket_default_burst_of_one_never_lets_two_requests_through_at_once(), test_token_bucket_does_not_wait_when_enough_time_has_passed(), test_token_bucket_first_request_is_immediate_and_the_second_waits_the_interval(), test_token_bucket_raises_instead_of_spinning_when_the_sleeper_does_not_advance_time(), test_token_bucket_rejects_a_non_positive_rate(), test_token_bucket_waits_only_the_remaining_part_of_the_interval()

### Community 190 - "devDependencies"
Cohesion: 0.11
Nodes (18): devDependencies, eslint, eslint-config-next, eslint-config-prettier, eslint-plugin-jsx-a11y, jsdom, openapi-typescript, prettier (+10 more)

### Community 191 - "ripple.core: writes, runner, versioning, forget, sweep, answers"
Cohesion: 0.25
Nodes (7): 1. What it does, 2. Why it exists, 4. Trade-offs, 5. Failure modes and tests, 6. Interview questions, 7. Exercise, ripple.core: writes, runner, versioning, forget, sweep, answers

### Community 192 - "dedupe.py"
Cohesion: 0.13
Nodes (13): canonical_url(), fingerprint(), _is_tracking(), _normalise(), canonical_of_source_ref(), _held_fingerprints(), _held_urls(), test_canonical_url_is_idempotent() (+5 more)

### Community 193 - "target_outcomes"
Cohesion: 0.19
Nodes (10): correct_updates(), stale_kept(), target_outcomes(), TargetOutcome, wrongful_changes(), test_a_deletion_is_a_should_change_target_once_and_a_should_stay_target_after(), test_correct_updates_counts_should_change_targets_that_match_gold(), test_stale_kept_counts_should_change_targets_that_did_not_move() (+2 more)

### Community 194 - "test_generators.py"
Cohesion: 0.23
Nodes (12): _identifiers(), test_adding_a_persona_leaves_earlier_personas_scenarios_unchanged(), test_baselines_fail_and_check_everything_misses_only_the_ask_family(), test_every_scenario_is_valid_in_its_domain_and_every_family_is_covered(), test_generate_changes_with_the_seed(), test_generate_is_deterministic_for_the_same_seed(), test_the_checked_in_track_matches_a_fresh_generation(), test_the_snapshot_family_uses_the_domains_snapshot_link() (+4 more)

### Community 195 - "migrate"
Cohesion: 0.11
Nodes (17): ADR-0029: Deployment topology: one VPS, Compose, Caddy TLS, GHCR images, pg_dump backups, Alternatives considered, Consequences, Context, Decision, Revisit if, 2026-10-26 — Status analysis and checkpoint C3 (coordinator session), Backups (+9 more)

### Community 196 - "Pilot consent (draft for departmental review)"
Cohesion: 0.22
Nodes (8): Contact, How it is used, Pilot consent (draft for departmental review), Taking part is voluntary, What Ripple is, What we collect, Where it lives and who sees it, Your rights

### Community 197 - "Ripple dashboard (apps/web)"
Cohesion: 0.29
Nodes (6): Commands (run inside apps/web), Deploy, Developing against a local API, Regenerating the API client, Ripple dashboard (apps/web), Rules

### Community 198 - "no-business-logic.test.ts"
Cohesion: 0.29
Nodes (3): FORBIDDEN, sourceFiles(), SRC

### Community 199 - "ADR-NNNN: <title>"
Cohesion: 0.29
Nodes (6): ADR-NNNN: <title>, Alternatives considered, Consequences, Context, Decision, Revisit if

### Community 200 - "ADR-0001: Record decisions as ADRs"
Cohesion: 0.29
Nodes (6): ADR-0001: Record decisions as ADRs, Alternatives considered, Consequences, Context, Decision, Revisit if

### Community 201 - "ADR-0002: Job hunting is the primary domain"
Cohesion: 0.29
Nodes (6): ADR-0002: Job hunting is the primary domain, Alternatives considered, Consequences, Context, Decision, Revisit if

### Community 202 - "ADR-0003: The graph decides scope; the LLM decides action"
Cohesion: 0.29
Nodes (6): ADR-0003: The graph decides scope; the LLM decides action, Alternatives considered, Consequences, Context, Decision, Revisit if

### Community 203 - "ADR-0004: PostgreSQL + pgvector with in-process traversal"
Cohesion: 0.29
Nodes (6): ADR-0004: PostgreSQL + pgvector with in-process traversal, Alternatives considered, Consequences, Context, Decision, Revisit if

### Community 204 - "ADR-0005: LangGraph for agents; core stays framework-free"
Cohesion: 0.29
Nodes (6): ADR-0005: LangGraph for agents; core stays framework-free, Alternatives considered, Consequences, Context, Decision, Revisit if

### Community 205 - "ADR-0006: Expose memory tools over MCP"
Cohesion: 0.29
Nodes (6): ADR-0006: Expose memory tools over MCP, Alternatives considered, Consequences, Context, Decision, Revisit if

### Community 206 - "ADR-0007: Retire, never silently delete"
Cohesion: 0.29
Nodes (6): ADR-0007: Retire, never silently delete, Alternatives considered, Consequences, Context, Decision, Revisit if

### Community 207 - "ADR-0008: The human applies; allowed sources only"
Cohesion: 0.29
Nodes (6): ADR-0008: The human applies; allowed sources only, Alternatives considered, Consequences, Context, Decision, Revisit if

### Community 208 - "ADR-0009: A trained small model for link finding"
Cohesion: 0.29
Nodes (6): ADR-0009: A trained small model for link finding, Alternatives considered, Consequences, Context, Decision, Revisit if

### Community 209 - "ADR-0010: Provider-agnostic LLM router with structured outputs"
Cohesion: 0.29
Nodes (6): ADR-0010: Provider-agnostic LLM router with structured outputs, Alternatives considered, Consequences, Context, Decision, Revisit if

### Community 210 - "ADR-0011: Python tooling: uv, ruff, pyright, pytest"
Cohesion: 0.29
Nodes (6): ADR-0011: Python tooling: uv, ruff, pyright, pytest, Alternatives considered, Consequences, Context, Decision, Revisit if

### Community 211 - "ADR-0012: Evaluation-first development"
Cohesion: 0.29
Nodes (6): ADR-0012: Evaluation-first development, Alternatives considered, Consequences, Context, Decision, Revisit if

### Community 212 - "ADR-0013: Wave-by-wave ripple over core link classes"
Cohesion: 0.29
Nodes (6): ADR-0013: Wave-by-wave ripple over core link classes, Alternatives considered, Consequences, Context, Decision, Revisit if

### Community 213 - "ADR-0014: Memory versions are rows; dependency links are copied to the new version"
Cohesion: 0.29
Nodes (6): ADR-0014: Memory versions are rows; dependency links are copied to the new version, Alternatives considered, Consequences, Context, Decision, Revisit if

### Community 214 - "ADR-0015: Every change is a memory write; temporary facts self-expire"
Cohesion: 0.29
Nodes (6): ADR-0015: Every change is a memory write; temporary facts self-expire, Alternatives considered, Consequences, Context, Decision, Revisit if

### Community 215 - "ADR-0016: SQLAlchemy 2 (async, psycopg) + Alembic, in a storage package outside core"
Cohesion: 0.29
Nodes (6): ADR-0016: SQLAlchemy 2 (async, psycopg) + Alembic, in a storage package outside core, Alternatives considered, Consequences, Context, Decision, Revisit if

### Community 216 - "ADR-0017: Background jobs with arq on Redis"
Cohesion: 0.29
Nodes (6): ADR-0017: Background jobs with arq on Redis, Alternatives considered, Consequences, Context, Decision, Revisit if

### Community 217 - "ADR-0018: Observability with Langfuse over OpenTelemetry; structured logging until then"
Cohesion: 0.29
Nodes (6): ADR-0018: Observability with Langfuse over OpenTelemetry; structured logging until then, Alternatives considered, Consequences, Context, Decision, Revisit if

### Community 218 - "ADR-0020: Change detection: deterministic for structured facts, LLM for prose"
Cohesion: 0.29
Nodes (6): ADR-0020: Change detection: deterministic for structured facts, LLM for prose, Alternatives considered, Consequences, Context, Decision, Revisit if

### Community 219 - "ADR-0021: Scenario files are YAML, parsed with PyYAML"
Cohesion: 0.29
Nodes (6): ADR-0021: Scenario files are YAML, parsed with PyYAML, Alternatives considered, Consequences, Context, Decision, Revisit if

### Community 220 - "ADR-0022: Web API stack: FastAPI, uvicorn, httpx, python-multipart"
Cohesion: 0.29
Nodes (6): ADR-0022: Web API stack: FastAPI, uvicorn, httpx, python-multipart, Alternatives considered, Consequences, Context, Decision, Revisit if

### Community 221 - "ADR-0023: LangGraph dependency and Postgres checkpointer"
Cohesion: 0.29
Nodes (6): ADR-0023: LangGraph dependency and Postgres checkpointer, Alternatives considered, Consequences, Context, Decision, Revisit if

### Community 222 - "ADR-0024: Resume parsing: pypdf text extraction, LLM structuring, user confirmation"
Cohesion: 0.29
Nodes (6): ADR-0024: Resume parsing: pypdf text extraction, LLM structuring, user confirmation, Alternatives considered, Consequences, Context, Decision, Revisit if

### Community 223 - "ADR-0025: Notifications: Telegram Bot API over httpx; email deferred"
Cohesion: 0.29
Nodes (6): ADR-0025: Notifications: Telegram Bot API over httpx; email deferred, Alternatives considered, Consequences, Context, Decision, Revisit if

### Community 224 - "new_id"
Cohesion: 0.16
Nodes (10): 1. What it does, 2. Why it exists, 3. How it works, 4. Trade-offs, 5. Failure modes and tests, 7. Exercise, ripple.core foundations: clock, ids, errors, boundaries, new_id() (+2 more)

### Community 225 - "ADR-0044: Export everything, delete through forget, keep the deletion audit"
Cohesion: 0.29
Nodes (6): ADR-0044: Export everything, delete through forget, keep the deletion audit, Alternatives considered, Consequences, Context, Decision, Revisit if

### Community 226 - "build_dashboard"
Cohesion: 0.22
Nodes (8): export(), test_build_dashboard_installs_then_builds_when_forced(), test_build_dashboard_reuses_a_current_export_without_running_npm(), test_export_is_current_only_when_index_is_newer_than_every_source(), _web(), build_dashboard(), export_is_current(), web_sources()

### Community 227 - "ADR-0063: Metric definitions for RippleBench v0 (interfaces; bodies are [human])"
Cohesion: 0.29
Nodes (6): ADR-0063: Metric definitions for RippleBench v0 (interfaces; bodies are [human]), Alternatives considered, Consequences, Context, Decision, Revisit if

### Community 228 - "ADR-0086: Dashboard pages, token session in sessionStorage, query-string routing"
Cohesion: 0.29
Nodes (6): ADR-0086: Dashboard pages, token session in sessionStorage, query-string routing, Alternatives considered, Consequences, Context, Decision, Revisit if

### Community 229 - "Operations runbook"
Cohesion: 0.29
Nodes (6): Data requests (DPDP, FR-15), Health, Key rotation, Operations runbook, Rollback and restore, Symptoms

### Community 230 - "main"
Cohesion: 0.12
Nodes (7): streamable_http_app(), main(), _fakes(), test_main_serves_http_from_flags_over_environment(), test_main_serves_stdio_only_with_a_token_in_the_environment(), test_settings_default_to_stdio_on_loopback(), test_settings_read_the_environment_and_name_a_bad_value()

### Community 231 - "InlineKeyboard"
Cohesion: 0.18
Nodes (3): BotSender, InlineKeyboard, RecordingSender

### Community 232 - "Contract requests (coordinator)"
Cohesion: 0.11
Nodes (15): Contract requests (coordinator), Open problems, Status, Suggested commit message, Verification (real output, 2026-10-31), What it does (short), WS-16 handover — Pilot operations, _require_database() (+7 more)

### Community 233 - "bench/metrics.py"
Cohesion: 0.10
Nodes (16): _median(), questions_asked(), _ratio(), scenario_metrics(), ScenarioMetrics, stale_hits(), stale_ids_at(), stale_recommendation_counts() (+8 more)

### Community 234 - "Thesis outline: Ripple — a consistency layer for agent memory"
Cohesion: 0.13
Nodes (14): Appendices, Chapter: Conclusion and future work, Chapter: Introduction, Chapter: Learning dependency links, Chapter: Literature survey, Chapter: Pilot study, Chapter: Requirements and evaluation plan, Chapter: Results and discussion (+6 more)

### Community 235 - "ADR-0042: Inspector endpoints: I1 at the boundary, history on request, edits go straight to versioning"
Cohesion: 0.33
Nodes (5): ADR-0042: Inspector endpoints: I1 at the boundary, history on request, edits go straight to versioning, Alternatives considered, Consequences, Context, Revisit if

### Community 236 - "local_run.py"
Cohesion: 0.26
Nodes (6): test_demo_openings_quote_the_exact_words_they_were_read_from(), _closing(), _deadline_words(), demo_openings(), DemoOpening, parsed_opening()

### Community 237 - "Incident runbook (ADR-0107)"
Cohesion: 0.22
Nodes (8): Bot down (S2), Data deletion request (S1 until done), Digest sent twice (S2), First 15 minutes (every incident), Incident log, Incident runbook (ADR-0107), Severity, Wrong eligibility shown (S1)

### Community 238 - "ADR-0075: Telegram inbound: a strict subset of the Update type, private chats only, drops counted"
Cohesion: 0.33
Nodes (5): ADR-0075: Telegram inbound: a strict subset of the Update type, private chats only, drops counted, Alternatives considered, Consequences, Context, Revisit if

### Community 239 - "ADR-0080: MCP server on the SDK's low-level `Server`, explicit Pydantic tool schemas, seven tools"
Cohesion: 0.33
Nodes (5): ADR-0080: MCP server on the SDK's low-level `Server`, explicit Pydantic tool schemas, seven tools, Alternatives considered, Consequences, Context, Revisit if

### Community 240 - "current_user"
Cohesion: 0.17
Nodes (7): ADR-0081: MCP identity: one bearer token per connection, hashed through ADR-0040, bound per request, Alternatives considered, Consequences, Context, Decision, Revisit if, current_user()

### Community 241 - "ADR-0088: API additions for the dashboard: /graph, /vocabulary, editable valid_to, required output fields"
Cohesion: 0.33
Nodes (5): ADR-0088: API additions for the dashboard: /graph, /vocabulary, editable valid_to, required output fields, Alternatives considered, Consequences, Context, Decision

### Community 242 - "WS-11 handover: MCP server"
Cohesion: 0.33
Nodes (5): Open problems, Suggested commit message, Tool surface, Verification (run 2026-10-25, after the code-review pass), WS-11 handover: MCP server

### Community 243 - "embedded_pg.py"
Cohesion: 0.29
Nodes (5): main(), run_slow_suite(), serve(), start(), main()

### Community 244 - ".prettierrc.json"
Cohesion: 0.40
Nodes (4): printWidth, semi, singleQuote, trailingComma

### Community 245 - "Requirements"
Cohesion: 0.40
Nodes (4): Functional (FR) — with acceptance criteria, MVP (target: in daily use by 2027-02-01), Non-functional (NFR), Requirements

### Community 246 - "ADR-0092: The 300-pair hand check is stratified, blind, keyed and re-drawn at report time"
Cohesion: 0.29
Nodes (6): ADR-0092: The 300-pair hand check is stratified, blind, keyed and re-drawn at report time, Alternatives considered, Consequences, Context, Decision, Revisit if

### Community 248 - "news_registry"
Cohesion: 0.18
Nodes (9): ADR-0100: Minimal news and finance adapters are vocabularies mapped onto the core link classes, Alternatives considered, Consequences, Context, Decision, Revisit if, news_registry(), test_only_shared_from_is_a_snapshot_and_it_never_propagates() (+1 more)

### Community 249 - "delivery_log.py"
Cohesion: 0.09
Nodes (11): ADR-0106: The weekly pilot report computes two docs/04 metrics and marks three TBD, Alternatives considered, Consequences, Context, Decision, Revisit if, DeliveryReader, PostgresDeliveryReader (+3 more)

### Community 250 - "comparable"
Cohesion: 0.18
Nodes (8): ADR-0121: "Three seeds" means three generator seeds, one results folder per seed, Alternatives considered, Consequences, Context, Decision, Revisit if, comparable(), _normalise()

### Community 252 - "ADR-0107: Three incident severities and a daily monitoring check for a one-operator pilot"
Cohesion: 0.29
Nodes (6): ADR-0107: Three incident severities and a daily monitoring check for a one-operator pilot, Alternatives considered, Consequences, Context, Decision, Revisit if

### Community 285 - "questions_needed"
Cohesion: 0.20
Nodes (8): _gold_of(), questions_needed(), ADR-0123: A row a version behind gold is stale; a repeated gold keeps the TTC window open, Alternatives considered, Consequences, Context, Decision, Revisit if

### Community 286 - "Production hardening — delivery log, atomic confirm, resume text, API boundary"
Cohesion: 0.29
Nodes (6): 1. What it does, 2. Why it exists, 4. Trade-offs, 6. Interview questions, 7. Exercise, Production hardening — delivery log, atomic confirm, resume text, API boundary

### Community 287 - "paper: numbers from results/ and the I8 check"
Cohesion: 0.29
Nodes (6): 1. What it does, 2. Why it exists, 4. Trade-offs, 6. Interview questions, 7. Exercise, paper: numbers from results/ and the I8 check

### Community 288 - "stale_retrieval_rate"
Cohesion: 0.20
Nodes (8): stale_retrieval_rate(), ADR-0120: Metric bodies, pooled suite aggregation and a retrieval probe in the replay, Alternatives considered, Consequences, Context, Decision, Revisit if, test_stale_retrieval_rate_counts_unflagged_hits_on_gold_stale_rows()

### Community 289 - "RuleResolver"
Cohesion: 0.12
Nodes (12): ADR-0019: Rule-first resolution, Alternatives considered, Consequences, Context, Decision, Revisit if, ADR-0031: Jobs rule resolvers recompute derived beliefs from their parents, Alternatives considered (+4 more)

### Community 290 - "Wave B — evaluation, pilot operations and write-up plumbing"
Cohesion: 0.20
Nodes (9): Checkpoint C4, Ground truth at launch, Rules for every wave-B session, Wave B — evaluation, pilot operations and write-up plumbing, Workstreams, WS-14 acceptance, WS-15 acceptance, WS-16 acceptance (+1 more)

### Community 291 - "worked_trace"
Cohesion: 0.36
Nodes (5): stale_recommendation_rate(), RecommendationSnapshot, test_events_without_gold_count_their_recommendations_in_the_denominator_only(), test_stale_recommendation_rate_counts_unflagged_recommendations_on_stale_beliefs(), worked_trace()

### Community 292 - "ADR-0070: Allowed-sources registry: a YAML file validated into Pydantic, terms note required"
Cohesion: 0.33
Nodes (5): ADR-0070: Allowed-sources registry: a YAML file validated into Pydantic, terms note required, Alternatives considered, Consequences, Context, Revisit if

### Community 293 - "Decision"
Cohesion: 0.09
Nodes (13): ADR-0072: The Scout is a plain loop over injected parts, fetching only through the sources package, Alternatives considered, Consequences, Context, Decision, Revisit if, ADR-0079: Event observers on the runner; a criteria change queues a per-user Scout run, Alternatives considered (+5 more)

### Community 294 - "ADR-0096: Candidate decisions are a compare-and-set on status, so a double confirm cannot write twice"
Cohesion: 0.33
Nodes (5): ADR-0096: Candidate decisions are a compare-and-set on status, so a double confirm cannot write twice, Alternatives considered, Context, Decision, Revisit if

### Community 295 - "Pilot metrics: definitions, sources and what is still missing"
Cohesion: 0.33
Nodes (5): Feedback the product records (ADR-0105), Pilot metrics: definitions, sources and what is still missing, The five metrics, Weekly survey (draft, for the guide's review), What would close the TBDs (proposals for the coordinator)

### Community 296 - "ripple.agents.scout and ripple.domains.jobs.sources: the Scout"
Cohesion: 0.25
Nodes (7): 1. What it does, 2. Why it exists, 4. Trade-offs, 5. Failure modes and tests, 6. Interview questions, 7. Exercise, ripple.agents.scout and ripple.domains.jobs.sources: the Scout

### Community 297 - "ripple.worker and ripple.notify — scheduled jobs, digest and alerts"
Cohesion: 0.25
Nodes (7): 1. What it does, 2. Why it exists, 4. Trade-offs, 5. Failure modes and tests, 6. Interview questions, 7. Exercise, ripple.worker and ripple.notify — scheduled jobs, digest and alerts

### Community 299 - "ADR-0091: Negatives at 3 per positive with every reversed link kept; train decontaminated against test"
Cohesion: 0.29
Nodes (6): ADR-0091: Negatives at 3 per positive with every reversed link kept; train decontaminated against test, Alternatives considered, Consequences, Context, Decision, Revisit if

### Community 308 - "ADR-0115: Embedded Postgres with pgvector for development and the local slow suite"
Cohesion: 0.29
Nodes (6): ADR-0115: Embedded Postgres with pgvector for development and the local slow suite, Alternatives considered, Consequences, Context, Decision, Revisit if

### Community 309 - "ADR-0125: The trained link finder fine-tunes ModernBERT-base on CPU; torch and transformers in a `linkfinder` group"
Cohesion: 0.29
Nodes (6): ADR-0125: The trained link finder fine-tunes ModernBERT-base on CPU; torch and transformers in a `linkfinder` group, Alternatives considered, Consequences, Context, Decision, Revisit if

### Community 310 - "ADR-0127: Link-finder evaluation: a transfer mode for H4, CPU cost per call, and a three-seed summary folder"
Cohesion: 0.29
Nodes (6): ADR-0127: Link-finder evaluation: a transfer mode for H4, CPU cost per call, and a three-seed summary folder, Alternatives considered, Consequences, Context, Decision, Revisit if

### Community 311 - "ADR-0130: Dashboard information architecture and visual system"
Cohesion: 0.29
Nodes (6): ADR-0130: Dashboard information architecture and visual system, Alternatives considered, Consequences, Context, Decision, Revisit if

### Community 312 - "ADR-0132: One-command local run of the whole product"
Cohesion: 0.29
Nodes (6): ADR-0132: One-command local run of the whole product, Alternatives considered, Consequences, Context, Decision, Revisit if

### Community 313 - "Running the whole product locally (tools/local_run.py, ripple.worker.run_once)"
Cohesion: 0.29
Nodes (6): 1. What it does, 2. Why it exists, 4. Trade-offs, 6. Interview questions, 7. Exercise, Running the whole product locally (tools/local_run.py, ripple.worker.run_once)

### Community 314 - "ripple.mcp_server — Ripple's memory as MCP tools"
Cohesion: 0.29
Nodes (7): 1. What it does, 2. Why it exists, 4. Trade-offs, 5. Failure modes and tests, 6. Interview questions, 7. Exercise, ripple.mcp_server — Ripple's memory as MCP tools

### Community 315 - "Pilot operations — feedback capture, the weekly report, incident handling"
Cohesion: 0.29
Nodes (6): 1. What it does, 2. Why it exists, 4. Trade-offs, 6. Interview questions, 7. Exercise, Pilot operations — feedback capture, the weekly report, incident handling

### Community 316 - "ripple.notify.inbound — the Telegram bot the student talks to"
Cohesion: 0.29
Nodes (6): 1. What it does, 2. Why it exists, 5. Failure modes and tests, 6. Interview questions, 7. Exercise, ripple.notify.inbound — the Telegram bot the student talks to

### Community 317 - "WS-18 handover: metric functions and the full benchmark"
Cohesion: 0.29
Nodes (6): Contract requests, Files by purpose, Follow-ups (not done), Suggested commit message, Verification (real output, final state), WS-18 handover: metric functions and the full benchmark

### Community 318 - "ADR-0026: Retrieval is lexical-first behind an Embedder contract; dense model decided at integration"
Cohesion: 0.33
Nodes (5): ADR-0026: Retrieval is lexical-first behind an Embedder contract; dense model decided at integration, Alternatives considered, Consequences, Context, Revisit if

### Community 319 - "ADR-0043: Resume candidates live in their own table until the user decides"
Cohesion: 0.33
Nodes (5): ADR-0043: Resume candidates live in their own table until the user decides, Alternatives considered, Consequences, Context, Revisit if

### Community 320 - "ADR-0094: The training loop is an interface with a fixed data view; the loop is the author's"
Cohesion: 0.33
Nodes (5): ADR-0094: The training loop is an interface with a fixed data view; the loop is the author's, Alternatives considered, Consequences, Context, Revisit if

### Community 321 - "ADR-0126: Link-finder training recipe, artifact folder, and the served linker in ripple.linking.trained"
Cohesion: 0.33
Nodes (5): ADR-0126: Link-finder training recipe, artifact folder, and the served linker in ripple.linking.trained, Alternatives considered, Consequences, Context, Revisit if

### Community 322 - "docs/paper — outlines and rendered numbers"
Cohesion: 0.33
Nodes (5): Commands, docs/paper — outlines and rendered numbers, How a number gets into the write-up, LaTeX-ready structure, What is here

### Community 323 - "Final delivery — everything buildable, built and verified (2026-10-31)"
Cohesion: 0.33
Nodes (5): Acceptance (the whole project), Done before the workstreams launched, Final delivery — everything buildable, built and verified (2026-10-31), What cannot be delivered from a chat, and is not faked, Workstreams (one shared checkout, file ownership as in wave B)

### Community 327 - "next.config.ts"
Cohesion: 0.50
Nodes (3): nextConfig, ADR-0029, ADR-0086

## Knowledge Gaps
- **53 isolated node(s):** `ADR-0029`, `ADR-0086`, `react-dom`, `@testing-library/dom`, `@types/node` (+48 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 2997 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **75 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Status` connect `FakeClock` to `useApi`, `generate_finance.py`, `ScenarioRunner`, `load_scenario`, `Link`, `fact`, `agents/conversation.py`, `Clock`, `Postgres Store`, `pytest`, `InMemoryStore`, `test_local_run.py`, `derive_for_opening`, `run`, `DecisionAction`, `Store`, `test_conversation.py`, `scout.py`, `generate.py`, `Resolution`, `build`, `api/schemas.py`, `User`, `RippleRunner`, `asyncio`, `job_context_from_env`, `tools.py`, `record_opening`, `models.py`, `jobs/schemas.py`, `Harness`, `StructuredFact`, `collections_abc`, `answers.py`, `jobs/vocabulary.py`, `ScoutCriteria`, `Kind`, `test_ranking.py`, `dedupe.py`, `asyncio`, `Memory`, `User`, `Services`?**
  _High betweenness centrality (0.107) - this node is a cross-community bridge._
- **Are the 24 inferred relationships involving `FakeClock` (e.g. with `ScenarioRunner` and `conversation_agent()`) actually correct?**
  _`FakeClock` has 24 INFERRED edges - model-reasoned connections that need verification._
- **What connects `ADR-0029`, `ADR-0086`, `react-dom` to the rest of the system?**
  _53 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `QuestionsView.tsx` be split into smaller, more focused modules?**
  _Cohesion score 0.07955596669750231 - nodes in this community are weakly interconnected._
- **Why does `3. How it works` connect `useApi` to `QuestionsView.tsx`, `FakeClock`, `types.ts`, `helpers.tsx`, `TellView.tsx`, `SessionProvider.tsx`, `MemoryDetailView.tsx`?**
  _High betweenness centrality (0.062) - this node is a cross-community bridge._
- **Are the 49 inferred relationships involving `InMemoryStore` (e.g. with `ScenarioRunner` and `test_tailor_refuses_an_unusable_opening()`) actually correct?**
  _`InMemoryStore` has 49 INFERRED edges - model-reasoned connections that need verification._
- **Should `FakeClock` be split into smaller, more focused modules?**
  _Cohesion score 0.05232383808095952 - nodes in this community are weakly interconnected._