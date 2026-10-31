# ADR-0060: Baseline memory strategies behind one MemoryStrategy protocol
Status: Accepted under the autonomous mandate · Date: 2026-10-19 (WS-7)

## Context
docs/04-evaluation.md names four baselines (append-only, newest-wins, Mem0-style,
check-everything) and H1 compares Ripple's accuracy and cost with check-everything.
The scenario runner (bench/scenario.py) replays a timeline through `RippleRunner`.
For a comparison to be fair the baselines must see the same writes, the same scripted
resolver and the same clock, and their cost must be counted the same way (eval-auditor
checklist, item 2).

## Decision
1. A `MemoryStrategy` protocol in bench/strategies.py with `run(event)`,
   `resume(event)`, `name` and `resolver_calls`: exactly the surface the sweep and
   the answer flow use on a `RippleRunner`. The runner performs every write
   identically and hands the open ChangeEvent to the strategy.
2. Four strategies share one Store, one Resolver (wrapped in a `CountingResolver`)
   and one Clock:
   - `ripple`: the real `RippleRunner` and the human-owned `WaveEngine`.
   - `append_only`: no propagation; the version the write superseded is restored to
     VALID (recorded as a wave-0 KEEP decision, so I2 holds). Every statement stays
     retrievable: the plain-log baseline.
   - `newest_wins`: no propagation; the superseded version stays RETIRED.
   - `check_everything`: `RippleRunner` driven by a one-shot engine whose single wave
     is every VALID memory of the user except the trigger. It ignores the graph; the
     commit protocol, decisions and events are Ripple's, so the baseline is audited
     the same way (I2) and never calls an LLM from the engine (I3).
3. Expiry of temporary facts is data-model behaviour (ADR-0015) shared by all
   strategies; only ripple and check_everything propagate it. A scenario that answers
   a question a baseline never asked records that as the baseline's failure.
4. Gold expectations are the same for every strategy; the bench shows baseline
   failures rather than relaxing the gold.
5. Mem0-style stays undecided (docs/04 open question: real library and a dependency
   ADR, or a documented reimplementation). Not built here.

## Alternatives considered
- Subclass `RippleRunner` per baseline — type-checks without a cast, but couples
  baselines to the runner's private commit methods. Lost on coupling.
- Separate write paths per baseline (append_only never retiring at write time) —
  closer to a literal append-only log, but then the baselines no longer share the
  store's versioning and the comparison measures two things at once. Lost on
  fairness; the restore-after-write gives the same observable state.
- check_everything with its own apply logic (no graph anywhere, including the ask
  subtree) — purer, but duplicates ~100 lines of commit code that I2 tests cover
  once. Lost; the only graph use left is parking the subtree below an ask, which the
  one-shot wave has already marked SUSPECT anyway.

## Consequences
- `as_runner` casts a strategy to `RippleRunner` for `NightlySweep` and
  `ripple.core.answers`; a `RippleDriver` protocol in core would remove the cast
  (contract request in docs/plans/parallel-execution/ws-7.md).
- With the scripted oracle resolver, check_everything is the accuracy ceiling at the
  cost ceiling, which is exactly the reference point H1 needs; its real-resolver
  over-correction is a Phase 3 measurement.
- The baselines run today without the human engine (results/2026-10-19_v0_*).

## Revisit if
The Mem0-style baseline is decided, or a baseline needs a write path the shared
runner cannot express.
