# ADR-0034: CGPA is compared with a cutoff only on one scale; otherwise the rules defer
Status: Accepted under the autonomous mandate · Date: 2026-10-26 · Amends ADR-0031
(points 1 and 5) · IDEAS 9 · checkpoint C3

## Context
`ProfileAttribute.CGPA_SCALE` (4 or 10; none recorded means 10) was stored by the jobs
adapter but read nowhere, so a 4-point student's 3.6 was compared with a ten-point JD
cutoff of 7.8 and the student was told "not eligible". JD cutoffs are ten-point only:
the JD parser drops numbers above `CGPA_SCALE_MAX` (10), `schemas.parse_cgpa` accepts
0..10, and no opening attribute records another scale. No conversion between 4-point
GPA and 10-point CGPA is standard across Indian universities.

## Decision
1. `ProfileView` carries the latest live `cgpa_scale` fact; `cgpa_scale_value` is 10
   without one; `cgpa_on_cutoff_scale` says whether the CGPA compares with a cutoff.
2. `compute_eligibility` returns None when the opening states a cutoff and the CGPA is
   not on the cutoff's scale: no belief is derived rather than a guessed one. When it
   does compare, the scale fact (if any) is among the belief's parents, so changing the
   scale ripples to it.
3. `EligibilityRule` also declines in that case (it reads the scale among its parents),
   and the resolver chain falls back to the LLM resolver, which can ask (ADR-0019).
   Without a cutoff, or on the ten-point scale, decisions are unchanged.
4. `compute_criteria` drops the `cgpa_cutoff <= x` clause off the cutoff scale, so the
   Scout does not filter on a comparison it cannot make; the scale fact is a parent of
   the criteria either way.
5. ADR-0031 point 5 gains two rule links: a cgpa_scale fact links `eligibility_of` to
   every live eligibility belief and `criteria_from` to the criteria. A new fact gets
   them with its write; a changed scale first gets missing ones on its current version,
   which `update_memory` copies to the new version in the same transaction as the
   ChangeEvent (ADR-0014).

## Alternatives considered
- Convert 4-point to 10-point (×2.5, or a university table): no agreed formula; a
  wrong "eligible" sends a student to an application they cannot make, a wrong "not
  eligible" hides one. Declining and asking is honest.
- Store a scale on every cutoff: the parser sees ten-point cutoffs only today; a JD
  that states "3.0/4" is a parser follow-up, not a reason to model both scales now.
- Leave the rule check only (the first fix): derivation would still write "not
  eligible" from raw numbers before any rule ran.

## Consequences
- tests/domains/jobs/test_cgpa_scale.py (rule, links) and
  tests/domains/jobs/test_cgpa_scale_derivation.py (derivation, criteria).
- A 4-point student sees no eligibility verdict for openings with a cutoff. For a
  belief that existed before the scale was recorded, the ripple reaches the LLM
  resolver, which can ask; for an opening recorded afterwards no eligibility belief is
  derived at all, so nothing asks and the recommendation shows eligibility as unknown.
  The Scout does not gate their openings on CGPA.
- The CGPA fact stays a parent of the criteria even off the scale, so correcting the
  scale to 10 brings the clause back through the ordinary ripple (pinned by
  test_correcting_the_scale_to_10_brings_the_cgpa_gate_back_into_the_criteria).
- One check: `EligibilityRule` calls `compute_eligibility`, the function derivation
  uses, so the rule and derivation cannot disagree about the scale.
- Open: the JD parser reads "3.0/4" as 3.0 on the ten-point scale; a parser fix should
  drop or flag a cutoff written on another scale.
