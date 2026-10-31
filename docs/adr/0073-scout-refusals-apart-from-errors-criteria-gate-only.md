# ADR-0073: Scout refusals are counted apart from errors; criteria parse only the gates
Status: Accepted under the autonomous mandate · Date: 2026-10-26 · Amends ADR-0072
points 3 and 4 (checkpoint C3)

## Context
ADR-0072 point 4 counted a refused fetch (an off-host link, a robots.txt disallow, a
login page) as a candidate failure, listed with its URL in `ScoutReport.errors`. Point 3
parsed the criteria memory into `ScoutCriteria` with cgpa, batch and skills. The WS-9
review pass changed both in code before the session stopped: a refusal is ADR-0008
doing its job, not something an operator should chase, and listing refusals as errors
buries real failures (a 500, a parser rejection) under expected policy outcomes every
night. Skills are a graded fit (ADR-0031), not a gate, so parsing them into the filter
would make every new skill re-judge every filtered JD through the fingerprint.

## Decision
1. `SourceCount` has `candidates` (items the listing offered, after the cap), `new`,
   `duplicates`, `filtered`, `refused` and `errors`. A `FetchRefusedError` increments
   `refused`, is remembered in the ledger so the request is not sent again, and is
   logged at INFO. It is not appended to `ScoutReport.errors`.
2. `errors` and `ScoutReport.errors` hold only failures: fetch errors after retries,
   parser rejections, adapter validation, derivation failures after recording.
3. `ScoutCriteria` holds `cgpa` and `batch` only. Its fingerprint, which keys the
   "filtered" ledger marks, changes only when a gate changes.
4. The canonical URL keeps `ref` as a query parameter: career sites use it as the job
   reference id, so dropping it would merge different openings (ADR-0071's tracking
   list is `utm_*` plus named click ids).

## Alternatives considered
- Keep refusals in `errors` with a reason code: one list for two different audiences;
  every nightly report would show the same expected refusals.
- Parse skills but leave them out of the fingerprint: dead data in the filter, and a
  later reader would assume skills gate.
- Drop `ref` with the other tracking parameters: merges distinct openings on sites that
  route `?ref=<job id>`, which is a silent data loss; a duplicate is the cheaper error.

## Consequences
- tests/agents/test_scout.py, test_scout_invariants.py and
  tests/domains/jobs_sources/test_canonical.py assert the new shape;
  docs/learning/scout.md describes it.
- An operator reading a ScoutReport sees refusals as a count per source and errors as
  a list worth reading.
