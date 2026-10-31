# ADR-0126: Link-finder training recipe, artifact folder, and the served linker in ripple.linking.trained
Status: Accepted under the autonomous mandate · Date: 2026-10-31 (WS-19)
Amends ADR-0094 (the interface: implemented by the collaborator at the author's request
on 2026-10-31; shape changes in points 8–10). Builds on ADR-0009, ADR-0125.

## Context
ADR-0094 fixed the training interface and left the loop to the author; the author has
now asked for it to be written. The recipe in docs/learning/link-finder-data.md §8
sketches the steps; the open choices are the input encoding, class balance, epoch and
threshold choice on 200 train pairs, determinism, the saved format, and where the served
linker lives so the API can import it (the `training/` tree is not part of the package).

## Decision
1. **Input.** Each memory is `"[kind] content || subject attribute value"` (structure
   only when present), and a pair is the tokenizer's sentence pair (parent, dependent),
   so direction is visible to the encoder. One function, `memory_text`, serves training
   and serving.
2. **Model and loss.** The base encoder with a linear head over `label_space` (every
   registered type plus "none"), cross-entropy with balanced class weights over the
   classes present in the fitted examples ("none" is about three quarters); a class with
   no training pair keeps weight 1. AdamW (weight decay 0.01), linear warmup over the first tenth of
   the steps (`warmup_ratio`) then linear decay, gradient clipping at 1.0.
3. **CLI defaults** (`python -m training.train`): ModernBERT-base, 10 epochs, learning
   rate 5e-5, batch 16, max length 128. `TrainConfig`'s own defaults stay as ADR-0094
   wrote them (3 epochs, 2e-5) for callers that build one directly.
4. **Validation by persona.** `validation_personas` are held out of fitting. After every
   epoch the held-out pairs are scored in both orientations and decided exactly as the
   served linker decides (point 7); the threshold is the value on a 0.05–0.95 grid with
   the best untyped F1 (ties go to the value nearest the default threshold), and the epoch with the best
   such F1 wins (ties keep the earlier epoch); its weights are restored. A validation
   set without a gold link is refused (F1 could not choose). The runs here hold out
   `p2_harsh` and fit on `p0_jay` and `p1_dev`; the counts are in each artifact
   manifest and each results/ run's `linker_details.training`. With no validation
   persona the last epoch and threshold 0.5 are kept.
5. **Artifact folder.** `save_pretrained` weights and tokenizer plus `ripple_artifact.json`:
   format and version, label space, training pair file path and sha256, seed, threshold
   and its source, base model and the hub commit hash loaded, max length, the text
   template, the full `TrainConfig`, label counts, class weights, per-epoch history,
   chosen epoch, wall time and thread count, library versions and processor. The
   commit is read from the Hugging Face cache path (snapshots/<commit>/), since
   transformers 5 no longer sets `_commit_hash`; `--base-model-revision` pins one. Folders go
   under `training/artifacts/`; a `.gitignore` there keeps only the manifests tracked.
6. **Determinism.** Python's and torch's generators are seeded with the run seed, the
   batch order comes from a seeded `torch.Generator`, and
   `torch.use_deterministic_algorithms(True, warn_only=True)`, restored to the caller's
   setting when training ends (it is process-wide). Tested: two runs with one
   seed write byte-identical weights on the offline model. Across machines or thread
   counts results may differ; the manifest records both.
7. **Serving.** `ripple.linking.trained.TrainedLinker` scores both orientations of every
   candidate in one batch, off the event loop (`asyncio.to_thread`), and proposes at
   most one edge per candidate: the more probable direction, when its best non-"none"
   class clears the threshold, with `created_by MODEL` and that probability as
   confidence. ADR-0094 said "each direction that clears"; proposing both would write a
   two-memory dependency cycle, which no real dependency is. An exact tie between the
   directions proposes nothing, so the answer does not depend on which memory is new.
8. `TrainedLinker`, `TrainedArtifact` and `NO_LINK` move to `ripple.linking.trained`
   (the package must be importable without `training/`); `training.train` re-exports them,
   so ADR-0094's imports still work. `TrainedLinker(artifact, scorer, threshold=None)`
   takes a scorer callable, so its decision logic is tested without weights;
   `load(model_dir, threshold=None, registry=None)` uses the validated threshold unless
   one is given, and refuses a registry missing any type the model can propose.
9. `TrainingExample` gains `persona` (validation is by persona); `TrainConfig` gains
   `domain` (whose registry is the label space), `weight_decay` and `warmup_ratio`.
10. The base model name `scratch:tiny` builds a randomly initialised two-layer
    ModernBERT with a word-level tokenizer over the fitted texts: the offline test model
    (unit tests never download), and usable as a "no pretraining" ablation. The
    ADR-0094 strict xfail tests now pass on it and their markers are removed.

## Alternatives considered
- Train on all three train personas, threshold 0.5 — uses every pair, but nothing would
  choose the epoch or the threshold without touching test; lost.
- Random-item validation — breaks docs/04's split rule inside training; lost.
- Hugging Face `Trainer` — hides the loop the author has to defend, and brings
  `accelerate`; a 60-line loop is enough here; lost.
- Score one orientation and propose it — the harness and Intake both need direction; a
  model that never compares the two orientations proposes reversed edges; lost.
- Keep the linker in `training/` — the API could not import it from the installed
  package; lost.

## Consequences
- Validation uses one persona's pairs: the chosen threshold and epoch are noisy, and
  three seeds show how noisy (docs/results/link-finder.md).
- The first two artifact manifests were written before the cache-path revision
  lookup and record `base_model_revision: null`; the third records the commit.
- Weights are not tracked; a folder is rebuilt from the command in its manifest.

## Revisit if
The pair set grows enough for k-fold persona validation, or the hand-checked gold set
(ADR-0092) exists (then validate on gold pairs from train personas).
