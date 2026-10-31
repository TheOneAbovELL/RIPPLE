# ADR-0140: Hardening of the final integration after code review
Status: Accepted under the autonomous mandate · Date: 2026-10-31 · Amends ADR-0116
(point 1: what counts as permanent) and ADR-0118 (points 1, 2 and 5)

## Context
The code-reviewer pass over the coordinator's final-delivery changes found no blockers
and eight should-fix issues. The engine finding is ADR-0119; this ADR records the rest,
because each one changes a contract another component relies on.

## Decision
1. **Permanent facts are keyed on (subject, attribute)** (`permanent_facts` on
   `detect_structured_update` and `Intake`; the jobs adapter's `PERMANENT_PROFILE_FACTS`).
   An opening field never borrows a profile attribute's permanence. The deterministic
   NEW also steps aside when an earlier value of the same fact is SUSPECT or
   PENDING_USER (for a multi-valued attribute, the same value): the change detector
   decides, as before ADR-0116, instead of a second live value appearing.
2. **`GET /events` counts a ripple as rippled when it reached another belief**, decided
   or not: an event with `affected_ids` and no decisions (a model outage mid-ripple) is
   shown. A decision about, producing or resting on a forgotten memory, or in an event a
   forgotten memory triggered, has its reason and question replaced by "forgotten at
   the user's request" (I7: ChangeEvents are not deleted, ADR-0044).
3. **Profile attribute specs carry `choices`** when the write path accepts a fixed set;
   `cgpa_scale` is published as an integer with choices 4 and 10. A test runs
   `profile_fact` on a sample of every published shape.
4. **The worker's injected transport and delivery log are chosen with `is None`**, not
   truthiness, and `DigestService` exposes both, so the run-once dry-run test checks what
   the digest really uses.
5. **The derivation observer isolates each opening**: an opening whose field cannot be
   read or that closed meanwhile is logged with its id and skipped.
6. A blank `RIPPLE_LINKER` or `RIPPLE_TRAINED_LINKER_MODEL` means the default.

## Alternatives considered
- Keep attribute-only permanence and rely on opening fields never passing through
  Intake: true today, but an MCP or inspector path could break it silently.
- Delete or rewrite ChangeEvents on forget: ADR-0044 keeps events as the audit; redacting
  at the read boundary keeps the audit and the promise.
- Let one failing opening stop the derivation loop: every later opening would silently
  lose its eligibility belief.

## Consequences
- Known and left: two concurrent derivations for one user (a live API ripple and the
  sweep) can both create the same missing criteria belief; a per-user lease around
  derivation would close it (DEVLOG). `cgpa_cutoff_value` and `batch_value` still raise
  on prose, which the observer now isolates.
- Tests: tests/core/test_change_detection_permanent.py, tests/api/test_events.py,
  tests/api/test_graph_vocabulary_edit.py, tests/api/test_wiring_c3.py,
  tests/worker/test_run_once.py, tests/domains/jobs/test_structural_linking.py.
