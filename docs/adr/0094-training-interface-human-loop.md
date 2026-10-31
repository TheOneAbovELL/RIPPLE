# ADR-0094: The training loop is an interface with a fixed data view; the loop is the author's
Status: Accepted under the autonomous mandate · Date: 2026-10-31 (WS-14)
Builds on ADR-0009; roadmap Phase 4 "[human] Training loop and evaluation".

## Context
The training loop is a [human] task. Its inputs and outputs still have to be fixed
now so the evaluation harness, the Linker protocol and tests can be written against
them, and so the loop cannot quietly train on the gold set or on test pairs.

## Decision
1. `training/train.py` owns the data view: `training_examples` returns train-split
   pairs of the configured provenances (default SCENARIO and RULE; HUMAN pairs are the
   gold set and stay out unless a run opts in), refusing unregistered link types;
   `label_space` = every registered link type plus "none".
2. `TrainConfig` (pairs file, output dir, base model, seed, epochs, learning rate,
   batch size, max length, provenances), `TrainedArtifact` (model dir, label space,
   train pair file sha256, seed), `train()` and `TrainedLinker` (`load`, `propose`
   under the Linker protocol, created_by MODEL, both directions scored) are
   interfaces whose bodies raise NotImplementedError("TODO(human): roadmap Phase 4
   '[human] Training loop and evaluation'").
3. Two strict xfail tests state the contract; `training.evaluate --linker trained`
   reports "not runnable" until then.
4. No model library is imported; PyTorch and Hugging Face need their dependency ADR
   (the CLAUDE.md stack already names them) before the author's first import.

## Alternatives considered
- Writing the loop — it is the author's task by the roadmap.
- No interface until the loop exists — the harness would be untested against the
  trained linker, and the train/test boundary would be the loop's to get right.

## Consequences
The author implements two functions and one class against fixed types and tests; the
recipe in docs/learning/link-finder-data.md lists the steps.

## Revisit if
The author prefers another shape (for example a scoring function separate from the
Linker); amend this ADR.
