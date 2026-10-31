# ADR-0104: check_everything applies its one wave parents first
Status: Accepted under the autonomous mandate · Date: 2026-10-31 (WS-15, wave B)
Amends ADR-0060 (check_everything's member order); ADR-0060 is not edited.

## Context
check_everything resolves every VALID memory in one wave through the core
`RippleRunner`, which applies decisions in member order. An `ask` parks only the
**VALID** descendants of the asked memory. So when a dependent comes before the memory
it depends on, the dependent is first kept (VALID again) and then parked (SUSPECT) by the
later ask; when it comes after, its own keep stands. ADR-0060 reasoned that parking is a
no-op because the one-shot wave "has already marked [the subtree] SUSPECT anyway", which
is true only in the second order. The order was `(recorded_at, id)`, and root ids are
scenario aliases, so the outcome depended on spelling: in v0 ("eligibility" before
"recommendation") the ask family fails, as WS-7 reported; in the new news track
("briefing" before "summary") the same family passed by accident.

## Decision
`CheckEverythingStrategy.run` orders members with `parents_first` over the depends_on
graph: no member precedes one of its ancestors among the members, except an ancestor
on a cycle through it (a cycle has no right order, so its members keep their given
order); members below a cycle wait for the whole cycle; otherwise the
`(recorded_at, id)` order is kept (stable). Every member therefore keeps its own decision, which is what a
graph-blind re-check does, whatever the aliases are called.

## Alternatives considered
- Keep alphabetical order and choose aliases carefully — fragile and invisible; a
  renamed alias silently changes a baseline. Lost.
- Children first (so asks always override) — would make check_everything pass the ask
  family by using the graph for its result, against the baseline's definition. Lost.
- Change RippleRunner to skip parking members of the current wave — the cleanest
  semantics, but core is coordinator-owned and frozen for this wave. Not available;
  noted for the coordinator.

## Consequences
- v0 outcomes are unchanged (its aliases already sorted parents first): the re-run
  results/2026-10-30_v0_check_everything_uncommitted_2 has per-scenario pass, failed
  checks, failure lines and resolver calls identical to
  results/2026-10-19_v0_check_everything_uncommitted_2 (30/35 passed, 5/175 checks
  failed, 144 resolver calls in both metrics.json files).
- news_v1 and finance_v1 check_everything fail the ask family like v0, so the three
  tracks agree. A test renames an alias and asserts the outcome does not move.
- check_everything now reads the graph for ordering only; its scope is still every
  VALID memory.

## Revisit if
Core stops parking same-wave members (then the order no longer matters), or a baseline
needs ordering semantics of its own.
