# Vision

## One line
Ripple keeps an AI agent's knowledge correct as the world changes: when one fact changes,
every belief that depended on it is updated.

## The problem
Agents now remember and act for months. Their worst failure is not forgetting; it is
acting confidently on knowledge that went stale. When a student's CGPA rises, eligibility,
recommendations and search criteria built on the old CGPA must change too. Current memory
systems update the contradicted fact and leave its dependents stale.

## Thesis
Make dependencies between memories explicit. Deterministic code decides WHICH memories a
change affects; the LLM decides only HOW to fix each one.

## What we claim (contributions)
- C1 Learned dependency induction: a small trained model infers typed links between memories
  from raw text. Recent cascading-invalidation work (PACMI, rollback repair) assumes these
  links are given.
- C2 Action-level evaluation: we measure whether cascades change agent actions (stale
  recommendations, wrong eligibility), not only memory states, at realistic scale.
- C3 Real-world pilot: a deployed job-hunt agent used by students in a placement season.
- C4 Cost: graph-scoped resolution vs re-checking everything, measured.

## What we do NOT claim
- We did not invent cascading invalidation (see docs/06-related-work.md).
- Not a general personal assistant.
- No financial advice; finance is an unseen-domain test only.
- The agent never applies to jobs for the user.

## Scope
| Role | Domain | Depth |
|---|---|---|
| Primary | Internship and job hunting | Full product + pilot |
| Secondary | News and current affairs | Benchmark only |
| Generalization | Finance | Unseen-domain test + small demo |

## Success by May 2028
- Deployed agent used by 30–50 students during a placement season.
- RippleBench released with three tracks.
- Link finder report: accuracy, cost, cross-domain transfer.
- Hypotheses H1–H4 (docs/04-evaluation.md) answered with numbers from results/, whether
  they hold or not.
