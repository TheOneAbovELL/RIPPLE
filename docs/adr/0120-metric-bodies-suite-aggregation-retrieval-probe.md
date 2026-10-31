# ADR-0120: Metric bodies, pooled suite aggregation and a retrieval probe in the replay
Status: Accepted under the autonomous mandate · Date: 2026-10-31 (WS-18)
Implements ADR-0063 (whose bodies were [human]; the author asked on 2026-10-31 for them
to be implemented, docs/plans/final-delivery.md). ADR-0063 is not edited.

## Context
ADR-0063 fixed every metric's definition and left the bodies to the author;
paper/registry.py `MEMORY_METRICS` names the keys the paper reads from
`metrics.json → memory_metrics`. Three things were still open: how a run of 35 scenarios
turns per-scenario counts into one number, what the stale *retrieval* rate is measured
on (the bench never ran a retriever, so `stale_retrieval_rate` had no input), and what
to write for tokens and USD when no LLM ran.

## Decision
1. **Bodies follow the docstrings literally.** Shared helpers keep one definition per
   idea: `stale_ids_at(snapshot)` (gold-stale rows: the row a gold target addresses when
   gold is RETIRED or deleted, or names a content the row does not hold) feeds both stale
   rates, and `stale_hits` is the one numerator, used on live `RetrievedMemory` lists and
   on traces read back from JSON alike. `questions_needed` counts should-change targets
   whose gold is PENDING_USER (docs/04's "needed?").
2. **Suite aggregation pools counts before any ratio (micro average).**
   `update_accuracy = Σcorrect / Σshould_change`; the two stale rates, the never-converged
   share and `cost_per_ripple = Σresolver_calls / ΣChangeEvents` likewise. The registry
   formats `stale_kept`, `wrongful_changes` and `questions_asked` as floats: they are
   per-scenario averages (total / scenarios). Raw totals go to `memory_totals`, per
   scenario counts to `per_scenario[*].memory`, and shares beside the registry keys
   (`stale_kept_share`, `wrong_update_share`, `wrongful_change_share`, TTC medians).
   A ratio with a zero denominator is `null`, never 0.
3. **`tokens_per_ripple` and `usd_per_ripple` are `null` when no LLM ran.** The scripted
   oracle spends no tokens; a 0 would read as "Ripple is free" instead of "not measured",
   and the paper's derived ratios refuse a zero denominator or a missing input,
   which is correct.
4. **A retrieval probe runs after every event that carries gold** (bench/probe.py). For
   each gold target's alias, the real `HybridRetriever` (contract C2) is queried with the
   content the alias was first written with: lexical BM25 over an in-memory index rebuilt
   from the store (every status indexed, visibility left to the retriever, I1), graph
   expansion on, flagged results included with their flag, and **every match returned**
   (k = the store size). A top-k cut was tried first (k = 3) and made two runs of one
   configuration disagree: ties are broken by memory id, and core gives every new
   version a random uuid, so which tied version fell inside the cut changed per run.
   With no cut the counted set does not depend on order. Results
   are stored in the trace (`EventSnapshot.retrieved`), so the rate is recomputable from
   `snapshots/*.json`. Queries come from the scenario file, never from system state, so
   every strategy is asked the same questions. A memory returned by two queries counts
   twice, in the numerator and the denominator alike: the rate is per result shown, the
   same rule for every strategy.
5. **`dependent_update_accuracy`** is reported beside update accuracy: the same ratio
   over should-change targets other than the alias the event acted on. The trigger's
   own targets (its retirement, the new row) are met by the shared write under every
   strategy and narrow the visible gap; this reading leaves them out.
6. **`source_sha256`** covers exactly the files a bench run executes: bench/ (minus the
   grid driver and the summary, which never run inside a run), the ripple packages it
   imports (core, domains, retrieval, the package __init__) and the test support it
   imports (tests/fakes/, tests/scenarios/runner.py). A test runs the bench in a fresh
   process and fails if any loaded repository module lies outside these roots. Hashing
   all of src/ripple was tried first: a concurrent edit to the worker by another
   workstream orphaned every run although the bench never executes it. bench.summary
   uses it to summarise only runs of the current code, refuses runs with scenarios that
   did not run, and refuses to average runs labelled alike whose configuration differs
   beyond the volatile fields paper/numbers.py ignores.

## Alternatives considered
- **Macro average (mean of per-scenario rates)** — every scenario weighs the same, but a
  scenario with one should-change target then counts as much as one with ten, and a
  scenario with none has no rate at all. Lost; ADR-0063 already rejected per-scenario
  pass rate as the headline for the same reason. The per-scenario counts are in the run
  folder for anyone who wants the macro view.
- **0 for tokens and USD** — keeps every field numeric, but turns "not measured" into a
  number the paper would print. Lost on I8.
- **Retrieval queried with the *current* content of each memory** — closer to an agent
  that knows the new fact, but then the query depends on what the strategy wrote and
  baselines are asked different questions. Lost on fairness.
- **Measure stale retrieval on the whole store instead of retrieved results** — that is
  a memory-state metric (stale_kept already covers it), not what an agent is shown. Lost.
- **Dense retrieval too** — needs an embedder, whose ADR is pending (CLAUDE.md). The probe
  is lexical plus graph expansion; this is stated in every run's config.json.

## Consequences
- Every bench run now writes `memory_metrics` as an object with all ten registry keys;
  the paper's memory macros stop being refused for a "TBD string" reason (they still need
  a committed sha, and the headline ones the trained linker; ADR-0122).
- Should-change targets depend on the system's own previous state (ADR-0063's
  definition), so the denominator of update accuracy differs between strategies; the
  report shows the totals so a reader sees both.
- Traces are larger (one probe per gold event); still small JSON.
- The probe's k and query rule are a protocol choice: changing them means re-running
  every published stale retrieval number.

## Revisit if
An embedder ADR lands (add the dense path to the probe), the agents' real query
patterns are known from the pilot (replace the first-content query rule), or the
Phase 3 baseline ADR chooses a macro average.
