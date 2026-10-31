# ripple.agents — Conversation and Tailor
Written 2026-10-19 for src/ripple/agents as built by WS-4 (ADR-0045, ADR-0046).

## 1. What it does
The Conversation agent turns one user message into one of four things: a fact written
through Intake, an answer built only from retrieved memories, a plan built the same
way, or an answer to a question the ripple had parked. The Tailor agent, for one
opening, says which of the student's real projects and skills to highlight, picking by
memory id from a candidate set it was shown. Both are LangGraph graphs whose only
outside contacts are the Store, the Retriever, Intake, the answers API and the Router.

## 2. Why it exists
FR-10 (answers via validity-aware RAG with citations), FR-7 (questions queued and
answered in conversation), FR-11 (tailoring that never invents). ADR-0005 and ADR-0023
put agents on LangGraph with a Postgres checkpointer. I4 (schema before use), I5 (no
invented facts) and I6 (no external action) shape every node. ADR-0045 and ADR-0046
record the designs.

## 3. How it works
- `conversation.ConversationAgent.turn(user_id, message)` invokes the graph on thread
  `user_id`. `_classify` sends the intent prompt, the message, the last six turns and
  the user's PENDING_USER memories to the Router for an `IntentVerdict`; `_route`
  picks the branch.
- `_tell` grounds the model's restatement (`_grounded`: any number in the statement
  or its structured value must appear in the message, else the message itself is
  recorded as prose), builds a `Statement(origin="conversation")` and calls
  `Intake.ingest`; the reply names what was recorded, updated, kept or already known, then lists every
  memory the ripple parked (`_questions_from` reads the event's `ask` decisions).
- `_answer` (ask and plan) calls `Retriever.search(include_flagged=True,
  expand_graph=True)`. Zero hits: a fixed "nothing recorded" reply, no model call. Else
  the evidence block (`agents.evidence.retrieved_block`: id, status, flagged, content,
  source refs) goes to the Router for an `AnswerVerdict` of claims. `_compose_answer`
  keeps a claim only if one of its evidence ids was retrieved this turn, appends
  "(unconfirmed)" when any cited memory is flagged, collects `Citation`s, and adds
  one line saying how many claims were left out.
- `_answer_question` accepts a memory id only if it is PENDING_USER for this user,
  then calls `answers.confirm_still_holds`, `answer_no_longer_holds` or
  `answer_with_correction` (passing the corrected structured value, grounded the
  same way); otherwise, or if the question was answered meanwhile (`NotPendingError`),
  it replies that it could not tell which question was meant and writes nothing.
- Thread state keeps only the last six turns (`_recent` reducer): the classifier reads
  no more, and the checkpoint is a copy of user text outside the forget API.
- `tailor.TailorAgent.suggest(user_id, opening_memory_id)`: `_gather` loads the
  opening (must be the user's, `Kind.OPENING`, not RETIRED), its field memories
  (subject `opening:<id>`), every project or skill fact from the store, plus the
  Retriever hits for "title company role skills" that describe the student
  (`_about_the_student`). `_suggest` asks for a `TailorVerdict`; highlights naming ids
  outside the candidates, or repeating one, are dropped and counted; opening evidence ids are filtered to the opening and its fields.
- `capabilities.Capability` is the closed list of what a graph may do; each agent
  declares its subset. `checkpoints.memory_saver` (tests) and
  `checkpoints.postgres_saver` (service start-up, runs LangGraph's `setup()`).

## 4. Trade-offs
- Claims, not prose. A model that forgets a citation loses a true claim; the student
  sees the count. Wrong when the pilot shows more true claims dropped than invented
  ones blocked; then the drop rule becomes a flag rule (ADR-0045, revisit).
- Dropping unknown ids instead of retrying: the schema was valid, the content was
  not; a filter is cheaper and predictable (same choice as the LLM linker).
- Zero hits means zero model calls. Wrong when the question is answerable from
  general knowledge; that is not this product's job (docs/00: not a general assistant).
- The Tailor scans the store for every project and skill rather than trusting
  retrieval recall. Wrong when a student has hundreds of skill facts; then the
  candidate set needs a pre-filter.
- The question text of an `ask` is not stored by the runner, so pending questions
  are shown as the memory's content plus the decision's reason. Contract request in
  the WS-4 handover.
- Grounding is numeric only. A restated skill or preference passes as written;
  numbers are where invention hurts most and are the cheapest to check. Wrong when the
  pilot shows models rewording non-numeric facts into something the student never said.
- The whole turn is one graph run; there is no interrupt for a clarifying question
  mid-turn. Fine for four intents; revisit if a multi-step intent arrives.

## 5. Failure modes and tests
| Failure | Test |
|---|---|
| Model claims a fact not in evidence | test_invariant_I5_conversation_marks_unsupported_claims |
| Tailor cites a memory that is not the student's | test_invariant_I5_tailor_cites_only_existing_memories |
| A tool that could act outside memory | test_invariant_I6_agents_expose_no_submit_or_browser_tool |
| Intent never matches the schema | test_invariant_I4_agent_rejects_invalid_llm_output |
| Answer or tailor output never matches | test_invariant_I4_conversation_rejects_invalid_answer_output, test_invariant_I4_tailor_rejects_invalid_output |
| Tell restates a number the student never wrote | test_tell_with_a_number_the_student_did_not_write_records_the_message |
| Corrected answer keeps the stale structured value | test_answer_question_corrected_updates_the_structured_value |
| Question answered between read and write | test_answer_question_answered_meanwhile_replies_instead_of_raising |
| Thread state grows without bound | test_checkpoint_keeps_only_the_recent_turns |
| Another opening's field offered as the student's skill | test_tailor_ignores_retrieved_fields_of_other_openings |
| Answer names a memory id that is not pending | test_answer_question_for_an_unknown_question_writes_nothing |
| Ripple parks a belief after a tell | test_tell_that_parks_a_belief_surfaces_the_pending_question |
| Nothing retrieved | test_ask_with_no_hits_answers_honestly_without_calling_the_model |
| Flagged evidence shown as fact | test_ask_renders_flagged_evidence_as_unconfirmed |
| History lost between turns | test_checkpoint_keeps_turn_history_across_two_turns |
| Threads shared between users | test_threads_are_per_user |
| Tailor writes | test_tailor_never_writes_to_the_store |
| Tailor on another user's or a retired opening | test_tailor_refuses_an_unusable_opening |

## 6. Interview questions
1. *Where exactly is I5 enforced for answers?* In `_compose_answer`: the reply is
   assembled from claims whose evidence ids are in the set retrieved this turn. The
   prompt asks for it; the code guarantees it.
2. *Why does the agent not ask the model to mark flagged memories itself?* The flag
   comes from `visible_for_retrieval` (I1) and is applied by code; a model can forget,
   code cannot.
3. *How is I6 tested without enumerating every possible tool?* Three ways: a closed
   `Capability` enum each agent declares against, the graph's node set compared to the
   ADR, and an AST scan of the package's imports against an allowlist.
4. *What does the checkpoint hold and what does it not?* The turn history and last
   verdict per user thread. Memory state lives in the Store; a write is final when its
   ChangeEvent commits whatever the checkpoint says (ADR-0023).
5. *Why is the Tailor allowed to import the jobs vocabulary when the Conversation
   agent is not?* FR-11 is a jobs feature (openings, projects, skills); conversation is
   domain-agnostic and takes `domain` as a parameter.

## 7. Exercise
Script a FakeLLM answer with one claim citing a VALID memory and a SUSPECT memory
together. Predict the exact reply text and the `flagged` value of each `Citation`
before running `test_ask_renders_flagged_evidence_as_unconfirmed` with your change.
