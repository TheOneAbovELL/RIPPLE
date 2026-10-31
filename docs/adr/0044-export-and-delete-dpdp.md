# ADR-0044: Export everything, delete through forget, keep the deletion audit
Status: Accepted under the autonomous mandate · Date: 2026-10-19

## Context
FR-15 and NFR-3: export and delete all user data on request, aligned with India's DPDP
Act. ADR-0007 / I7: hard deletion only through the forget API, cascading along
depends_on links, with a ForgetEvent naming what left.

## Decision
- `GET /me/export` returns one JSON document: the user record, **every** memory
  including RETIRED versions (this is the user's own record, not retrieval, so I1 does
  not apply), every link, every ChangeEvent and ForgetEvent, and every resume
  candidate. Nothing is summarised or redacted; the user may want to take it elsewhere.
- `DELETE /me` (204): forgets every memory of the user through
  `ripple.core.forget.forget` until none remain (a cascade may remove several per call,
  so the loop re-lists), deletes the resume candidates, then the user with their tokens
  and link codes. The token used for the call stops working immediately.
- **ForgetEvents stay.** They hold the user id, memory ids and a timestamp, no content.
  They are the evidence that deletion happened and when, which an audit may ask for.
- **ChangeEvents are a known gap.** Core's forget deletes memories and links only;
  ChangeEvents remain, and their decision reasons may quote content. Until the Store
  offers a per-user event deletion that the delete path can call (contract change
  request in the WS-3 handover), `DELETE /me` is not a complete erasure. Recorded as an
  open problem, not hidden.
- There is no soft-delete or grace period: the dashboard must confirm with the user
  before calling DELETE, and offer the export first.

## Alternatives considered
- A deactivated flag with later purge — simpler to undo, but "delete" must mean delete
  under DPDP and the author has no support process to run purges. Lost.
- Deleting rows directly in the API — bypasses I7 and the ForgetEvent audit. Lost.
- Removing ForgetEvents too — leaves no proof the deletion happened. Lost.

## Consequences
- Export size grows with history; fine for the pilot.
- Until the Store change lands, ChangeEvent reasons for a deleted user remain; the
  handover flags it as the one gap in erasure.

## Revisit if
Legal guidance on DPDP retention arrives, or the pilot consent form promises a grace
period.
