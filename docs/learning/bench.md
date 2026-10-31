# bench: strategies, RippleBench v0 generator, replay harness, metrics
Written 2026-10-19 (WS-7); updated 2026-10-31 (WS-18): the metric bodies are now
implemented (you asked for them on 2026-10-31), runs write `memory_metrics`, seeds are
generator seeds, two ablations run, and a retrieval probe measures stale retrieval.
Describes only code that exists. Results: docs/results/benchmark.md.

## 1. What it does
`bench/` replays scenario timelines against a memory strategy and writes every result
into results/. It generates the RippleBench v0 jobs track from seeded personas and
templates, records a per-event trace of memory states and recommendations, and fixes
the definitions of the metrics you will implement in bench/metrics.py.

## 2. Why it exists
ADR-0012 (evaluation first, I8: every number traces to results/), docs/04 (baselines,
split by persona and template, protocol), proposal 0003 (time-to-consistency),
ADR-0060 (strategies), ADR-0061 (generator), ADR-0062 (replay harness), ADR-0063
(metric definitions), ADR-0120 (metric bodies, pooling, retrieval probe), ADR-0121
(generator seeds), ADR-0122 (ablations, linker key, counted LLM calls). H1 needs
check_everything's accuracy and cost as the reference.

## 3. How it works
- `bench/scenario.py`: `ScenarioSpec` (memories, links, resolutions, events with
  `expect`) loaded by `load_scenario`; `ScenarioRunner(spec, strategy=...)` seeds the
  in-memory store (root id = alias), applies events through `update_memory`,
  `record_memory`, the sweep, the answer functions or `forget`, hands each open
  ChangeEvent to `strategy.run`, then calls `snapshot_after_event` and checks the
  gold against that snapshot (`GoldState.mismatches`). `AliasResolver` is the scripted
  oracle: answers by alias, optionally scoped to the alias that triggered the ripple.
- `bench/strategies.py`: `build_strategy(name, ...)` returns `ripple`, `append_only`,
  `newest_wins` or `check_everything`; every resolver call passes through
  `CountingResolver`, so `resolver_calls` is comparable. `one_shot_engine(ids)` is the
  graph-ignoring engine behind check_everything.
- `bench/replay.py`: `VersionState`, `MemorySnapshot` (root + latest), `GoldState`,
  `RecommendationSnapshot` (with `based_on`), `EventSnapshot`, `ReplayTrace`;
  `StubActionLayer` is the placeholder ranking (rule on the class).
- `bench/generate.py`: `make_personas`, seven template functions, `generate` →
  files + manifest; `load_jobs_v0(split)` reads them back; `--check` verifies drift.
- `bench/run.py`: `--suite smoke|v0 --strategy <name> [--split]`; validates each
  scenario, writes config.json (sha marked `-dirty` when the tree differs from HEAD),
  metrics.json (`checks_failed` per gold target, `errors` for runtime problems),
  report.md and snapshots/*.json into a folder that is never overwritten.
- `bench/metrics.py`: `target_outcomes`, `correct_updates`, `stale_kept`,
  `wrongful_changes`, `questions_asked`, `stale_retrieval_rate`,
  `stale_recommendation_rate`, `time_to_consistency`, `cost_per_ripple`, each as its
  docstring says. `stale_ids_at` is the one gold-stale rule both stale rates use;
  `scenario_metrics` collects one scenario's counts (the runner calls it at the end of
  every scenario with the store's ChangeEvents) and `suite_metrics` pools them into the
  run's `memory_metrics` (ADR-0120: counts summed before any ratio; stale_kept,
  wrongful_changes and questions_asked are per-scenario averages; tokens and USD are
  null without an LLM).
- `bench/probe.py`: after every event with gold, `retrieval_probe` queries the real
  `HybridRetriever` (lexical, graph expansion on, flagged included, every match) once per gold
  alias with the content it was first written with; results land in
  `EventSnapshot.retrieved`, which the stale retrieval rate is computed from.
- `bench/seeds.py`: `generator_seeds(suite)` (DEFAULT_SEED and the next two),
  `generate_track(suite, seed)` (in memory; the default seed must reproduce the
  checked-in hash), `select_split`. `bench.run --generator-seeds 3` writes one folder
  per seed (`..._g<seed>_<sha>`).
- `bench/strategies.py` ablations: `--ablation no_graph` (check_everything's scope under
  the ripple name) and `--ablation no_ask_user` (`NoAskResolver`: ask becomes keep).
- `bench/matrix.py` runs the whole grid; `bench/summary.py` writes
  results/<date>_benchsummary_<sha>/ (metrics.json and report.md: seed means, H1 and H2
  readings, source folders)
  from the runs of the current code only.

## 4. The metrics, with a worked example (tests/scenarios/test_bench_metrics.py)
Trace: seed → event 1 `update:cgpa` → event 2 `update:acme` (an unrelated deadline).
Gold at event 1: cgpa RETIRED; eligibility@latest v2 "eligible"; recommendation@latest
v2 "apply"; acme VALID v1. The system retired cgpa and wrote eligibility v2 "eligible"
but left recommendation at v1 "skip". Gold at event 2: acme@latest v2;
eligibility@latest v2 "eligible"; recommendation@latest v1 "skip". The system wrote
acme v2 and also rewrote recommendation to v2 "apply", late and unasked.

| event | target | should change | moved | matches gold | counts as |
|---|---|---|---|---|---|
| 1 | cgpa | yes (VALID→RETIRED) | yes | yes | correct update |
| 1 | eligibility@latest | yes | yes | yes | correct update |
| 1 | recommendation@latest | yes | no | no | stale kept |
| 1 | acme | no | no | yes | correct non-update |
| 2 | acme@latest | yes | yes | yes | correct update |
| 2 | eligibility@latest | no | no | yes | correct non-update |
| 2 | recommendation@latest | no | yes | no | wrongful change |

correct_updates = 3 · stale_kept = 1 · wrongful_changes = 1 · should-change targets
= 4, so update accuracy (ADR-0063's H1 reading) = 3/4.

How a run aggregates (ADR-0120): with a second scenario that has one should-change
target, correct, the run's update accuracy pools the counts, (3 + 1) / (4 + 1), rather
than averaging the two scenarios' own ratios. `test_suite_metrics_pool_counts_before_taking_ratios` checks exactly this.

time_to_consistency: cgpa and eligibility converge at k = 0 (0 days); acme@latest at
event 2, k = 0. recommendation@latest should change at event 1; at event 2 the
system writes v2 "apply", which *would* satisfy gold(1), but event 2 carries a new
gold for the same target (v1 "skip"), so the window closed first: None. Records =
(0, 0, None, 0); share never converged = 1/4.

stale_recommendation_rate: event 1 shows one recommendation resting on
`recommendation` (gold v2 "apply", row v1 "skip": stale) → stale. Event 2 shows one
resting on `rec-v2` "apply" while gold wants v1 "skip" → stale. 2/2 = 1.0. Flag the
second (the agent was warned) and it drops out of the numerator: 1/2.

stale_retrieval_rate: four results, one unflagged hit on a gold-stale row, one
flagged hit on a stale row (not counted) → 1/4.

questions_asked: count ASK decisions, here 2 across two events. cost_per_ripple:
5 resolver calls over 2 ChangeEvents = 2.5.

Hand-check the second TTC example: eligibility should change at event 1 (day 0),
nothing happens at event 2 (day 2), the new version lands at event 3 (day 5):
ttc_events = 2, ttc_days = 5.0.

## 5. Trade-offs
- Generator seeds, not run seeds (ADR-0121): the oracle replay is deterministic, so the
  only variance is in the data; each seed re-draws personas, values and the split.
- The retrieval probe asks every strategy the same queries (the scenario's first
  content per alias); it is lexical only until an embedder ADR exists.
- Should-change targets depend on what the system held before each event, so update
  accuracy's denominator differs by strategy (read the totals beside the rate).
- Scripted oracle vs real resolver: v0 measures the engine and the write semantics
  at zero LLM cost; with a perfect oracle check_everything is the accuracy ceiling,
  which is what H1 compares against. LLM quality is Phase 3.
- `trigger`-scoped answers: without them check_everything would apply every gold
  decision whenever it re-checked, which flatters nobody but muddles over-correction.
- Root id = alias: readable traces and deterministic baseline order; ids are opaque
  to core so nothing depends on it, but a scenario cannot reuse an alias.
- The stub action layer reads content ("not " prefix). Honest only because it is the
  same rule for every strategy and is replaced by the adapter's ranking.

## 6. Failure modes and tests
| Failure | Test |
|---|---|
| Baseline silently matches gold it should fail | test_baselines_disagree_with_gold_where_propagation_is_the_point, test_append_only_fails_gold_in_every_family_that_propagates |
| Baseline state change without a decision (I2) | test_append_only_records_the_restoration_as_a_wave_zero_decision |
| check_everything skips unlinked memories or re-checks the trigger | test_check_everything_resolves_every_valid_memory_including_unlinked_ones, test_one_shot_engine_… |
| Generator drifts from checked-in data | test_checked_in_data_matches_a_fresh_default_generation, `python -m bench.generate --check` |
| Split leaks a persona or template | test_split_is_by_persona_and_template_never_by_item |
| Answer to a never-asked question crashes a baseline run | test_an_answer_to_a_question_a_baseline_never_asked_is_a_recorded_error |
| Results folder overwritten or mislabelled (I8) | test_a_second_run_on_the_same_day_gets_its_own_folder, test_git_short_sha_marks_a_dirty_tree |
| Generator overwrites hand-written scenarios | test_write_data_refuses_a_directory_of_hand_written_scenarios |
| append_only restore lands without its decision (I2) | test_append_only_restoration_and_completion_commit_together |
| results/ run without config, seeds or snapshots | test_v0_baseline_run_writes_config_metrics_report_and_snapshots |
| Engine missing reported as a pass | run_suite records NotImplementedError as "not runnable" (bench/run.py) |
| A metric drifts from its definition | tests/scenarios/test_bench_metrics.py (worked example + edge cases) |
| Ratios averaged instead of pooled | test_suite_metrics_pool_counts_before_taking_ratios |
| "Not measured" printed as 0 | test_memory_metrics_of_a_v0_run_carry_every_registry_key_as_a_number_or_none |
| Seeded runs differ in more than their seed | test_runs_of_one_seed_group_differ_only_in_their_seed |
| Default seed silently differs from checked-in data | test_a_drifted_default_seed_is_refused |
| Retired rows leak through the probe (I1) | test_probe_queries_each_gold_alias_after_an_event_and_never_after_the_seed |
| no_graph diverges from its definition | test_no_graph_ablation_scores_exactly_as_check_everything_on_every_smoke_scenario |
| Summary mixes runs of different code or disagreeing reruns | test_summary_ignores_runs_of_other_code, test_summary_refuses_reruns_of_one_seed_that_disagree |

## 7. Interview questions
1. *Why do baselines share the store's versioning instead of their own write path?*
   So the only variable is propagation; append_only restores the old version after
   the shared write, recorded as a decision, and the observable state is the same.
2. *Is check_everything using the graph?* Only to park the subtree below an ask; its
   scope is every VALID memory, chosen without links, through a one-shot engine.
3. *Why is the split by persona and template?* Items from one persona share facts;
   items from one template share structure. A test set that shares either with
   training measures memorisation, not transfer.
4. *What does TTC = None mean?* The belief never reached the gold state before the
   gold for it changed again or the scenario ended; append_only's dependents all
   score None, which is the gap Ripple claims to close.
5. *Where do a run's numbers come from?* Only results/<run>/metrics.json and
   snapshots/, with config.json naming strategy, seeds, data hash and engine (I8).

6. *Why is tokens_per_ripple null and not 0?* No LLM ran; 0 would read as "free".
7. *Why does no_graph score exactly like check_everything?* Without a graph there is
   nothing to scope by, so everything is re-checked: that is check_everything.

## 8. Exercise
Take `cutoff_unknown__p0_jay` from bench/data/jobs_v0 and, by hand, fill the table of
section 4 for each of the three baselines after event 1. Then run
`uv run python -m bench.run --suite v0 --strategy check_everything` and compare with
the scenario's row in report.md (it fails exactly one check; say why).
