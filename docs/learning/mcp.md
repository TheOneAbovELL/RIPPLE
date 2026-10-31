# ripple.mcp_server — Ripple's memory as MCP tools
Written 2026-10-24 for workstream WS-11 (docs/plans/production-plan.md), ADR-0080 to
ADR-0082.

## 1. What it does
Lets any agent that speaks the Model Context Protocol search, save, update, forget and
explain one user's memories, and list or answer the questions Ripple parked for that
user. Every call is scoped to the bearer token's user and passes the same boundary
rules the HTTP API enforces: retired memories never come back from search (I1), nothing
is written until the arguments parse into a schema (I4), deletion goes only through the
forget API (I7). It serves over stdio for a locally launched client and over stateless
streamable HTTP for a hosted one.

## 2. Why it exists
FR-14 and ADR-0006: Ripple is a consistency layer other agents should be able to use,
and MCP is the standard those agents speak. ADR-0040 fixes identity as admin-issued
hashed bearer tokens; ADR-0041 fixes `Services` as the one composition object;
ADR-0042 fixes what "explain" and "edit" mean. The MCP server adds no second rule of
its own: it is a thin boundary over Intake, forget, answers, the Retriever and the
inspector's "why".

## 3. How it works
- **Server** (`server.py`): the SDK's low-level `mcp.server.Server`, not its decorator
  layer, because the published input schemas must forbid unknown fields and the server
  must validate before it acts (ADR-0080). `SPECS` is a table of seven `ToolSpec`
  rows (name, description, input model, output model, operation). `tools/list` emits
  `model_json_schema()` of both models; `tools/call` looks the tool up, reads the user
  from the identity contextvar, validates the arguments into the input model, runs the
  operation, and returns `CallToolResult` with the output model as
  `structured_content` (and its JSON as text). Failures are `is_error` results whose
  structured content is `{"error": code, "detail": ...}`.
- **Schemas** (`schemas.py`): `ToolInput` sets `extra="forbid"`; `SearchIn` (query, k
  ≤ 50, include_flagged), `SaveIn` (content, kind ∈ fact|derived|criteria, structured,
  source_ref), `UpdateIn` (memory_id, content, structured, timezone-aware valid_to),
  `ForgetIn`, `ExplainIn`, `QuestionsIn`, `AnswerIn` (reply, content required for a
  correction). Outputs: `SearchOut`, `WriteOut` (memory, change kind, links written,
  event id, the questions that write parked), `ForgetOut` (deleted ids, event id),
  `ExplainOut` (memory, status, visibility, why, history, events with decisions),
  `QuestionsOut`, `AnswerOut`, `ErrorOut`.
- **Identity** (`identity.py`): `resolve_user` = `hash_token` + `user_for_token_hash`,
  the API's own rule. A `TokenSource` reads the raw token per request: the
  `Authorization` header of the Starlette request the SDK attaches to the context (HTTP),
  `RIPPLE_MCP_TOKEN` from the environment (stdio), a holder (tests). `BearerIdentity`
  is server middleware: it binds the user to a contextvar around `call_next`, raises a
  JSON-RPC `INVALID_REQUEST` "unauthorized" for `tools/call` without one, and lets
  discovery through. `current_user()` is what the call handler reads.
- **Operations** (`tools.py`, `RippleTools`): `search` calls the Retriever for the
  user, drops any hit that is not the user's, and runs `visible_for_retrieval` once
  more so I1 holds even if a retriever misbehaves. `save` builds a `Statement` with
  `origin="agent"`, `created_by="agent"` and runs `Intake.ingest`; the receipt lists the
  pending questions whose event is this write's. `update` dereferences the memory
  through `_owned` (unknown or another user's id → `not_found`), refuses RETIRED
  (`not_found`) and PENDING_USER (`conflict`, pointing at `ripple_answer`), then runs
  `Intake.edit` as the agent, keeping `valid_to` unless given. `forget` calls
  `ripple.core.forget.forget` and returns the ForgetEvent's ids. `explain` returns the
  memory with `visibility` (`visible`, `flagged`, `hidden` for RETIRED, which is
  reachable here as the history view), `why` from `ripple.api.inspector.why` (superseded
  depends_on parents skipped, snapshot_of parents kept), the version chain, and every
  ChangeEvent that mentions any version. `questions` and `answer` wrap
  `ripple.core.answers`. LLM failures become `llm_output_invalid` / `llm_unavailable`
  with the user's open ChangeEvent ids, since the write may have committed before the
  model failed (ADR-0013).
- **HTTP** (`http.py`): `streamable_http_app(server, user_store, host, path)` is the
  SDK's Starlette app (`json_response=True`, `stateless_http=True`) wrapped in
  `BearerGate`, a pure ASGI middleware that answers 401 with `WWW-Authenticate: Bearer`
  unless the header maps to a user. The app's lifespan runs the SDK session manager.
  `host` is also what the SDK's DNS-rebinding guard keys on: for a loopback bind it
  accepts only localhost `Host` headers (421 otherwise), so behind Caddy the server
  binds 0.0.0.0 inside its container and the proxy is the boundary.
- **Wiring and entry point** (`wiring.py`, `__main__.py`): `McpSettings.from_env`
  reads `RIPPLE_MCP_TRANSPORT|HOST|PORT|PATH`; `production_services` calls
  `ripple.api.wiring.build_services` and returns its `Services.retriever` (one engine,
  since checkpoint C3). `main` parses flags over the environment, refuses stdio
  without `RIPPLE_MCP_TOKEN`, builds the server with the matching token source, and
  runs `stdio_server` or uvicorn. The builders and runners are injectable, so the CLI
  is tested without a database.

## 4. Trade-offs
- Low-level server over the decorator API: more lines, but the schema and the
  validation step are ours and visible; the decorator layer would have accepted
  unknown fields silently.
- Errors inside the result (`is_error`) rather than protocol errors: a model can read
  `not_found` and try another id; only "no identity" and "unknown tool" are protocol
  errors, as the spec intends.
- Stateless HTTP: no elicitation, sampling or progress; none of the tools needs them,
  and a restart loses nothing. Wrong once a tool must ask the client something.
- `ripple_save` accepts only fact, derived and criteria: an opening written raw would
  bypass the jobs adapter's structure. Revisit for a second domain.
- The HTTP gate and the middleware both look the token up: two cheap queries per call
  against threading the gate's result into the JSON-RPC context.
- `why` and the event filter are imported from the API router's private functions
  rather than copied: one statement of ADR-0042, at the cost of a cross-module
  private import until the coordinator lifts them (handover request).

## 5. Failure modes and tests
| Failure | Test |
|---|---|
| RETIRED leaks through search, or a leaky retriever is trusted | test_invariant_I1_mcp_search_never_returns_retired |
| Forget misses a version or a dependent, or leaves no audit | test_invariant_I7_mcp_forget_cascades_and_logs |
| Invalid LLM output half-applied on save | test_invariant_I4_mcp_save_with_invalid_llm_output_writes_nothing |
| A tool that applies or submits for the user slips into the listing | test_invariant_I6_mcp_exposes_no_apply_or_submit_tool |
| Missing, wrong or revoked token reaches a tool | test_tool_calls_without_a_resolvable_token_are_refused, test_a_revoked_token_stops_working_on_the_next_call |
| Another user's id is readable or writable | test_users_cannot_see_or_touch_each_others_memories |
| Unknown field accepted (a smuggled user_id) | test_every_tool_rejects_unknown_fields_before_touching_the_store |
| Schema drift: a tool without strict input or typed output | test_tool_listing_publishes_strict_input_schemas_and_output_schemas |
| Edit of a pending or retired memory | test_update_refuses_unknown_retired_foreign_and_pending_memories |
| Naive valid_to accepted | test_update_keeps_valid_to_unless_given_and_rejects_a_naive_one |
| Parked question not reported to the writer | test_save_returns_the_questions_its_ripple_parked |
| Explain shows a history parent or misses the question | test_explain_shows_live_parents_history_and_decisions_with_questions |
| HTTP without a token opens a session | test_http_requests_without_a_valid_bearer_token_are_401 |
| HTTP end to end with a token | test_http_client_with_a_valid_token_calls_tools_as_that_user |
| stdio started without a token; bad settings | test_main_serves_stdio_only_with_a_token_in_the_environment, test_settings_read_the_environment_and_name_a_bad_value |

## 6. Interview questions
1. *Why not the SDK's `MCPServer` decorators?* Their argument model ignores unknown
   fields and the schema is derived behind our back; I4 wants the boundary to own the
   parse. The low-level server lets the Pydantic models be the schema.
2. *Where is the user decided for a stdio connection?* The client sets
   `RIPPLE_MCP_TOKEN` when it launches the process; the middleware hashes and looks it
   up on every call, so a revoked token stops working without a restart.
3. *Why does `ripple_explain` return a RETIRED memory when `ripple_search` never
   does?* Search is retrieval (I1). Explain is the history view, the same as the API's
   `history=true`; it says `visibility: hidden` so the caller cannot mistake it.
4. *A save returns `llm_output_invalid`. Was anything written?* Possibly: Intake
   writes the memory before the ripple runs. The error carries the user's open
   ChangeEvent ids; the nightly sweep resumes them (ADR-0013).
5. *How does another user's id get `not_found` and not `forbidden`?* `_owned`
   compares the memory's `user_id` with the caller's and raises the same failure as
   for an unknown id (ADR-0040), so the server never confirms an id exists.

## 7. Exercise
Add an eighth row to `SPECS` for a `ripple_history(memory_id)` tool that returns only
the version chain. Run `uv run pytest tests/mcp_server -q` and watch
`test_tool_listing_publishes_strict_input_schemas_and_output_schemas` fail on the tool
name set; decide whether the tool earns its place (hint: `ripple_explain` already
returns `history`). Remove it.
