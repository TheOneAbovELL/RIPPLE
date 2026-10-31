# Proposal 0003: Time-to-consistency as an action-level metric
Status: proposed · Date: 2026-10-19 · Tier B

## Problem
docs/04-evaluation.md measures stale recommendations as a rate per event. It does not
capture how long a stale belief survives, which is what a student experiences: a wrong
eligibility fixed at the next event is a nuisance; one that survives a deadline is a
missed job. Existing benchmarks (STALE, RECON) score single questions, not persistence
over time.

## Proposed change
1. **Replay harness** in bench/: after every event of a jobs-track scenario, run the
   deterministic ranking layer (eligibility + fit + urgency) and record the recommended
   set and each belief's state.
2. **Time-to-consistency (TTC):** for each belief that the gold labels say should change
   at event t, the number of events (and simulated days) until the system's state
   matches gold. Report the distribution and the share that never converge.
3. **Stale-action window:** events during which a recommendation was shown that gold
   says was stale, summed per scenario.

## Rationale
A single intuitive number for C2 that reviewers can compare across baselines.
Append-only has infinite TTC; newest-wins has TTC 0 for the direct fact and infinite
for its dependents, which is exactly the gap Ripple claims to close.

## Alternatives
- Rate-only metrics — already planned; keep them, TTC is additive.
- LLM judge on transcripts — subjective and costly; keep as a secondary check.

## Cost
Harness ~200 lines on top of the planned bench runner; the metric functions are [human].

## Risks
- Needs per-event gold states, which the jobs track already promises.
- Changes the evaluation protocol (docs/04) → ADR, and eval-auditor sign-off.

## How we measure it
It is the measurement. Validate on the Phase 1 smoke suite (10 scenarios) before v0.

## Recommendation
Do now at protocol level (define it in docs/04 before RippleBench v0); implement the
harness in Phase 3.
