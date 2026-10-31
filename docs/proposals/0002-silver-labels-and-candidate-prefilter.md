# Proposal 0002: Structure-derived silver labels and a candidate pre-filter for the link finder
Status: proposed · Date: 2026-10-19 · Tier B

## Problem
ADR-0009 plans thousands of LLM-labelled pairs, 300 hand-checked. LLM labels are costly
and their quality is unknown until checked. Separately, a pair classifier over all
existing memories is quadratic: a new opening against 500 memories is 500 model calls.

## Proposed change
1. **Silver labels from structure.** Where both memories carry structured fields
   (FR-2 spans, profile subject/attribute/value), links such as eligibility_of and
   criteria_from are derivable by rule. Generate those labels by rule, free and exact;
   reserve LLM labelling for hidden links (depends_on_fact between prose memories).
   Record label provenance per pair.
2. **Candidate pre-filter.** Before the classifier, keep only pairs that share a subject
   or entity, plus the top-k embedding neighbours, plus all profile facts. The
   classifier runs on that candidate set only. The pre-filter's recall is measured
   against the labelled set.
3. **Active learning from corrections.** Pilot corrections enter training with
   uncertainty sampling: pairs the model scored near 0.5 are shown first in the
   inspector.

## Rationale
Cheaper, higher-quality labels for the common link types; the LLM budget goes to the
hard cases, which is where C1's novelty lies. The pre-filter makes write-time linking
affordable at pilot scale.

## Alternatives
- LLM labels for everything — known cost, unknown quality; lost on both.
- Embedding similarity as the linker — measures similarity, not dependency (ADR-0009).
- No pre-filter, batch the classifier — still quadratic; lost at pilot scale.

## Cost
Label generator ~200 lines; pre-filter ~100 lines; measurement scripts. No new
dependency beyond the embedding model already planned (which needs its own ADR).

## Risks
- Silver labels teach the model the rules, not the hidden links; mitigated by
  stratified evaluation per label provenance.
- Pre-filter recall caps link recall (ADR-0003 revisit condition); measured.
- Changes the training-data protocol (docs/04) → needs an ADR; the eval-auditor must
  confirm no bench persona leaks into silver labels.

## How we measure it
Agreement with the 300 hand-checked pairs by provenance; linker F1 trained with vs
without silver labels; pre-filter recall and candidate-set size.

## Recommendation
Do later: Phase 4, when training-data generation starts. Decide the embedding ADR first.
