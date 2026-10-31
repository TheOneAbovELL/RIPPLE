# Pilot metrics: definitions, sources and what is still missing
Draft, 2026-10-31 (WS-16; ADR-0105, ADR-0106). Expands docs/04 "Pilot metrics" for
claim C3. Every reported number comes from `python -m ripple.pilot.report` and lives in
results/pilot/<week>/ (I8). Nothing here is a result.

## The five metrics
| docs/04 metric | Status | Definition | Source |
|---|---|---|---|
| Saved or applied share of recommendations | computed weekly | (student, opening) pairs alerted that week which the student had saved or applied to by the week's end (any earlier week counts; a later "dismissed" undoes "saved", not "applied"; versions of one opening joined) / pairs alerted that week | delivery_log alerts, pilot_feedback, memory version chains |
| Days earlier than self-discovery | TBD (pending data) | per opening a student saved or applied to: the date they say they would have found it themselves minus the date Ripple first showed it; median over pairs | survey S1 + first alert or feedback date |
| Stale recommendation rate | TBD (pending data) | delivered recommendations whose eligibility or fit rested on a belief that was already superseded or retired at send time / delivered recommendations | needs a belief snapshot per delivered item (not recorded) |
| Question usefulness | computed weekly | asked memories first rated that week and rated useful / asked memories first rated that week (first rating: the store keeps the first row per kind) | pilot_feedback |
| Self-reported trust | TBD (pending data) | mean of S2 per week, with the number of answers | survey S2 |

Limits that every report repeats:
- Digests do not record which openings they listed (ADR-0095), so openings shown only
  in a digest are not in the saved share's denominator. Reactions to openings that were
  not alerted that week (dashboard, digest, self-pasted) are counted separately and
  left out of the share.
- Alert rows are upserted per (student, opening, kind): a re-alert moves the earlier
  send out of its week. Run the report every Monday for the week just ended.
- Fewer than five active students in a week (active: a delivery, a feedback row, an
  edit or an answer): the report goes to results/pilot/raw/<week>/ (gitignored) and
  says "Not for publication".

## Weekly survey (draft, for the guide's review)
Sent by the operator in person or through a form outside Ripple, once a week, optional.
Answers are stored apart from the product database, keyed by an anonymous pilot code,
never by name.
- **S1** For each opening you saved or applied to this week (the bot lists them):
  "Would you have found this opening without Ripple? If yes, roughly when?" (date or
  "never").
- **S2** "This week, how much did you trust Ripple's eligibility and reminders?"
  1 (not at all) to 5 (completely).
- **S3** (free text, optional) "Anything Ripple got wrong this week?" Read by the
  operator; quoted in the thesis only with the student's separate permission.
Until the survey is collected and an ingestion step exists, S1 and S2 stay TBD.

## Feedback the product records (ADR-0105)
| Kind | Means | Recorded from |
|---|---|---|
| saved | the student wants to come back to this opening | bot button on a digest item or alert; dashboard Recommendations |
| applied | the student says they applied (Ripple applies nowhere, I6) | same |
| dismissed | not interested | same |
| question_useful / question_not_useful | the question the agent asked was worth asking | bot buttons under a question; dashboard Questions |
One row per (student, memory, kind); repeats are ignored. A short optional note (≤ 280
characters) stays in the database and never appears in a report. Forgetting the memory
deletes the rows about it (database cascade, I7).

## What would close the TBDs (proposals for the coordinator)
- A per-item digest record (which openings, with the ids of the eligibility and fit
  beliefs they rested on) at send time: gives the full denominator and the stale
  recommendation rate. Changes the delivery log, so it is Tier B with an ADR.
- A survey ingestion command reading an anonymised CSV into results/pilot/<week>/
  survey.json: gives S1 and S2. No new dependency.
