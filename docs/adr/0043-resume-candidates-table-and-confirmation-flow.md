# ADR-0043: Resume candidates live in their own table until the user decides
Status: Accepted under the autonomous mandate · Date: 2026-10-19

## Context
ADR-0024 decided that extracted resume facts are not memories until confirmed and left
"a confirmation flow and its storage" to this workstream. FR-1 / I5: no fact is stored
without confirmation. The user needs to see what was extracted, confirm or reject each
item, and later see what they declined.

## Decision
- A `resume_candidates` table (migration 0003) and `ResumeCandidate` model in
  `ripple.storage.candidates`: user_id, upload_id, attribute, value (JSONB so the
  scalar type survives), span (start, end, text), confidence, content, status
  `pending | confirmed | rejected`, created_at, decided_at, memory_id. `CandidateStore`
  protocol with Postgres and in-memory implementations and a shared contract test.
- `POST /resume` accepts multipart `file`, checks the `%PDF-` magic (415 otherwise)
  and a size cap (413), hands the bytes to the injected `ResumeParser` with
  `source_ref="resume:<upload id>"`, and stores the result as pending candidates. It
  writes **no memory**.
- `POST /resume/candidates/{id}/confirm` turns the candidate into a Statement through
  the injected `CandidateStatements` (WS-2's `candidate_to_statement`, which appends
  `#start-end` to the source ref) and runs Intake; the candidate records the memory id.
  `reject` keeps the row with status rejected. Either on a non-pending candidate is 409;
  another user's candidate is 404.
- Candidates are included in the user's export and removed on `DELETE /me`
  (ADR-0044). A forget of the confirmed memory leaves the candidate row: it records
  that the user once confirmed it, not the content of the memory, and the memory id
  it names is a plain string, not a foreign key.

## Alternatives considered
- PENDING_USER memories — rejected already in ADR-0024 (never-valid is not "in
  question").
- Keeping candidates only in the response and letting the client resend them on
  confirm — the server would then trust the client's values (I5 again). Lost.
- Deleting rejected candidates — loses the "you declined this" view and makes a
  re-upload re-offer the same item. Lost.

## Consequences
- One more table in the identity migration; the drift test covers it.
- Rejected rows accumulate; a retention sweep is a later task.

## Revisit if
Pilot users re-upload resumes often enough that candidate diffing is needed.
