# ADR-0102: Finance link pairs for H4 come from the finance_v1 scenarios, test split only
Status: Accepted under the autonomous mandate · Date: 2026-10-31 (WS-15, wave B)

## Context
H4: the link finder transfers to finance with a modest drop. WS-14's harness scores any
`Linker` over a C5 pair file (bench/linkpairs.py, coordinator-owned). The finance track
must therefore ship pairs in that format, and none may be usable for training. Labels
must be trustworthy without a human pass, since the 300-pair hand check (ADR-0009) is
the author's and covers the jobs track.

## Decision
1. `bench/generate_finance.py` writes `bench/data/finance_v1/pairs.jsonl` with
   `write_pairs`; the manifest records its sha256 under `extra_files` and
   `--check` compares it byte for byte with a fresh generation.
2. Every pair: `split = Split.TEST`, `track = finance_v1`, `domain = finance`,
   `provenance = SCENARIO`, persona and template from the scenario, memories as text plus
   structure (no ids), `pair_id = finance_v1:<scenario>:<parent>><dependent>`.
3. Candidates are every ordered pair of memories within one scenario, including
   memories a `new` event adds with its links.
   - positive: a direct link parent -> dependent written in the scenario, with its type
     and the class from `finance_registry()`;
   - negative: no direct link; a reversed edge stays in, marked `note: reversed edge`,
     so direction is scored; two facts about the same subject and attribute (a
     contradiction, which the change detector handles) stay in, marked
     `note: same structured key`;
   - left out: a pair whose dependent is reachable from the parent only through other
     links. A correct linker writes the direct edges, but labelling an indirect
     dependency "no link" would punish a linker for a true dependency.
4. **One pair per distinct text pair.** Templates reuse background memories (another
   company's margin and thesis), so the same (parent, dependent) texts recur across a
   persona's scenarios. The file keeps each text pair once (the smallest pair_id), so
   template overlap does not weight the score; two copies with different labels are
   refused at generation.
5. Seed 20261031, 5 personas: the counts are data facts in pairs.jsonl and the manifest.

## Alternatives considered
- Negatives sampled across scenarios of the same persona — more and harder negatives,
  but the memories of two scenarios were never designed to be unrelated, so some labels
  would be guesses. Lost for v1; within-scenario pairs are fully determined.
- Rule (structure-derived) positives as for jobs (proposal 0002) — the finance adapter
  has no rules (ADR-0100). Not applicable.
- Labelling indirect pairs as links — inflates positives with edges no annotator would
  write directly. Lost.

## Consequences
- The class balance (positives vs negatives) is a property of the templates, so it must
  be reported beside any H4 number; it is not a sampled ratio.
- Finance persona names, company names, tickers and leaders appear in no jobs or news
  scenario file and no `training/data/*.jsonl` file (tested), so nothing in a
  jobs-trained linker has seen this text.
- No human has checked these labels yet; before an H4 number is quoted, a hand-checked
  sample (the ADR-0009 protocol, WS-14's training/handcheck.py) should be reported
  beside it.
- WS-14 can score finance with the same harness and per-provenance breakdown.

## Revisit if
Curated real finance theses exist, or the H4 ADR (Phase 3 baseline ADR) fixes a
different negative-sampling protocol for the jobs pairs that finance must match.
