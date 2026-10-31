# ADR-0135: Paper macros for generator-seeded oracle runs and trained-linker runs; the draft gate
Status: Accepted under the autonomous mandate · Date: 2026-10-31 (WS-21) · Amends ADR-0110

## Context
ADR-0110 built the macro registry before any metric, seeded run or trained linker existed.
Today results/ holds the runs WS-18 and WS-19 produced (docs/results/benchmark.md,
docs/results/link-finder.md), and no macro renders from them:
- The bench writes one folder per *generator* seed with `run_seed: null` (ADR-0121), so
  every MEAN macro refused with "no run seed recorded".
- The headline `mem.*` macros match `linker: "trained"`. Every bench run records
  `linker: "scenario"` (gold links, ADR-0122). They should, since no trained-linker bench
  run exists or is planned before a key and a design choice (ws-18.md, request 5).
- `oracle.v0.*` (SINGLE, split all) would pick whichever seed's folder is newest.
- The three trained-linker runs share one evaluation `run_seed`. What varies is the
  *training* seed (`linker_details.seed`, ADR-0126), so they also counted as one seed.
- A trained classifier names a model but uses no prompt. The prompt-version gate
  refused it.
- `--draft` relaxed the clean-commit gate for non-headline macros only. The author asked
  for complete paper and thesis drafts today, on an uncommitted tree, with every number
  rendered by the pipeline. Under ADR-0110 every headline number would print TBD.

## Decision
1. **Generator seeds count.** `RunRecord.run_seeds` returns `seeds.generator_seed` when
   `seeds.kind == "generator"` (ADR-0121). The data differs per seed, but the config's
   `data` block is identical across a seed group, so the existing grouping holds.
2. **A spec can name its seed.** `MacroSpec.seed_path` (a config.json path) and
   `seed_varies` (top-level fields that change with that seed) let a MEAN macro average
   over a seed other than the run seed. The trained linker's macros use
   `linker_details.seed` and let `linker_details` and `models` vary. Everything else
   must still agree. `Rendered.seeds` carries the seed set, so a headline derived macro
   still refuses inputs averaged over different seeds.
3. **The prompt gate applies to models that prompt.** It applies when the run called an
   LLM, or when it names a model and does not report `llm_calls == 0`. A run that
   reports zero LLM calls may record `prompt_versions: {}`.
4. **Oracle-labelled memory macros** `oracle_mem.<suite>.<strategy>.<key>` for v0,
   news_v1 and finance_v1. They use the test split and the resolver prefix
   "scripted oracle", require `linker: "scenario"`, `ablation: null` and
   `seeds.kind: "generator"`, and take the mean over the three generator seeds. They
   carry the ADR-0063 keys without tokens or USD (null without an LLM), plus
   `dependent_update_accuracy`. Stale recommendations are v0 only (the placeholder
   ranking ranks jobs openings). Derived: `oracle_h1.<suite>.accuracy_ratio`,
   `oracle_h1.<suite>.cost_ratio` and `oracle_h2.<suite>.stale_retrieval_gap_points`,
   which are ratios and differences of seed means, as bench/summary.py computes them.
   The ablations that run offline are `oracle_ablation.<suite>.<no_graph|no_ask_user>.<key>`.
   The `mem.*`, `h1.*`, `h2.*` and `ablation.*` macros of the system C1 claims (a
   trained linker) stay, and refuse until such runs exist. The two namespaces never
   stand in for each other.
5. **`oracle.v0.*` is pinned** to `seeds.generator_seed: 20261019`, the seed that
   reproduces the checked-in bench/data/jobs_v0.
6. **Link-finder macros match the harness as built.**
   - The config filter adds `new_memory: "dependent"`, so the `--new parent`
     orientation runs never double a seed.
   - The held-out cells (`f1_|precision_|recall_|typed_f1_` × `both|persona|template`),
     finance precision and recall, and CPU seconds per call are added.
   - The rule linker is deterministic. Its macros are SINGLE and non-headline, so one
     run is enough.
   - The trained linker is the MEAN over three training seeds, as a headline.
   - `h4.transfer_difference_points` now subtracts finance F1 from the **held_out=both**
     jobs cell. WS-19's report reads that cell, and the overall jobs F1 mixes in cells
     whose templates were seen in training.
   - Two non-headline differences compare the trained mean with the rule run:
     `link.jobs_v0.f1_both_trained_minus_rule_points` and
     `h4.finance_trained_minus_rule_points`. They are non-headline because the seed
     sets differ by design (a rule has no seed).
   - `transfer` joins the track fields a comparison may differ in.
7. **`--draft` relaxes the clean-commit gate for every macro**, headline included.
   Everything else still applies: the seed count, completeness, the pins, agreement
   between repeats, and refusal by a newer failing run. Draft output stays in
   docs/paper/generated/draft/ and is marked DRAFT in every file. The default and
   `--strict` renders are unchanged, so nothing uncommitted reaches
   docs/paper/generated/ or a camera-ready build.

## Alternatives considered
- **Read the means from the summary folders** (results/*_benchsummary_*,
  results/*_linkpairs_summary_*). This is simpler, but it would print numbers past
  every provenance check the registry exists for. Recomputing from run folders lets the
  renderer refuse a disagreeing repeat or a mixed configuration itself. The summaries
  remain a cross-check: the eval-auditor compares the two.
- **Relabel the existing `mem.*` macros to `linker: "scenario"`.** That would make
  C1's headline name print a gold-link number. A later trained-linker run would then
  silently change what the name means.
- **Keep headline macros refused in draft mode.** That is honest, but the drafts would
  carry no numbers to review. The DRAFT marking and the unchanged default and strict
  modes keep the camera-ready guarantee.
- **Treat the trained runs' shared run seed as the seed and require three evaluation
  seeds.** The evaluation is deterministic given a model; re-running it thrice would
  measure nothing. The training seed is the variance docs/04's three seeds are about.

## Consequences
- With the current results/, `python -m paper.numbers --draft` renders the oracle bench
  macros and the trained and rule link macros. The default render still refuses them
  all, because the tree is uncommitted.
- After the author's first commit and a re-run of `bench.matrix` and the WS-19
  evaluations, the default render takes the same values, and docs/paper/generated/
  becomes citable.
- The registry grows from 126 to over 300 macros. tests/paper covers each new rule
  with a fixture in the real producers' config shape.
