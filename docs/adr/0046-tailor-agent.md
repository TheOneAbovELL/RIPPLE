# ADR-0046: Tailor agent: read-only, picks from id-validated candidates
Status: Accepted under the autonomous mandate · Date: 2026-10-19

## Context
FR-11: suggest which real projects to highlight for an opening; never invent (I5).
docs/02 gives the Tailor read-only permission. The model is good at matching a
project description to a job's required skills and bad at being trusted with the
project list itself.

## Decision
1. `ripple.agents.tailor.TailorAgent` is a two-node LangGraph (`gather`, `suggest`)
   that never opens a store transaction. `gather` loads the opening memory (must
   belong to the user, be `Kind.OPENING`, and not be RETIRED), its field memories
   (subject `opening:<id>`), and the candidate set: every profile fact with attribute
   `project` or `skill` from the store, unioned with those Retriever hits for a
   query built from the opening's fields that describe the student (not an opening,
   application or criteria memory; structured only with subject `student`). Flagged
   memories are included and marked.
2. `suggest` asks the Router for `TailorVerdict{highlights: [{memory_id, reason,
   opening_evidence_ids}]}`. A highlight whose memory id is not in the candidate set,
   or repeats one already kept, is dropped and counted; opening evidence ids are filtered to the opening and its
   fields. The output is `TailorSuggestions` with one `Suggestion` per kept highlight,
   carrying the memory content, the reason, the evidence ids and a flagged marker.
3. With no candidates, the agent returns an empty list and a note without a model
   call: there is nothing real to highlight.

## Alternatives considered
- Let the model write the tailored paragraph — I5 cannot be checked on prose.
- Rules only (skill-name overlap) — misses "built a CNN for X" matching "deep learning"; kept
  as the candidate pre-filter, not the decision.
- Persist suggestions as derived memories with `fit_of` links — useful for the ripple
  (a changed project would update the suggestion) but a write path, outside the
  read-only permission docs/02 gives the Tailor; a later ADR may add it to the Curator.

## Consequences
- Suggestions are only as complete as the candidate set; the store scan guarantees
  every recorded project is offered, whatever retrieval recall is.
- The agent needs the jobs vocabulary (`Kind`, `ProfileAttribute`, `opening_subject`),
  so unlike the Conversation agent it is domain-specific by design (FR-11 is).

## Revisit if
A second domain needs a Tailor (then the candidate rule becomes an adapter hook), or
the pilot shows suggestions citing real memories that do not support the reason.
