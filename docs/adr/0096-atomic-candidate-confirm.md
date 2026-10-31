# ADR-0096: Candidate decisions are a compare-and-set on status, so a double confirm cannot write twice
Status: Accepted under the autonomous mandate · Date: 2026-10-26
Amends ADR-0043 (the confirm and reject endpoints).

## Context
ADR-0043 made `POST /resume/candidates/{id}/confirm` and `/reject` answer 409 on a
candidate that is no longer pending. The check was a read: load the candidate, refuse
if not pending, run Intake, then overwrite the row with `replace_candidate`. Two
requests for the same candidate (a double click, a dashboard retry, two tabs) could
both read it as pending and both write; the second overwrite won, and a confirm racing
a reject could leave a row that says "rejected" with a memory written for it. The WS-3
handover listed this as open problem m6; the production plan puts it in WS-13.

## Decision
1. `CandidateStore.replace_candidate(candidate, *, expected_status=None)`: with
   `expected_status`, the write happens only if the stored row still has that status;
   otherwise it raises `CandidateAlreadyDecidedError(candidate_id, actual)` and changes
   nothing. Without it, the old unconditional overwrite is kept.
2. Postgres does the check and the write in one statement:
   `UPDATE resume_candidates SET ... WHERE id = :id AND status = :expected`. A
   `rowcount` of 0 means another request committed first; the store then reads the
   current status, inside the same transaction, to put it in the error. The in-memory
   store (`tests/api/fakes.py`) compares and writes with no `await` in between, which
   is atomic on one event loop.
3. The router claims the row through one helper, `_claim`, with
   `expected_status=PENDING`, for both confirm and reject. A lost race becomes the same
   409 `"candidate already <status>"` that ADR-0043's read check gives; the read check
   stays as the fast path.
4. Confirm still runs Intake before the claim. Intake is idempotent for an identical
   structured fact (`ChangeKind.UNCHANGED` writes nothing), so two confirms racing each
   other leave one memory; the claim decides which request owns the candidate.

## Alternatives considered
- `SELECT ... FOR UPDATE` around the whole confirm — holds a row lock across Intake,
  which can call the LLM linker and change detector for seconds; the in-memory store
  has no equivalent, so the contract test could not cover it. Lost.
- Claim first (pending → a new `confirming` status), then Intake, then confirmed —
  closes the confirm-versus-reject window below, but adds a fourth status to the
  candidate model, a migration, and a recovery path for rows stuck in `confirming`
  after a crash. Not worth it for a pilot where the window needs two clicks within one
  Intake call. Lost for now; see "Revisit if".
- A version column with optimistic locking — the same compare-and-set with one more
  column; status already is the only field that changes. Lost.
- An idempotency key per request from the dashboard — protects one client's retries
  but not two tabs or a confirm against a reject. Lost.

## Consequences
- Two concurrent confirms: one 200, one 409, one memory, one confirmed row
  (`test_two_concurrent_confirms_yield_one_success_one_409_and_one_memory`).
- Confirm racing reject: the first decision stands and the other request gets 409
  (`test_confirm_racing_a_reject_leaves_the_first_decision_standing`). If the reject
  wins, the losing confirm has already run Intake, so a memory exists for a candidate
  the user rejected. The test asserts statuses only. The user sees the memory in the
  inspector and can forget it; the handover records this as an open problem.
- If the candidate row disappears between the read and the claim (a `DELETE /me`
  in between), the Postgres store raises nothing and the request answers 200 for a
  row that no longer exists; the in-memory fake raises `KeyError`. Harmless after a
  deletion, but the two implementations differ there.
- The contract `ConditionalReplaceContract` runs against both stores; the Postgres run
  is slow and unverified on the author's machine until a database is available.

## Revisit if
Pilot data shows a memory written from a candidate whose row says rejected, or Intake
grows slow enough that the confirm-versus-reject window matters: then move to
claim-first with a `confirming` status.
