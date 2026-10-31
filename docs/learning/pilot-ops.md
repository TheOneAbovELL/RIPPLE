# Pilot operations — feedback capture, the weekly report, incident handling
Written 2026-10-31 for workstream WS-16 (docs/plans/wave-b.md), ADR-0105 to ADR-0107.

## 1. What it does
Turns the deployed product into something a pilot can be measured on (claim C3):
- Students tell Ripple what they did with a recommendation (saved, applied, dismissed)
  or whether a question it asked was useful. `POST /feedback` stores one row per
  (student, memory, kind) in `pilot_feedback`; `GET /feedback` lists their own rows.
- Every Monday the operator runs `python -m ripple.pilot.report --week 2026-W45`. It
  reads the delivery log, the feedback table and the ChangeEvents for that ISO week and
  writes results/pilot/2026-W45/ with metrics.json, report.md and config.json.
- docs/ops/incident.md and the runbook's monitoring checklist tell one operator what to
  do when the bot is down, a digest repeats, eligibility is wrong, a student asks to be
  deleted, or the LLM provider is down.

## 2. Why it exists
docs/04 names five pilot metrics, but until now nothing in the product recorded what a
student did with a recommendation, and I8 forbids a number without a file behind it.
The consent draft promises aggregates only, so the report had to be designed to hold
no identifier. And a pilot run by a student for students needs a written plan for the
night the bot stops answering.

## 3. How it works
- **Storage** (`ripple.storage.feedback_tables`, `ripple.storage.feedback`, migration
  0009). The unique constraint `uq_pilot_feedback_user_target_kind` is the whole
  idempotency story: `PostgresFeedbackStore.record` does `INSERT ... ON CONFLICT DO
  NOTHING RETURNING id`; no row back means the statement existed, so it reads and
  returns the first one (or raises `FeedbackRecordRaceError` if a concurrent delete
  removed it in between). The in-memory store keys a dict by the same triple. Both run
  `FeedbackStoreContract`. Both foreign keys cascade: deleting the user or forgetting
  the target memory deletes the rows, so a note never outlives its memory (I7).
- **Rules** (`ripple.pilot.feedback.record_feedback`), shared by the API and, next,
  the Telegram buttons: unknown or foreign target → `FeedbackTargetNotFoundError`;
  recommendation kinds need `memory.kind == "opening"` and question kinds need
  `store.events_asking(memory_id)` to be non-empty, else `FeedbackKindMismatchError`.
- **API** (`ripple.api.routers.feedback`) maps those to 404 and 422 (and the race to
  409); 201 for a new row, 200 for a repeat. The response is the `Feedback` row: ids, kind, note, time; never memory
  content (I1). Nothing else is written: no memory, no ChangeEvent, no message (I6).
- **Report** (`ripple.pilot`). `weeks.parse_week` turns `2026-W45` into a half-open UTC
  window. `deliveries.PostgresDeliveryReader` reads `delivery_log` rows in the window.
  `report.collect` reads that week's deliveries, all feedback up to the week's end and
  every account's ChangeEvents, and maps each opening id to its first version.
  `metrics.week_metrics` is pure: it counts activity and computes two rates, each with
  numerator, denominator and definition; the three metrics the data cannot support are
  "TBD (pending data)" with a reason. `report.generate` refuses an unfinished week
  (unless `--partial`) and an existing folder (unless `--overwrite`), then writes the
  three files to results/pilot/<week>/, or to results/pilot/raw/<week>/ (gitignored)
  when fewer than five students were active.

## 4. Trade-offs
- First statement wins: a duplicate tap is harmless, but a student cannot take back
  "applied"; they can only add "dismissed". Good enough for a pilot; an undo route is
  the revisit.
- The saved share's denominator is "alerted this week", because digests do not record
  their items: openings seen only in a digest are invisible, and reactions to openings
  not alerted this week are counted apart. The first draft used "alerted or reacted
  to" and called it an upper bound; the code review showed self-pasted openings and
  earlier saves push it both ways. Recording digest items is a Tier B change for later.
- Question usefulness uses the first rating, because the store keeps the first row per
  kind: after useful → not useful → useful, the third tap is invisible.
- UTC weeks: consistent with UTC digest days, slightly odd for students in IST (a
  Monday 03:00 IST action belongs to the previous week).
- A minimum cohort of five before a week is publishable is a policy choice, not a
  statistic; it protects the consent promise, not the confidence interval.

## 5. Failure modes and tests
- Double tap or retry → one row (contract test "returns existing row when repeated",
  API test "returns first row with 200").
- Feedback on someone else's memory → 404, nothing stored.
- "Saved" on a CGPA fact, "useful" on a memory nobody asked about → 422.
- `DELETE /me` leaves feedback → xfail(strict) test until the coordinator adds the line.
- Report numbers wrong → tests/pilot/support.py builds a week whose answers are derived
  by hand in comments (3 / 5 saved share, 2 / 3 usefulness, 3 questions asked, 4 of 5
  accounts active), with rows just outside both window edges, a save on a second
  version, a save from the previous week and a saved-then-dismissed opening.
- A user id or note in results/ → `test_generate_output_holds_no_user_id_or_note`
  (one fixture row carries a sentinel note). A small week in committed results →
  `test_generate_small_cohort_goes_to_the_gitignored_raw_folder`.
- Overwriting a quoted week → `ReportExistsError`.
- Two Alembic heads when 0007/0008 land → `test_migration_chain_has_a_single_head`.
- Postgres behaviour (racing inserts, the user and forget cascades, the migration
  matching the table, UTC reads of delivery_log) → slow tests, skipped without a
  database.

## 6. Interview questions
1. Why is the idempotency rule a database constraint and not a read-before-write?
2. Why is the saved share's denominator "alerted this week" and not "everything
   shown", and which way does that bias the number?
3. Why is `target_memory_id` a cascading foreign key here when `delivery_log` keeps
   opening ids as plain strings?
4. Why does the report refuse to overwrite a week, and when would you pass
   `--overwrite`?
5. A week has three active students. What does the report say, and why?
6. Why is stale recommendation rate TBD when the store has every ChangeEvent?

## 7. Exercise
Add a `DELETE /feedback/{id}` route that lets a student withdraw one statement: own
rows only (404 otherwise), the store gains `delete(feedback_id, user_id)`, the
contract test gains one case, and ADR-0105's "Revisit if" becomes a new ADR that amends
it. Then decide whether the weekly report should count a withdrawn "applied".
