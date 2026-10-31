# ripple.core: writes, runner, versioning, forget, sweep, answers
Written 2026-10-19 for the Phase 1 core as built.

## 1. What it does
Turns a change into a completed, audited ripple. A write opens a ChangeEvent; the
runner marks a wave SUSPECT, asks the Resolver, applies the decisions, and repeats until
the engine has nothing left; every state transition lands in that one event.

## 2. Why it exists
ADR-0013 (waves, two commits each), ADR-0014 (versions as rows, links copied),
ADR-0015 (every change is a memory write; temporary facts self-expire), ADR-0007 and I7
(retire, never delete; forget is the only deletion). FR-5, FR-6, FR-7, FR-12.

## 3. How it works
- `writes.record_memory` / `writes.update_memory` write the trigger and its ChangeEvent
  in one transaction (`open_event`). An update goes through
  `versioning.write_new_version`: new row, old row RETIRED, incoming depends_on links
  copied to the new row (skipping retired dependents), outgoing depends_on links copied
  and re-pointed at each parent's latest version, snapshot_of links left alone.
- `ripple.RippleRunner.run(event)`: load the trigger, build the graph, ask the engine
  for wave 1. Per wave: commit one marks members SUSPECT and records them in
  `affected_ids`; the Resolver is called outside any transaction; commit two applies
  keep → VALID, retire → RETIRED, update → new version (content replaced; valid_to
  and structured carried over unless the resolver set them), ask → PENDING_USER plus
  the subtree SUSPECT with the parked ids recorded on the event, and appends Decisions
  with the wave number. Rows are re-read inside commit two; a member that changed
  meanwhile is skipped and logged. `completed_at` closes it. Only ids actually flipped
  to SUSPECT count as affected, so history versions in a wave leave no trace.
- `RippleRunner.resume(event)` replays recorded decisions through a fresh engine to
  rebuild its visited set, resolves whatever is affected, undecided and still SUSPECT,
  and carries on. `sweep.NightlySweep.resume_open` calls it for open events older
  than a threshold.
- Per-event lease (ADR-0099): `RippleRunner(..., event_lease=...)` takes an optional
  `core.lease.EventLease`. `run` and `resume` hold it, keyed by the event id, for the
  whole call; when another process holds it they log and return the event unchanged
  and open, so an open event from `resume` always means "skipped". With a lease the
  runner re-reads the stored event first and drives that copy through the resume
  path: a completed one is returned, a crashed holder's progress is continued. `resume_open`
  leaves skipped events out of its result and logs them. The worker wires
  `worker.lease.ChangeEventLease` (Redis, 2 h ttl); the API's runner is not wired yet
  (ADR-0099 point 6). No lease means exactly the earlier behaviour.
- `sweep.NightlySweep.expire` retires VALID memories whose valid_to has passed and
  ripples each with trigger_kind=expiry. No LLM decides that a date passed.
- `answers`: every answer first restores exactly the ids the ask parked (read from the
  asking event's `parked` map; a child parked by another open question stays flagged),
  recording wave-0 KEEP decisions. Still-holds then completes the event; no-longer-holds
  retires (wave-0 RETIRE decision) and ripples; a correction writes a new version and
  ripples.
- `forget.forget`: whole version chain plus depends_on cascade deleted, snapshot_of
  links removed, one ForgetEvent; all in one transaction.
- `visibility.visible_for_retrieval`: the I1 rule every retrieval path must use.

## 4. Trade-offs
- Two commits per wave instead of one per ripple: a ripple can wait on an LLM or a user,
  and SUSPECT must be observable so retrieval can flag it (I1). Cost: a crash between
  commits leaves work for the sweep; that is by design and tested.
- Copying links instead of a stable identity: the author's choice (ADR-0014); the
  price is the dedupe and history logic in versioning, which tests pin down.
- The Resolver is called memory by memory, not batched: simpler evidence per call and
  a clean I4 story. Batching is a Phase 3 cost optimisation to measure, not assume.
- Marking the subtree below an ask SUSPECT trades a few over-flagged memories for
  honesty in retrieval; the author may flip it (ADR-0013 consequences).

## 5. Failure modes and tests
| Failure | Test |
|---|---|
| Crash between commits strands SUSPECT rows | test_runner_crash_between_commits_leaves_open_event_and_suspect_wave, test_runner_resume_finishes_the_pending_wave_and_continues |
| Update loses dependents or parents | test_versioning: incoming/outgoing copies, second change reaches updated dependent |
| Snapshot links ripple | test_snapshot_links_stay_on_the_old_version, resume_version_snapshot.yaml |
| Expiry needs an LLM | test_sweep_retires_expired_memory_and_ripples_with_expiry_trigger (scripted, zero model calls) |
| State change without an event | test_invariant_I2_every_state_change_is_covered_by_a_change_event |
| Forget leaks or over-deletes | test_forget_* and test_invariant_I7_* |
| Answer on a non-pending memory | test_answers_refuse_memories_that_are_not_pending |
| Sweep resumes an event a slow live ripple is still resolving | test_a_sweep_cannot_resume_an_event_a_live_ripple_is_still_resolving (tests/core/test_event_lease.py) |

## 6. Interview questions
1. *Why can a ripple not be one database transaction?* It waits on an LLM for seconds
   and on a user for days; and SUSPECT must be visible to retrieval meanwhile.
2. *How is I2 enforced for a retired old version?* The event whose trigger supersedes
   it records that retirement; the invariant test audits every changed memory.
3. *What makes the runner resumable?* Decisions carry a wave number and the event has
   completed_at; resume replays decisions to rebuild the engine's state.
4. *Why does forget delete a whole version chain?* A copied link could otherwise point
   at a deleted parent; and privacy means the old value must go too (ADR-0007).
5. *Where does the LLM get called?* Only in `_resolve_wave`, through the injected
   Resolver; the engine and the transactions never see it (I3, I4).

## 7. Exercise
Write a scenario YAML where a memory has two changed parents in the same wave and
predict how many times the resolver is called for it. Run it once the engine exists.
