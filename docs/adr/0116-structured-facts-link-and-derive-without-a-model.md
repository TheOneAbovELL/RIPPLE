# ADR-0116: Structured facts are classified, linked and derived from without a model
Status: Accepted under the autonomous mandate · Date: 2026-10-31 · Amends ADR-0020
(structured path), ADR-0031 point 5 and ADR-0079 (a second observer)

## Context
The first live run of the production API (embedded Postgres, ADR-0115) showed that
`POST /statements` with a structured profile fact ("CGPA is 8.1") returned 503 without
an LLM key. Two model calls sat on that path: the change detector was asked whether a
brand-new fact is temporary, and the LLM linker was asked which beliefs depend on it.
For the jobs profile both answers are part of the domain: a CGPA has no end date, and
CGPA, batch, scale and skills feed eligibility, fit and the search criteria by rule
(the rules already used by `record_profile_fact`). A third gap was worse: nothing in
production ever called `derive_criteria`, so the Scout's criteria never existed, and an
opening saved before the student's CGPA never got an eligibility belief, because the
ripple keeps beliefs current but cannot create one.

## Decision
1. Core: `detect_structured_update(..., permanent=...)` classifies a new structured fact
   whose attribute the adapter declares permanent as NEW, deterministically; Intake takes
   `permanent_attributes`. The jobs adapter declares `PERMANENT_PROFILE_ATTRIBUTES`
   (cgpa, cgpa_scale, batch, branch, skill, project, resume, accepted_offer); attributes
   that can lapse (availability, preference, looking) still go to the change detector.
2. `ripple.domains.jobs.linker.JobsStructureLinker` proposes the domain's exact links for
   a profile fact (`profile.rule_targets`, shared with `record_profile_fact`), at
   confidence 1.0 and created_by RULE.
3. `ripple.linking.composite.StructuredFirstLinker(deterministic, prose)`: a structured
   memory is linked by the deterministic linkers only (structure linker and RuleLinker's
   mention rules); a prose memory also goes to the prose linker (the LLM in production).
4. `ripple.domains.jobs.derive.ProfileDerivationObserver`, an EventObserver (ADR-0079):
   after any completed event triggered by a profile fact, derive the criteria and every
   live opening's eligibility, fit and reminder; existing beliefs are returned untouched,
   so it only fills gaps. It runs before the criteria-change trigger, so a first CGPA
   creates the criteria and that event queues the Scout.
5. Wired in the API (`build_services`) and the worker (`job_context_from_env`).

## Alternatives considered
- Keep the LLM on the structured path: correct results, but every profile edit pays two
  model calls for answers the domain already knows, and the product is unusable without
  a key or during a provider outage. C4 is about not paying for computable decisions.
- Derive in each write path (API routes, resume confirm, bot, MCP): several call sites
  and the sweep's expiry path would miss it; the observer seam already exists.
- Have the rules create missing beliefs during the ripple: the ripple's contract is to
  re-examine existing dependents (ADR-0013); creating new ones there would blur scope.

## Consequences
- A student can state profile facts and see eligibility, fit and criteria update with no
  model involved; prose statements, resume parsing and JD parsing still need the LLM.
- Hidden links from a structured fact to prose memories rely on RuleLinker's mention
  rule only; the LLM is not asked. That is the trade made for structured facts.
- tests/domains/jobs/test_structural_linking.py pins the linker, the composite, the
  observer and the end-to-end path (opening first, CGPA later, eligibility derived,
  criteria updated by the rules, no model call).
