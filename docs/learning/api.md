# ripple.api — identity, inspector, confirmation flow, export and delete
Written 2026-10-19 for workstream WS-3 (docs/plans/parallel-execution.md).

## 1. What it does
Puts the core write flow and the inspector behind HTTP for the dashboard and the
Telegram worker: statements in, memories with their reasons and history out, questions
answered, resumes confirmed fact by fact, openings pasted, recommendations read, and
the user's whole record exported or deleted. Every call is scoped to the bearer token's
user.

## 2. Why it exists
FR-1 (resume confirmation), FR-3/FR-7 (questions), FR-12 (inspector), FR-15 and NFR-3
(export, delete, DPDP). ADR-0022 fixed the stack; ADR-0040 to ADR-0044 fix identity,
composition, inspector semantics, candidate storage and deletion. ADR-0006 says
invariants and auth are enforced at the server boundary; this module is that boundary
for HTTP.

## 3. How it works
- **Composition** (`app.py`, `services.py`, `wiring.py`): `create_app(services)` is the
  only constructor. `Services` carries store, clock, registry, Intake, runner, the
  user and candidate stores, an `EventLog`, and the injected contracts. Production
  builds it from the environment in `wiring.build_services`; tests build it from fakes
  in `tests/api/harness.py`. No globals, no settings in code.
- **Contracts** (`contracts.py`): `ResumeParser`, `CandidateStatements`,
  `OpeningParser`, `OpeningRecorder`, `EventLog`, plus `RecommendationSource` from the
  vocabulary. WS-1 and WS-2 implement them; the coordinator wires them in
  `wiring.default_adapters()`.
- **Auth** (`auth.py`): `HTTPBearer` → sha256 of the token → `UserStore
  .user_for_token_hash`. `owned_memory(store, user, id)` is the one place a memory id
  is dereferenced for a user: unknown or someone else's is 404.
- **Identity** (`ripple.storage.users`, `admin.py`, `directory.py`): `User`,
  `ApiToken` (hash only), `TelegramLinkCode` (one use, 15 minutes), `UserStore`
  protocol, `PostgresUserStore`, `link_telegram()` for the worker, the admin CLI that
  prints a token once, and `UserDirectoryAdapter` for the worker's digest loop.
- **Inspector** (`routers/memories.py`): list through `visible_for_retrieval` (I1),
  detail with `why` (parents, history links skipped, snapshots kept) and optional
  `history` (version chain + events mentioning any version), edit via
  `writes.update_memory` + `runner.run` as a `user_edit`, forget via `core.forget`.
- **Questions** (`routers/questions.py`): PENDING_USER memories with the ask decision
  from `events_asking`; answers map to `confirm_still_holds`, `answer_no_longer_holds`,
  `answer_with_correction`. `NotPendingError` is 409 through the error table.
- **Resume** (`routers/resume.py`, `ripple.storage.candidates`): PDF magic and size
  checks, parser, candidates stored pending; confirm builds a Statement through the
  injected builder and runs Intake; reject keeps the row. No memory before confirm (I5).
- **Openings, recommendations** (`routers/openings.py`, `routers/recommendations.py`):
  thin pass-throughs to the injected parser/recorder and ranking source; the API adds
  the user id and the clock.
- **Me** (`routers/me.py`): profile, link code, export (everything, including RETIRED
  and events), delete (forget loop, candidates, user).
- **Errors** (`errors.py`): one table from Ripple exception types to statuses; routers
  raise core exceptions as they are.

## 4. Trade-offs
- 404 instead of 403 across users hides id existence at the cost of a less specific
  error for a buggy client. Chosen for tenant isolation.
- Edit bypasses Intake's change detection and Linker (ADR-0042): correct versioning
  for prose memories mattered more than new links on edit.
- `EventLog` duplicates two queries the Store should own; it is a stop-gap with a
  contract change request, not a design.
- Candidates keep rejected rows forever; a retention sweep is a later task.
- Tokens never expire; fine for a hand-enrolled pilot, wrong for a public beta.

## 5. Failure modes and tests
| Failure | Test |
|---|---|
| Another user reads, edits, answers or forgets a memory | test_users_cannot_see_or_touch_each_others_memories |
| A RETIRED memory leaks through list, detail, questions | test_invariant_I1_api_never_returns_retired |
| An endpoint acts on an external site | test_invariant_I6_api_has_no_apply_endpoint (route allowlist) |
| A resume fact becomes a memory without confirmation | test_upload_stores_candidates_as_pending_and_writes_no_memory |
| Invalid LLM output is half-applied | test_invalid_llm_output_is_a_503_not_a_partial_write |
| Edit of a pending memory skips the answer flow | test_edit_of_a_pending_memory_is_refused_and_points_at_answers |
| Link code reused or expired | test_telegram_link_code_is_one_time_and_expires |
| Delete leaves data or a live token | test_delete_me_forgets_everything_and_revokes_the_token |
| Token stored in clear | test_create_user_prints_the_token_once_and_stores_only_its_hash |
| Migration drifts from tables | test_migration_0003_matches_users_tables (slow) |
| Settings guessed in code | test_missing_setting_names_the_variable |

## 6. Interview questions
1. *Why is identity in `ripple.storage` and not `ripple.api`?* Storage may import only
   core; the Postgres implementation needs the models, so they live where storage can
   see them and the API imports them.
2. *Why does the edit endpoint not use Intake?* The user named the memory; detection
   would be guessing, and an LLM "NEW" verdict on prose would create a duplicate
   instead of a version.
3. *What stops a client from writing under another user's id?* Request bodies forbid
   extra fields and never carry a user id; the token decides.
4. *Is DELETE /me a complete erasure?* Memories, links, candidates, tokens, codes and
   the user go; ForgetEvents stay by design; ChangeEvents remain until the Store gains
   a per-user event deletion (ADR-0044, open problem).
5. *How does the worker learn a user's chat id?* The user asks the API for a code,
   types it into the bot, the worker calls `link_telegram`, which consumes the code.

## 7. Exercise
Add a route `POST /applications/{id}/apply` to any router, run
`uv run pytest tests/api -q`, and read how the I6 test refuses it. Remove it.
