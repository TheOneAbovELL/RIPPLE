# ADR-0093: Link finders are scored per pair with opaque ids, stratified by provenance and held-out cell
Status: Accepted under the autonomous mandate · Date: 2026-10-31 (WS-14)
Builds on ADR-0009, ADR-0060 (bench folder naming), ADR-0061 (held_out cells),
ADR-0090, ADR-0091, docs/04 protocol, I8.

## Context
H3 compares a trained linker with the LLM linker; proposal 0002 asks for results by
label provenance. The `Linker` protocol takes a new memory and candidates and may
propose edges either way. A harness must fix how a pair becomes a call and how a
proposal becomes a prediction, or two linkers are not comparable.

## Decision
1. Per pair, one call: `propose(dependent, [parent])` (the usual write order: a
   belief is written after the facts it rests on). `--new parent` flips it and is
   recorded in config.json.
2. Memory ids are opaque ("m1"/"m2", which one is the parent decided by a seeded coin
   per pair, `--seed`, recorded as `seeds.run_seed`): the LLM prompt shows ids, so an
   id must name neither the persona nor the side.
3. Prediction: a proposal parent -> dependent; with several, the most confident
   one's type. A proposal dependent -> parent counts for the reversed pair only and
   is reported as `reversed_proposals`. Invalid model output
   (LLMOutputInvalidError) is an abstention (no prediction), counted in
   `abstentions`, the same rule for every linker.
4. Metrics: confusion counts (tp, fp, fn, tn) and typed tp; precision, recall, F1;
   typed precision, recall, F1 (a tp with the wrong type is a typed miss).
   Precision and recall are null when their denominator is zero; F1 is 0 when gold
   links exist and none was found. In a stratum without gold negatives (every RULE
   pair is a positive) precision and F1 are null. Typed metrics are null for a
   linker that proposes one fixed type (`typed: false`, the rule linker). Strata:
   overall, per provenance, per held-out cell (none / persona / template / both,
   from the test personas and templates the pair manifest records; "both" is the
   strict cell), false-positive rate per negative kind ("reversed link", "same
   scenario, no link"), recall per gold link type with `seen_in_train`, and a gold ->
   predicted type table.
5. Output: results/<date>_linkpairs_<track>_<linker>_<sha>/ with config.json (linker
   and details, `models` and `prompt_versions` as mappings ({} when none), seeds,
   split, query side, `data` = pair file and manifest paths and sha256, generator,
   pair seed, negative ratio and source block), metrics.json (with `linker_calls`
   and `llm_calls`), predictions.jsonl, report.md. The linker name is part of the
   folder name, as the strategy is for bench runs (ADR-0060); a same-day folder is
   never overwritten.
6. Baselines offline: `rule` (RuleLinker) and `fake_llm` (LLMLinker through the real
   router on FakeLLM scripted to propose nothing), the latter flagged
   `plumbing_only` in config and metrics and in bold in the report: it measures no
   model. `llm` runs the configured provider and records the fallback chain and the
   config file's sha256 (not run offline). `trained` loads the author's model,
   refuses to score a pair file other than the one it was trained on, and reports
   "not runnable" until it exists.

## Alternatives considered
- Score both orientations and take either — hides direction errors; lost.
- All candidates of a scenario per call (ranking) — closer to Intake, but couples
  the score to scenario size and to the pre-filter that does not exist yet; a later
  ranking track, not a replacement.
- Ids derived from pair_id — readable traces, but they leak the persona and the side
  into the LLM prompt; lost.
- Report only overall F1 — proposal 0002's question is per provenance, and H3 needs
  the strict held-out cell; lost.

## Consequences
- The headline cell for H3 is held_out=both; on v0 it is small (a handful of
  scenarios), so v0 cannot settle H3 and confidence intervals over personas are
  needed before any H3 claim.
- One call per pair with one candidate overstates the LLM linker's cost per pair
  against write-time use (one call per new memory with k candidates). H3's cost side
  needs a candidate-set measurement or cost per new memory; recorded as open.
- The orientation changes rule and LLM results but not a linker that scores both
  directions; an H3 run reports both `--new` settings.
- Numbers in the results/ folders written so far come from an uncommitted tree:
  TBD (pending a committed run) for anything cited.

## Revisit if
The pre-filter lands (add a ranking track over candidate sets), or the LLM linker
exposes per-call usage (then cost and the model actually served go into metrics.json).
