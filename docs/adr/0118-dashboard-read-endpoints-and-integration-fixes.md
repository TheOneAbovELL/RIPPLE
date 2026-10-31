# ADR-0118: Profile vocabulary, an events feed and the final-delivery integration fixes
Status: Accepted under the autonomous mandate · Date: 2026-10-31 · Amends ADR-0087
(vocabulary), ADR-0131 point 6 (Home reads the export), ADR-0134 (run_once wiring)
and ADR-0128 (wired)

## Context
The WS-20 and WS-19 handovers asked the API for what the finished dashboard and the
trained linker need. The dashboard hardcoded the profile subject and attribute list,
and labelled five recent events by downloading the whole export (history, resume
text, feedback). The live run also surfaced three defects: a deadline edited to prose
crashed the reminder rule mid-ripple, despite the vocabulary's "unknown, never an
error" contract (ADR-0035); a duplicate opening answered 500; and `run_once` copied the
worker's wiring by hand, which had already drifted once (the derivation observer).

## Decision
1. `GET /vocabulary` adds `profile_subject` and `profile_attributes`, each with
   `value_type` (number, integer, bool, text), `permanent` (ADR-0116), `multi_valued`
   (ADR-0020) and `stated_by_user` (false for the resume, which the resume review
   writes). The jobs adapter declares `PROFILE_VALUE_TYPES` and
   `PROFILE_ATTRIBUTES_NOT_STATED` beside its other attribute sets.
2. `GET /events?limit=N&rippled_only=true` returns the user's ChangeEvents newest first
   and labels exactly the memory ids those events name, with each memory's current
   status. It is an audit view like the inspector's `history=true`: a version an event
   retired is shown with status RETIRED, as the past; nothing is offered as current, so
   I1 (a retrieval rule) is untouched. Forgotten memories (I7) are left unlabelled.
3. `OpeningView.deadline_value` returns None for a value that is not a full ISO
   date-time; `parse_deadline` stays strict for writes. The reminder rule then declines
   and the fallback decides, as for any belief a rule cannot compute.
4. `OpeningAlreadyRecordedError` maps to 409.
5. `job_context_from_env` takes `engine`, `transport` and `delivery_log`; `run_once`
   builds its context through it and only chooses those three.
6. `build_services` picks the prose linker with `select_linker(settings.linker, ...)`
   (RIPPLE_LINKER, RIPPLE_TRAINED_LINKER_MODEL); a bad choice fails at start-up.
   The image excludes the `linkfinder` group by default (`SYNC_GROUPS` build argument).
7. Kept as is: a structured statement whose ripple stops on a model outage answers 503
   with `open_change_event_ids`, and the nightly sweep resumes the event
   (`NightlySweep.resume_open`). The dashboard says so instead of the API answering 201
   for beliefs that were not yet re-checked.

## Alternatives considered
- A per-domain "profile form" endpoint: a second vocabulary for the same facts; the
  attribute specs are what a form needs and stay domain-declared.
- Filter `/me/export` client-side (status quo): ships every historical memory, the resume
  text and feedback to show five rows; the export is for FR-15, not for a home page.
- Return 201 after a model outage mid-ripple: the write is saved, but the dependents are
  not re-checked yet; 201 would claim a finished ripple.
- Keep `run_once`'s copy of the wiring with a parity test: the test only catches drift
  in what it inspects; one function cannot drift.

## Consequences
- The dashboard hardcodes no domain value; a second domain with a profile publishes its
  own specs. Home loads in one small request.
- Tests: tests/api/test_events.py, test_graph_vocabulary_edit.py (profile specs),
  test_openings.py (409), test_wiring_c3.py (linker selection),
  tests/domains/jobs/test_end_to_end.py (prose deadline), tests/worker/test_run_once.py.
