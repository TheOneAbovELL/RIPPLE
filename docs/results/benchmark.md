# RippleBench results: v0, news_v1, finance_v1 and smoke under four strategies
Written 2026-10-31 (WS-18); revised after the eval-auditor's review the same day. Every
number below is copied from results/2026-10-31_benchsummary_uncommitted/report.md, which
bench/summary.py wrote from the 82 run folders it lists (one per strategy, split,
ablation and generator seed). Each run folder holds config.json, metrics.json, report.md
and the per-scenario replay traces the metrics were computed from (I8).

## Read this first: what these numbers are and are not
- **Synthetic data.** All three tracks are generated from templates with invented
  people, companies and stories (ADR-0061, ADR-0101). They test whether each strategy
  keeps memory consistent under the labelled semantics, not language understanding.
- **The gold is not human-audited.** The expected states were written by the template
  authors and the generators. No sample has been hand-checked against them, and there
  is no LLM judge whose calibration docs/04's protocol could report.
- **Scripted oracle resolver, no LLM.** Every decision about *how* to change a belief
  comes from the scenario file (bench/scenario.py AliasResolver). `llm_calls` is 0 in
  every run, and tokens and USD per ripple are not measured (n/a). Cost is resolver
  calls: the number of calls an LLM resolver would have made (ADR-0110 point 8,
  ADR-0122).
- **Gold links, no link finder.** Links come from the scenario file (`linker:
  "scenario"`); the trained linker (C1) is not in these runs.
- **Ripple meeting every gold state is a correctness check, not a discovery.** The gold
  states and the oracle's answers were written for graph-scoped propagation, so ripple
  meeting them shows the engine implements the specified semantics. The comparison
  shows how far each *other* strategy falls from those semantics, and at what resolver
  cost.
- **The tracks mirror each other** family by family (docs/learning/bench-v1.md), so
  news_v1 and finance_v1 repeat v0's pattern by construction. They are not independent
  evidence; they show the semantics carry across three domain vocabularies.
- **"Held out" means held out from link-finder training only.** The test split is the
  persona and template cells no training pair may come from (ADR-0061). The engine and
  the baselines were not trained on anything. But design decisions such as ADR-0104's
  wave order were made with these tracks' outcomes in view.
- **Uncommitted code.** Every run says `git_sha: "uncommitted"`. The paper's macros
  refuse such runs (ADR-0110) until the author's first commit and a re-run.
- Readings of H1 and H2 follow ADR-0063 and ADR-0110 point 8. They are the
  collaborator's provisional readings until the Phase 3 baseline ADR.

## What was run
`uv run python -m bench.matrix` (bench/matrix.py) runs, with the scripted oracle:
- smoke (tests/scenarios, hand-written) under each strategy, once (no generator);
- v0 and news_v1 on the test and all splits, and finance_v1 on test (it is test only),
  each under ripple, append_only, newest_wins and check_everything, with three generator
  seeds (ADR-0121: v0 20261019 to 20261021, the v1 tracks 20261031 to 20261033). The
  first seed is the checked-in data; the others are regenerated in memory, and each
  seed re-draws its own persona/template split;
- the two ablations that run offline (ADR-0122), on the test split of each track with
  three seeds: `no_graph` and `no_ask_user` (every ask becomes a keep).

check_everything is graph-blind in *scope*: it re-checks every VALID memory. It still
reads the gold graph to apply its one wave parents first (ADR-0104). `no_graph` is
ripple with no graph to scope by, which is check_everything's scope under the ripple
name (ADR-0122).

Not run: the LLM-linker, without-Curator and without-evidence ablations (they need a
model), the Mem0-style baseline (undecided, ADR-0060), and STALE (no local copy).

Then `uv run python -m bench.summary` writes the summary folder. It:
- reads only runs whose `source_sha256` equals the current code's (the files a bench run
  executes, ADR-0120 point 6);
- keeps one run per seed, and refuses reruns that disagree;
- refuses runs labelled alike that differ in configuration, and ratios over strategies
  that ran different seeds;
- leaves out runs with scenarios that did not run (none were left out).
A second run of the whole grid into a scratch folder gave identical metrics for all 82
runs. That check is not in results/; it is re-runnable with the same two commands.

Metric definitions: ADR-0063 as implemented in ADR-0120, with the gold-stale rule and
TTC window amended by ADR-0123. Rates pool counts over scenarios; stale kept, wrongful
changes and questions are averages per scenario. Means are over the three seeds, with
[min to max] when the seeds differ.

## Headline split: v0 test
| strategy | passed | update accuracy | dependent update accuracy | stale kept | stale retrieval | stale recommendations | never consistent | resolver calls per ripple | source |
|---|---|---|---|---|---|---|---|---|---|
| ripple | 20.0/20 | 100.0% | 100.0% | 0.00 | 0.0% | 0.0% | 0.0% | 1.56 [1.50 to 1.67] | results/2026-10-31_benchsummary_uncommitted |
| check_everything | 17.0/20 [15 to 18] | 94.8% [91.8% to 96.4%] | 93.0% [89.1% to 95.2%] | 0.15 [0.10 to 0.25] | 0.0% | 0.0% | 5.2% [3.6% to 8.2%] | 3.45 [3.22 to 3.75] | results/2026-10-31_benchsummary_uncommitted |
| newest_wins | 0.0/20 | 28.7% [23.7% to 36.4%] | 9.6% [8.7% to 10.5%] | 2.00 [1.75 to 2.25] | 32.3% [30.3% to 33.4%] | 50.0% | 71.3% [63.6% to 76.3%] | 0.00 | results/2026-10-31_benchsummary_uncommitted |
| append_only | 0.0/20 | 19.7% [16.9% to 23.6%] | 9.6% [8.7% to 10.5%] | 2.25 [2.10 to 2.45] | 33.1% [32.7% to 33.7%] | 66.7% | 80.3% [76.4% to 83.1%] | 0.00 | results/2026-10-31_benchsummary_uncommitted |

Counts behind those rates, per run (mean over seeds, [min to max]):

| strategy | errors | should change | change events | resolver calls | recommendations shown | retrieved | source |
|---|---|---|---|---|---|---|---|
| ripple | 0 | 58 [54 to 63] | 25 [24 to 27] | 39 [36 to 41] | 13 [9 to 16] | 321.7 [308 to 330] | results/2026-10-31_benchsummary_uncommitted |
| check_everything | 0 | 57 [54 to 61] | 25 [24 to 27] | 86 [81 to 90] | 13 [9 to 16] | 321.7 [308 to 330] | results/2026-10-31_benchsummary_uncommitted |
| newest_wins | 3 [2 to 5] | 56 [54 to 59] | 22 | 0 | 8 [4 to 10] | 368.3 [357 to 383] | results/2026-10-31_benchsummary_uncommitted |
| append_only | 3 [2 to 5] | 56 [54 to 59] | 22 | 0 | 12 [6 to 15] | 408.3 [398 to 425] | results/2026-10-31_benchsummary_uncommitted |

How to read the columns:
- *Update accuracy* is correct updates over should-change targets (ADR-0063). Whether a
  target "should change" depends on what the strategy itself held before the event, so
  the denominator (*should change* above) differs between strategies.
- *Dependent update accuracy* leaves out the alias the event wrote (ADR-0120 point 5).
  That write is shared by every strategy and inflates the baselines' scores.
- *Stale retrieval* is the share of probe results that are unflagged and gold-stale
  (ADR-0123's rule). The probe uses the real retriever: lexical, graph expansion,
  flags kept, every match (ADR-0120 point 4). Its denominator (*retrieved*) differs by
  strategy, because strategies that keep old rows have more rows to match.
- *Stale recommendations* uses the placeholder ranking (StubActionLayer). It ranks only
  jobs openings, so it is n/a on the v1 tracks. On v0 it rests on the small sample in
  *recommendations shown*.
- *Never consistent* is the share of should-change targets that never reached gold
  (time to consistency, ADR-0062).

## H1: check-everything's accuracy at a fraction of its cost
docs/04 states the targets: an accuracy ratio of at least nine tenths and a cost ratio
under one fifth. Reading (ADR-0063, ADR-0110 point 8):
- accuracy ratio = ripple update accuracy / check_everything update accuracy;
- cost ratio = ripple resolver calls per ripple / check_everything's;
- both are ratios of the seed means.

| suite | split | accuracy ratio | cost ratio | by seed | source |
|---|---|---|---|---|---|
| v0 | test | 105.4% | 45.3% | 20261019: accuracy 103.7% cost 44.4%; 20261020: accuracy 108.9% cost 47.1%; 20261021: accuracy 103.8% cost 44.4% | results/2026-10-31_benchsummary_uncommitted |
| v0 | all | 105.1% | 47.1% | 20261019: accuracy 105.1% cost 47.2%; 20261020: accuracy 105.1% cost 47.2%; 20261021: accuracy 105.1% cost 46.9% | results/2026-10-31_benchsummary_uncommitted |
| news_v1 | test | 103.6% | 47.5% | 20261031: accuracy 103.8% cost 44.2%; 20261032: accuracy 103.3% cost 51.9%; 20261033: accuracy 103.6% cost 46.2% | results/2026-10-31_benchsummary_uncommitted |
| news_v1 | all | 105.1% | 50.0% | 20261031: accuracy 105.1% cost 50.0%; 20261032: accuracy 105.2% cost 50.0%; 20261033: accuracy 105.1% cost 50.0% | results/2026-10-31_benchsummary_uncommitted |
| finance_v1 | test | 105.1% | 50.0% | 20261031: accuracy 105.1% cost 50.0%; 20261032: accuracy 105.0% cost 50.0%; 20261033: accuracy 105.1% cost 50.0% | results/2026-10-31_benchsummary_uncommitted |

**Answer on these benchmarks: the accuracy half is met, but by construction; the cost
half is not met.**

*Accuracy.* Under the oracle the accuracy ratio cannot fall below one. Ripple meets gold
by construction (see "Read this first"). check_everything loses accuracy only in the ask
family: cutoff_unknown in v0, conflicting_reports in news_v1, rate_edge in finance_v1.
There, its one wave re-decides the asked belief's dependent on its own and keeps it
VALID. Gold wants it SUSPECT, waiting for the user's answer (the run reports' failure
lines, for example "recommendation: status VALID, expected SUSPECT").

Whether a graph-blind re-check should leave that dependent VALID depends on the wave
order ADR-0104 chose. Applying the wave parents first (the order chosen) gives this
result; children first would make check_everything pass the family (ADR-0104,
alternatives). The excess above one is therefore that convention, not a measured
advantage. Quote the accuracy half as "met; at least one by construction under the
oracle". A ratio without the ask family is TBD (pending run): the summary does not
compute it.

*Seed spread.* Seed 20261020's split holds out the cutoff_unknown template itself
(regenerate its manifest with `bench.seeds.generate_track("v0", 20261020)`). So every
persona's ask-family scenario falls in its test split, rather than only the held-out
personas'. That is why its check_everything accuracy is the lowest and its accuracy
ratio the highest in the v0 test row above.

*Cost.* On the v0 test split, ripple uses 45.3% of check_everything's resolver calls per
ripple (results/2026-10-31_benchsummary_uncommitted). Across the seeded tracks the
per-seed cost ratio stays between 44.2% and 51.9% (same folder), so it is not one draw.
Smoke has no H1 row. The docs/04 target is under one fifth, so the cost half is not met
on these benchmarks. The comparison is like for like: ripple and check_everything open
the same number of ChangeEvents in every v0 test seed (*change events* in the counts
table), so the cost ratio is a ratio of resolver calls.

*Why the cost ratio is far from one fifth.* check_everything re-checks every VALID
memory after each write; ripple re-checks only the affected subgraph. The scenario
stores here are small (each scenario file declares all its memories), so re-checking
everything costs only about twice the graph-scoped ripple. **That the ratio would fall
on larger stores is a prediction, not a result:** no run here varies store size.
A scaling run (the same scenarios padded with unrelated memories) is the measurement
H1's cost half needs; it is a follow-up in docs/plans/parallel-execution/ws-18.md.

*Two more predictions, untested here.* With a real resolver, check_everything's errors
would scale with the number of memories it re-checks. Ripple's would come from resolver
mistakes inside its subgraph and from links the link finder misses.

## H2: stale retrieval rate far below standard memory retrieval
Reading (ADR-0110 point 8): "standard memory retrieval" is append_only, where every
statement stays retrievable. Mem0-style is not built. The gap is append_only's rate
minus ripple's, in points. newest_wins is shown beside them as the stronger baseline.

| suite | split | append_only | newest_wins | ripple | gap (points) | source |
|---|---|---|---|---|---|---|
| v0 | test | 33.1% | 32.3% | 0.0% | 33.1 | results/2026-10-31_benchsummary_uncommitted |
| v0 | all | 33.1% | 31.4% | 0.0% | 33.1 | results/2026-10-31_benchsummary_uncommitted |
| news_v1 | test | 34.9% | 33.9% | 0.0% | 34.9 | results/2026-10-31_benchsummary_uncommitted |
| news_v1 | all | 33.6% | 32.8% | 0.0% | 33.6 | results/2026-10-31_benchsummary_uncommitted |
| finance_v1 | test | 32.8% | 32.0% | 0.0% | 32.8 | results/2026-10-31_benchsummary_uncommitted |

**Answer on these benchmarks: yes in direction.** Whether the gap counts as "far below"
waits for the numeric target docs/04 leaves open. On the v0 test split, 33.1% of the
probe results append_only shows are unflagged stale beliefs; ripple shows none
(results/2026-10-31_benchsummary_uncommitted). Why:
- Ripple retires superseded beliefs, and the retriever never returns RETIRED rows (I1).
- Ripple shows beliefs that wait on a question with their flag, and flagged results do
  not count as stale.
- Append_only keeps every old version VALID. Newest_wins retires only the direct fact,
  so its stale dependents stay visible: 32.3% on v0 test (results/2026-10-31_benchsummary_uncommitted).

Caveats specific to H2:
- The probe queries each gold alias with its *first* content, the wording before any
  change. That is close to the worst case for strategies that keep old rows: the old
  row matches its own words best.
- The rate covers every lexical match plus graph neighbours, not the top few an agent
  would read. With no top-k cut, tie order cannot change the count (ADR-0120 point 4).
- The denominator differs by strategy (*retrieved* in the counts table).
- The probe is lexical BM25 with graph expansion; the dense path waits for its embedder
  ADR.
- Ripple's zero depends on the gold graph and on the oracle writing exactly the gold
  content. With a learned linker, a missing link would leave a stale dependent visible.
  With an LLM resolver, an update with the wrong content counts as stale too.

## Ablations (test split, three seeds)
| suite | variant | update accuracy | stale kept | questions asked | stale retrieval | never consistent | resolver calls per ripple | source |
|---|---|---|---|---|---|---|---|---|
| v0 | ripple | 100.0% | 0.00 | 0.15 [0.10 to 0.25] | 0.0% | 0.0% | 1.56 [1.50 to 1.67] | results/2026-10-31_benchsummary_uncommitted |
| v0 | no_graph | 94.8% [91.8% to 96.4%] | 0.15 [0.10 to 0.25] | 0.15 [0.10 to 0.25] | 0.0% | 5.2% [3.6% to 8.2%] | 3.45 [3.22 to 3.75] | results/2026-10-31_benchsummary_uncommitted |
| v0 | no_ask_user | 82.4% [72.9% to 89.1%] | 0.50 [0.30 to 0.80] | 0.00 | 2.5% [1.2% to 3.8%] | 17.6% [10.9% to 27.1%] | 1.68 [1.59 to 1.73] | results/2026-10-31_benchsummary_uncommitted |
| news_v1 | no_ask_user | 87.1% [85.2% to 90.2%] | 0.37 [0.30 to 0.40] | 0.00 | 2.2% [1.2% to 2.8%] | 12.9% [9.8% to 14.8%] | 1.64 [1.45 to 1.86] | results/2026-10-31_benchsummary_uncommitted |
| finance_v1 | no_ask_user | 82.5% [81.0% to 84.2%] | 0.51 [0.46 to 0.57] | 0.00 | 2.8% [2.1% to 3.5%] | 17.5% [15.8% to 19.0%] | 1.62 | results/2026-10-31_benchsummary_uncommitted |
| any | llm_linker | not run: needs a model and the trained linker in the bench | | | | | | - |
| any | no_curator | not run: needs the Curator agent with a model | | | | | | - |
| any | no_evidence | not run: needs the tailor's evidence path with a model | | | | | | - |

- `no_graph` equals check_everything on every metric and track by construction
  (ADR-0122), and a test asserts this on the smoke scenarios. It adds no information on
  an oracle; it fills the ablation family for a later LLM-resolver run. A second reading
  of "without graph", ripple with every link removed, would behave like newest_wins.
  It was not run (ADR-0122, alternatives).
- `no_ask_user` is the informative ablation. Without questions, the beliefs the
  resolver could not settle stay VALID and unflagged:
  - update accuracy falls to 82.4% on v0 test (results/2026-10-31_benchsummary_uncommitted);
  - stale retrieval rises from 0.0% to 2.5% (results/2026-10-31_benchsummary_uncommitted);
  - later answer events fail, because nothing was asked (the `errors` counts of
    results/2026-10-31_v0_ripple_no_ask_user_g20261019_uncommitted and its seed
    siblings).

  Its cost per ripple reads slightly *higher* (1.68 against 1.56,
  results/2026-10-31_benchsummary_uncommitted), but not
  because it does more work. With no question there is no answer event, so about the
  same resolver calls are divided by fewer ChangeEvents. Compare `resolver_calls` and
  `change_events` in `memory_totals` of
  results/2026-10-31_v0_ripple_g20261019_uncommitted and
  results/2026-10-31_v0_ripple_no_ask_user_g20261019_uncommitted. Cost per ripple has a
  strategy-dependent denominator; `resolver_calls_per_scenario` in the summary has a
  fixed one.

## Smoke suite (hand-written scenarios, no seeds)
| strategy | passed | update accuracy | wrongful changes | stale retrieval | stale recommendations | resolver calls per ripple | source |
|---|---|---|---|---|---|---|---|
| ripple | 11.0/11 | 100.0% | 0.00 | 0.0% | 0.0% | 1.33 | results/2026-10-31_benchsummary_uncommitted |
| check_everything | 8.0/11 | 92.9% | 0.18 | 0.0% | 0.0% | 2.27 | results/2026-10-31_benchsummary_uncommitted |
| newest_wins | 0.0/11 | 28.6% | 0.00 | 34.7% | 50.0% | 0.00 | results/2026-10-31_benchsummary_uncommitted |
| append_only | 0.0/11 | 21.4% | 0.00 | 35.9% | 66.7% | 0.00 | results/2026-10-31_benchsummary_uncommitted |

check_everything's smoke failures are **planted resolver errors, not over-correction it
would show on its own.** Two smoke files script oracle answers that contradict gold, and
only a strategy that re-checks everything ever receives them:
- tests/scenarios/resume_version_snapshot.yaml answers "retire" for an application that
  gold keeps VALID. Ripple never asks about it, because snapshot_of links do not
  propagate.
- tests/scenarios/ask_unanswered_subtree.yaml gives an update with no `trigger:` scope,
  which check_everything receives already at the first event.

The trap is deliberate for ripple's own tests: it proves ripple does not touch those
memories. But it makes smoke unfit for comparing check_everything with ripple. The
generated tracks scope such answers by trigger (bench/scenario.py), and their wrongful
changes are zero for every strategy. **Do not quote "check_everything over-corrects"
from smoke.** A bench copy of the two files with trigger-scoped answers would remove
the trap; that is a follow-up.

## What these results do not establish
- LLM resolver quality, tokens or money (C4 beyond resolver calls). These need
  `ANTHROPIC_API_KEY` and an LLM resolver run.
- The trained link finder (C1, H3, H4); see docs/results/link-finder.md (WS-19).
  A caveat for a future trained-linker bench run: link pairs are built from the
  checked-in seed only, and seeds 20261020 and 20261021 hold out templates that are
  training cells in seed 20261019 (for example accepted_offer and cutoff_unknown). A
  trained-linker run on those seeds' test splits would include templates the linker
  trained on. Restrict such runs to the first seed, or retrain per seed.
- Behaviour on real stories or real students. The v1 tracks have no curated stories
  yet, and the pilot (C3) has not run.
- H1's cost half at realistic store sizes (see H1).
- Agent task success: the action layer is the placeholder ranking.

## Reproduce
```
uv run python -m bench.matrix
```
This runs the whole grid and then the summary. A single run looks like
`uv run python -m bench.run --suite v0 --strategy ripple --split test --generator-seeds 3`.

Folder names are `<date>_<suite>_<strategy>[_<ablation>]_g<seed>_<sha>`. The second
split of one configuration on the same day gets a `_2` suffix, for example the v0 all
split under results/2026-10-31_v0_ripple_g20261019_uncommitted_2. Each config.json names
its split.
