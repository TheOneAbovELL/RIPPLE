# ADR-0062: Time-to-consistency replay harness with per-event snapshots
Status: Accepted under the autonomous mandate · Date: 2026-10-19 (WS-7; from proposal 0003)

## Context
docs/proposals/0003-time-to-consistency.md: rate metrics do not say how long a stale
belief survives. It proposes a replay harness that, after every event, records each
belief's state and the recommended set, so time-to-consistency (TTC) and the
stale-action window can be computed. The metric functions are [human] (Phase 3); the
harness is not.

## Decision
1. The scenario runner records a snapshot after seeding (index 0) and after every
   event: for each alias the root row and the latest version (id, status, version,
   content), the gold expectations of that event, the recommendation set, cumulative
   resolver calls, open questions and the simulated day. Types live in
   bench/replay.py; `ReplayTrace.to_dict()` is written by bench/run.py to
   results/<run>/snapshots/<scenario>.json.
2. The runner's own gold checks read the same snapshot (`GoldState.mismatches`), so
   the pass/fail report and the metrics computed later cannot disagree about what
   the system held.
3. `ActionLayer` is the bench's name for contract C1 `RecommendationSource`
   (same signature). Until the jobs adapter's ranking exists, `StubActionLayer`
   projects memory state onto recommendations with one documented rule: every VALID
   opening is recommended unless a non-retired dependent reached through an
   `eligibility_of` link starts with "not "; it is flagged when anything below it is
   SUSPECT or PENDING_USER; fit is 1.0; order is by deadline then id. It is a
   placeholder, applied identically to every strategy.
4. Which beliefs a recommendation rests on (`based_on`) is read from the dependency
   graph by the harness, not reported by the action layer, so a real ranking later
   gets the same accounting.
5. This changes the evaluation protocol: docs/04 should list TTC and the stale-action
   window under action-level metrics (doc request in the handover; the file is not
   WS-7 owned).

## Alternatives considered
- Snapshot only memory states and derive actions later — cheaper, but then the
  action layer would be re-run outside the replay and could silently diverge from
  what was shown. Lost.
- Record the full store per event — complete, but large and not what the metrics
  read; the alias-keyed view is what gold addresses. Lost on size.
- Wait for WS-1's ranking before building the harness — blocks the harness on a
  contract-dependent workstream; the stub is swappable through the protocol.

## Consequences
- Snapshots are per alias, so memories not named in the scenario (none today) would
  be invisible to the metrics; the generator names everything.
- The stub's "not " heuristic is the one piece of content reading in the bench; it
  is replaced, not tuned.
- Traces make results/ runs larger (35 small JSON files per v0 run); raw/ stays
  gitignored for anything bigger.

## Revisit if
The adapter's ranking lands (swap the stub, keep the format), or TTC needs
per-recommendation reasons that `based_on` cannot express.
