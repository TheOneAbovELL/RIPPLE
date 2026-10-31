# ADR-0045: Conversation agent: one LangGraph turn, strict intent, evidence-only answers
Status: Accepted under the autonomous mandate · Date: 2026-10-19

## Context
FR-10 asks for answers via validity-aware RAG with citations; FR-7 for queued
questions the user can answer in conversation; I5 forbids invented facts; I6 forbids
acting on external sites; ADR-0005 and ADR-0023 fix LangGraph with a Postgres
checkpointer in production and the in-memory saver in tests. The write flow already
exists (`ripple.core.intake.Intake`) and so does the answers API
(`ripple.core.answers`); the agent must not re-implement either.

## Decision
1. **One graph, one turn.** `ripple.agents.conversation.ConversationAgent` is a
   LangGraph `StateGraph` whose thread id is the user id. Nodes: `classify`, then one
   of `tell`, `answer` (ask and plan), `answer_question`. Every node is plain Python;
   the only model calls go through `Router.complete` with a schema (I4).
2. **Strict intent.** `classify` asks the Router for an `IntentVerdict`
   (`ask | tell | plan | answer_question`). The schema's validator ties the payload to
   the intent (a tell carries the statement, an answer_question carries a pending memory
   id and the answer kind), so a half-formed verdict is retried, then rejected, before
   anything is written.
3. **Tell writes through Intake only**, with `origin="conversation"`, and the reply
   lists what was recorded plus every memory the ripple parked in PENDING_USER. The
   model's restatement is grounded first: if it, or its structured value, contains a
   number the message does not, the student's own message is recorded as prose and the
   structured form is dropped (I5). The same rule applies to a corrected answer.
4. **Answers are built from claims, not prose.** The answer prompt returns
   `AnswerVerdict{claims: [{text, evidence_ids}]}`. The agent keeps a claim only when
   at least one of its evidence ids is a memory the retriever returned for this turn;
   every other claim is dropped and the reply says how many were left out. A claim
   resting on a SUSPECT or PENDING_USER memory is rendered "(unconfirmed)" by code,
   not by the model. Zero retrieval hits produce an honest "nothing recorded" reply
   with no model call.
5. **answer_question routes to `ripple.core.answers`** and only for a memory that is
   PENDING_USER for this user; any other id, or one answered between the read and the
   write (`NotPendingError`), is refused without a write. A corrected answer passes
   its structured form, so content and value never disagree.
6. **Capabilities are declared, not discovered.** The agent exposes the set of things
   its graph can do (`Capability`); the I6 test checks it against an allowlist and
   scans the package's imports for anything that could reach the network.

## Alternatives considered
- Free-text answer plus a second "checker" model call — doubles cost and the checker
  can be fooled the same way; the claim schema makes support a structural property.
- Flag unsupported claims instead of dropping them — keeps a possibly invented fact in
  front of a student with a warning label; dropping and disclosing is safer (I5).
- A ReAct agent with tools (retrieve, write, answer) — flexible but the tool surface is
  exactly what I6 must police, and the control flow is harder to test deterministically.
- No checkpointer in the conversation graph — loses the turn history that lets the
  classifier read "yes" after a question; ADR-0023 already pays for the saver.

## Consequences
- A true claim whose citation the model forgot is dropped. Acceptable: the student
  sees the count and can ask again; the alternative is trusting uncited text.
- A claim that cites a real memory but misreads it is not caught; the citation is
  shown so the inspector can be checked. A judge-based check is a Tier B idea.
- Thread state is a second copy of user text (recent turns and the last verdict)
  in LangGraph's tables, outside the forget API (I7). It is bounded to the turns the
  classifier reads; deleting the thread on forget is a contract request in the WS-4
  handover.
- The grounding rule is numeric only: a restated skill or preference passes as the
  model wrote it. Numbers are where invention does the most harm (CGPA, cutoffs,
  dates) and the cheapest to check structurally.
- The prompts speak of "the student" and subject "student": the agent takes `domain`
  as a parameter, but its v1 prompts are jobs-flavoured. A second domain needs a v2.
- The question text of an `ask` decision is not stored by the runner (`Decision` has
  no question field), so pending questions are shown as the memory's content plus the
  decision's reason. Contract request filed in the WS-4 handover.

## Revisit if
The pilot shows the drop rule removing more true claims than it blocks invented ones
(measure: dropped claims per answer in the bench, Phase 3), or LangGraph's state
serialisation rejects the typed reply objects.
