# ADR-0063: Metric definitions for RippleBench v0 (interfaces; bodies are [human])
Status: Accepted under the autonomous mandate · Date: 2026-10-19 (WS-7)

## Context
docs/04-evaluation.md lists the metric families and leaves open what "accuracy" in
H1 means. docs/05-roadmap.md marks "[human] Metric functions" as the author's Phase 3
task. The author needs exact definitions to implement against, and the bench needs
them fixed before any number is published (ADR-0012, I8).

## Decision
bench/metrics.py fixes the signatures and definitions; the bodies raise
NotImplementedError(TODO(human)); tests/scenarios/test_bench_metrics.py holds worked
examples (xfail strict) and docs/learning/bench.md the hand computation.

Over the replay trace (ADR-0062), for every event t ≥ 1 and every gold target:
before = state at t-1, observed = state at t, *should change* = gold(t) is not
satisfied by before, *moved* = observed ≠ before.
- correct_updates = #(should change ∧ observed satisfies gold).
- stale_kept = #(should change ∧ not moved).
- wrongful_changes (over-correction) = #(should stay ∧ moved).
- The remainder, should change ∧ moved ∧ not matching gold, is a wrong update and is
  reported as `should_change − correct − stale_kept` in the report, not as a function.
- questions_asked = #ASK decisions across the scenario's ChangeEvents; "needed" is
  gold status PENDING_USER at that event (ratio derived in the report).
- stale_retrieval_rate(retrieved, stale_ids) = unflagged results whose id is
  gold-stale / all results (I1: a flagged result counts as warned).
- stale_recommendation_rate(snapshots) = unflagged (event, recommendation) pairs
  resting on a gold-stale belief / all pairs, seed snapshot excluded.
- time_to_consistency = per should-change target, events (and simulated days) until
  observed satisfies gold(t); None when a newer gold for the target arrives first or
  the trace ends; report the records and the never-converged share.
- cost_per_ripple = resolver calls / ChangeEvents.
- Proposed H1 "accuracy" := correct_updates / #should-change targets (update
  accuracy), with stale_kept and wrongful_changes reported beside it. The author
  may override this in the Phase 3 baseline ADR; until then it is the collaborator's
  reading, flagged as such.

## Alternatives considered
- Per-scenario pass rate as the headline — already reported, but it hides partial
  convergence and treats a 1-check and a 10-check scenario alike. Kept as a
  secondary number.
- Counting over memories rather than gold targets — would reward strategies for
  touching memories no gold names. Lost; gold targets are the labelled set.
- Defining TTC in wall-clock seconds — meaningless under FakeClock; events and
  simulated days are what a student experiences.

## Consequences
- Baselines score by the same code paths as Ripple (eval-auditor item 2).
- Until the author implements the bodies every results/ run reports memory metrics as
  "TBD (pending run)"; the raw traces are there for the implementation to be checked
  against.
- Changing a definition later means a new ADR and re-running every published number.

## Revisit if
The Phase 3 baseline ADR chooses a different H1 metric, or LLM-judge scores need a
place beside these automatic ones (docs/04 protocol).
