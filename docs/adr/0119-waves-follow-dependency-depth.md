# ADR-0119: A memory is resolved after every affected parent of it (waves follow depth)
Status: Accepted under the autonomous mandate · Date: 2026-10-31 · Amends ADR-0013
(contract rules 1 and 3 of the WaveEngine)

## Context
ADR-0013's engine emitted every direct dependent of the trigger in wave 1 and never
revisited a memory. A code review of the implementation found the case this gets wrong:
with cgpa -> eligibility -> recommendation and also cgpa -> recommendation, wave 1 holds
both the eligibility and the recommendation. The recommendation is decided against the
eligibility's *old* value; when the eligibility then updates, the recommendation is
already visited and is never re-checked. That leaves exactly the stale dependent Ripple
exists to prevent. Today's jobs graphs are one level deep, so the product was not hit,
but deeper graphs (the v1 tracks, any future domain) can be.

## Decision
1. `first_wave` computes the affected set (everything reachable from the seeds along
   propagating links) and levels each member by its longest path from a seed (Kahn's
   order inside the set; members on a cycle get one more than their deepest levelled
   parent, in discovery order).
2. A member is *due* once one of its parents changed: a seed, or a resolved member
   whose outcome changed (through its id or its new version's id). Each wave is the due,
   unresolved members of the lowest level that has any. A keep or ask halts only its own
   branch: a member with another changed parent is still due.
3. Every memory is still resolved at most once (cycle safety); a dependent reached only
   through a new version's copied links is scheduled one level below its parent. Wave
   numbers count emitted waves; `max_depth` and `truncated` are unchanged.
4. The engine stays pure, deterministic and LLM-free (I3).

## Alternatives considered
- Re-emit a visited memory when a parent changes after it was resolved (with a budget
  per memory): correct in the end, but it resolves the same memory twice, paying a model
  call twice and recording two decisions for one change.
- Keep the old rule and document the limitation: cheapest, but it leaves a known stale
  belief in the core promise of the project.
- Full closure in one wave: re-checks branches whose parent turned out unchanged, the
  over-correction and cost ADR-0013 rejected.

## Consequences
- A memory waits for every affected parent, so its resolver sees their decided values.
- Waves can be fewer and deeper; cost is unchanged or lower (no double resolution).
- tests/core/test_engine.py: three new contract tests (shortcut path, keep on the middle
  parent, an empty level skipped); all earlier contract tests, the scenario suite and the
  v1 tests pass unchanged. The benchmark grid is re-run on this code.
