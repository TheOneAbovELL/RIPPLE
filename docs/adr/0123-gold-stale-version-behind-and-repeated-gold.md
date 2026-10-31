# ADR-0123: A row a version behind gold is stale; a repeated gold keeps the TTC window open
Status: Accepted under the autonomous mandate · Date: 2026-10-31 (WS-18)
Amends the wording of three definitions written under ADR-0063 (in bench/metrics.py
docstrings); ADR-0063 itself is not edited. Found by the code-reviewer on WS-18's diff,
before any number was published.

## Context
ADR-0063 left "gold-stale" undefined; bench/metrics.py's docstrings (written with it)
said a row is gold-stale when gold is RETIRED or deleted, or gold's content differs
from the row's. Much of the generated gold pins a derived belief's new version without
its text: `availability@latest: {status: VALID, version: 2}` in jobs_v0 exam_block and
accepted_offer, and the matching v1 families. Under that wording, append_only's
untouched v1 row is never stale, so both stale rates (and H2's gap) were understated
for every strategy that leaves a belief behind. Two smaller gaps: a recommendation of an
opening gold says is retired was not stale unless something *below* it was, and a later
event repeating the same gold for a target closed its time-to-consistency window, so a
belief that caught up at that event scored "never".

## Decision
1. A row is **gold-stale** when gold for the target that addresses it is RETIRED or
   deleted, names a content the row does not hold, **or names a version newer than the
   row's** (`stale_ids_at`). A row *ahead* of gold's version is over-correction
   (wrongful_changes), not staleness.
2. A recommendation is stale when **its opening** or any belief in `based_on` is
   gold-stale (and it is shown unflagged).
3. Time to consistency: the window for a target closes at a later event only when that
   event's gold for the target **differs** from gold(t). A repeat leaves it open; the
   later event still opens its own record when the target had to change before it.
4. `questions_needed` counts one question per (event, row), so gold naming "x" and
   "x@latest" on one row counts once.

## Alternatives considered
- **Keep the docstring wording and caveat H2** — honest but measures less than the gold
  labels say; every strategy that leaves an old version behind gets credit for it. Lost.
- **Require gold to always carry content** — would need every generator and the smoke
  scenarios rewritten and re-hashed, for the same information the version already gives.
  Lost.
- **Close the TTC window on any later gold** (the old wording's literal reading) — makes
  "never converged" depend on whether a scenario author restated an expectation. Lost.

## Consequences
- No published number changes: the bench had written no memory metrics before this.
- The worked example's numbers (docs/learning/bench.md) are unchanged; edge-case tests
  pin each new clause.
- Any later change to these clauses means re-running every stale-rate and TTC number.

## Revisit if
Gold starts carrying versions for reasons other than "a new version must exist" (for
example pinning a version that must *not* be superseded), or real-resolver runs show
version numbers drifting for reasons gold does not model.
