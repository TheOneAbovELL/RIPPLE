# ADR-0127: Link-finder evaluation: a transfer mode for H4, CPU cost per call, and a three-seed summary folder
Status: Accepted under the autonomous mandate · Date: 2026-10-31 (WS-19)
Amends ADR-0093 (point 6: a trained linker scored only on its own pair file). Builds on
ADR-0102 (finance pairs, test only), docs/04 (H3, H4), I8.

## Context
H4 trains on jobs and tests on finance. The harness refuses a trained linker on a pair
file other than its training file (ADR-0093), which is the right default and blocks H4.
H3 needs a cost side; metrics.json had only total wall seconds. Three training seeds give
three result folders; a report needs their mean and spread from a file, not from a
calculator (I8).

## Decision
1. A trained linker is scored on test pairs only: `--split train|all` on its own
   pair file is refused (those are pairs it fitted or validated on).
   `training.evaluate --transfer` lets it score another pair file when every selected
   pair is a test pair of a track absent from its training split, the file is not its
   own, the model's training file is present with the sha256 it was trained on, and
   no evaluated (parent, dependent) text pair equals a training pair (refused
   otherwise). Pairs sharing one text with training are counted
   in config.json's `transfer` block. When the file's gold link types are outside the
   model's label space (jobs types vs finance types), typed metrics are null and the
   report says why; untyped link detection is the H4 measure. For a trained linker,
   `seen_in_train` per gold type comes from the link types it was fitted on (the
   artifact manifest's `fit_label_counts`, so validation personas do not count).
2. Every run records `cost` in metrics.json: wall and process CPU seconds per linker call
   (CPU over all threads, `time.process_time`), total CPU seconds and the processor. For
   the trained linker this is its whole cost on CPU; for an LLM run it excludes the
   provider's side, which needs per-call usage from the LLM linker (an open request from
   WS-14). One call is one pair with one candidate (ADR-0093 consequence 2).
3. `training.summarize` reads named run folders and writes
   results/<date>_linkpairs_summary_<sha>/ (summary.json, report.md): per group of
   runs that differ only by seed (same linker, base model, pair file sha256, split,
   query side and transfer setting; a folder named twice counts once), the mean, sample standard deviation, minimum and maximum over runs of F1,
   precision, recall and typed F1, overall and per held-out cell, plus cost, each with
   the folders it came from. It computes nothing a run folder does not already hold.
4. Protocol for the link-finder report: rule linker once per track (deterministic);
   trained linker for three seeds (20261031, 20261032, 20261033) on the jobs test split
   with `--new dependent`, plus one `--new parent` run of the first seed (the trained
   linker scores both orientations, so it should not move); finance transfer for all
   three seeds. held_out=both is the primary jobs cell (WS-14 handover).

## Alternatives considered
- Retrain a finance model — that is in-domain training, not transfer; lost.
- Map jobs types onto finance types by link class for typed metrics — every finance and
  jobs type is `depends_on`, so the mapping says nothing beyond the untyped score; lost.
- Skip the text-overlap check — ADR-0102 already tests that finance names never appear in
  jobs files, but generic texts could still coincide; the check is cheap; lost.
- Report seeds as three separate tables — readable, but mean and spread must still be
  stated, and I8 wants them in a file; lost.

## Consequences
- Finance pairs have no held-out cell manifest, so a transfer run reports
  held_out=unknown for every pair; the whole file is unseen (another domain).
- The per-call cost of the trained linker depends on the machine and thread count; the
  processor and thread count travel with the number.

## Revisit if
The LLM linker reports usage per call (then H3's cost comparison can be computed), or a
candidate-set (ranking) track is added.
