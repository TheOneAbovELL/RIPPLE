# ADR-0032: Ranking openings: eligible, then urgent, then fit, then variety; flagged, never retired
Status: Accepted under the autonomous mandate · Date: 2026-10-19 (WS-1)

## Context
The digest (WS-6), the API (WS-3) and the agents read ranked openings through the
`RecommendationSource` contract. The ranking must come from the memory layer, not from
a recomputation over the JD, otherwise a stale belief would be invisible to the very
layer that exists to flag it (I1, C2 action-level evaluation).

## Decision
1. `JobsRecommender` reads only memories, through `visible_for_retrieval` with
   `include_flagged=True`: RETIRED anchors, fields and beliefs never take part (I1);
   SUSPECT or PENDING_USER ones take part and set `flagged=True` on the recommendation.
2. Per opening it reads the anchor, the title / company / deadline fields and the
   eligibility and fit beliefs. An opening with no eligibility belief counts as not
   eligible (the profile lacks the fact needed to decide); no fit belief is fit 0.
3. Order: eligible before not eligible; within that, openings whose deadline falls
   within the next 48 hours before the rest; within that, higher fit score first; then
   earlier deadline, no deadline last. Openings whose deadline has passed are left out.
4. Variety: within each (eligible, urgent) tier the list is rebuilt greedily, each step
   taking the remaining opening whose company has appeared least so far, ties broken
   by the order above. Two Acme roles never crowd out a Globex role of the same tier.
5. Flagged fields are **used**, not dropped: a SUSPECT deadline still orders the opening
   and is still shown, with `flagged=True`. Only the memories a recommendation is built
   from (anchor, title, company, deadline, eligibility, fit) can flag it; a flagged
   reminder does not. Openings with no parsed company form their own variety bucket.
6. `fit_reasons` are the reason lines stored in the fit belief's content; they quote
   the JD span text, which is why the belief stores them (ADR-0031).

## Alternatives considered
- Fit before urgency (the order the task sketch listed): with continuous scores
  urgency would almost never break a tie, and a deadline tomorrow matters more than a
  0.1 difference in skill overlap. The digest is a daily nudge, not a leaderboard.
- Recompute eligibility and fit from the fields at ranking time: faster to write,
  but a wrong or stale belief would never surface, so the action-level metrics would
  measure nothing.
- Weighted score (w1*eligible + w2*fit + w3*urgency): one number is easy to sort but
  impossible to explain to a student; tiers are what the digest prints.

## Consequences
- Ranking is deterministic and offline-testable; no clock inside, `now` is injected.
- A profile without a CGPA ranks every cutoff-bearing opening as not eligible until
  the fact is recorded; the agent should ask, which is the intended behaviour (I5).
- Past-deadline openings vanish from the list but stay in memory until the lifecycle
  of closing an opening is decided (open problem in the WS-1 handover).

## Revisit if
Pilot users report that variety hides their best match, or the digest needs a per-user
weighting; then the tiers become a configurable policy object.
