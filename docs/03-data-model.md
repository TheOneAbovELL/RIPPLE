# Data model

ADR-0013, 0014 and 0015 (kickoff interview, 2026-10-19) are Accepted. Lines marked
*(assumed)* are the collaborator's resolution of a contradiction; the author approved
the ADRs that contain them but may still refine the wording.

## Memory
id (uuid4) · user_id · domain · kind (string declared by the domain adapter; core
interprets none of them; generic: fact | derived; jobs adds opening | application |
criteria) ·
content (text) · structured (JSON: subject, attribute, value) ·
status (VALID | SUSPECT | RETIRED | PENDING_USER) · valid_from · valid_to · recorded_at ·
confidence (0–1) · sensitivity (low | medium | high) · source_ref (message id or url + span) ·
created_by (user | agent name) · version · supersedes_id (previous version, nullable)

- A **temporary fact** ("busy with exams this month") is an ordinary memory with a
  valid_to. The change detector fills valid_to; nothing else marks temporariness
  (ADR-0015).
- **Every version is its own row.** An update writes a new row with supersedes_id pointing
  at the old one and retires the old one (ADR-0014). The version chain is supersedes_id
  only; there is no supersedes link.
- Creation (none → VALID) is recorded by the row itself (recorded_at, created_by,
  source_ref). I2 covers transitions between states, not creation.

## Link (dependency edge)
id · parent_id · dependent_id · link_type · link_class · strength (0–1) ·
created_by (rule | llm | model | human) · confidence (0–1) · created_at · verified_at

- **confidence** is the linker's belief that the dependency exists; FR-16's weak-link
  re-check reads it. **strength** is how much the dependent relies on the parent; unused
  until idea 6 in docs/IDEAS.md (strength-based damping) is approved.

**Direction convention** *(assumed)*. Stored as parent_id → dependent_id: the dependent
is the memory that would be wrong if the parent changed. In prose and diagrams we write
`dependent --type--> parent`, read as "dependent is <type> parent", e.g.
`eligibility(Acme) --eligibility_of--> cgpa`.

**Where the mapping lives.** link_class is a column supplied by the caller. Core
validates only that the class is one it knows. The link_type → link_class registry is
part of each domain adapter and is applied in the write flow (agents / api), never in
core. verified_at supports FR-16 (nightly re-check of weak links).

## Link classes (core) and link types (domains)
Core knows two **link classes** with fixed behaviour (ADR-0013). Each domain link type
maps to exactly one class.

| Class | Propagates a change | Copied to the new version on update | On forget of the parent (I7) |
|---|---|---|---|
| depends_on | yes | yes | dependent hard-deleted (cascade) |
| snapshot_of | no | no | link removed; dependent kept |

Forget always applies to a whole version chain, never to one version, and cascades
along depends_on links whose parent is in that chain. This is the behaviour ADR-0007
calls "cascading along derived_from links": in this model the dependency class is named
depends_on, and I7 reads accordingly.

| Link type | Class | Owner |
|---|---|---|
| depends_on_fact | depends_on | generic |
| depends_on_time_period | depends_on | generic |
| eligibility_of | depends_on | jobs |
| fit_of | depends_on | jobs |
| reminder_for | depends_on | jobs |
| criteria_from | depends_on | jobs |
| sent_with_resume | snapshot_of | jobs |

`sent_with_resume` is snapshot_of so that a new resume version never ripples into past
applications: the "correct non-update" case falls out of the copy rule. Provenance to a
source (a message or JD) is source_ref on the memory, not a link, because sources are
not memories.

## Ripple semantics (ADR-0013)
Propagation is **wave by wave**, and each wave is two commits:
1. The trigger is a memory write (new memory, new version, or expiry; ADR-0015). The
   write transaction also creates the ChangeEvent (trigger_kind, trigger_memory_id, and
   the old version's retirement if any), so even an empty ripple leaves history (I2).
2. The engine takes an explicit **seed set**: the new version for a write, the retired
   memory itself for expiry or retire. Wave 1 = dependents of the seeds along depends_on
   links, with **no status filter** (the copy rule keeps old versions out of the seed
   set, and the dependents of a retired memory are exactly what a retire must reach).
   Each becomes SUSPECT; commit one.
3. The Resolver decides keep / update / retire / ask for every memory in the wave. The
   decisions (tagged with the wave number) and resulting state changes commit as one
   transaction, appended to the ChangeEvent; commit two. A failed commit two rolls back
   to the committed SUSPECT state (NFR-4).
4. Only memories that were **updated or retired** seed the next wave. A **keep** halts
   that branch. An **ask** parks the memory in PENDING_USER; the engine then marks its
   depends_on subtree SUSPECT without resolving it (no LLM), so retrieval flags it while
   the user has not answered. When the user answers: a changed memory is a new write
   and starts a **new ripple** (trigger_kind=user_answer) whose waves cover the subtree;
   a "still holds" answer restores the marked subtree to VALID deterministically, with a
   ChangeEvent of trigger_kind=user_answer. *(assumed; author to confirm)*
5. Stop at an empty wave, or at the depth limit (configurable, default TBD in Phase 1),
   with a visited set for cycle safety. The ChangeEvent's completed_at is set.
The engine is a pure iterator: it emits a wave, receives decisions, emits the next wave.
It never calls an LLM (I3). The nightly sweep resumes ChangeEvents with no
completed_at older than a configurable age, so a crash between commits cannot strand
SUSPECT memories.

## Versioning (ADR-0014)
Update = new row + supersedes_id + old row RETIRED + the ChangeEvent. Inside the same
transaction:
- every **incoming** depends_on link to the old row is **copied** to the new row, so the
  new version has the same dependents; a dependent that is itself RETIRED (superseded)
  is history and is not copied; one copy per (dependent, type);
- every **outgoing** depends_on link of the old row is copied to the new row, re-pointed
  at each parent's latest version, so a second change to the parent still reaches the
  new version even if the Linker misses the link; the Linker may add links, never
  replace these;
- snapshot_of links stay on the old row.
A link is **history** when its parent is superseded (a row with supersedes_id = parent
exists). The inspector's "why is this held" and retrieval graph expansion skip history
depends_on links; snapshot_of links are shown always, since their parent is by design a
superseded version. The engine applies no such filter (see Ripple semantics, step 2).
A crash mid-update rolls back everything (NFR-4).

## ChangeEvent (ADR-0015)
id · user_id · trigger_kind (ripple | expiry | user_edit | user_answer) ·
trigger_memory_id · affected_ids · decisions[] · parked (asked memory id -> ids its ask marked
SUSPECT) · cost · latency_ms · trace_id · created_at · completed_at (null while the ripple is open)

Every state change has a trigger memory: a conversation or Scout write (ripple); the
expiring memory (expiry); a new version created_by user from the inspector (user_edit);
the PENDING_USER memory the user answered (user_answer). One ChangeEvent per ripple,
created in the trigger's write transaction and appended per wave. This is what makes
I2 testable per trigger kind, and completed_at is how the sweep finds ripples to resume.
When the trigger is a new version, its event also records the retirement of the version
it supersedes (the trigger's supersedes_id); no separate event is written for that.

## ForgetEvent
id · user_id · root_memory_id · deleted_ids · created_at
Forget is deletion, not a state change, so it has no ChangeEvent (I7).

## Decision
memory_id · wave (0 = deterministic restoration recorded by an answer, before any wave) ·
action (keep | update | retire | ask) · reason · evidence_refs · new_version_id ·
question (only an ask carries one; what the user is shown, FR-7)

## Tables outside the memory model
Delivery and pilot records live beside the memory tables, keyed by user. They never
hold beliefs, never ripple, and are erased by `DELETE /me` (FR-15).
- users, link codes (migration 0003, ADR-0040); resume candidates (0003, ADR-0043).
- delivery_log (0005, ADR-0095): user_id · kind (digest or alert kind) · key (day or
  opening memory id) · sent_at; one row per (user_id, kind, key).
- resume_uploads (0006, ADR-0097): the text layer of an uploaded resume so a fact's
  `resume:<id>#a-b` span resolves.
- pilot_feedback (0009, ADR-0105): id · user_id · target_memory_id (cascades with the
  memory) · kind (saved | applied | dismissed | question_useful | question_not_useful)
  · note · created_at; one row per (user_id, target_memory_id, kind), first statement
  wins. "applied" records the student's statement; nothing is applied anywhere (I6).

## Validity states
| From | To | When |
|---|---|---|
| none | VALID | write flow creates the memory |
| VALID | SUSPECT | in the current wave of a ripple, or below a memory that went PENDING_USER |
| VALID | RETIRED | valid_to passed (expiry sweep), or a user edit created a new version |
| SUSPECT | VALID | resolver decides keep, or the user answers "still holds" above it |
| SUSPECT | RETIRED | resolver decides retire, or update creates a new version |
| SUSPECT | PENDING_USER | resolver decides ask |
| PENDING_USER | VALID | user confirms it still holds |
| PENDING_USER | RETIRED | user says it no longer holds, or the answer creates a new version |
| any | deleted | forget API only (I7); whole version chain plus depends_on cascade |

**Retrieval (I1):** VALID is returned; SUSPECT and PENDING_USER only with a flag;
RETIRED never.

## Worked example
Facts: cgpa=7.6 (v1). Derived: `"not eligible for Acme (cutoff 7.8)" --eligibility_of--> cgpa`,
`criteria(cgpa filter) --criteria_from--> cgpa`.
Event: user writes cgpa=7.9 → cgpa v2 (supersedes_id = v1); v1 RETIRED; incoming
depends_on links copied to v2; ChangeEvent created. Seed set = {cgpa v2}.
Wave 1: affected = {eligibility(Acme), criteria} → SUSPECT, committed. Resolver:
eligibility → update to eligible (new version, whose outgoing link now points at
cgpa v2); criteria → update cutoff (new version). Committed, appended to the ChangeEvent.
Wave 2: dependents of the two new versions, e.g. recommendation("apply to Acme") → update.
Wave 3: empty. Scout re-runs because criteria changed.
One ChangeEvent (trigger_kind=ripple, trigger=cgpa v2) holds every decision with its
evidence (the user's message).

Temporary example: "busy with exams until 2026-11-30" is a fact with valid_to. It ripples
normally into availability. On 2026-12-01 the sweep retires it (trigger_kind=expiry),
seed set = {the retired fact}; wave 1 = availability (its dependent, reached because the
engine does not filter on parent status); the resolver restores availability. No LLM is
needed to detect expiry.

Forget example: "forget my CGPA" deletes cgpa v1 and v2, the eligibility and criteria
memories that depend on them, and their own dependents, and writes one ForgetEvent.
