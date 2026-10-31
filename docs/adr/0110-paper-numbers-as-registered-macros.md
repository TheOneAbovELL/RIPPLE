# ADR-0110: Paper and thesis numbers are registered macros rendered from results/
Status: Accepted under the autonomous mandate · Date: 2026-10-31 (WS-17)

## Context
I8: every number in README, docs or the paper traces to a file in results/. docs/04
Protocol: model versions pinned per run, three seeds minimum for headline numbers,
eval-auditor before publication. The write-up (a paper and a B.Tech thesis, May 2028)
will quote dozens of numbers, many recomputed as runs are repeated. Hand-copying them
from report.md files is how a stale, irreproducible or cherry-picked number reaches a
PDF. Today no Ripple-strategy number exists (the WaveEngine and metric bodies are the
author's) and every results/ folder is uncommitted, so the plumbing must show
"TBD (pending run)" honestly rather than leave gaps.

## Decision
1. **Registry.** `paper/registry.py` names every printable number as a dotted macro
   (`oracle.v0.check_everything.scenarios_passed`, `mem.ripple.update_accuracy`,
   `h1.accuracy_ratio`). A `MacroSpec` holds a glob under results/, a config filter
   (dotted config.json path → value; `None` also matches a missing key; `Prefix(...)`
   matches the start of a string), a JSON path in metrics.json or config.json, a format
   (`int`, `float:N`, `pct:N`, `points:N`, `usd:N`), a headline flag, an aggregate
   (`single` or `mean`) and the ids it supports. A `DerivedSpec` is a ratio or
   difference of two macros with `differ`, the config fields the compared runs may
   differ in. A `FigureSpec` is rows × macros with the same `differ`. Entries whose
   JSON path no producer writes yet are `provisional`, with the reason.
2. **Provenance checks** per candidate run (`provenance_problems`):
   - config.json and metrics.json parse; a matching folder holding only one of them
     or an unreadable one refuses the macro (a half-written run never lets an older run
     through); `run_at` is ISO 8601, and a failing run without one counts as newest;
   - a clean commit sha (`[0-9a-f]{7,40}`, not "uncommitted", not "-dirty") for every
     macro; `--draft` relaxes this for non-headline macros only, writes to
     generated/draft/ and marks every file DRAFT;
   - the run is complete: no not-runnable scenario, read from `per_scenario` or
     `scenarios_not_runnable`; a bench run (config has `strategy`) that reports neither
     is refused;
   - a run that called an LLM or names models has every model id pinned (non-empty,
     no "latest", no wildcard) and a non-empty prompt-version mapping. This pin check is
     weak: it cannot tell an alias from a snapshot id or see which model served a call
     after a fallback; producers must record served model ids (contract request);
   - a `pct` value read from a file is a share in [0, 1];
   - headline: `models` recorded (an explicit empty mapping declares "no model" only
     when metrics.json has `llm_calls`), prompt versions recorded;
   - `mean`: every run carries a run seed (the generator seed does not count).
3. **Selection is never by value, and fails closed.** `single`: the newest qualifying
   run by `run_at`. `mean`: runs are grouped by their whole config minus seeds, run_at,
   platform and python (paths normalised); the newest group is taken, one run per seed;
   a group mixing one-folder-per-seed and multi-seed folders is refused. Then:
   - a candidate newer than the selection that fails the checks refuses the macro;
   - an older qualifying run with the same configuration and seed but a different
     value refuses the macro (the run is not reproducible);
   - headline: fewer than three distinct run seeds (1, 1.0 and "1" are one seed)
     refuses the macro, and a headline comparison needs the same seed set on both sides;
   - superseded runs and their values, and the per-run values behind a mean (min, max)
     are written to numbers.json.
4. **Comparisons.** A derived macro, and a figure, is refused unless all its source runs
   agree on the whole config except `differ` (for H1: strategy, engine, linker; for H3:
   linker, linker details, models, prompt versions, typed; for H4: track, data,
   pair count, provenances — the harness keeps the pair file in a nested `data` block).
   A refused input refuses the derived macro. Draft figure files carry DRAFT in their
   header, title and CSV label column.
5. **Outputs** (`python -m paper.numbers`, into docs/paper/generated/, deterministic):
   `numbers.tex` (`\rnum{key}` through `\csname rnum@key\endcsname` defined with
   `\newcommand`; an unknown key prints `??key` in bold via `\detokenize`),
   `numbers.json`, `numbers.md`, and per figure a CSV, a pgfplots `.dat` (`nan` when
   refused) and a hand-written SVG. `--check` exits 1 when the files are stale;
   `--strict` exits 1 while any macro is refused (the camera-ready gate).
6. **Markdown references.** `{{num:key}}` in outlines; `value<!--num:key-->` where a
   document shows the value, checked by the I8 test (ADR-0111).
7. **Scripted-oracle replays are their own namespace.** `oracle.v0.*` reads only runs
   whose resolver starts with "scripted oracle", split all: a sanity check of write and
   ripple semantics that supports no claim and can never be replaced by, or compared
   with, an LLM-resolver run.
8. **Provisional readings, open until the Phase 3 baseline ADR** (each is a registry
   edit, never a typed number): headline memory metrics read v0 split `test`; H1
   "accuracy" is ADR-0063's update accuracy and H1 "cost" is resolver calls per ripple,
   with tokens and USD ratios beside it; the main ripple runs use the trained linker;
   H2 compares with append-only ("standard memory retrieval" may mean Mem0-style); H3
   and H4 are untyped F1 differences in points on silver labels, with typed F1, the
   scenario-provenance F1 (the rule linker is otherwise scored on its own labels), the
   strict split and hand-check agreement reported beside them; whether docs/04's
   "seeds" are run seeds or generator seeds (run seeds today; a deterministic harness
   meets the gate trivially).

## Alternatives considered
- **Copy numbers by hand with a citation comment** — nothing stops a stale copy and
  nothing enforces seeds or pinned models. Lost on I8.
- **Allow uncommitted runs outside headline numbers** — convenient today, but such a run
  cannot be reproduced once the tree moves (the two v0 append_only runs of 2026-10-19
  report different `checks_failed` for one configuration). Lost; kept as the `--draft`
  view.
- **One TeX command per macro with a mangled name** — digits are illegal in TeX command
  names and the mangling breaks one name across Markdown, JSON and TeX. Lost.
- **siunitx `\num`** — a LaTeX package choice the author has not made. Lost.
- **Pick the best run among repeats, or pin an exact folder per macro** — the first
  inflates numbers; the second needs an edit per re-run and invites hand-picking. Lost
  to "newest, fail closed, superseded listed".
- **An allow-list of config fields for consistency** — fits one producer's config shape
  and silently ignores new fields (pair file, budget). Lost to "whole config minus
  volatile fields".
- **matplotlib or a LaTeX toolchain for figures** — new dependencies (none allowed in
  wave B). Lost; data files plus a hand-written SVG.

## Consequences
- 126 macros registered; with today's results/ all are refused by default (every run is
  uncommitted); `--draft` renders the non-headline scripted-oracle counts, refuses the
  ones whose repeats disagree, and refuses the oracle figure because its rows come from
  different code versions.
- Producers must write what the registry reads: bench.run `memory_metrics` as an
  object, real `llm_calls` and served models, an `ablation` and a `linker` config key;
  the linker harness top-level `models`, `prompt_versions`, `seeds` and a cost per pair;
  a pilot season folder. Contract requests in docs/plans/parallel-execution/ws-17.md.
- The linker harness already records `models`, `prompt_versions`, `seeds.run_seed`,
  `typed` and a nested `data` block (WS-14); a cost per pair and served model ids are
  still missing.

## Revisit if
The Phase 3 baseline ADR fixes H1–H4 metrics, splits, comparators or seed semantics
differently; the author adopts a LaTeX template with its own number macros; or a run
format with per-seed sub-folders replaces one folder per seed.
