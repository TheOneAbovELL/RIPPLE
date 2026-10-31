# ADR-0091: Negatives at 3 per positive with every reversed link kept; train decontaminated against test
Status: Accepted under the autonomous mandate · Date: 2026-10-31 (WS-14)
Builds on ADR-0090, ADR-0061 (split by persona and template), docs/04 protocol.

## Context
Inside a v0 scenario almost every ordered pair is "no link" (the candidate negatives
outnumber the positives several times over: `negatives_available` in
training/data/jobs_v0_pairs.manifest.json). A pair classifier needs negatives, but how many sets the
prevalence that precision depends on, and which ones decides what the model learns.
Separately, v0 personas share template text ("no summer offer accepted" ->
"available for summer 2027" is identical for all five), so a persona/template split
alone still puts identical pairs in train and test.

## Decision
1. Negatives are same-scenario ordered pairs with no link (ADR-0090), never a pair
   linked anywhere in the persona and never a transitive ancestor.
2. Per persona: keep **every reversed positive** (the pair (dependent, parent) of a
   link); fill up to **3 negatives per positive** with a seeded sample
   (`random.Random(f"{seed}:negatives:{persona}")`, default seed 20261031) of the
   other negatives. The ratio and counts are in the pair manifest.
3. After the split, a **train** pair whose unordered texts {parent, dependent} equal
   a test pair's is dropped (`train_dropped_text_in_test` in the manifest); test is
   never edited. The generator refuses to write a set that fails
   `training.leakage.leakage_problems`.

Why 3: the write-time setting proposal 0002 plans is a pre-filtered candidate set
(shared subject or entity, top-k neighbours), where most candidates are plausible,
so prevalence is far above the full quadratic set's; 1:3 makes positives about a
quarter of the data before decontamination (the manifest's `prevalence_by_split` has
the exact share per split), enough for a small classifier to see each link type, and keeps the full v0
negative pool larger than the sample so the seed matters. Reversed links are kept
whole because direction is the error a pair classifier makes most cheaply and the
engine's behaviour depends on it.

## Alternatives considered
- All negatives (the whole pool, larger on larger tracks) — prevalence then tracks
  scenario size, not a deployment setting; lost.
- 1:1 — inflates precision against any realistic candidate set; lost.
- Random negatives only — reversed links would appear by chance; lost.
- Decontaminating test instead of train — would make the evaluation set depend on
  what is trained on; lost (standard practice removes test items from training).
- Ordered-text decontamination — a train (b, a) still teaches the texts of a test
  (a, b); lost for the unordered key.

## Consequences
- Precision on these files is at the prevalence the manifest records per split and
  is not comparable with a run on another ratio; the evaluation config records the
  pair file and manifest hashes.
- Decontamination removes train pairs on v0 (`train_dropped_text_in_test` in the
  manifest); train is small (ADR-0090).
- The same rule (reversed edges kept, transitive ancestors excluded) is what WS-15
  uses for finance pairs, so one harness reads both.
- Decontamination removes only exact text pairs. Test pairs that share one text with
  train (a persona's seeded CGPA appears in train and test templates) and identical
  test pairs across personas remain; the manifest counts both
  (`test_pairs_sharing_a_text_with_train`, `test_duplicate_texts`) and the harness
  reports the strict held_out=both cell separately (ADR-0093).

## Revisit if
The pre-filter is built and its candidate sets give a measured prevalence; then the
ratio should match it.
