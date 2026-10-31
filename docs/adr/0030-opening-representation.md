# ADR-0030: An opening is one anchor memory plus one structured fact per field
Status: Accepted under the autonomous mandate · Date: 2026-10-19 (WS-1)

## Context
A parsed job description (`ParsedOpening`, contract C1) carries a summary and a list
of fields with character spans. The ripple engine only propagates along links between
memories, and the rule linker and the jobs rules only read `StructuredFact`
(subject / attribute / value). One memory per JD would make "the deadline moved" a
prose edit that needs an LLM to interpret; one memory per field with no grouping would
leave nothing to forget as a unit (I7) and nothing to retire when the opening closes.

## Decision
1. `record_opening` writes one **anchor** memory (kind `opening`, content = the
   one-line summary, `source_ref` = the JD's source) and one **field fact** per parsed
   field (kind `fact`, subject `opening:<anchor id>`, attribute from
   `OpeningAttribute`, value typed, content = the exact JD span text, `source_ref` =
   `<source>#<start>-<end>`).
2. Every field fact is linked `field --depends_on_fact--> anchor`. Forgetting the
   anchor therefore cascades to every field and, through the derived beliefs' links,
   to everything built on the opening (I7). Retiring the anchor (closing the opening)
   ripples into its fields.
3. The anchor, its fields and their links commit in **one transaction** that opens one
   ChangeEvent with the anchor as trigger; the caller's `RippleRunner` runs it. A JD
   either lands whole or not at all.
4. Because wave 1 of that event is the opening's own fields, the jobs resolver chain
   carries an `OpeningFieldRule` (ADR-0031): a field whose anchor is VALID is kept, a
   field whose anchor is RETIRED is retired. Recording or closing an opening never
   calls the LLM.
5. Values are validated at write time (`cgpa_cutoff` numeric, `batch` integer,
   `deadline` an ISO 8601 date-time with a timezone; every span non-empty and equal to
   `raw_text[start:end]`; every attribute except `required_skill` at most once); a
   malformed field raises `InvalidObjectError` and nothing is written.
6. **Stable opening key.** The anchor carries `structured = (opening:<first version
   id>, "opening_key", source_ref)`. Every field and belief uses that subject.
   Versioning carries `structured` over (`writes.update_memory`, the inspector edit), so
   a user who edits an anchor's summary keeps its fields, beliefs and ranking attached;
   the rules and the recommender compare against `opening_key(anchor)`, never
   `anchor.id`. (Added after the WS-1 code review, blocker B2.)
7. **One live opening per source.** `record_opening` raises
   `OpeningAlreadyRecordedError` when a non-RETIRED anchor with the same `source_ref`
   exists; once the old one is retired the source may be recorded again.

## Alternatives considered
- One memory per JD with the fields in `structured` as a dict: core's
  `StructuredFact` is a single triple on purpose; rules could not address one field,
  and a deadline change would be a prose rewrite resolved by the LLM.
- One `record_memory` call per row (N+1 ChangeEvents per JD): matches ADR-0015 word
  for word but is not atomic. A crash leaves an anchor with half its fields, and the
  ten empty ripples per JD are noise in the audit log.
- Fields depend on nothing; the anchor depends on the fields: forgetting the anchor
  would then leave orphan fields behind, the opposite of what "forget this opening"
  means.
- Creation with no ChangeEvent at all (docs/03 says creation is recorded by the row):
  cheaper, but every other write in the system opens an event, and the API, the digest
  and the bench all read "what changed" from ChangeEvents. One event per JD is the
  consistent choice.

## Consequences
- Under the real engine, recording an opening produces one wave of deterministic
  `keep` decisions, one per field. Accepted: zero LLM cost, and it is the same path
  that retires the fields when the opening closes.
- Derived beliefs link to the field facts they read **and** to the anchor, so a closed
  opening retires its beliefs in one wave (ADR-0031).
- The span text as content gives retrieval the JD's own words and lets fit reasons
  quote the JD line (FR-2) without a second lookup.
- Multi-valued fields (`required_skill`) are several facts with the same subject and
  attribute. Core's deterministic change detection treats same subject + attribute as
  an update; openings are never written through `Intake`, so this is safe here, but the
  same holds for profile skills, which is raised as a contract question in the WS-1
  handover.

## Revisit if
The scout re-fetches openings often enough that re-parsing a whole JD into field
updates becomes the main write path; then an `update_opening` that diffs fields
belongs in this module.
