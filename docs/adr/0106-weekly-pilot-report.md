# ADR-0106: The weekly pilot report computes two docs/04 metrics and marks three TBD
Status: Accepted under the autonomous mandate · Date: 2026-10-31

## Context
docs/04 lists five pilot metrics: saved or applied share of recommendations, days
earlier than self-discovery, stale recommendation rate, question usefulness and
self-reported trust. I8 requires every number to trace to a file in results/. The
pilot consent (docs/pilot/consent.md) promises aggregates only. What the product
records: the delivery log (ADR-0095; digests as one row per UTC day, alerts as one
upserted row per (user, kind, opening)), the feedback table (ADR-0105, first statement
per kind wins) and ChangeEvents (asks, edits, answers). Digests do not record which
openings they listed.

## Decision
1. `python -m ripple.pilot.report --week YYYY-Www` reads one ISO week as a half-open
   UTC window, Monday 00:00 to the next Monday 00:00. UTC because digest days are UTC
   days (ADR-0056).
2. It writes metrics.json (every value with its numerator, denominator and definition),
   report.md (the same, readable) and config.json (report version, week, generation
   time, partial and published flags, code version, source description; never a
   database URL). Code version is the git short sha, or `--code-version` (the image
   tag inside a container). It refuses to overwrite an existing week folder without
   `--overwrite`, which records the replaced `generated_at`, and to report a week that
   has not ended without `--partial`, which is recorded.
3. **Saved or applied share** = (student, opening) pairs alerted this week that the
   student had saved or applied to by the week's end / pairs alerted this week.
   - "By the week's end" includes earlier weeks: a save before a re-alert counts.
   - "Applied" counts once said; "saved" counts unless a later "dismissed" replaced it.
   - Openings are compared by their first version (`version_chain`), so an alert on one
     version and a save on the next are one pair; a forgotten id stands alone.
   - Known bias, stated in every output: digests record no items, so openings shown only
     in a digest are not in the denominator. Reactions to openings not alerted this
     week (dashboard, digest, self-pasted) are counted apart
     (`recommendation_reactions_without_alert`), not in the share.
4. **Question usefulness** = asked memories whose first rating falls in this week and is
   useful / asked memories first rated this week. First rating, because the store keeps
   the first row of each kind: after useful → not useful → useful the third tap returns
   the first row, so "latest" would be wrong and "first" is the one rule the data can
   answer. Questions asked this week (distinct (event, memory) `ask` decisions of
   ChangeEvents created this week) are shown for context.
5. Reported as "TBD (pending data)" with the reason, never estimated: days earlier than
   self-discovery (survey S1), stale recommendation rate (needs the beliefs each
   delivered recommendation rested on at send time) and self-reported trust (survey
   S2); docs/pilot/metrics.md. A computed metric with a zero denominator is TBD too.
6. Aggregates only: no user id, name, note or memory content in any output. A student
   is active in a week with a delivery, a feedback row, or a `user_edit` / `user_answer`
   ChangeEvent. Below five active students (`MIN_PUBLISHABLE_COHORT`, a policy choice)
   the week is written to results/pilot/raw/<week>/ (gitignored, `published: false`)
   and says "Not for publication"; otherwise to results/pilot/<week>/.
7. The delivery-log read is a separate `DeliveryReader` in `ripple.pilot.deliveries`
   over the same table, not a new method on the worker's `DeliveryLog` protocol.

## Alternatives considered
- Weeks in IST (the students' time zone) — matches how students think, but splits a
  UTC digest day across two weeks and needs tzdata on Windows. Lost; revisit with the
  recommendation snapshot.
- Denominator "alerted or reacted to this week" (the first draft) — mixes openings
  Ripple never recommended (self-pasted) into the share and drops earlier saves; the
  code review showed it is not an upper bound in either direction. Lost.
- Count every delivered digest item in the denominator — the right denominator, but
  the data does not exist; reconstructing it from today's ranking would be an invented
  number (I8). Lost; the snapshot proposal adds it.
- A proxy stale rate (alerts whose opening was already retired or updated before the
  send) — computable, but staleness here mostly lives in derived beliefs (eligibility
  from an old CGPA), not in the opening, so the proxy would read near zero and look like
  a result. Lost.
- Small-cell suppression (print "<5" for small counts) in publishable weeks — the counts
  are of events (saves, alerts), not of student attributes, and with five or more
  active students a count does not say who; suppression would also break the rule that
  every rate can be recomputed from its file. Lost; the cohort threshold routes whole
  weeks instead.
- Per-student rows in results/ — useful for debugging, but they break the consent's
  aggregate-only promise once committed. Lost; the operator reads the database.

## Consequences
- Two of five pilot metrics are measurable from week one; the other three need the
  survey (docs/pilot/metrics.md) and a recommendation snapshot at send time (Tier B,
  for the coordinator's IDEAS list).
- Alert rows are upserted, so a re-alert moves the earlier send out of its week.
  Running the report once per week, soon after the week ends, captures each send.
- Early pilot weeks with few students produce only raw (unpublished) folders.
- The report never runs without a database in tests: they use constructed sources with
  hand-derived answers (tests/pilot/support.py).

## Revisit if
The digest starts recording its items, the survey is collected in the product, or the
pilot cohort grows past one department (the publishable threshold).
