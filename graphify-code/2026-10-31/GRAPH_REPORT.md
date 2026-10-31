# Graph Report - RIPPLE  (2026-10-31)

## Corpus Check
- 679 files · ~370,965 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 25 file(s) not represented in the graph (top: (none) 6, .jsonl 3, .toml 3)

## Summary
- 7991 nodes · 26543 edges · 308 communities (229 shown, 79 thin omitted)
- Extraction: 81% EXTRACTED · 19% INFERRED · 0% AMBIGUOUS · INFERRED: 4991 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- api/uploads.py
- FakeClock
- generate_finance.py
- ScenarioRunner
- Feedback
- StoreReader
- api/wiring.py
- fact
- agents/conversation.py
- Benchmark Metrics & Gold State
- Postgres Store
- pytest
- Telegram Notifications
- Alert Rendering & Digests
- InMemoryStore
- FakeLLM
- Router
- run
- test_handcheck.py
- sqlalchemy
- DecisionAction
- test_settings.py
- models.py
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
- PostgresUserStore
- RippleRunner
- types.ts
- asyncio
- RouterConfig
- raw_text_update
- job_context_from_env
- What was built
- anthropic.py
- current_user
- tools.py
- routers/resume.py
- jobs/openings.py
- OpeningAttribute
- fact
- test_i8_detector.py
- users.py
- LinkTypeRegistry
- run.py
- Kind
- Harness
- evaluate.py
- dates.py
- manifest.json
- replay.py
- agents/tailor.py
- OpeningView
- test_fetcher.py
- InMemoryCandidateStore
- test_ranking.py
- jobs_registry
- parsers/jd.py
- jobs_pairs.py
- jobs.py
- test_migration_0004.py
- tracks.py
- parsers/resume.py
- strip_email_envelope
- json
- pilot/report.py
- health.py
- i8.py
- CandidateStore
- package.json
- test_boundaries.py
- test_hardening_ratelimit.py
- me.py
- test_stale.py
- checkpoints.py
- test_feedback.py
- fixture
- logging.py
- channel.py
- _require_aware
- collections_abc
- PairMemory
- User
- TelegramBotApi
- Services
- paper/numbers.py
- engine_from_url
- FeedbackStore
- MemoryDetailView.tsx
- fetcher.py
- entrypoint.sh
- helpers.tsx
- __main__.py
- MapView.tsx
- ripple
- pytest
- AccountView.tsx
- resolve_all
- keyboards.py
- load_scenario
- RedisLease
- tracing.py
- InMemoryDeliveryLog
- Linker
- test_intake.py
- test_inbound_telegram_api.py
- compilerOptions
- test_inbound_render.py
- SelectableNode
- build_server
- ADR-0055: Digest and alert policy: thresholds, rendering, what never alerts
- routers/feedback.py
- .__call__
- ADR-0077: Telegram delivery: secret-token webhook into the API, at-most-once by update_id, long polling for development only
- RobotsPolicy
- Ripple — instructions for Claude Code
- 2. The original plan, item by item
- test_report.py
- Ordered tasks (each one session; tests first; [human] marks author-owned work)
- Split
- Ordered tasks
- test_scout_trigger.py
- app.py
- 3. How it works
- test_run_v1.py
- finance_v1/manifest.json
- Workstreams (dependency order, then value)
- InMemoryRateLimiter
- news_v1/manifest.json
- Data model
- EnqueueingScoutTrigger
- re
- Architecture
- Template
- paper/registry.py
- Bot
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
- ADR-0076: Telegram dispatcher: commands, link flow, keyboards for answers, two-step forget, agent for the rest
- bench: strategies, RippleBench v0 generator, replay harness, metric interfaces
- ripple.core.engine — the ripple engine (your module)
- Paper outline: Ripple — learned dependency links keep agent memory consistent
- identity.py
- Memory
- PostgresFeedbackStore
- ripple.api — identity, inspector, confirmation flow, export and delete
- test_tailor.py
- Files
- Linkers, change detection and intake
- ripple.llm: provider adapter, transport retries, prices, tracing
- devDependencies
- ripple.core: writes, runner, versioning, forget, sweep, answers
- dedupe.py
- ripple.storage — PostgresStore, tables and migrations
- test_generators.py
- Deploying Ripple (ADR-0029)
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
- UserDirectory
- ADR-0029: Deployment topology: one VPS, Compose, Caddy TLS, GHCR images, pg_dump backups
- ADR-0044: Export everything, delete through forget, keep the deletion audit
- ADR-0050: Lexical scoring (BM25 / PostgreSQL FTS), reciprocal rank fusion and one-hop graph expansion for retrieval
- ADR-0063: Metric definitions for RippleBench v0 (interfaces; bodies are [human])
- ADR-0086: Dashboard pages, token session in sessionStorage, query-string routing
- JobFailedForUsersError
- main
- WriteOut
- Contract requests (coordinator)
- EventSnapshot
- Thesis outline: Ripple — a consistency layer for agent memory
- ADR-0042: Inspector endpoints: I1 at the boundary, history on request, edits go straight to versioning
- test_bench_replay.py
- Incident runbook (ADR-0107)
- ADR-0075: Telegram inbound: a strict subset of the Update type, private chats only, drops counted
- ADR-0080: MCP server on the SDK's low-level `Server`, explicit Pydantic tool schemas, seven tools
- ADR-0081: MCP identity: one bearer token per connection, hashed through ADR-0040, bound per request
- ADR-0088: API additions for the dashboard: /graph, /vocabulary, editable valid_to, required output fields
- What was built
- finance/test_vocabulary.py
- .prettierrc.json
- Requirements
- ADR-0092: The 300-pair hand check is stratified, blind, keyed and re-drawn at report time
- ResizeObserverStub
- ADR-0106: The weekly pilot report computes two docs/04 metrics and marks three TBD
- test_migration_0005_matches_delivery_tables
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
- ripple.agents — Conversation and Tailor
- Production hardening — delivery log, atomic confirm, resume text, API boundary
- paper: numbers from results/ and the I8 check
- list_recommendations
- ADR-0019: Rule-first resolution
- ADR-0032: Ranking openings: eligible, then urgent, then fit, then variety; flagged, never retired
- ADR-0046: Tailor agent: read-only, picks from id-validated candidates
- ADR-0070: Allowed-sources registry: a YAML file validated into Pydantic, terms note required
- ADR-0072: The Scout is a plain loop over injected parts, fetching only through the sources package
- ADR-0096: Candidate decisions are a compare-and-set on status, so a double confirm cannot write twice
- Pilot metrics: definitions, sources and what is still missing
- ADR-0031: Jobs rule resolvers recompute derived beliefs from their parents

## God Nodes (most connected - your core abstractions)
1. `FakeClock` - 307 edges
2. `InMemoryStore` - 279 edges
3. `Memory` - 254 edges
4. `Status` - 239 edges
5. `fact()` - 215 edges
6. `FakeLLM` - 176 edges
7. `derived()` - 154 edges
8. `memory()` - 153 edges
9. `link()` - 136 edges
10. `ChangeEvent` - 132 edges

## Surprising Connections (you probably didn't know these)
- `Decision` --references--> `setup()`  [INFERRED]
  docs/adr/0023-langgraph-checkpointer.md → apps/web/tests/questions.test.tsx
- `Consequences` --references--> `validate_scenario()`  [INFERRED]
  docs/adr/0100-news-and-finance-vocabularies.md → bench/scenario.py
- `Context` --references--> `create_app()`  [INFERRED]
  docs/adr/0098-api-boundary-hardening.md → src/ripple/api/app.py
- `Decision` --references--> `DomainVocabulary`  [INFERRED]
  docs/adr/0088-dashboard-api-additions.md → src/ripple/api/contracts.py
- `Alternatives considered` --references--> `answer_question()`  [INFERRED]
  docs/adr/0076-telegram-dispatcher.md → src/ripple/api/routers/questions.py

## Import Cycles
- None detected.

## Communities (308 total, 79 thin omitted)

### Community 0 - "api/uploads.py"
Cohesion: 0.16
Nodes (11): SourceOut, source_for(), parse_resume_ref(), Quote, quote(), ResumeRef, test_parse_resume_ref_reads_upload_id_and_span(), test_parse_resume_ref_rejects_anything_else() (+3 more)

### Community 1 - "FakeClock"
Cohesion: 0.05
Nodes (87): TriggerKind, update_memory(), test_scout_run_isolates_a_failing_user_and_raises_at_the_end(), run_for_user(), runner(), test_opening_recorder_records_anchor_fields_and_derived_beliefs(), test_fake_clock_set_jumps_to_moment(), _cgpa_edit() (+79 more)

### Community 2 - "generate_finance.py"
Cohesion: 0.08
Nodes (51): ceo_departure(), Company, _company_fact(), _floor(), forget_holding(), guidance_cut(), Investor, journal_entry() (+43 more)

### Community 3 - "ScenarioRunner"
Cohesion: 0.08
Nodes (29): ScenarioOutcome, ScenarioRunner, scenario_paths(), _cgpa_spec(), _scripted(), __init__(), test_an_answer_to_a_question_a_baseline_never_asked_is_a_recorded_error(), test_append_only_keeps_the_superseded_version_valid_and_touches_no_dependent() (+21 more)

### Community 4 - "Feedback"
Cohesion: 0.08
Nodes (47): Rendered numbers, DeliveryRecord, alerted_pairs(), _opening(), _ordered(), pending(), positive_pairs(), question_usefulness() (+39 more)

### Community 5 - "StoreReader"
Cohesion: 0.05
Nodes (15): ADR-0087: Openings map built from the inspector's `why` links, laid out by kind, Alternatives considered, Consequences, Context, Decision, Revisit if, 1. What it does, 2. Why it exists (+7 more)

### Community 6 - "api/wiring.py"
Cohesion: 0.04
Nodes (53): Consequences, ADR-0078: The Telegram channel is hosted in the API's lifespan; Services carries the shared parts, Alternatives considered, Consequences, Context, Decision, Integration done at checkpoint C3 (coordinator), Contract change requests (coordinator) (+45 more)

### Community 7 - "fact"
Cohesion: 0.07
Nodes (70): RetrievalPath, FusedHit, candidate_count(), _Collected, _Frontier, HybridRetriever, _source_evidence(), _visible() (+62 more)

### Community 8 - "agents/conversation.py"
Cohesion: 0.07
Nodes (23): ADR-0045: Conversation agent: one LangGraph turn, strict intent, evidence-only answers, Alternatives considered, Consequences, Context, Decision, Revisit if, 6. Interview questions, _compose_answer() (+15 more)

### Community 9 - "Benchmark Metrics & Gold State"
Cohesion: 0.12
Nodes (24): ConvergenceRecord, correct_updates(), cost_per_ripple(), questions_asked(), stale_kept(), stale_retrieval_rate(), target_outcomes(), TargetOutcome (+16 more)

### Community 10 - "Postgres Store"
Cohesion: 0.06
Nodes (15): 3. How it works, ChangeEventNotFoundError, _event(), _event_row(), _forget_row(), _link(), _link_row(), _memory() (+7 more)

### Community 11 - "pytest"
Cohesion: 0.06
Nodes (66): run(), change_event(), decision(), memory(), test_inmemory_store_refuses_writes_outside_a_transaction(), test_decision_keep_forbids_new_version_id(), test_decision_update_requires_new_version_id(), test_link_rejects_self_dependency() (+58 more)

### Community 12 - "Telegram Notifications"
Cohesion: 0.05
Nodes (36): 1. What it does, 2. Why it exists, 4. Trade-offs, 5. Failure modes and tests, 6. Interview questions, 7. Exercise, ripple.worker and ripple.notify — scheduled jobs, digest and alerts, Follow-ups (not in this round) (+28 more)

### Community 13 - "Alert Rendering & Digests"
Cohesion: 0.08
Nodes (39): 3. How it works, What was built, Recommendation, AlertKind, Thresholds, Alert, alert_kinds(), _alert_reason() (+31 more)

### Community 14 - "InMemoryStore"
Cohesion: 0.06
Nodes (31): Decision, forget(), MemoryNotFoundError, test_conversation_retries_an_answer_question_without_its_answer_kind(), CountingStore, __init__(), _seed(), test_forget_deletes_whole_version_chain_and_depends_on_cascade() (+23 more)

### Community 15 - "FakeLLM"
Cohesion: 0.10
Nodes (34): Open problems / follow-ups, extract_text(), build_pdf(), candidate(), pdf_with_lines(), resume_reply(), router_for(), text_stream() (+26 more)

### Community 16 - "Router"
Cohesion: 0.07
Nodes (15): OpeningParserAdapter, LLMLinker, Message, memories_block(), memory_block(), load_prompt(), LLMResolver, Router (+7 more)

### Community 17 - "run"
Cohesion: 0.04
Nodes (102): LinkCreator, Sensitivity, derive_criteria(), derive_for_opening(), record_opening(), _link_beliefs_derived_since(), _live_profile_facts(), record_profile_fact() (+94 more)

### Community 18 - "test_handcheck.py"
Cohesion: 0.10
Nodes (38): LabelledPair, _fill(), _rows(), _small_pair_file(), test_agreement_is_reported_overall_by_provenance_and_by_stratum(), test_allocate_gives_each_stratum_its_minimum_then_shares_the_rest_exactly(), test_allocate_keeps_the_minimums_when_they_exceed_the_total(), test_allocate_takes_everything_when_the_set_is_small() (+30 more)

### Community 19 - "sqlalchemy"
Cohesion: 0.04
Nodes (21): upgrade(), upgrade(), upgrade(), upgrade(), upgrade(), new_id(), Base, test_new_id_is_a_uuid4_string() (+13 more)

### Community 20 - "DecisionAction"
Cohesion: 0.12
Nodes (48): Consequences, DecisionAction, ResolverChain, compute_eligibility(), EligibilityRule, _eligibility_parents(), test_eligibility_rule_compares_as_before_on_an_explicit_10_point_scale(), test_eligibility_rule_declines_when_the_student_is_on_a_4_point_scale() (+40 more)

### Community 21 - "test_settings.py"
Cohesion: 0.15
Nodes (6): _cron_by_name(), test_job_context_is_read_from_arq_ctx_and_missing_context_is_a_configuration_error(), test_on_startup_refuses_to_run_without_a_database_url(), test_on_startup_refuses_to_run_without_redis_url(), test_worker_settings_register_sweep_digest_alerts_and_scout_slots(), test_worker_settings_schedule_is_utc_and_ordered_scout_sweep_digest()

### Community 22 - "models.py"
Cohesion: 0.03
Nodes (62): domain_of(), registry_for(), AppendOnlyStrategy, as_runner(), build_strategy(), CountingResolver, MemoryStrategy, NewestWinsStrategy (+54 more)

### Community 23 - "test_conversation.py"
Cohesion: 0.09
Nodes (40): RetrievedMemory, test_answer_question_answered_meanwhile_replies_instead_of_raising(), test_answer_question_corrected_updates_the_structured_value(), test_answer_question_corrected_writes_a_new_version_and_ripples(), test_answer_question_for_an_unknown_question_writes_nothing(), test_answer_question_no_longer_holds_retires_and_ripples(), test_answer_question_still_holds_restores_the_memory(), test_ask_answers_from_retrieved_evidence_with_citations() (+32 more)

### Community 24 - "recommendation"
Cohesion: 0.08
Nodes (37): test_fake_clock_advance_moves_now(), failing_transport(), RecordingTransport, SentMessage, FakeRecommendationSource, FakeUserDirectory, recommendation(), _service() (+29 more)

### Community 25 - "scout.py"
Cohesion: 0.04
Nodes (44): ADR-0073: Scout refusals are counted apart from errors; criteria parse only the gates, Alternatives considered, Consequences, Context, Decision, ADR-0079: Event observers on the runner; a criteria change queues a per-user Scout run, Alternatives considered, Consequences (+36 more)

### Community 26 - "test_bench_generate.py"
Cohesion: 0.08
Nodes (31): check_data(), generate(), Generated, main(), scenario_yaml(), write_data(), Verification (real output, 2026-10-20, final run), Code review (+23 more)

### Community 27 - "generate.py"
Cohesion: 0.16
Nodes (24): accepted_offer(), build_scenario(), _cgpa_memory(), cgpa_rise(), cutoff_unknown(), deadline_moved(), exam_block(), forget_cgpa() (+16 more)

### Community 28 - "Resolution"
Cohesion: 0.08
Nodes (15): AliasResolver, Decision, Context, Resolution, ResolutionContext, RuleResolver, _compare(), _in_doubt() (+7 more)

### Community 29 - "test_numbers.py"
Cohesion: 0.16
Nodes (51): 5. Failure modes and tests (tests/paper), Refused, Rendered, resolve_macro(), bench_config(), complete(), count_spec(), headline_config() (+43 more)

### Community 30 - "build"
Cohesion: 0.04
Nodes (53): answer_data(), feedback_data(), test_dispatcher_answer_tap_on_a_memory_that_is_no_longer_pending_is_refused(), run(), test_dispatcher_answer_tap_on_another_users_memory_changes_nothing(), run(), test_dispatcher_answer_tap_with_garbage_callback_data_is_refused(), test_dispatcher_correction_tap_then_text_writes_a_new_version_without_the_agent() (+45 more)

### Community 32 - "api/schemas.py"
Cohesion: 0.05
Nodes (38): description, not_found(), owned_memory(), mentions(), get_graph(), edit_memory(), forget_memory(), get_memory() (+30 more)

### Community 33 - "PostgresUserStore"
Cohesion: 0.10
Nodes (6): Contract change requests to the coordinator, Contracts, RecommendationSource (C1, consumed as-is), UserDirectory (defined here, implemented by the identity module), PostgresUserStore, _user()

### Community 34 - "RippleRunner"
Cohesion: 0.06
Nodes (36): CheckEverythingStrategy, one_shot_engine(), first_wave(), Context, ADR-0060: Baseline memory strategies behind one MemoryStrategy protocol, Alternatives considered, Context, Decision (+28 more)

### Community 35 - "types.ts"
Cohesion: 0.04
Nodes (49): ClientOptions, send(), encodeQuery(), FeedbackReceipt, messageFor(), Query, readDetail(), RippleApi (+41 more)

### Community 36 - "asyncio"
Cohesion: 0.05
Nodes (47): RecordingOpeningRecorder, ScriptedDetector, ScriptedRecommendations, SimpleCandidateStatements, _adapters(), error(), McpHarness, out() (+39 more)

### Community 37 - "RouterConfig"
Cohesion: 0.07
Nodes (31): 1. What it does, 2. Why it exists, 3. How it works, 4. Trade-offs, 5. Failure modes and tests, 6. Interview questions, 7. Exercise, ripple.llm — the Router (+23 more)

### Community 38 - "raw_text_update"
Cohesion: 0.06
Nodes (54): ReceiveResult, _callback(), DroppedUpdates, parse_update(), TelegramCallbackQuery, TelegramChat, TelegramMessage, TelegramUpdate (+46 more)

### Community 39 - "job_context_from_env"
Cohesion: 0.07
Nodes (33): nightly_sweep(), ChangeEventLease, event_lease_key(), InMemoryLease, sweep_lease_key(), test_scout_run_scouts_every_active_user_with_an_injected_agent(), context(), RecordingSweep (+25 more)

### Community 40 - "What was built"
Cohesion: 0.07
Nodes (18): ADR-0097: The text layer of every resume upload is stored so span references resolve, Alternatives considered, Consequences, Context, Decision, Revisit if, InMemoryUploadStore, PostgresUploadStore (+10 more)

### Community 41 - "anthropic.py"
Cohesion: 0.08
Nodes (19): CompletionRequest, CompletionResult, LLMClient, AnthropicClient, AnthropicLike, _default_factory(), _Messages, _tool_input() (+11 more)

### Community 42 - "current_user"
Cohesion: 0.22
Nodes (3): current_user(), _unauthorized(), services_of()

### Community 43 - "tools.py"
Cohesion: 0.17
Nodes (26): 3. How it works, AnswerIn, AnswerOut, DecisionOut, ErrorOut, EventOut, ExplainIn, ExplainOut (+18 more)

### Community 44 - "routers/resume.py"
Cohesion: 0.08
Nodes (22): candidate_from_fact(), fact_of(), _already(), _claim(), confirm_candidate(), list_candidates(), _pending_candidate(), reject_candidate() (+14 more)

### Community 45 - "jobs/openings.py"
Cohesion: 0.10
Nodes (16): InvalidObjectError, field_memory(), _validate(), _validate_opening(), profile_fact(), anchor_structured(), _facts(), parse_batch() (+8 more)

### Community 46 - "OpeningAttribute"
Cohesion: 0.14
Nodes (38): OpeningAttribute, jd_reply(), _field(), _parse(), test_parse_jd_adds_deadline_from_regex_when_model_missed_it(), test_parse_jd_builds_summary_from_title_and_company_not_from_the_model(), test_parse_jd_coerces_cutoff_to_float_and_batch_to_int(), test_parse_jd_does_not_take_a_date_from_the_next_sentence_as_deadline() (+30 more)

### Community 47 - "fact"
Cohesion: 0.06
Nodes (41): Decision, run(), run(), run(), run(), run(), run(), run() (+33 more)

### Community 48 - "test_i8_detector.py"
Cohesion: 0.10
Nodes (51): Category, Claim, judge(), KnownViolation, line_claims(), emit(), Rules, scan_text() (+43 more)

### Community 49 - "users.py"
Cohesion: 0.04
Nodes (29): ADR-0040: Identity for the pilot: admin-created users, hashed bearer tokens, one-time Telegram link codes, Alternatives considered, Consequences, Context, Decision, Revisit if, Consequences, Decision (+21 more)

### Community 50 - "LinkTypeRegistry"
Cohesion: 0.10
Nodes (28): _unknown_link_type(), ADR-0100: Minimal news and finance adapters are vocabularies mapped onto the core link classes, Alternatives considered, Consequences, Context, Decision, Revisit if, _cascade() (+20 more)

### Community 51 - "run.py"
Cohesion: 0.10
Nodes (24): load_jobs_v0(), load_manifest(), _content_line(), _data_description(), _display(), git_short_sha(), main(), _report() (+16 more)

### Community 52 - "Kind"
Cohesion: 0.12
Nodes (15): Decision, visible_for_retrieval(), VisibleMemory, fit_reasons(), opening_memories(), _belief(), JobsRecommender, _Ranked (+7 more)

### Community 53 - "Harness"
Cohesion: 0.03
Nodes (105): Consequences, candidate_fact(), _rebase_spans(), ScriptedOpeningParser, ScriptedResumeParser, span(), unparseable_opening(), unparseable_resume() (+97 more)

### Community 54 - "evaluate.py"
Cohesion: 0.10
Nodes (44): InvalidOutputLinker, _pair_file(), _prediction(), ScriptedLinker, test_confusion_counts_and_scores_detection_and_type(), test_confusion_for_an_untyped_linker_reports_no_typed_metrics(), test_confusion_reports_undefined_precision_as_none_and_f1_as_zero(), test_confusion_without_gold_negatives_reports_no_precision() (+36 more)

### Community 55 - "dates.py"
Cohesion: 0.17
Nodes (12): find_dates(), _moment_of(), normalise_deadline(), _zone_of(), test_find_dates_does_not_read_a_word_starting_with_am_as_a_time(), test_find_dates_ignores_version_numbers_and_stray_numbers(), test_find_dates_keeps_source_offsets(), test_normalise_deadline_keeps_the_date_when_the_time_is_impossible() (+4 more)

### Community 56 - "manifest.json"
Cohesion: 0.08
Nodes (23): accepted_offer, cgpa_rise, cutoff_unknown, deadline_moved, exam_block, forget_cgpa, resume_update, data_sha256 (+15 more)

### Community 57 - "replay.py"
Cohesion: 0.17
Nodes (8): _company_of(), _deadline_of(), memories_below(), _memory_snapshot(), RecommendationSnapshot, snapshot_after_event(), _state(), StubActionLayer

### Community 58 - "agents/tailor.py"
Cohesion: 0.09
Nodes (18): Decision, Code review (code-reviewer subagent, 2026-10-20) and what was done, Design in one paragraph each, How consumers call it, Suggested commit message, Verification (run 2026-10-20, paths restricted to WS-4 ownership), What was built, WS-4 handover: Conversation and Tailor agents (LangGraph) (+10 more)

### Community 59 - "OpeningView"
Cohesion: 0.07
Nodes (19): ADR-0034: CGPA is compared with a cutoff only on one scale; otherwise the rules defer, Alternatives considered, Context, Decision, Belief, compute_criteria(), compute_fit(), compute_reminder() (+11 more)

### Community 60 - "test_fetcher.py"
Cohesion: 0.08
Nodes (52): FetchFailedError, test_invariant_I5_scout_records_only_parsed_fields_with_spans_into_the_page_text(), test_invariant_I6_scout_declares_only_closed_capabilities_and_writes_only_openings(), test_invariant_I6_scout_only_gets_allowed_sources(), test_immediate_trigger_runs_the_scout_for_the_user(), test_scout_caps_the_candidates_parsed_per_source(), test_scout_counts_a_failing_source_and_continues_with_the_next(), test_scout_does_not_fetch_a_disabled_source() (+44 more)

### Community 61 - "InMemoryCandidateStore"
Cohesion: 0.28
Nodes (3): InMemoryCandidateStore, TestInMemoryConditionalReplace, TestInMemoryCandidateStore

### Community 62 - "test_ranking.py"
Cohesion: 0.18
Nodes (18): Status, StalePendingStore, test_invariant_I1_retrieval_never_returns_retired_and_flags_suspect(), Board, test_recommender_does_not_spread_openings_without_a_company_as_one_employer(), test_recommender_fills_title_company_deadline_and_cited_fit_reasons(), test_recommender_flags_an_opening_whose_belief_or_field_is_suspect_or_pending(), test_recommender_is_not_flagged_by_a_belief_it_does_not_use() (+10 more)

### Community 63 - "jobs_registry"
Cohesion: 0.08
Nodes (34): ADR-0094: The training loop is an interface with a fixed data view; the loop is the author's, Alternatives considered, Consequences, Context, Decision, Revisit if, 1. What it does, 2. Why it exists (+26 more)

### Community 64 - "parsers/jd.py"
Cohesion: 0.06
Nodes (37): ADR-0030: An opening is one anchor memory plus one structured fact per field, Alternatives considered, Consequences, Context, Revisit if, 3. How it works, What was built, DateMatch (+29 more)

### Community 65 - "jobs_pairs.py"
Cohesion: 0.11
Nodes (36): Provenance, scenario(), built(), _candidate(), test_jobs_pairs_build_is_deterministic(), test_jobs_pairs_carry_both_generated_provenances_and_no_other(), test_jobs_pairs_manifest_counts_and_hash_describe_the_file(), test_jobs_pairs_seed_moves_only_the_sampled_negatives() (+28 more)

### Community 66 - "jobs.py"
Cohesion: 0.07
Nodes (21): Decision, JobContext, Lease, leased(), daily_digest_job(), hourly_alerts_job(), job_context(), nightly_sweep_job() (+13 more)

### Community 67 - "test_migration_0004.py"
Cohesion: 0.08
Nodes (17): 1. What it does, 2. Why it exists, 4. Trade-offs, 5. Failure modes and tests, 6. Interview questions, 7. Exercise, ripple.retrieval — hybrid search, graph expansion, I1 filtering, content_tsvector() (+9 more)

### Community 68 - "tracks.py"
Cohesion: 0.06
Nodes (47): data_hash(), generate(), main(), _pairs_file(), pairs_text(), ManifestEntry, generate(), main() (+39 more)

### Community 69 - "parsers/resume.py"
Cohesion: 0.05
Nodes (39): ADR-0035: Parsers: LLM extraction with deterministic span, value and date validation, Alternatives considered, Consequences, Context, Decision, Revisit if, 1. What it does, 2. Why it exists (+31 more)

### Community 70 - "strip_email_envelope"
Cohesion: 0.18
Nodes (14): _cut_disclaimer(), _cut_signature(), _drop_headers(), strip_email_envelope(), test_strip_email_envelope_cuts_a_signature_followed_by_a_long_disclaimer(), test_strip_email_envelope_cuts_disclaimer_and_closing(), test_strip_email_envelope_keeps_a_date_line_inside_the_jd_body(), test_strip_email_envelope_keeps_a_double_dash_divider_above_long_content() (+6 more)

### Community 71 - "json"
Cohesion: 0.10
Nodes (23): ChangeKind, detect_structured_update(), LLMOutputInvalidError, LLMChangeDetector, _summarise(), ChangeVerdict, _detector(), test_llm_detector_classifies_temporary_with_valid_to() (+15 more)

### Community 72 - "pilot/report.py"
Cohesion: 0.07
Nodes (24): 3. How it works, Files by purpose, DeliveryReader, PostgresDeliveryReader, collect(), FeedbackReader, first_versions(), generate() (+16 more)

### Community 73 - "health.py"
Cohesion: 0.05
Nodes (34): ADR-0098: API boundary hardening: token-bucket write limits, health probes, request ids with JSON logs, security headers and a body cap, Alternatives considered, Consequences, Context, Decision, Revisit if, 3. How it works, 5. Failure modes and tests (+26 more)

### Community 74 - "i8.py"
Cohesion: 0.08
Nodes (32): _allowable(), _blank(), _blank_file_name(), _blank_pin(), blocks(), CategoryRule, check(), _cited_run() (+24 more)

### Community 75 - "CandidateStore"
Cohesion: 0.23
Nodes (5): CandidateStore, _candidate(), CandidateStoreContract, ConditionalReplaceContract, _decided()

### Community 76 - "package.json"
Cohesion: 0.05
Nodes (36): config, dependencies, next, react, react-dom, @xyflow/react, engines, node (+28 more)

### Community 77 - "test_boundaries.py"
Cohesion: 0.23
Nodes (9): _clock_reads(), _core_sources(), _imported_modules(), _is_allowed(), test_boundary_check_detects_a_forbidden_import(), test_clock_check_allows_injected_clock(), test_clock_check_detects_disguised_now_calls(), test_core_never_reads_the_wall_clock_outside_clock_module() (+1 more)

### Community 78 - "test_hardening_ratelimit.py"
Cohesion: 0.08
Nodes (21): Bucket, InMemoryRateLimiter, RateDecision, RateLimiter, RateLimitGuard, RateLimits, _refill(), _guarded() (+13 more)

### Community 79 - "me.py"
Cohesion: 0.24
Nodes (4): create_telegram_link_code(), delete_me(), export_me(), get_me()

### Community 80 - "test_stale.py"
Cohesion: 0.08
Nodes (32): iter_stale(), load_stale(), main(), stale_files(), stale_path_from_env(), StaleFormatError, StaleItem, StaleSession (+24 more)

### Community 81 - "checkpoints.py"
Cohesion: 0.17
Nodes (5): Open problems, memory_saver(), postgres_saver(), test_memory_saver_is_a_fresh_checkpointer_each_time(), test_postgres_saver_is_an_async_context_manager_that_does_not_connect_on_creation()

### Community 82 - "test_feedback.py"
Cohesion: 0.08
Nodes (36): asking(), feedback_harness(), opening(), seed_event(), test_delete_me_erases_feedback(), run(), test_export_includes_the_users_feedback(), run() (+28 more)

### Community 83 - "fixture"
Cohesion: 0.05
Nodes (48): Decision, What was built, Candidate, _collect_text(), _descendants(), _Element, _element_children(), extract_candidates() (+40 more)

### Community 84 - "logging.py"
Cohesion: 0.12
Nodes (12): accept_trace_id(), bind_trace_id(), _header(), logging_config(), new_trace_id(), reset_trace_id(), test_accept_trace_id_keeps_plain_tokens(), test_accept_trace_id_mints_a_fresh_id_for_anything_else() (+4 more)

### Community 85 - "channel.py"
Cohesion: 0.05
Nodes (32): Decision, 1. What it does, 2. Why it exists, 3. How it works, 4. Trade-offs, 5. Failure modes and tests, 6. Interview questions, 7. Exercise (+24 more)

### Community 87 - "collections_abc"
Cohesion: 0.03
Nodes (56): ADR-0026: Retrieval is lexical-first behind an Embedder contract; dense model decided at integration, Alternatives considered, Consequences, Context, Decision, Revisit if, 3. How it works, Contract change requests (coordinator) (+48 more)

### Community 88 - "PairMemory"
Cohesion: 0.09
Nodes (33): PairMemory, read_pairs(), split_for(), write_pairs(), ADR-0090: Jobs link pairs come from static scenario snapshots, with structure rules as a stratum, Alternatives considered, Consequences, Context (+25 more)

### Community 89 - "User"
Cohesion: 0.09
Nodes (23): Decision, CallbackAck, ChatDirectory, Conversation, InboundDispatcher, looks_like_opening(), Outcome, parse_command() (+15 more)

### Community 90 - "TelegramBotApi"
Cohesion: 0.06
Nodes (27): 1. What it does, 2. Why it exists, 3. How it works, 4. Trade-offs, 5. Failure modes and tests, 7. Exercise, ripple.core foundations: clock, ids, errors, boundaries, _open_telegram_channel() (+19 more)

### Community 91 - "Services"
Cohesion: 0.03
Nodes (63): ADR-0041: API composition: `create_app(services)`, a `Services` object, environment-only wiring, Alternatives considered, Consequences, Context, Decision, Revisit if, ADR-0043: Resume candidates live in their own table until the user decides, Alternatives considered (+55 more)

### Community 92 - "paper/numbers.py"
Cohesion: 0.08
Nodes (22): _all_filled(), comparable(), discover_runs(), lookup(), matches_config(), model_ids(), _normalise(), _not_runnable() (+14 more)

### Community 93 - "engine_from_url"
Cohesion: 0.06
Nodes (24): Contract change requests (coordinator-owned files), run_migrations_offline(), run_migrations_online(), _run_sync(), _url(), database_url(), engine_from_url(), _require_database() (+16 more)

### Community 94 - "FeedbackStore"
Cohesion: 0.09
Nodes (16): ADR-0105: Pilot feedback is one row per (student, memory, kind), first statement wins, Alternatives considered, Consequences, Context, Decision, Revisit if, feedback_store_of(), FeedbackStore (+8 more)

### Community 95 - "MemoryDetailView.tsx"
Cohesion: 0.09
Nodes (54): FeedbackKind, Link, Memory, QuestionOut, Empty(), FlaggedChip(), KindChip(), LABELS (+46 more)

### Community 96 - "fetcher.py"
Cohesion: 0.07
Nodes (10): Decision, ScoutTrigger, CachedPage, FetchCache, InMemoryFetchCache, FetchRefusedError, FetchResult, SourceFetcher (+2 more)

### Community 104 - "helpers.tsx"
Cohesion: 0.12
Nodes (37): ApiError, TOKEN_KEY, MemoryDetailView(), exportOut, me, editResult(), openEditFor(), ALL_STATUSES (+29 more)

### Community 106 - "__main__.py"
Cohesion: 0.12
Nodes (4): streamable_http_app(), serve_http(), serve_stdio(), _serve_stdio()

### Community 112 - "MapView.tsx"
Cohesion: 0.09
Nodes (34): GraphOut, MemoryStatus, VisibleStatus, VocabularyOut, MapPage(), MemoriesPage(), StatusChipProps, statusLabel() (+26 more)

### Community 127 - "pytest"
Cohesion: 0.13
Nodes (25): TokenBucket, parse_registry(), SourceRegistryError, test_intent_verdict_rejects_payload_that_does_not_match_the_intent(), advancing_sleeper(), test_token_bucket_default_burst_of_one_never_lets_two_requests_through_at_once(), test_token_bucket_does_not_wait_when_enough_time_has_passed(), test_token_bucket_first_request_is_immediate_and_the_second_waits_the_interval() (+17 more)

### Community 128 - "AccountView.tsx"
Cohesion: 0.06
Nodes (48): nextConfig, ADR-0029, ADR-0086, AccountPage(), DetailFromQuery(), MemoryDetailPage(), ADR-0086, LoginPage() (+40 more)

### Community 129 - "resolve_all"
Cohesion: 0.10
Nodes (29): figure_cells(), format_value(), inconsistent_sources(), main(), _markdown_value(), _plain(), render_figure_csv(), render_figure_dat() (+21 more)

### Community 130 - "keyboards.py"
Cohesion: 0.09
Nodes (15): BotSender, CallbackDataError, Button, forget_data(), forget_keyboard(), InlineKeyboard, keyboard_rows(), test_answer_callback_data_round_trips() (+7 more)

### Community 131 - "load_scenario"
Cohesion: 0.12
Nodes (18): load_scenario(), test_every_test_split_scenario_link_of_the_seeded_state_is_a_positive(), test_snapshot_of_link_stays_on_the_resume_version_it_was_written_with(), test_snapshots_drop_retired_expired_and_forgotten_memories(), _texts(), _check_expectations(), _cutoff_unknown(), test_replay_agrees_with_every_v0_scenario_expectation() (+10 more)

### Community 132 - "RedisLease"
Cohesion: 0.06
Nodes (23): ADR-0056: Worker jobs are idempotent per user; sweeps hold a per-user lease; UTC schedule, Alternatives considered, Consequences, Revisit if, ADR-0099: The runner holds a per-ChangeEvent lease while it drives an event, Alternatives considered, Consequences, Context (+15 more)

### Community 133 - "tracing.py"
Cohesion: 0.04
Nodes (33): ADR-0028: Langfuse tracer implemented now behind the Tracer protocol, Alternatives considered, Consequences, Context, Decision, Revisit if, 1. What it does, 2. Why it exists (+25 more)

### Community 134 - "InMemoryDeliveryLog"
Cohesion: 0.07
Nodes (16): ADR-0095: A Postgres delivery log keyed by (user, kind, key) makes digests and alerts survive restarts, Alternatives considered, Consequences, Context, Decision, Revisit if, _day_start(), InMemoryDeliveryLog (+8 more)

### Community 135 - "Linker"
Cohesion: 0.05
Nodes (30): ADR-0093: Link finders are scored per pair with opaque ids, stratified by provenance and held-out cell, Alternatives considered, Consequences, Context, Decision, Revisit if, ADR-0102: Finance link pairs for H4 come from the finance_v1 scenarios, test split only, Alternatives considered (+22 more)

### Community 136 - "test_intake.py"
Cohesion: 0.13
Nodes (21): 3. How it works, Coordinator actions requested, ChangeClassification, Intake, proposals_to_links(), __init__(), _intake(), __init__() (+13 more)

### Community 137 - "test_inbound_telegram_api.py"
Cohesion: 0.14
Nodes (17): run(), api(), Recorder, test_bot_api_answer_callback_query_posts_the_id_and_truncated_text(), test_bot_api_get_updates_posts_offset_timeout_and_allowed_updates(), test_bot_api_get_updates_rejects_a_result_that_is_not_a_list(), test_bot_api_get_updates_without_an_offset_omits_it(), test_bot_api_raises_call_error_with_method_and_description_never_the_token() (+9 more)

### Community 138 - "compilerOptions"
Cohesion: 0.08
Nodes (23): compilerOptions, allowJs, esModuleInterop, exactOptionalPropertyTypes, incremental, isolatedModules, jsx, lib (+15 more)

### Community 139 - "test_inbound_render.py"
Cohesion: 0.17
Nodes (12): Citation, render_reply(), split_text(), test_dispatcher_renders_agent_citations_as_a_numbered_footer(), test_render_reply_marks_flagged_citations_unconfirmed(), test_render_reply_numbers_citations_in_a_footer_with_memory_ids(), test_render_reply_without_citations_is_the_agent_text_alone(), test_split_text_cuts_at_line_breaks_when_it_can() (+4 more)

### Community 141 - "build_server"
Cohesion: 0.09
Nodes (13): ADR-0027: Anthropic SDK as the first provider adapter; structured output via forced tool use, Alternatives considered, Consequences, Context, Decision, Revisit if, current_user(), build_server() (+5 more)

### Community 142 - "ADR-0055: Digest and alert policy: thresholds, rendering, what never alerts"
Cohesion: 0.29
Nodes (6): ADR-0055: Digest and alert policy: thresholds, rendering, what never alerts, Alternatives considered, Consequences, Context, Decision, Revisit if

### Community 143 - "routers/feedback.py"
Cohesion: 0.10
Nodes (15): Requests to other workstreams (exact payloads), FeedbackIn, FeedbackListOut, list_feedback(), post_feedback(), FeedbackKindMismatchError, FeedbackTargetNotFoundError, record_feedback() (+7 more)

### Community 144 - ".__call__"
Cohesion: 0.31
Nodes (4): counting_receive(), tracking_send(), _content_length(), _send_413()

### Community 145 - "ADR-0077: Telegram delivery: secret-token webhook into the API, at-most-once by update_id, long polling for development only"
Cohesion: 0.18
Nodes (8): ADR-0077: Telegram delivery: secret-token webhook into the API, at-most-once by update_id, long polling for development only, Alternatives considered, Context, Revisit if, Open problems, Suggested commit message, Verification (coordinator, 2026-10-26), WS-10 handover: Telegram inbound channel

### Community 146 - "RobotsPolicy"
Cohesion: 0.17
Nodes (8): RobotsPolicy, ScriptedRobots, test_robots_policy_allows_everything_when_robots_txt_is_missing(), test_robots_policy_applies_rules_for_a_named_agent(), test_robots_policy_closes_the_host_when_robots_txt_cannot_be_read(), test_robots_policy_fetches_robots_txt_once_per_host_per_run(), test_robots_policy_reads_the_crawl_delay_for_our_agent(), test_robots_policy_refuses_a_disallowed_path_and_allows_the_rest()

### Community 147 - "Ripple — instructions for Claude Code"
Cohesion: 0.11
Nodes (17): Anti-slop rules, Code map, Commands, Decisions need ADRs (use /adr), End of session, Graph layout for this project, graphify, How we work (every task) (+9 more)

### Community 148 - "2. The original plan, item by item"
Cohesion: 0.11
Nodes (18): 1. Measured state of the checkout (17:55 IST), 2. The original plan, item by item, 3. The production plan, wave by wave, 4. The honest totals, 5. What only the author can unblock (in order of leverage), 6. What the collaborator does next (no author input needed), 7. After checkpoint C3 (same day, later), Acceptance criteria of the production plan (+10 more)

### Community 149 - "test_report.py"
Cohesion: 0.12
Nodes (24): 1. What it does, 2. Why it exists, 4. Trade-offs, 5. Failure modes and tests, 6. Interview questions, 7. Exercise, Pilot operations — feedback capture, the weekly report, incident handling, constructed_sources() (+16 more)

### Community 150 - "Ordered tasks (each one session; tests first; [human] marks author-owned work)"
Cohesion: 0.12
Nodes (16): 0.1 Project skeleton and tooling, 0.2 CI on GitHub Actions, 0.3 Services: docker compose (after ADR-0017), 0.4 Migrations pipeline (after ADR-0016), 0.5 Clock, ids and errors in core, 0.6 LLM router skeleton and FakeLLM, 0.7 ADRs for pending dependencies (before 0.3 and 0.4), 0.8 Phase close (+8 more)

### Community 151 - "Split"
Cohesion: 0.11
Nodes (22): Split, ADR-0091: Negatives at 3 per positive with every reversed link kept; train decontaminated against test, Alternatives considered, Consequences, Context, Decision, Revisit if, pair() (+14 more)

### Community 152 - "Ordered tasks"
Cohesion: 0.12
Nodes (15): 1.1 Core models and link policy, 1.2 Store protocol and in-memory store, 1.3 [human] Ripple engine, 1.4 Resolver protocol, rule-first stage, ripple runner, 1.5 Versioning, forget, expiry, user answers, 1.6 Linkers, 1.7 Change detector, 1.8 Postgres store (+7 more)

### Community 153 - "test_scout_trigger.py"
Cohesion: 0.29
Nodes (6): CriteriaChangeObserver, RecordingTrigger, _seed(), test_observer_stays_quiet_for_an_event_that_left_the_criteria_alone(), test_observer_triggers_when_the_event_updated_a_criteria_memory(), test_observer_triggers_when_the_event_was_triggered_by_a_criteria_memory()

### Community 154 - "app.py"
Cohesion: 0.06
Nodes (27): create_app(), create_production_app(), healthz(), Readiness, readyz(), BodySizeLimitMiddleware, enforce_rate_limit(), _app() (+19 more)

### Community 155 - "3. How it works"
Cohesion: 0.21
Nodes (6): GoldState, MemorySnapshot, VersionState, 3. How it works, _mem(), test_gold_state_reports_each_mismatch_with_the_runner_wording()

### Community 156 - "test_run_v1.py"
Cohesion: 0.05
Nodes (46): validate_scenario(), parents_first(), ADR-0061: RippleBench v0 jobs track is generated from seeded personas and templates, Alternatives considered, Consequences, Context, Decision, Revisit if (+38 more)

### Community 157 - "finance_v1/manifest.json"
Cohesion: 0.07
Nodes (29): ceo_departure, forget_holding, guidance_cut, journal_entry, peer_margin, rate_edge, trading_halt, content (+21 more)

### Community 158 - "Workstreams (dependency order, then value)"
Cohesion: 0.14
Nodes (13): Coordination, Prerequisites (author, before or alongside round 2), Round 2 plan — from "built offline" to "used daily", What this round does not do, Where the project stands against the original idea (checked 2026-10-24), Workstreams (dependency order, then value), WS-0 Coordinator: live verification and engine landing (sequential-only), WS-10 Telegram inbound: the student's channel (Phase 2 exit; parallel-ready) (+5 more)

### Community 159 - "InMemoryRateLimiter"
Cohesion: 0.17
Nodes (5): test_rate_limiter_allows_up_to_the_limit_then_refuses(), test_rate_limiter_forget_idle_drops_keys_older_than_the_window(), test_rate_limiter_keys_are_independent(), test_rate_limiter_refused_attempts_do_not_extend_the_lockout(), test_rate_limiter_releases_once_the_window_has_passed()

### Community 160 - "news_v1/manifest.json"
Cohesion: 0.07
Nodes (28): attribution_retracted, conflicting_reports, figure_revised, forget_story, other_story_develops, road_closure, shared_note, content (+20 more)

### Community 161 - "Data model"
Cohesion: 0.15
Nodes (12): ChangeEvent (ADR-0015), Data model, Decision, ForgetEvent, Link classes (core) and link types (domains), Link (dependency edge), Memory, Ripple semantics (ADR-0013) (+4 more)

### Community 163 - "re"
Cohesion: 0.05
Nodes (36): components, $defs, operations, paths, ADR-0013, ADR-0015, ADR-0042, webhooks (+28 more)

### Community 164 - "Architecture"
Cohesion: 0.18
Nodes (10): Agents, Architecture, Deployment, Flows, How core stays domain-agnostic (ADR-0013), Modules, Open (not yet decided; see docs/plans/phase-0.md), Principle (+2 more)

### Community 165 - "Template"
Cohesion: 0.17
Nodes (11): 2026-10-19 — Parallel round 1 closed at checkpoint C2 (coordinator session), 2026-10-19 — Parallel round 1: seven workstreams on one checkout (coordinator session), 2026-10-19 — Phase 0, kickoff session (docs only, no code), 2026-10-19 — Phase 0, project definition, 2026-10-19 — Phase 0, tasks 0.1–0.7 built (second session of the day), 2026-10-19 — Phase 1 built under the autonomous mandate (third session of the day), 2026-10-24 — Production plan and wave A launch (coordinator session), 2026-10-26 — Status analysis and checkpoint C3 (coordinator session) (+3 more)

### Community 166 - "paper/registry.py"
Cohesion: 0.17
Nodes (22): Decision, 3. How it works, Adding a number, Commands, docs/paper — outlines and rendered numbers, How a number gets into the write-up, LaTeX-ready structure, What is here (+14 more)

### Community 167 - "Bot"
Cohesion: 0.10
Nodes (4): InMemoryRateLimiter, Bot, incoming_callback(), incoming_text()

### Community 168 - "ADR-0062: Time-to-consistency replay harness with per-event snapshots"
Cohesion: 0.15
Nodes (8): ActionLayer, ADR-0062: Time-to-consistency replay harness with per-event snapshots, Alternatives considered, Consequences, Context, Decision, Revisit if, Summary

### Community 169 - "Evaluation"
Cohesion: 0.20
Nodes (9): Ablations, Baselines, Evaluation, Hypotheses (initial targets; revised after Phase 3 baselines, with an ADR), Metrics, Pilot metrics, Protocol, Questions (+1 more)

### Community 170 - "test_finance_pairs.py"
Cohesion: 0.12
Nodes (17): _same_key(), scenario_pairs(), track_pairs(), 3. How it works, finance_registry(), checked_in(), test_a_reversed_edge_is_a_negative_marked_as_such(), test_an_indirect_dependency_is_left_unlabelled() (+9 more)

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

### Community 178 - "ADR-0076: Telegram dispatcher: commands, link flow, keyboards for answers, two-step forget, agent for the rest"
Cohesion: 0.50
Nodes (3): ADR-0076: Telegram dispatcher: commands, link flow, keyboards for answers, two-step forget, agent for the rest, Alternatives considered, Revisit if

### Community 179 - "bench: strategies, RippleBench v0 generator, replay harness, metric interfaces"
Cohesion: 0.22
Nodes (8): 1. What it does, 2. Why it exists, 4. The metrics, with a worked example (tests/scenarios/test_bench_metrics.py), 5. Trade-offs, 6. Failure modes and tests, 7. Interview questions, 8. Exercise, bench: strategies, RippleBench v0 generator, replay harness, metric interfaces

### Community 180 - "ripple.core.engine — the ripple engine (your module)"
Cohesion: 0.22
Nodes (8): 1. What it does, 2. Why it exists, 3. How it works (what you implement), 4. Trade-offs you should be able to argue, 5. Failure modes and tests, 6. Interview questions, 7. Exercise, ripple.core.engine — the ripple engine (your module)

### Community 181 - "Paper outline: Ripple — learned dependency links keep agent memory consistent"
Cohesion: 0.08
Nodes (24): Ablations, Abstract, Action level: stale recommendations and time to consistency (C2), Asking the user, Conclusion, Cost (C4), Data model, Ethics (+16 more)

### Community 182 - "identity.py"
Cohesion: 0.11
Nodes (4): bearer_token(), BearerIdentity, env_token_source(), header_token_source()

### Community 183 - "Memory"
Cohesion: 0.09
Nodes (12): event_changed_criteria(), ChangeDetector, LinkProposal, Memory, StructuredFact, _existing(), find_opening(), RecordedOpening (+4 more)

### Community 184 - "PostgresFeedbackStore"
Cohesion: 0.15
Nodes (7): PostgresFeedbackStore, test_feedback_postgres_deleting_the_user_row_cascades(), test_feedback_postgres_forgetting_the_target_removes_its_rows(), test_feedback_postgres_racing_records_create_one_row(), race(), TestPostgresFeedbackStore, _user()

### Community 185 - "ripple.api — identity, inspector, confirmation flow, export and delete"
Cohesion: 0.25
Nodes (7): 1. What it does, 2. Why it exists, 4. Trade-offs, 5. Failure modes and tests, 6. Interview questions, 7. Exercise, ripple.api — identity, inspector, confirmation flow, export and delete

### Community 186 - "test_tailor.py"
Cohesion: 0.25
Nodes (17): test_invariant_I4_tailor_rejects_invalid_output(), test_invariant_I5_tailor_cites_only_existing_memories(), _candidates_shown(), _opening(), ReadOnlyStore, test_tailor_drops_highlights_for_ids_it_did_not_show(), test_tailor_ignores_retrieved_fields_of_other_openings(), test_tailor_includes_retrieved_candidates_and_marks_flagged_ones() (+9 more)

### Community 187 - "Files"
Cohesion: 0.09
Nodes (27): Decision, Decision, 1. What it does, 2. Why it exists, 3. How it works, 4. Trade-offs, 5. Failure modes and tests, 6. Interview questions (+19 more)

### Community 188 - "Linkers, change detection and intake"
Cohesion: 0.25
Nodes (7): 1. What it does, 2. Why it exists, 4. Trade-offs, 5. Failure modes and tests, 6. Interview questions, 7. Exercise, Linkers, change detection and intake

### Community 189 - "ripple.llm: provider adapter, transport retries, prices, tracing"
Cohesion: 0.25
Nodes (7): 1. What it does, 2. Why it exists, 4. Trade-offs, 5. Failure modes and tests, 6. Interview questions, 7. Exercise, ripple.llm: provider adapter, transport retries, prices, tracing

### Community 190 - "devDependencies"
Cohesion: 0.11
Nodes (18): devDependencies, eslint, eslint-config-next, eslint-config-prettier, eslint-plugin-jsx-a11y, jsdom, openapi-typescript, prettier (+10 more)

### Community 191 - "ripple.core: writes, runner, versioning, forget, sweep, answers"
Cohesion: 0.25
Nodes (7): 1. What it does, 2. Why it exists, 4. Trade-offs, 5. Failure modes and tests, 6. Interview questions, 7. Exercise, ripple.core: writes, runner, versioning, forget, sweep, answers

### Community 192 - "dedupe.py"
Cohesion: 0.07
Nodes (31): ADR-0071: Scout dedupe by canonical URL, then (company, title) fingerprint, with a seen ledger, Alternatives considered, Consequences, Context, Decision, Revisit if, 1. What it does, 2. Why it exists (+23 more)

### Community 193 - "ripple.storage — PostgresStore, tables and migrations"
Cohesion: 0.25
Nodes (7): 1. What it does, 2. Why it exists, 4. Trade-offs, 5. Failure modes and tests, 6. Interview questions, 7. Exercise, ripple.storage — PostgresStore, tables and migrations

### Community 194 - "test_generators.py"
Cohesion: 0.19
Nodes (12): _identifiers(), test_adding_a_persona_leaves_earlier_personas_scenarios_unchanged(), test_baselines_fail_and_check_everything_misses_only_the_ask_family(), test_every_scenario_is_valid_in_its_domain_and_every_family_is_covered(), test_generate_changes_with_the_seed(), test_generate_is_deterministic_for_the_same_seed(), test_the_checked_in_track_matches_a_fresh_generation(), test_the_snapshot_family_uses_the_domains_snapshot_link() (+4 more)

### Community 195 - "Deploying Ripple (ADR-0029)"
Cohesion: 0.25
Nodes (7): Backups, Deploying Ripple (ADR-0029), First deploy, Prerequisites (once), Rollback, Secrets, Upgrade

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

### Community 223 - "UserDirectory"
Cohesion: 0.12
Nodes (8): ADR-0025: Notifications: Telegram Bot API over httpx; email deferred, Alternatives considered, Consequences, Context, Decision, Revisit if, Transport, UserDirectory

### Community 224 - "ADR-0029: Deployment topology: one VPS, Compose, Caddy TLS, GHCR images, pg_dump backups"
Cohesion: 0.29
Nodes (6): ADR-0029: Deployment topology: one VPS, Compose, Caddy TLS, GHCR images, pg_dump backups, Alternatives considered, Consequences, Context, Decision, Revisit if

### Community 225 - "ADR-0044: Export everything, delete through forget, keep the deletion audit"
Cohesion: 0.29
Nodes (6): ADR-0044: Export everything, delete through forget, keep the deletion audit, Alternatives considered, Consequences, Context, Decision, Revisit if

### Community 226 - "ADR-0050: Lexical scoring (BM25 / PostgreSQL FTS), reciprocal rank fusion and one-hop graph expansion for retrieval"
Cohesion: 0.29
Nodes (6): ADR-0050: Lexical scoring (BM25 / PostgreSQL FTS), reciprocal rank fusion and one-hop graph expansion for retrieval, Alternatives considered, Consequences, Context, Decision, Revisit if

### Community 227 - "ADR-0063: Metric definitions for RippleBench v0 (interfaces; bodies are [human])"
Cohesion: 0.29
Nodes (6): ADR-0063: Metric definitions for RippleBench v0 (interfaces; bodies are [human]), Alternatives considered, Consequences, Context, Decision, Revisit if

### Community 228 - "ADR-0086: Dashboard pages, token session in sessionStorage, query-string routing"
Cohesion: 0.29
Nodes (6): ADR-0086: Dashboard pages, token session in sessionStorage, query-string routing, Alternatives considered, Consequences, Context, Decision, Revisit if

### Community 229 - "JobFailedForUsersError"
Cohesion: 0.12
Nodes (11): Data requests (DPDP, FR-15), Health, Key rotation, Monitoring checklist, Operations runbook, Rollback and restore, Symptoms, daily_digest() (+3 more)

### Community 230 - "main"
Cohesion: 0.18
Nodes (7): main(), McpSettings, _fakes(), test_main_serves_http_from_flags_over_environment(), test_main_serves_stdio_only_with_a_token_in_the_environment(), test_settings_default_to_stdio_on_loopback(), test_settings_read_the_environment_and_name_a_bad_value()

### Community 231 - "WriteOut"
Cohesion: 0.21
Nodes (3): WriteOut, not_found(), ToolCallError

### Community 232 - "Contract requests (coordinator)"
Cohesion: 0.16
Nodes (10): Contract requests (coordinator), Open problems, Status, Suggested commit message, Verification (real output, 2026-10-31), What it does (short), WS-16 handover — Pilot operations, scripts() (+2 more)

### Community 233 - "EventSnapshot"
Cohesion: 0.40
Nodes (3): stale_recommendation_rate(), EventSnapshot, test_stale_recommendation_rate_counts_unflagged_recommendations_on_stale_beliefs()

### Community 234 - "Thesis outline: Ripple — a consistency layer for agent memory"
Cohesion: 0.13
Nodes (14): Appendices, Chapter: Conclusion and future work, Chapter: Introduction, Chapter: Learning dependency links, Chapter: Literature survey, Chapter: Pilot study, Chapter: Requirements and evaluation plan, Chapter: Results and discussion (+6 more)

### Community 235 - "ADR-0042: Inspector endpoints: I1 at the boundary, history on request, edits go straight to versioning"
Cohesion: 0.33
Nodes (5): ADR-0042: Inspector endpoints: I1 at the boundary, history on request, edits go straight to versioning, Alternatives considered, Consequences, Context, Revisit if

### Community 236 - "test_bench_replay.py"
Cohesion: 0.29
Nodes (9): _recommend(), _spec(), _store_with(), test_stub_flags_a_recommendation_built_on_a_suspect_belief(), test_stub_ignores_retired_openings_and_non_openings(), test_stub_recommends_valid_openings_and_skips_negative_eligibility(), test_trace_keeps_the_opening_alias_after_the_opening_gets_a_new_version(), test_trace_records_recommendations_with_the_beliefs_they_rest_on() (+1 more)

### Community 237 - "Incident runbook (ADR-0107)"
Cohesion: 0.20
Nodes (9): Bot down (S2), Data deletion request (S1 until done), Digest sent twice (S2), First 15 minutes (every incident), Incident log, Incident runbook (ADR-0107), LLM provider down (S2 after 1 hour), Severity (+1 more)

### Community 238 - "ADR-0075: Telegram inbound: a strict subset of the Update type, private chats only, drops counted"
Cohesion: 0.33
Nodes (5): ADR-0075: Telegram inbound: a strict subset of the Update type, private chats only, drops counted, Alternatives considered, Consequences, Context, Revisit if

### Community 239 - "ADR-0080: MCP server on the SDK's low-level `Server`, explicit Pydantic tool schemas, seven tools"
Cohesion: 0.33
Nodes (5): ADR-0080: MCP server on the SDK's low-level `Server`, explicit Pydantic tool schemas, seven tools, Alternatives considered, Consequences, Context, Revisit if

### Community 240 - "ADR-0081: MCP identity: one bearer token per connection, hashed through ADR-0040, bound per request"
Cohesion: 0.33
Nodes (5): ADR-0081: MCP identity: one bearer token per connection, hashed through ADR-0040, bound per request, Alternatives considered, Consequences, Context, Revisit if

### Community 241 - "ADR-0088: API additions for the dashboard: /graph, /vocabulary, editable valid_to, required output fields"
Cohesion: 0.33
Nodes (5): ADR-0088: API additions for the dashboard: /graph, /vocabulary, editable valid_to, required output fields, Alternatives considered, Consequences, Context, Decision

### Community 242 - "What was built"
Cohesion: 0.11
Nodes (8): Open problems, Suggested commit message, Tool surface, Verification (run 2026-10-25, after the code-review pass), What was built, WS-11 handover: MCP server, IntakeResult, BearerGate

### Community 243 - "finance/test_vocabulary.py"
Cohesion: 0.29
Nodes (3): test_invariant_I3_engine_never_calls_an_llm(), test_the_adapter_imports_only_the_standard_library_and_core(), test_the_adapter_imports_only_the_standard_library_and_core()

### Community 244 - ".prettierrc.json"
Cohesion: 0.40
Nodes (4): printWidth, semi, singleQuote, trailingComma

### Community 245 - "Requirements"
Cohesion: 0.40
Nodes (4): Functional (FR) — with acceptance criteria, MVP (target: in daily use by 2027-02-01), Non-functional (NFR), Requirements

### Community 246 - "ADR-0092: The 300-pair hand check is stratified, blind, keyed and re-drawn at report time"
Cohesion: 0.29
Nodes (6): ADR-0092: The 300-pair hand check is stratified, blind, keyed and re-drawn at report time, Alternatives considered, Consequences, Context, Decision, Revisit if

### Community 249 - "ADR-0106: The weekly pilot report computes two docs/04 metrics and marks three TBD"
Cohesion: 0.29
Nodes (6): ADR-0106: The weekly pilot report computes two docs/04 metrics and marks three TBD, Alternatives considered, Consequences, Context, Decision, Revisit if

### Community 252 - "ADR-0107: Three incident severities and a daily monitoring check for a one-operator pilot"
Cohesion: 0.29
Nodes (6): ADR-0107: Three incident severities and a daily monitoring check for a one-operator pilot, Alternatives considered, Consequences, Context, Decision, Revisit if

### Community 285 - "ripple.agents — Conversation and Tailor"
Cohesion: 0.29
Nodes (6): 1. What it does, 2. Why it exists, 4. Trade-offs, 5. Failure modes and tests, 7. Exercise, ripple.agents — Conversation and Tailor

### Community 286 - "Production hardening — delivery log, atomic confirm, resume text, API boundary"
Cohesion: 0.29
Nodes (6): 1. What it does, 2. Why it exists, 4. Trade-offs, 6. Interview questions, 7. Exercise, Production hardening — delivery log, atomic confirm, resume text, API boundary

### Community 287 - "paper: numbers from results/ and the I8 check"
Cohesion: 0.29
Nodes (6): 1. What it does, 2. Why it exists, 4. Trade-offs, 6. Interview questions, 7. Exercise, paper: numbers from results/ and the I8 check

### Community 289 - "ADR-0019: Rule-first resolution"
Cohesion: 0.33
Nodes (5): ADR-0019: Rule-first resolution, Alternatives considered, Consequences, Context, Revisit if

### Community 290 - "ADR-0032: Ranking openings: eligible, then urgent, then fit, then variety; flagged, never retired"
Cohesion: 0.33
Nodes (5): ADR-0032: Ranking openings: eligible, then urgent, then fit, then variety; flagged, never retired, Alternatives considered, Consequences, Context, Revisit if

### Community 291 - "ADR-0046: Tailor agent: read-only, picks from id-validated candidates"
Cohesion: 0.33
Nodes (5): ADR-0046: Tailor agent: read-only, picks from id-validated candidates, Alternatives considered, Consequences, Context, Revisit if

### Community 292 - "ADR-0070: Allowed-sources registry: a YAML file validated into Pydantic, terms note required"
Cohesion: 0.33
Nodes (5): ADR-0070: Allowed-sources registry: a YAML file validated into Pydantic, terms note required, Alternatives considered, Consequences, Context, Revisit if

### Community 293 - "ADR-0072: The Scout is a plain loop over injected parts, fetching only through the sources package"
Cohesion: 0.33
Nodes (5): ADR-0072: The Scout is a plain loop over injected parts, fetching only through the sources package, Alternatives considered, Consequences, Context, Revisit if

### Community 294 - "ADR-0096: Candidate decisions are a compare-and-set on status, so a double confirm cannot write twice"
Cohesion: 0.33
Nodes (5): ADR-0096: Candidate decisions are a compare-and-set on status, so a double confirm cannot write twice, Alternatives considered, Context, Decision, Revisit if

### Community 295 - "Pilot metrics: definitions, sources and what is still missing"
Cohesion: 0.33
Nodes (5): Feedback the product records (ADR-0105), Pilot metrics: definitions, sources and what is still missing, The five metrics, Weekly survey (draft, for the guide's review), What would close the TBDs (proposals for the coordinator)

### Community 296 - "ADR-0031: Jobs rule resolvers recompute derived beliefs from their parents"
Cohesion: 0.40
Nodes (4): ADR-0031: Jobs rule resolvers recompute derived beliefs from their parents, Alternatives considered, Consequences, Revisit if

## Knowledge Gaps
- **41 isolated node(s):** `ADR-0029`, `ADR-0086`, `react-dom`, `@testing-library/dom`, `@types/node` (+36 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 2762 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **79 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Status` connect `test_ranking.py` to `AccountView.tsx`, `FakeClock`, `generate_finance.py`, `ScenarioRunner`, `load_scenario`, `StoreReader`, `fact`, `agents/conversation.py`, `test_intake.py`, `Postgres Store`, `pytest`, `InMemoryStore`, `run`, `DecisionAction`, `models.py`, `test_conversation.py`, `scout.py`, `generate.py`, `Resolution`, `build`, `api/schemas.py`, `RippleRunner`, `asyncio`, `Bot`, `tools.py`, `jobs/openings.py`, `fact`, `Kind`, `Harness`, `Memory`, `replay.py`, `agents/tailor.py`, `Files`, `test_tailor.py`, `dedupe.py`, `json`, `test_feedback.py`, `User`, `Services`, `test_bench_replay.py`?**
  _High betweenness centrality (0.099) - this node is a cross-community bridge._
- **Are the 23 inferred relationships involving `FakeClock` (e.g. with `ScenarioRunner` and `conversation_agent()`) actually correct?**
  _`FakeClock` has 23 INFERRED edges - model-reasoned connections that need verification._
- **What connects `ADR-0029`, `ADR-0086`, `react-dom` to the rest of the system?**
  _41 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `FakeClock` be split into smaller, more focused modules?**
  _Cohesion score 0.050505050505050504 - nodes in this community are weakly interconnected._
- **Why does `3. How it works` connect `AccountView.tsx` to `types.ts`, `helpers.tsx`, `SessionProvider.tsx`, `MapView.tsx`, `test_ranking.py`?**
  _High betweenness centrality (0.064) - this node is a cross-community bridge._
- **Are the 45 inferred relationships involving `InMemoryStore` (e.g. with `ScenarioRunner` and `test_tailor_refuses_an_unusable_opening()`) actually correct?**
  _`InMemoryStore` has 45 INFERRED edges - model-reasoned connections that need verification._
- **Should `generate_finance.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07641272020132693 - nodes in this community are weakly interconnected._