# ADR-0121: "Three seeds" means three generator seeds, one results folder per seed
Status: Accepted under the autonomous mandate · Date: 2026-10-31 (WS-18)
Settles the seed question ADR-0110 point 8 left open (run seeds or generator seeds).

## Context
docs/04's protocol asks for "three seeds minimum for headline numbers". ADR-0110 point 8
left open whether these are run seeds or generator seeds, noting that a deterministic
harness meets a run-seed gate trivially. Every bench run today uses the scripted oracle
resolver and the deterministic engine: running the same data twice gives the same
numbers bit for bit, so three run seeds would be three copies of one number. The
variation that exists is in the data: which personas, which values (CGPA, cutoffs,
margins), which persona/template cells are held out. All three tracks are generated from
a seed (bench/generate.py, bench/generate_news.py, bench/generate_finance.py) and the
checked-in data is the default seed's output.

## Decision
1. A seed is a **generator seed**. The seeds of a track are its generator's
   `DEFAULT_SEED` and the next two (`DEFAULT_SEED + 1`, `+ 2`): v0 20261019–20261021,
   news_v1 and finance_v1 20261031–20261033.
2. `bench.run --generator-seeds N` regenerates the track **in memory** for each seed
   (bench/seeds.py) and writes **one folder per seed**, named `..._g<seed>_<sha>`. The
   checked-in files are never rewritten. The default seed is generated too and must
   reproduce the checked-in manifest's `data_sha256`; a mismatch is refused as drift.
3. The split is re-drawn per seed by the generator's own rule (two of five personas and
   two templates held out), so "test split" means each seed's held-out cells.
4. config.json of a seeded run: `seeds = {kind: "generator", generator_seed, run_seed:
   null, data_sha256}`; `data` is **identical across the seed group** (it lists every
   seed and `data_sha256_by_seed`), so runs averaged over the group differ only in the
   volatile `seeds` field, as paper/numbers.py `comparable()` requires.
5. `run_seed` stays `null`: there is no run randomness to seed. Writing the generator
   seed into `run_seed` to satisfy the paper's counter would mislabel the run; instead
   the handover requests that paper/numbers.py count `seeds.generator_seed` when
   `seeds.kind == "generator"`.
6. Curated stories (none exist yet) are not generated per seed and are not part of
   seeded runs; the checked-in runs keep reporting them.

## Alternatives considered
- **Run seeds** — the paper's current reading; meaningless here (no stochastic
  component), and would pass the gate with zero information about variance. Lost.
- **Check the seed-2 and seed-3 tracks in under bench/data/** — inspectable files, but
  triples the data, invites hand edits, and the generator plus the hash in config.json
  already reproduce them exactly. Lost; anyone can write them with the generator's
  `--seed` flag into a scratch folder.
- **One folder holding all three seeds with averaged metrics** — supported by
  paper/numbers.py (`run_seeds` list), but per-scenario rows and snapshot files of three
  datasets would share names, and the paper's run counts (35 scenarios) would read 105.
  Lost on traceability.
- **More personas per seed instead of more seeds** — tests a larger sample, not
  robustness to the generator's draws. Kept as a possible later addition.

## Consequences
- Headline-style numbers in docs/results/benchmark.md are means over three seeds with
  min and max beside them; with an oracle resolver the spread comes only from the data.
- Until paper/numbers.py reads generator seeds, its headline memory macros count zero
  run seeds and refuse (contract request in docs/plans/parallel-execution/ws-18.md).
- A generator change that alters the default seed's output fails seeded runs loudly
  until the checked-in data is regenerated (`--check` first).
- Once an LLM resolver runs, run seeds become meaningful too; then a run would carry
  both, and the gate should require three of each (revisit).

## Revisit if
A stochastic component (an LLM resolver or linker with sampling) enters the bench, or
the Phase 3 baseline ADR fixes a different seed protocol.
