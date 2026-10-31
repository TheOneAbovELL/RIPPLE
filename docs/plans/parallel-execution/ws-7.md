# WS-7 handover: bench, baselines, RippleBench v0 generator, metric interfaces, TTC harness
Status: Locally verified; integration-blocked for ripple-strategy numbers (human engine)
Date: 2026-10-19 · Owner session: WS-7

## Summary
Built and tested offline, in owned paths only:
- `bench/strategies.py` (ADR-0060): `MemoryStrategy` protocol; ripple, append_only,
  newest_wins, check_everything over one shared Store/Resolver/Clock with one
  `CountingResolver`; check_everything = `RippleRunner` + a graph-ignoring one-shot
  engine (a `WaveEngine` subclass; engine.py untouched).
- `bench/scenario.py` (runner moved from tests/scenarios/runner.py, which re-exports):
  `--strategy` selection, `engine_factory` injection for tests, trigger-scoped scripted
  resolutions, root id = alias, per-event replay snapshots, an answer to a never-asked
  question recorded as a failure instead of a crash.
- `bench/generate.py` + `bench/data/jobs_v0/` (ADR-0061): 5 seeded personas × 7
  template families = 35 scenarios, 175 gold checks, manifest.json with persona and
  template split (`train` 15, `test` 20 of which `strict_test` 4) and a data sha256;
  `--check` verifies drift.
- `bench/replay.py` (ADR-0062): snapshot types, `ActionLayer` (= C1
  `RecommendationSource` shape), `StubActionLayer` placeholder, `ReplayTrace.to_dict`.
- `bench/metrics.py` (ADR-0063, [human]): signatures, exact definitions, bodies
  raise NotImplementedError(TODO(human)); 10 worked-example tests xfail(strict).
- Review fixes (see Code review): dirty-sha and no-overwrite results folders,
  per-target `checks_failed` plus `errors`, safe generator writes, action-alias
  validation, one-transaction append_only, carried-over update fields.
- `bench/run.py`: `--suite smoke|v0 --strategy <name> [--split]`; results folder
  with config.json (strategy, seeds, data hash, engine, resolver, action layer, models
  and prompt versions = null), metrics.json, report.md, snapshots/*.json.
- Docs: ADR-0060..0063, docs/learning/bench.md, results/README.md, this file.
Not touched: src/**, tests/fakes/**, tests/conftest.py, docs/04, docs/05, docs/adr/README.md,
pyproject. No `uv add`. Nothing committed.

## Plan (written before implementation; followed)
1. bench/replay.py snapshot types + ActionLayer + stub. 2. bench/strategies.py.
3. bench/scenario.py (moved runner, strategy, snapshots, trigger-aware oracle).
4. bench/generate.py + data + loader. 5. bench/metrics.py [human] stubs + xfail tests.
6. bench/run.py v0 suite. 7. ADRs, learning doc, results README, handover.
Each step left `uv run pytest tests/scenarios -q` green.

## Files
Code: bench/__init__.py (unchanged docstring), bench/replay.py, bench/strategies.py,
bench/scenario.py, bench/generate.py, bench/metrics.py, bench/run.py.
Data: bench/data/jobs_v0/*.yaml (35), bench/data/jobs_v0/manifest.json.
Tests: tests/scenarios/runner.py (shim), tests/scenarios/test_runner.py (rewritten for
the public API), tests/scenarios/test_bench_strategies.py, test_bench_replay.py,
test_bench_generate.py, test_bench_metrics.py, test_bench_run.py.
test_scenarios.py untouched (its 11 xfail(strict) markers stay).
Docs: docs/adr/0060-baseline-memory-strategies.md,
0061-ripplebench-v0-generator-and-split.md, 0062-ttc-replay-harness.md,
0063-ripplebench-metric-definitions.md, docs/learning/bench.md, results/README.md.
Results: results/2026-10-19_smoke_uncommitted/, results/2026-10-19_v0_{append_only,
newest_wins,check_everything,ripple}_uncommitted/ (each with snapshots/ where runnable).

## Verification (real output, final state)
```
$ uv run ruff check bench tests/scenarios
All checks passed!
$ uv run ruff format --check bench tests/scenarios
16 files already formatted
$ uv run pyright bench tests/scenarios
0 errors, 0 warnings, 0 informations
$ uv run pytest tests/scenarios -q
254 passed, 21 xfailed in 4.42s
$ uv run python -m bench.generate --check
C:\Users\omjee\OneDrive\Desktop\RIPPLE\bench\data\jobs_v0: in sync
$ uv run python -m bench.run --suite smoke
smoke/ripple: 0/0 runnable scenarios passed, 11 not runnable -> results\2026-10-19_smoke_uncommitted_2
  FAIL accepted_offer_chain: not runnable: TODO(human) engine: TODO(human): roadmap Phase 1 '[human] Ripple engine' — see the class docstring and test
$ uv run python -m bench.run --suite v0 --strategy append_only
v0/append_only: 0/35 runnable scenarios passed, 0 not runnable -> results\2026-10-19_v0_append_only_uncommitted_2
$ uv run python -m bench.run --suite v0 --strategy newest_wins
v0/newest_wins: 0/35 runnable scenarios passed, 0 not runnable -> results\2026-10-19_v0_newest_wins_uncommitted_3
$ uv run python -m bench.run --suite v0 --strategy check_everything
v0/check_everything: 30/35 runnable scenarios passed, 0 not runnable -> results\2026-10-19_v0_check_everything_uncommitted_2
$ uv run python -m bench.run --suite v0 --strategy ripple
v0/ripple: 0/0 runnable scenarios passed, 35 not runnable -> results\2026-10-19_v0_ripple_uncommitted_2
```

Full suite was not run by WS-7 (rule 3: own paths only); the coordinator's message of
2026-10-19 reports 566 passed overall with the bench tests included before the review
fixes. pytest line above: 254 passed, 21 xfailed = 11 scenario xfails (engine) + 10
metric xfails ([human]).

## Results written (numbers from results/<run>/metrics.json, I8)
| suite / strategy | results folder | scenarios | runnable | passed | checks failed / checks | errors | resolver calls |
|---|---|---|---|---|---|---|---|
| smoke / ripple | results/2026-10-19_smoke_uncommitted_2 | 11 | 0 | 0 | 0 / 0 | 0 | 0 |
| v0 / append_only | results/2026-10-19_v0_append_only_uncommitted_2 | 35 | 35 | 0 | 76 / 175 | 5 | 0 |
| v0 / newest_wins | results/2026-10-19_v0_newest_wins_uncommitted_3 | 35 | 35 | 0 | 66 / 175 | 5 | 0 |
| v0 / check_everything | results/2026-10-19_v0_check_everything_uncommitted_2 | 35 | 35 | 30 | 5 / 175 | 0 | 144 |
| v0 / ripple | results/2026-10-19_v0_ripple_uncommitted_2 | 35 | 0 | 0 | 0 / 0 | 0 | 0 |

Superseded same-day folders (first runs, before the review fixes changed
`checks_failed` from a message count to a per-target count and added `errors`):
results/2026-10-19_smoke_uncommitted, 2026-10-19_v0_append_only_uncommitted,
2026-10-19_v0_newest_wins_uncommitted, 2026-10-19_v0_newest_wins_uncommitted_2 (a
duplicate CLI run, identical numbers), 2026-10-19_v0_check_everything_uncommitted,
2026-10-19_v0_ripple_uncommitted. WS-7 did not delete them (deletion needs the
author's go-ahead); nothing cites them. `errors` = 5 for append_only and newest_wins
are the five ask-family answer events ("memory 'eligibility' is VALID, not
PENDING_USER"): the baseline never asked, so the scenario's answer cannot apply.

Reading: with the scripted oracle, check_everything is the accuracy ceiling at the
cost ceiling (H1's reference); its five failures are the ask family, where flagging
the subtree below a question needs the graph. append_only and newest_wins pass no
scenario: every family needs propagation. The ripple strategy is integration-blocked
on the author's WaveEngine and is reported "not runnable: TODO(human) engine", never
as a pass. Memory metrics are "TBD (pending run)" until bench/metrics.py is implemented.

## Eval-auditor checklist (.claude/agents/eval-auditor.md), run by WS-7 on its own code
1. Train/test separation — no training/ directory exists yet; persona names, template
   names and gold phrasing live only in bench/generate.py and bench/data/jobs_v0.
   `grep` over src/, tests/ (outside tests/scenarios/test_bench_*) and docs/ finds no
   persona or template string except a WS-1 test *function name* containing
   "cgpa_rise" (tests/domains/jobs/test_end_to_end.py:21), which is not data. The
   split is recorded per scenario in manifest.json and tested
   (test_split_is_by_persona_and_template_never_by_item). Phase 4 must draw the link
   finder's training pairs from `train` only; the loader's `split` argument is how.
   Outcome: pass.
2. Baselines get the same inputs — one ScenarioRunner, one AliasResolver, one FakeClock,
   identical gold for every strategy; resolver calls counted by one CountingResolver.
   The documented difference is the propagation policy (ADR-0060). Outcome: pass.
3. Numbers traceable — every number in this file's results table comes from
   results/2026-10-19_*/metrics.json; ADR-0061's "35 scenarios, 175 checks" are data
   facts in manifest.json and metrics.json; docs/learning/bench.md section 4 numbers
   are a hand-computed worked example on a synthetic trace and are labelled as such,
   not reported results. README.md and the paper quote nothing from WS-7. Outcome: pass.
4. Seeds, model and prompt versions recorded — config.json records generator_seed
   20261019, run_seed null (runs are deterministic, no randomness), models null and
   prompt_versions null (no LLM is called; llm_calls = 0 in metrics.json), engine and
   resolver names, action layer, data sha256, git_sha "uncommitted" (no commits exist
   in the repo; the coordinator's checkpoint will give real shas). Outcome: pass with
   the known "uncommitted" sha until the first commit.
5. LLM-judge scores beside automatic metrics and a human-checked sample — not
   applicable in v0: no LLM, no judge. Phase 3 must add both. Outcome: n/a, noted.

## Code review
Reviewed by the code-reviewer subagent on the full diff (one blocker, four majors,
eight minors). All fixed and covered by tests except m7, which is recorded here:
- B1 tests pinned to the "uncommitted" sha → `git_short_sha` monkeypatched in
  tests/scenarios/test_bench_run.py.
- M1 results traceability (I8) → `git_short_sha` appends "-dirty" when the tree
  differs from HEAD; `run_dir_for` never overwrites (suffix `_2`, `_3`, ...);
  test_git_short_sha_marks_a_dirty_tree, test_a_second_run_on_the_same_day_gets_its_own_folder.
- M2 `checks_failed` was a mismatch-line count → now one per failed gold target;
  runtime problems live in `ScenarioOutcome.errors` and metrics.json `errors`.
- M3 `write_data` wiped every yaml in `--out` → only files its previous manifest
  listed are replaced; a manifest-less directory with scenarios is refused
  (test_write_data_refuses_a_directory_of_hand_written_scenarios).
- M4 unvalidated action aliases crashed a run → `validate_scenario` checks
  update/answer/forget aliases in timeline order and exactly one action per event;
  `run_suite` reports "not runnable: invalid scenario: ..."; MemoryNotFoundError
  during an event is recorded as an error.
- m1 opening alias lost after a new opening version → resolved through the version
  chain root (test_trace_keeps_the_opening_alias_after_the_opening_gets_a_new_version).
- m2 append_only restore and completion in two transactions → one transaction
  (test_append_only_restoration_and_completion_commit_together).
- m3 check_everything wave order relied on store ordering → explicit sort.
- m4 update events dropped structured/valid_to → carried over from the latest
  version; corrections pass `structured` (test_update_carries_over_...).
- m5 persona count silently capped → ValueError. m6 looping tests → parametrized.
  m8 AliasResolver's unused `ids` parameter → removed.
- m7 (open): bench imports tests.fakes and tests.scenarios.runner, so
  `python -m bench.run` needs the repo root as cwd. Moving the fakes out of tests/
  is a coordinator decision (tests/fakes is coordinator-owned); noted for DEVLOG.

## Contract and doc change requests for the coordinator
- core: a `RippleDriver` protocol (`run(event)`, `resume(event)`) that `NightlySweep`
  and `ripple.core.answers` accept instead of the concrete `RippleRunner`, so
  `bench/strategies.as_runner` loses its cast.
- docs/04-evaluation.md: list time-to-consistency and the stale-action window under
  action-level metrics (ADR-0062); record ADR-0063's proposed H1 "accuracy" reading
  (correct_updates / should-change targets) as the collaborator's proposal pending the
  Phase 3 baseline ADR; Mem0-style baseline still open.
- docs/05-roadmap.md: Phase 3 "RippleBench v0 (jobs, ~30 scenarios) + baselines" is
  built (35 scenarios, baselines runnable; ripple numbers blocked on the engine);
  "[human] Metric functions" has its interface, tests and docs ready.
- docs/adr/README.md: index 0060–0063 (Accepted under the autonomous mandate).
- docs/IDEAS.md: v1 generator items — missing-link scenarios (Linker in the loop),
  multi-parent same-wave cases (docs/learning/ripple-runner-and-writes.md exercise),
  prose fields for the change detector.
- CLAUDE.md commands: `uv run python -m bench.run --suite v0 --strategy <name>` and
  `uv run python -m bench.generate --check`.

## Open problems / integration-blocked
- Ripple-strategy numbers (smoke and v0) wait on the author's WaveEngine. When it
  lands: remove the xfail markers in tests/scenarios/test_scenarios.py (coordinator /
  author), rerun `bench.run --suite smoke` and `--suite v0 --strategy ripple`, then
  compare resolver_calls with check_everything's 144 for the H1 cost ratio.
- Metric bodies are [human]: tests/scenarios/test_bench_metrics.py (10 xfail strict)
  and docs/learning/bench.md section 4 are the spec. Once implemented, bench/run.py
  should call them over the snapshots (today it writes the traces only and reports
  "TBD (pending run)").
- StubActionLayer is a placeholder; swap in WS-1's RecommendationSource via
  `ScenarioRunner(action_layer=...)` and bench/run.py config.
- check_everything's ask handling still parks the subtree through the graph
  (documented in ADR-0060); only the ask family is affected.
- Repo has no commits, so every results folder carries sha "uncommitted".

## Suggested commit message
bench: baselines, RippleBench v0 generator, TTC harness and metric interfaces — make
the evaluation runnable and honest before the engine exists (ADR-0060..0063; baselines
run today, ripple reported not runnable; [human] metrics specified with xfail tests)
