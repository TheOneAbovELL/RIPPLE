# Link-finder data, training, hand check and evaluation harness (training/)
Written 2026-10-31 (WS-14); training sections added the same day (WS-19), when you
asked for the [human] training loop to be implemented. Describes only code that
exists. Results are in docs/results/link-finder.md.

## 1. What it does
`training/` turns RippleBench v0 into labelled link pairs in the C5 format
(bench/linkpairs.py), proves the train split does not leak into test, gives you a
blind 300-pair hand-check protocol, and scores any `Linker` on a pair file into
results/. `train.py` fine-tunes ModernBERT-base as a pair classifier on CPU, and
`ripple.linking.trained` serves the result behind the `Linker` protocol.

| Module | Job | Run |
|---|---|---|
| `replay.py` | static scenario replay into snapshots (versions, waves, removals) | used by jobs_pairs |
| `jobs_pairs.py` | v0 scenarios -> `training/data/jobs_v0_pairs.jsonl` + manifest | `uv run python -m training.jobs_pairs [--check]` |
| `structure_rules.py` | silver labels from structure (proposal 0002) | used by jobs_pairs |
| `leakage.py` | split and text leakage checks | used by jobs_pairs and the named test |
| `handcheck.py` | sample, blind CSV sheet + key file, agreement report, gold pairs | `... -m training.handcheck sample --out x.csv` / `report --sheet x.csv` |
| `evaluate.py` | any Linker over a pair file -> results/ | `... -m training.evaluate --linker rule\|fake_llm\|llm\|trained` |
| `train.py` | data view, the training loop, artifact folder (ADR-0126) | `... -m training.train --validation-persona p2_harsh --seed N` |
| `summarize.py` | mean and spread over run folders (ADR-0127) | `... -m training.summarize results/<a> results/<b> ...` |
| `src/ripple/linking/trained.py` | `TrainedLinker`, `memory_text`, `select_linker` | `RIPPLE_LINKER=trained` (ADR-0128) |

## 2. Why it exists
C1 (learned dependency induction) and H3 (trained linker within 5 points of the LLM
linker at a fraction of the cost) need labelled pairs, a fair split and one scorer for
every linker. ADR-0009 fixes three linkers behind one protocol and 300 hand-checked
pairs; proposal 0002 asks for structure-derived labels and results per provenance;
docs/04 forbids splitting by item. ADR-0090..0094 record the choices made here.

## 3. How it works
**Snapshots** (`replay.py`). Each scenario is replayed without the engine. The
seeded state is snapshot 0; every event gives one more snapshot. Versioning follows
docs/03: a depends_on link follows both ends to new versions, a snapshot_of link does
not (so "resume v2" -> "applied to initech with resume v1" is *not* a link, a
negative you cannot get from the seeded state alone). A change ripples in waves:
update or retire passes it on, keep or ask stops the branch, as the engine contract
says. Retire, expiry and forget drop memories from later snapshots. A test replays
all 35 v0 scenarios and checks each event's `expect` block against the replay.

**Claims.** For every ordered pair of memories in one snapshot: scenario link,
transitive-only (excluded), or no link (the scenario's link list is complete inside
the scenario). Structure rules add RULE claims, inside each snapshot and across a
Claims merge by (persona, parent, dependent). A scenario link a rule also derives
becomes RULE ("structure determines it"); the remaining scenario links are the ones
no v0 rule derives (the hidden depends_on_fact links, and some structural links the
rules miss on wording). If a rule names a different type, the scenario wins.
Contradictions are dropped and counted in the manifest's `process` block.

**Negatives and split.** Per persona, every reversed link is a negative, plus a seeded
sample of other negatives up to 3 per positive (ADR-0091). A pair is train only if its
persona and every template it was seen under are train. Then any train pair whose two
texts equal a test pair's (either order) is dropped. `leakage_problems` must return
nothing or the generator refuses to write.

**Evaluation.** Per pair: `propose(dependent, [parent])` with opaque ids ("m1",
"m2"), so the prompt never sees the persona or which side is the parent; predicted
linked if some proposal goes parent -> dependent (most confident wins the type);
invalid model output is an abstention. Confusion counts, P/R/F1 and typed versions,
overall, per provenance, per held-out cell (`both` = persona and template unseen,
the H3 cell), false positives per negative kind, recall per gold type, into
results/<date>_linkpairs_<track>_<linker>_<sha>/.

**Hand check.** 300 pairs stratified by split × provenance × label (min 10 each),
shuffled, written to a CSV that hides the silver label and the pair_id (a key file
beside it maps rows to pairs). You fill `human_link_type`, `sure`, `labeller`. The
report re-draws the sample to prove the sheet is it, then writes agreement, Cohen's
kappa and `gold_pairs.jsonl` (HUMAN provenance) to results/.

## 4. Worked example
`cgpa_rise__p0_jay`: seeded CGPA 7.2, Umbrella cutoff 7.4, "not eligible for umbrella
(7.2 < 7.4)", "search openings with cutoff <= 7.2". Snapshot 0 gives three links;
the rules derive all three (eligibility from the cutoff opening, eligibility from
CGPA because Umbrella states a cutoff, criteria from the CGPA value), so they are
RULE pairs. The CGPA update gives snapshot 1 with "CGPA is 7.6" -> "eligible for
umbrella (7.6 >= 7.4)": three more RULE pairs. Their reversals are negatives; the
template is a test template, so all are test.

## 5. Trade-offs
- Static replay re-implements a slice of versioning and the wave rule; the
  expectation test keeps it honest on v0. If docs/03 or the engine contract
  changes, `training/replay.py` must follow.
- Rules read v0 surface forms; they say nothing about real JD text.
- The v0 pair set is small: it tests the protocol, not a model.
- Fixed 1:3 negatives makes precision depend on a chosen prevalence (recorded per
  split in the manifest).
- Decontamination removes exact text pairs only: many test pairs still share one
  text with train (counted in the manifest). Read held_out=both for H3.

## 6. Failure modes and tests (tests/training/)
- Leakage: `test_no_test_persona_template_or_text_leaks_into_train` (named test) plus
  unit tests per leak kind; removing decontamination makes the generator refuse.
- Replay: `test_replay_agrees_with_every_v0_scenario_expectation` (one case per v0
  scenario; it fails broadly when rippling is disabled), ask stops a branch, structure carries over.
- Drift: `test_jobs_pairs_checked_in_files_equal_a_fresh_generation`, manifest hash.
- Versioning: snapshot_of stays on the old resume, retire/expiry/forget drop memories.
- Labels: reversed links kept, transitive pairs never negatives, every test seeded
  link present, each conflict rule in `resolve` has a test.
- Harness: direction, opaque ids, abstention, null precision without negatives,
  folders never overwritten, the fake-LLM run labelled a plumbing check, a trained
  linker refused on another pair file.
- Hand check: allocation exact, sheet blind, key verified, half-filled and duplicated
  rows refused, BOM accepted, kappa value.

## 7. Interview questions
1. Why split by persona and template and then *also* decontaminate by text?
2. Why are RULE pairs positives only, and what does that do to per-provenance precision?
3. Why is (resume v2, application sent with v1) a negative but (resume v2, tailoring) a link?
4. Why keep every reversed link as a negative instead of sampling them?
5. When is Cohen's kappa undefined, and why report raw agreement too?

## 8. Training recipe (implemented; ADR-0125, ADR-0126, ADR-0127)
The steps below were the recipe left for you; each is now built as noted in
brackets. Read `training/train.py` top to bottom: it is one function.

Implement `training/train.py`: `train`, `TrainedLinker.load`, `TrainedLinker.propose`.
1. ADR for the model dependency (PyTorch + transformers, exact pins) and the base
   model (ADR-0009: ModernBERT or DeBERTa-v3 small). [ADR-0125: ModernBERT-base,
   torch 2.15.0 CPU + transformers 5.22.1 in the `linkfinder` group; DeBERTa-v3-small
   needed sentencepiece or tiktoken on top.]
2. Data: `training_examples(read_pairs(...), config, jobs_registry())` — train split,
   SCENARIO + RULE. Input text: one fixed template for both memories, for example
   `"[kind] content || subject attribute value"` for parent then dependent, encoded as
   a sentence pair so direction is visible. Labels: `label_space(registry)`.
   [`memory_text` in ripple.linking.trained, shared by training and serving.]
3. Model: encoder + linear head over the label space, cross-entropy; consider class
   weights, since "none" is about three quarters of train (`prevalence_by_split` in
   the manifest). [Balanced weights over the classes present; AdamW, warmup, decay.]
4. Validation: no test pairs. Hold out one *train persona* (`validation_personas` in
   `TrainConfig`, not random items) for early stopping, so the split rule holds
   inside training too. Fix the decision threshold there and record it. [p2_harsh;
   best epoch and threshold by untyped F1 on a fixed grid, decided as served.]
5. Determinism: seed Python, NumPy and torch; record seed, base model, label space and
   the pair file sha256 in `TrainedArtifact` and in the model folder.
   [`ripple_artifact.json`; byte-identical weights for one seed, tested.]
6. `propose`: score (candidate, memory) and (memory, candidate) for each candidate;
   propose a direction when its best non-"none" probability clears `threshold`, with
   `LinkCreator.MODEL` and that probability as confidence. [Built, with one change:
   at most one edge per candidate, the more probable direction, so no two-memory cycle.]
7. Score: `uv run python -m training.evaluate --linker trained --model <dir>`; compare
   with `--linker rule` and a real `--linker llm` run on the same pair file, both
   `--new` settings, three seeds, reading held_out=both (H3 needs both linkers, plus
   cost). Remove the two xfail markers in tests/training/test_train_interface.py.
   [Done for rule and trained, three seeds, plus the finance transfer with
   `--transfer`; the LLM run waits for a key. Markers removed.]

**Offline test model.** `--base-model scratch:tiny` builds a random two-layer
ModernBERT and a word tokenizer from the training texts. The tests train it in
seconds without a download. It is plumbing, not a link finder.

**Interview questions on training.**
1. Why choose the threshold on a held-out *persona* instead of on random train pairs?
2. Why score both orientations and keep only the more probable one?
3. With 128 fitted pairs, what does the seed spread tell you, and what does it not?
4. Why does the finance transfer report only untyped metrics?

## 9. Exercise
Add a rule `fit_from_skill` (skill fact -> "fit for <company>" when that company's
opening requires the skill). On v0 it would fire on no pair: why? What would v1 need?
