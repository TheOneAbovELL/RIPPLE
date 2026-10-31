# WS-4 handover: Conversation and Tailor agents (LangGraph)
Status: **Locally verified** · 2026-10-20 (code review applied) · ADR-0045, ADR-0046

## What was built
- `src/ripple/agents/`
  - `conversation.py` — `ConversationAgent(store, clock, router, intake, retriever,
    runner, checkpointer, domain, fact_kind="fact", k=8)`;
    `await agent.turn(user_id, message, message_id=..., trace_id=...) ->
    ConversationReply(intent, text, citations, recorded_memory_id, questions,
    dropped_claims)`. StateGraph `classify -> tell | answer | answer_question`,
    thread id = user id, thread state bounded to the last 6 turns. Tasks `intent`
    (schema `IntentVerdict`) and `conversation` (schema `AnswerVerdict`), prompts
    `intent.v1`, `conversation.v1`.
  - `tailor.py` — `TailorAgent(store, router, retriever, k=10)`;
    `await agent.suggest(user_id, opening_memory_id) -> TailorSuggestions(
    opening_memory_id, suggestions, dropped, note)`; raises `OpeningUnavailableError`.
    StateGraph `gather -> suggest`, no checkpointer, never opens a transaction. Task
    `tailor`, schema `TailorVerdict`, prompt `tailor.v1`.
  - `capabilities.py` — `Capability` enum (closed list of what a graph may do; I6).
  - `checkpoints.py` — `memory_saver()` for tests; `postgres_saver(dsn)` async context
    manager for the service (runs LangGraph `setup()`; psycopg DSN, not a SQLAlchemy URL).
  - `evidence.py` — evidence blocks with the retrieval flag and source refs.
- `src/ripple/llm/schemas/conversation.py` (`IntentVerdict`, `Claim`, `AnswerVerdict`),
  `src/ripple/llm/schemas/tailor.py` (`Highlight`, `TailorVerdict`).
- `src/ripple/llm/prompts/intent.v1.md`, `conversation.v1.md`, `tailor.v1.md`.
- `tests/fakes/retriever.py` — `ScriptedRetriever(*hits)`, `hit(memory, ...)`,
  `SearchCall`. Honours I1 through `visible_for_retrieval` and records every call.
- `tests/agents/` — `wiring.py` (shared offline wiring), `test_conversation.py` (20),
  `test_tailor.py` (11), `test_invariants_agents.py` (7, the four named ones included),
  `test_schemas.py` (7), `test_checkpoints.py` (2). 47 tests.
- `docs/adr/0045-conversation-agent.md`, `docs/adr/0046-tailor-agent.md`,
  `docs/learning/agents.md`.

## Design in one paragraph each
**Conversation (ADR-0045).** The classifier's schema ties the payload to the intent
(a tell needs a statement; an answer_question needs a pending memory id and an answer
kind; structured is allowed only on a tell or a corrected answer), so a half-formed
verdict is retried then rejected before any write. A tell is grounded first: if the
model's restatement or structured value holds a number the message does not, the
student's own message is recorded as prose. It then goes through `Intake.ingest` with
`origin="conversation"`, and the reply lists every memory the ripple parked in
PENDING_USER. Ask and plan retrieve with `include_flagged=True`; zero hits give a fixed
honest reply and no model call; otherwise the model returns claims with evidence ids
and the agent keeps only claims citing a memory retrieved this turn, renders
"(unconfirmed)" when a cited memory is flagged, and discloses the number dropped (I5
by construction). answer_question is accepted only for a memory that is PENDING_USER
for this user, routes to `ripple.core.answers` (a correction carries its structured
value), and turns a concurrent `NotPendingError` into a reply.

**Tailor (ADR-0046).** Read-only. Candidates are every project or skill fact in the
store plus the retrieval hits for "title company role skills" that describe the
student (no openings, applications or criteria; structured only with subject
`student`). The model picks by id; ids outside the candidate set, or repeats, are
dropped and counted; opening evidence ids are filtered to the opening and its fields.
No candidates means no model call.

## How consumers call it
```python
from ripple.agents.checkpoints import memory_saver, postgres_saver
from ripple.agents.conversation import ConversationAgent
from ripple.agents.tailor import TailorAgent

async with postgres_saver(dsn) as saver:            # service start-up; tests: memory_saver()
    agent = ConversationAgent(store=store, clock=clock, router=router, intake=intake,
                              retriever=retriever, runner=runner, checkpointer=saver,
                              domain="jobs")
    reply = await agent.turn(user_id, text, message_id="tg:123")
    for q in reply.questions: ...                   # PENDING_USER memories to confirm

tailor = TailorAgent(store=store, router=router, retriever=retriever)
suggestions = await tailor.suggest(user_id, opening_memory_id)
```
Router config needs tasks `intent`, `conversation`, `tailor`.

## Verification (run 2026-10-20, paths restricted to WS-4 ownership)
```
$ uv run ruff check src/ripple/agents tests/agents tests/fakes/retriever.py src/ripple/llm/schemas/conversation.py src/ripple/llm/schemas/tailor.py
All checks passed!
$ uv run ruff format --check src/ripple/agents tests/agents tests/fakes/retriever.py src/ripple/llm/schemas/conversation.py src/ripple/llm/schemas/tailor.py
16 files already formatted
$ uv run pyright src/ripple/agents tests/agents tests/fakes/retriever.py src/ripple/llm/schemas/conversation.py src/ripple/llm/schemas/tailor.py
0 errors, 0 warnings, 0 informations
$ uv run pytest tests/agents -q
...............................................                          [100%]
47 passed in 2.39s
```
Full fast suite at the same time, read-only: `uv run pytest -m "not slow" -q` →
`865 passed, 43 deselected, 31 xfailed in 14.34s` (the xfails are the human-owned
WaveEngine). Earlier failures in sibling directories have cleared.

Mutation check: each review fix was reverted in turn and its new test went red
(structured correction, other openings' fields, bounded turns, ungrounded number,
answered-meanwhile race); both I5 invariant tests also go red under a mutation that
lets an unsupported claim or unknown id through.

## Code review (code-reviewer subagent, 2026-10-20) and what was done
- **Blocker — corrected answer kept the stale structured value.** Fixed: the schema
  allows `structured` on a corrected answer, the agent passes it to
  `answer_with_correction`, the v1 intent prompt asks for it.
- **Tailor offered other openings' fields as the student's skills.** Fixed:
  `_about_the_student` filters retrieval hits.
- **Checkpoint kept every raw message forever.** Fixed: `_recent` reducer bounds the
  thread to 6 turns; ADR-0045 records that thread state is a copy of user text
  outside forget; contract request 3 below.
- **No test for `no_longer_holds`.** Added.
- **Tell could record a model-invented number.** Fixed: numeric grounding rule
  (ADR-0045 §3), tested both ways.
- Minor, done: `NotPendingError` race handled; TEMPORARY, all-claims-dropped and
  query-fallback tests; I4 test split in three; I6 import check is now an explicit
  allowlist; tailor test no longer touches private store attributes; `waves`
  keyword-only in the wiring; "return no claims" in the answer prompt; drop
  wording covers repeats.
- Minor, not done: `evidence.py` duplicates most of `ripple.llm.evidence` (the shared
  module is coordinator-owned; adding a `flagged` key there is a small follow-up).
  The I5 conversation test keeps the name the brief fixed, although the behaviour is
  drop-and-disclose; its docstring says so. `_gather` was not split.

## Contract change requests (coordinator-owned files)
1. **`ripple.core.models.Decision` has no `question` field.** `RippleRunner._apply_one`
   builds the ASK decision from `resolution.reason` only, so the question text the
   resolver wrote is never stored. The conversation agent shows pending questions as
   "Does this still hold? <memory content> (<decision reason>)". Request: add
   `question: str | None` to `Decision` (set exactly when action is ask, mirroring
   `Resolution`), fill it in `_apply_one`, and the agent will read it.
2. **No core API lists a user's open questions with their reasons.** The agent uses
   `memories_for_user(user_id, [PENDING_USER])` and, for a fresh event, its decisions.
   WS-3's API will want the same; a `pending_questions(user_id)` helper in
   `ripple.core.answers` returning (memory, asking event, reason) would serve both.
3. **Forget should also delete the user's agent thread (I7, DPDP).** The checkpoint
   holds the last 6 messages verbatim. Whoever calls the forget-all / export-delete
   flow (FR-15, WS-3) should also run `await checkpointer.adelete_thread(user_id)`.
4. **Shared evidence formatting.** Optional: add `flagged` to
   `ripple.llm.evidence.memories_block` rows so `ripple.agents.evidence` can reuse it.
5. **Retrieval (C2) and vocabulary (C1)** are consumed as written; no change needed.
   Agents always call with `include_flagged=True, expand_graph=True` and cite
   `RetrievedMemory.evidence`.

## Open problems
- `postgres_saver` is constructed in tests but never connected (NFR-1). It needs a
  slow test once a database is available: open it, run two turns, reopen, assert the
  thread state survived.
- The Conversation agent is one graph run per turn with no interrupt; a clarifying
  question mid-turn is a reply, not a LangGraph interrupt.
- A claim that cites a real memory but misreads it is not caught (ADR-0045,
  consequences). The citation is shown so the inspector can be checked.
- Grounding is numeric only; reworded non-numeric facts pass.
- `fact_kind` for tells is `"fact"`; a tell that is really a derived belief ("I am
  eligible for Acme") is still written as a fact.
- The v1 prompts say "student"; a second domain needs v2 prompts.

## Suggested commit message
agents: conversation and tailor LangGraph agents — FR-10/FR-11 with I5 enforced by
claim citation, numeric grounding and id validation, I6 by a closed capability set,
bounded per-user checkpoints (ADR-0045, ADR-0046)
