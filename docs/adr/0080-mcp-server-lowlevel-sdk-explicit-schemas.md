# ADR-0080: MCP server on the SDK's low-level `Server`, explicit Pydantic tool schemas, seven tools
Status: Accepted under the autonomous mandate · Date: 2026-10-24 · Workstream WS-11
Implements ADR-0006 (expose memory tools over MCP). Depends on ADR-0040 (identity),
ADR-0042 (inspector semantics) and the C2 retrieval contract (ADR-0026, ADR-0050).

## Context
FR-14: search, save, update, forget, explain over the Model Context Protocol so that
agents other than ours can use Ripple's memory. ADR-0006 says invariants and auth are
enforced at the server boundary. The coordinator added `mcp==2.3.0`. That SDK offers two
server layers: `MCPServer` (decorator-registered functions whose JSON schemas are derived
from signatures) and the low-level `mcp.server.Server` (explicit `tools/list` and
`tools/call` handlers). The derived argument model of `MCPServer` does not forbid unknown
fields, and the SDK does not validate arguments against the published schema on the
low-level path at all; I4 demands that every input crossing into core is parsed into a
schema before use, so the server has to own validation either way.

## Decision
1. **Low-level `Server`, explicit schemas.** `ripple.mcp_server.server.build_server`
   returns an `mcp.server.Server`. Each tool is a row in one table: name, description,
   a Pydantic input model with `extra="forbid"` and an output model. `tools/list`
   publishes `model_json_schema()` of both, so `additionalProperties: false` is on the
   wire; `tools/call` validates the arguments into the input model first and runs the
   operation only on a valid instance. A validation failure is an `is_error` result
   with code `invalid_arguments`, never a partial call.
2. **Seven tools.** `ripple_search(query, k, include_flagged)` → `Retriever.search`
   for the caller's user, then `visible_for_retrieval` again at the boundary (I1 holds
   even against a misbehaving retriever) and a user-id check on every hit.
   `ripple_save(content, kind, structured?, source_ref?)` → `Intake.ingest` of a
   `Statement(origin="agent", created_by="agent")`; `kind` is limited to the kinds an
   agent may write raw (`fact`, `derived`, `criteria`; openings and applications are
   built by the jobs adapter). It returns the memory, the change kind, the number of
   links written, the event id and the questions that write's ripple parked.
   `ripple_update(memory_id, content, structured?, valid_to?)` → `Intake.edit` with
   `created_by="agent"`, under ADR-0042's rules: RETIRED is not found, PENDING_USER is a
   `conflict` that points at `ripple_answer`. `ripple_forget(memory_id)` →
   `ripple.core.forget.forget` (I7), returning every deleted id and the ForgetEvent id.
   `ripple_explain(memory_id)` → the memory with a `visibility` value (`visible`,
   `flagged`, `hidden` for RETIRED, which is reachable here because explain is the
   history view, as `history=true` is for the API), `why` (live parents: superseded
   depends_on parents skipped, snapshot_of parents kept), `history` (the version chain)
   and `events` (every ChangeEvent mentioning any version, with decisions, reasons and
   questions). `ripple_questions()` → `ripple.core.answers.pending_questions`.
   `ripple_answer(memory_id, reply, content?, structured?, valid_to?)` → the three
   answer functions; a correction needs content.
3. **Errors.** Anticipated failures are `CallToolResult(is_error=True)` with
   `structured_content={"error": <code>, "detail": ...}` so a model can read and
   self-correct: `not_found` (unknown id, another user's id, RETIRED where the API
   answers 404), `conflict` (`NotPendingError`, edit of a pending memory),
   `invalid_arguments`, `llm_unavailable` and `llm_output_invalid` (the latter two carry
   `open_change_event_ids`, as the API's 503 does, because an LLM can fail after the
   write committed). An unexpected exception is logged and reported as
   `internal_error` without its message. Missing identity is a protocol error (ADR-0081).
4. **Explain reuses the inspector's rules.** `why` and the event filter call the
   functions the API's memories router already has (`_why`, `_mentions`) rather than
   restating ADR-0042 in a second place; the handover asks the coordinator to make
   them public in a shared module.

## Alternatives considered
- **`MCPServer` with decorated functions** — less code and nicer signatures, but its
  argument model ignores unknown fields unless its private `fn_metadata` is patched,
  and the server would own neither the schema nor the validation step I4 asks for. Lost.
- **A single generic `ripple` tool with an `action` field** — fewer schemas, but models
  pick tools by name and description; one tool per verb is what MCP clients expect. Lost.
- **Protocol errors for not-found and conflicts** — the spec says errors a model can
  correct belong inside the result with `is_error`; protocol errors are for "could not
  serve the call" (no identity, unknown tool). Followed the spec.
- **Accepting every memory kind in `ripple_save`** — an opening written raw would lack
  the structured requirements the ranking reads; restricted, with the list in one
  constant. Revisit when a domain other than jobs is configured.

## Consequences
- Two schema sources (this table, the API's `schemas.py`) describe similar shapes; they
  are kept apart on purpose because the MCP outputs carry more (evidence, decisions)
  and the inputs less (no origin, no sensitivity).
- Output models embed core models (`Memory`, `Decision`) directly, so a change to those
  changes the published output schema; the schema test pins the tool names and the
  `additionalProperties` rule, not the field lists.
- No resources or prompts are exposed; the tools are the product surface.

## Revisit if
The SDK's high-level server gains strict argument models, or a second domain needs a
different set of writable kinds.
