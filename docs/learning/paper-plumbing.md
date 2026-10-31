# paper: numbers from results/ and the I8 check
Written 2026-10-31 (WS-17); updated the same day (WS-21) for generator and training
seeds, the oracle namespace, the draft gate and the rendered drafts (ADR-0135,
ADR-0136). Describes only code that exists: paper/registry.py, paper/numbers.py,
paper/i8.py, the two TOML rule files, tests/paper.

## 1. What it does
`paper.registry` names every number the paper and thesis may print as a macro
(`h1.accuracy_ratio`, `oracle.v0.check_everything.scenarios_passed`).
`python -m paper.numbers` reads each macro's value from results/ run folders that pass
provenance checks, or refuses it with a reason, and writes docs/paper/generated/ (TeX,
JSON, Markdown, figure data, and the paper and thesis drafts with their macros filled
in). `python -m paper.i8` and the test `test_invariant_I8_...`
scan README.md and docs/ for result-like numbers and fail on any that do not trace to
results/.

## 2. Why it exists
I8 (every number traces to results/), docs/04 Protocol (pinned models, three seeds for
headline numbers, eval-auditor before publishing), ADR-0012 (evaluation first).
ADR-0110 fixes the macro scheme and provenance rules, ADR-0111 the check's rules.
Without it a number copied by hand from an old report.md, from an uncommitted run, or
from the best of several runs reaches the PDF.

## 3. How it works
- `REGISTRY` is built by small generators (`_oracle_run_counts`, `_memory_metrics`,
  `_oracle_memory`, `_hypotheses`, `_linkers`, `_link_cells`, `_handcheck`,
  `_ablations`, `_oracle_ablations`, `_pilot`). Two namespaces never stand in for each
  other: `oracle_mem.*`, `oracle_h1.*`, `oracle_h2.*` and `oracle_ablation.*` read the
  runs that exist (scripted oracle, gold links, three generator seeds), while `mem.*`,
  `h1.*`, `h2.*` and `ablation.*` wait for the system C1 claims (a trained linker). A `MacroSpec` says
  where to look (`run_pattern`, `config_match`, with `Prefix` for string starts), what
  to read (`json_path`), how to print (`fmt`) and how strict to be (`headline`,
  `aggregate`). A `DerivedSpec` divides or subtracts two macros; its `differ` names the
  config fields the compared runs may differ in. `FIGURES` are rows of macros.
- `resolve_macro`: `discover_runs` → `matches_config` → `provenance_problems` per run
  (run_at, clean commit unless `--draft`, complete run, models and prompt versions,
  a seed for means) → `select_runs` (newest run, or the newest group sharing the whole
  config minus `VOLATILE_CONFIG`, one run per seed) → fail closed on a newer failing
  run, on same-configuration runs that disagree, and on fewer than three seeds for a
  headline → `format_value`. Any failure returns `Refused(name, reason)`.
- Which seed counts (`spec_seeds`): a bench run with `seeds.kind == "generator"` counts
  its generator seed (ADR-0121); a spec with `seed_path` reads its seed there (the
  trained linker: `linker_details.seed`, the training seed) and lets the `seed_varies`
  fields differ inside a group. The deterministic rule linker is one SINGLE run.
- Prompt versions are required for a model that prompts: one the run says made LLM
  calls, or one named without `llm_calls == 0` (a trained classifier has no prompt).
- `resolve_derived` and `figure_cells` call `inconsistent_sources` so a ratio or a
  figure never mixes runs of different code, data or resolver. `render_files` writes
  numbers.tex (`\rnum{key}`), numbers.json (sources, per-run values, superseded runs),
  numbers.md, per figure a CSV, a pgfplots `.dat` and an SVG, and `render_document`
  copies docs/paper/paper.md and thesis.md with each `{{num:key}}` outside inline code
  replaced by its value (ADR-0136).
- `paper.i8.scan_text` masks structural numbers (`mask_line`), then `line_claims` finds
  claims with `DETECTORS`, `OUTCOME_COUNT` (verification only beside a test runner),
  `FRACTION`, `DECIMAL` and, under docs/paper, `STRICT_NUMBER`. `macro_claims` checks
  `{{num:key}}` and `value<!--num:key-->`. `judge` accepts a claim by citation
  (`vouches`: exact bounded report text, or the counted noun's metrics key), allow-list
  category, allow-list text with its line `context`, or known violation, and reports
  stale rule entries.

## 4. Trade-offs
- A heuristic detector instead of "every digit": far fewer false positives, but a bare
  integer with no metric noun outside docs/paper is invisible (results tables included).
  Wrong if results are written as bare table cells outside docs/paper.
- Fail closed (commit required, newer failure blocks, disagreement blocks): nothing
  renders by default today. `--draft` relaxes only the commit gate, headline numbers
  included, so drafts can be reviewed with real values (ADR-0135); every draft file says
  DRAFT and the default and `--strict` renders are unchanged.
- Recomputing means from run folders instead of reading the summary folders: more code,
  but the renderer can refuse a disagreeing repeat itself; the summaries become a
  cross-check for the eval-auditor.
- Test-outcome counts accepted in DEVLOG and docs/plans when they look like runner
  output: command output, not research results. Wrong if the author reads I8 literally;
  delete the category rule.

## 5. Failure modes and tests (tests/paper)
- Uncommitted, incomplete or unprovenanced run → `test_resolve_macro_provenance_refusals`,
  `test_draft_mode_allows_an_uncommitted_run_for_non_headline_macros`,
  `test_draft_mode_allows_an_uncommitted_headline_mean_but_keeps_the_seed_gate`,
  `test_real_results_never_render_from_an_uncommitted_or_incomplete_run`.
- Picking by value, a hidden newer failure, irreproducible repeats →
  `test_resolve_macro_picks_the_newest_run_by_run_at_not_by_value_or_name`,
  `test_resolve_macro_refuses_when_a_newer_run_fails_the_checks`,
  `test_resolve_macro_refuses_when_runs_of_one_configuration_disagree`.
- Headline from too few seeds, mixed layouts, different models or pair files →
  `test_headline_*`, `test_mixed_seed_layouts_are_refused`,
  `test_linker_runs_on_different_pair_files_are_never_averaged`.
- Generator and training seeds, the orientation runs, models without prompts →
  `test_run_seeds_count_the_generator_seed_of_a_generator_seeded_run`,
  `test_trained_linker_mean_counts_the_training_seed_not_the_shared_run_seed`,
  `test_a_parent_orientation_run_never_doubles_a_trained_seed`,
  `test_a_model_without_prompts_is_refused_unless_the_run_reports_zero_llm_calls`,
  `test_oracle_v0_counts_read_the_checked_in_seed_not_the_newest`.
- Rendered drafts → `test_render_document_*`.
- Ratios or figures across incomparable runs →
  `test_derived_inputs_from_different_data_are_refused`,
  `test_figure_cells_from_incomparable_runs_are_all_refused`.
- Masks hiding real numbers, loose citations →
  `test_line_claims_still_sees_numbers_next_to_structural_ones`,
  `test_a_citation_needs_a_whole_number_match_in_the_report`,
  `test_a_citation_ties_a_count_to_its_own_metric_key`.
- New untraced numbers, stale rule entries, stale generated files →
  `test_invariant_I8_*` in tests/paper/test_paper_invariants.py.

## 6. Interview questions
1. *Why not copy numbers from report.md?* Copies go stale and nothing enforces seeds,
   commits or pinned models; a macro is re-read from results/ on every render.
2. *How do you avoid cherry-picking among repeated runs?* Selection is by `run_at` and
   configuration group, never by value; a newer failing run or a disagreeing repeat
   refuses the number; superseded runs are listed with their values.
3. *What makes a number "headline"?* It answers a hypothesis: recorded models and prompt
   versions, a clean commit (outside `--draft`), at least three seeds (docs/04): generator
   seeds for the bench, training seeds for the trained linker.
4. *Why a separate `oracle_mem` namespace?* The runs that exist use gold links and a
   scripted oracle; printing them under `mem.ripple.*` would let a later trained-linker
   run silently change what the name means.
5. *Why refuse a ratio when the two runs differ in data?* A ratio of numbers from
   different code or data compares nothing; only the compared field may differ.
6. *What does the I8 test not catch?* Bare integers without a metric noun outside
   docs/paper and numbers written in words (ADR-0111).

## 7. Exercise
Copy one v0 baseline folder into a temporary directory three times, give each a fake
clean `git_sha`, `run_seed` 1, 2 and 3, `models: {}` and `prompt_versions: {}`, and
predict what `uv run python -m paper.numbers --results <tmp> --out <tmp>/gen` prints for
`oracle.v0.<strategy>.scenarios_passed` and for `mem.<strategy>.update_accuracy`.
(Hints: run_at decides which folder; the split and `memory_metrics` decide the rest.)
