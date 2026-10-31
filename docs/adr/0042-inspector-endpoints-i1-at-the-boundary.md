# ADR-0042: Inspector endpoints: I1 at the boundary, history on request, edits go straight to versioning
Status: Accepted under the autonomous mandate · Date: 2026-10-19

## Context
FR-12: see each belief, why it is held, its history; edit; forget. I1 says retrieval
never returns RETIRED and flags SUSPECT / PENDING_USER. docs/03 says the inspector's
"why" skips history depends_on links and always shows snapshot_of links, and that an
edit is a new version created_by user that ripples as a user_edit.

## Decision
- `GET /memories` passes every row through `ripple.core.visibility.visible_for_retrieval`
  with `include_flagged=True` by default (`flagged=false` hides them); each item carries
  `flagged`. `status` accepts only VALID, SUSPECT, PENDING_USER (RETIRED is 422).
- `GET /memories/{id}` answers 404 for a RETIRED memory unless `history=true`. With
  history it returns the version chain and every ChangeEvent that mentions any version
  (trigger, affected, decision, new version, parked). `why` lists parents from
  `parents_of`, skipping a depends_on link whose parent is superseded and keeping
  snapshot_of links, one entry per (parent, link type).
- `POST /memories/{id}/edit` calls `ripple.core.writes.update_memory` with
  `TriggerKind.USER_EDIT`, `created_by="user"`, `source_ref="inspector:<user id>"`, and
  runs the ripple. It does **not** go through Intake's change detection: the user
  named the memory, so classifying "is this new or an update" would be guessing, and
  for prose memories the LLM detector could answer NEW and leave a duplicate instead
  of a version. An edit of a PENDING_USER memory is 409 and points at the answer
  endpoint, because that is a correction (ADR-0013 step 4); RETIRED is 404.
- `POST /memories/{id}/forget` is the only deletion path and calls
  `ripple.core.forget.forget` (I7); the ForgetEvent is returned.
- `POST /statements` is the Intake path for new facts, with `origin` limited to
  `conversation | inspector` (the `agent` origin is not accepted from a client).
- `GET /questions` lists PENDING_USER memories with the ask decision from
  `events_asking`; until `Decision` carries the question text (contract change request
  in the WS-3 handover) the decision's `reason` is shown.

## Alternatives considered
- Edit through Intake with `origin="inspector"` — honours the letter of "Intake origin
  inspector" and lets the Linker add links to the new version, but risks the duplicate
  described above. Lost; the Linker's additions on edit are a follow-up once Intake
  accepts a target memory id (requested).
- A separate `GET /memories/{id}/history` route — one more route for the same data;
  a query flag keeps the single-memory view in one place. Lost.
- Returning RETIRED rows in the list with a flag — breaks I1 at the first client that
  forgets to filter. Lost.

## Consequences
- The named test `test_invariant_I1_api_never_returns_retired` covers list, detail,
  questions and export in one place.
- Edits skip the Linker: a new version keeps the copied links (ADR-0014) but gains no
  new ones until the follow-up lands.

## Revisit if
Intake gains an explicit "update this memory" entry point, or the dashboard needs the
history view paginated.
