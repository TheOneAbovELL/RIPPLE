# WS-3 handover: API, identity, inspector, confirmation flow
Status: **Locally verified** (offline; integration needs `default_adapters()` wired) ·
2026-10-19 · ADR-0040 to ADR-0044

## What was built
- `src/ripple/api/`
  - `app.py` — `create_app(services)`; `create_production_app()` (the uvicorn factory
    `infra/entrypoint.sh` names, lazy import of wiring).
  - `services.py` — `Services` dataclass; `services_of(request)`.
  - `contracts.py` — `ResumeParser`, `CandidateStatements`, `OpeningParser`,
    `OpeningRecorder` (+ `OpeningWritten`), `EventLog`; re-exports `RecommendationSource`,
    `CandidateFact`, `ParsedOpening`, `Recommendation`; `ResumeUnparseableError`,
    `OpeningUnparseableError`.
  - `auth.py` — `HTTPBearer` → sha256 → `UserStore`; `owned_memory` (404 across users).
  - `schemas.py` — request/response models; `errors.py` — exception → status table.
  - `routers/` — statements, memories, questions, resume, openings, recommendations, me.
  - `wiring.py` — `Settings.from_env` (DATABASE_URL, RIPPLE_LLM_CONFIG), `DomainAdapters`,
    `build_services` (TOML router, `ResolverChain(jobs_rules(), fallback=LLMResolver)`,
    Intake with `MULTI_VALUED_PROFILE_ATTRIBUTES`), `default_adapters()` (TODO, see below),
    `app_from_env`.
  - `admin.py` — `python -m ripple.api.admin create-user <name>` prints a token once.
  - `directory.py` — `UserDirectoryAdapter(user_store)` satisfies WS-6's `UserDirectory`.
  - `event_log.py` — `PostgresEventLog` (stop-gap, see contract request 1).
  - `candidates.py` — `candidate_from_fact`, `fact_of` (CandidateFact ↔ ResumeCandidate).
- `src/ripple/storage/users_tables.py` — users, api_tokens, telegram_link_codes,
  resume_candidates on the shared `Base.metadata`.
- `src/ripple/storage/users.py` — `User`, `ApiToken`, `TelegramLinkCode`, `UserStore`
  protocol, `PostgresUserStore`, `new_raw_token`, `hash_token`, `new_link_code`,
  `link_telegram(store, code, chat_id, now)` (the worker calls this).
- `src/ripple/storage/candidates.py` — `ResumeCandidate`, `CandidateStatus`,
  `CandidateStore`, `PostgresCandidateStore`.
- `infra/migrations/versions/0003_users.py` (down_revision "0002").
- Tests: `tests/api/` (61 tests: one module per router, `test_auth` isolation,
  `test_invariants_api` with named I1/I5/I6/I7 tests, store contracts run against the
  in-memory fakes, admin, wiring, directory), `tests/storage/test_users_postgres.py`
  and `test_candidates_postgres.py` (slow; user store, candidate store, event log
  contracts against Postgres; drift check for migration 0003).
- Docs: ADR-0040 (identity), 0041 (composition), 0042 (inspector semantics), 0043
  (candidates), 0044 (export/delete); `docs/learning/api.md`.

## Endpoints (all `Authorization: Bearer`, all scoped to the token's user)
| Method | Path | Notes |
|---|---|---|
| POST | /statements | Intake; `kind` fact\|derived, `origin` conversation\|inspector |
| GET | /memories | I1 filter; `kind`, `status` (no RETIRED), `flagged` |
| GET | /memories/{id} | why (parents, history links skipped); `history=true` for chain + events; RETIRED only with history |
| POST | /memories/{id}/edit | `update_memory` + ripple as user_edit; 409 on PENDING_USER |
| POST | /memories/{id}/forget | `core.forget` (I7) |
| GET | /questions | `core.answers.pending_questions` |
| POST | /questions/{id}/answer | still_holds \| no_longer_holds \| correction; receipt never carries a RETIRED memory |
| POST | /resume | multipart `file` (PDF magic, 5 MB cap) → candidates pending |
| GET | /resume/candidates | `status` pending\|confirmed\|rejected\|all |
| POST | /resume/candidates/{id}/confirm \| reject | confirm → `CandidateStatements` → Intake |
| POST | /openings | `OpeningParser` → `OpeningRecorder` |
| GET | /recommendations | `RecommendationSource`, `limit` ≤ 50 |
| GET | /me · POST /me/telegram/link · GET /me/export · DELETE /me | ADR-0040/0044 |

Errors: 401 no/invalid token; 404 unknown or another user's id; 409 `NotPendingError`,
already-decided candidate; 413/415 upload; 422 unparseable input, unknown link type;
503 LLM failure with `open_change_event_ids` listing what the sweep will resume; 5xx
bodies never carry the exception message.

## Verification (run 2026-10-19, after the code-review fixes)
```
$ uv run ruff check src/ripple/api src/ripple/storage/users_tables.py src/ripple/storage/users.py src/ripple/storage/candidates.py tests/api tests/storage/test_users_postgres.py tests/storage/test_candidates_postgres.py infra/migrations/versions/0003_users.py
All checks passed!
$ uv run ruff format --check <same paths>
43 files already formatted
$ uv run pyright <same paths>
0 errors, 0 warnings, 0 informations
$ uv run pytest tests/api tests/storage -q
65 passed, 31 skipped in 2.87s
$ uv run pytest tests/api -q
61 passed in 2.65s
$ uv run pytest -q -m "not slow"   # whole repo, information only
605 passed, 39 deselected, 31 xfailed in 11.78s
```
Skips are the slow Postgres tests (no TEST_DATABASE_URL on this machine). Migration
0003 and the Postgres stores are therefore unverified against a live database; CI's
services job will run them.

Code review (code-reviewer subagent): 1 blocker, 7 majors, 16 minors. Fixed: the
blocker (questions now read `Decision.question` via `pending_questions`), M1 (storage
no longer imports the jobs vocabulary; conversion moved to `ripple.api.candidates`),
M2 (ADRs, learning doc, this handover), M4 (LLM failure after a committed write: 503
body lists the user's open ChangeEvents; test with a failing resolver), M5
(`EventLogContract` for in-memory and Postgres), M6 (client kinds limited to
fact|derived), M7 (answer receipts carry no RETIRED memory; named I1 test), m3, m4, m5,
m7, m8, m11, m12. Recorded, not fixed: M3 (see request 3), m1/m2 (see request 2), m6,
m10, m13, m14, m16 under Open problems.

## Integration: what the coordinator wires in `ripple.api.wiring.default_adapters()`
```python
import asyncio
from ripple.api.contracts import OpeningWritten, ResumeUnparseableError
from ripple.api.wiring import DomainAdapters
from ripple.domains.jobs.openings import record_opening
from ripple.domains.jobs.parsers import (
    UnparseableResumeError,
    candidate_to_statement,
    extract_text,
    parse_jd,
    parse_resume,
    strip_email_envelope,
)
from ripple.domains.jobs.ranking import JobsRecommender


class ResumeParserAdapter:  # contracts.ResumeParser
    def __init__(self, router):
        self._router = router

    async def parse(self, pdf, *, source_ref):
        try:
            text = await asyncio.to_thread(extract_text, pdf)  # WS-2: sync, CPU-bound
        except UnparseableResumeError as exc:
            raise ResumeUnparseableError(
                str(exc)
            ) from exc  # or add the WS-2 class to errors.STATUS_FOR
        return await parse_resume(self._router, text)


class CandidateStatementsAdapter:  # contracts.CandidateStatements
    def statement_for(self, user_id, candidate, *, source_ref):
        return candidate_to_statement(candidate, user_id, source_ref)  # WS-2 appends #start-end


class OpeningParserAdapter:  # contracts.OpeningParser
    def __init__(self, router):
        self._router = router

    async def parse(self, text, *, source_ref):
        body = strip_email_envelope(text) if source_ref.startswith("email:") else text
        return await parse_jd(self._router, body, source_ref)


class OpeningRecorderAdapter:  # contracts.OpeningRecorder
    def __init__(self, store, clock, runner): ...
    async def record(self, user_id, opening):
        r = await record_opening(
            self._store, self._clock, user_id, opening, self._runner, created_by="user"
        )  # a paste is the user's, not the Scout's
        # optionally: await derive_for_opening(...) here, or leave it to the Curator
        return OpeningWritten(
            opening_memory_id=r.anchor.id,
            memory_ids=(r.anchor.id, *(f.id for f in r.fields)),
            event_id=r.event.id,
        )


def default_adapters(store, clock, runner, router) -> DomainAdapters:
    return DomainAdapters(
        resume_parser=ResumeParserAdapter(router),
        candidate_statements=CandidateStatementsAdapter(),
        opening_parser=OpeningParserAdapter(router),
        opening_recorder=OpeningRecorderAdapter(store, clock, runner),
        recommendations=JobsRecommender(store),
    )
```
`default_adapters` currently takes no arguments and raises `NotImplementedError`;
`build_services` will need to construct the store, clock, runner and router first and
pass them (reorder the two lines in `app_from_env`). The router config must list tasks
`jd_parser` and `resume_parser` (config/llm.default.toml already does).

Worker (WS-6): `ripple.api.directory.UserDirectoryAdapter(PostgresUserStore(engine))`
satisfies `UserDirectory` (`active_user_ids()`, `telegram_chat_id(user_id) -> str |
None`). The bot's "/link <code>" handler calls
`ripple.storage.users.link_telegram(user_store, code, chat_id, now)`; None means
unknown, expired (15 min) or already used.

Entrypoint: `uvicorn ripple.api.app:create_production_app --factory` matches
`infra/entrypoint.sh` as written; no change needed there.

## Contract change requests (coordinator-owned files)
1. **Store (C3): per-user event reads.** Add to `StoreReader`:
   `change_events_for_user(user_id) -> list[ChangeEvent]` and
   `forget_events_for_user(user_id) -> list[ForgetEvent]` (oldest first). Then delete
   `ripple.api.contracts.EventLog`, `ripple.api.event_log`, `tests/api/fakes
   .InMemoryEventLog` and pass the store itself; `EventLogContract` moves into
   `tests/core/store_contract.py`. InMemoryStore already has the test-only accessors.
2. **Intake: an explicit edit entry point.** `Intake.edit(memory_id, *, content,
   structured, valid_to, created_by, source_ref, trace_id)` = `update_memory` with
   `TriggerKind.USER_EDIT` plus `_link_new_version` plus the ripple. Today
   `POST /memories/{id}/edit` calls `update_memory` directly (ADR-0042) and the new
   version gains no Linker links. Also lets the API expose `valid_to` on edit.
3. **Store (C3) / core.forget: per-user event deletion for DELETE /me.**
   `Transaction.delete_change_events_for_user(user_id)` (and forget_events if the
   author wants erasure over audit). Until it exists `DELETE /me` leaves ChangeEvents,
   whose decision reasons may quote content (ADR-0044, FR-15 gap).
4. **Shared metadata import.** `ripple.storage.users_tables` registers four tables on
   `Base.metadata` only when imported. `infra/migrations/env.py` imports `Base` alone,
   so `alembic revision --autogenerate` would propose dropping them, and
   `tests/storage/test_postgres_store.py::test_migrations_match_table_metadata` will
   report them as unexpected once 0003 has run unless the module is imported first.
   Please import `ripple.storage.users_tables` (and WS-5's search tables) in
   `src/ripple/storage/__init__.py` or in `env.py`.
5. **tests/storage/conftest.py.** `test_candidates_postgres.py` imports the `migrated`
   fixture from `test_users_postgres.py`; a shared conftest (coordinator-owned area)
   would be cleaner.
6. **Vocabulary (C1), observation only.** `OpeningSource` for a paste vs an email is an
   API notion (`paste:<id>` / `email:<id>` source refs, matching WS-2's convention);
   nothing to add unless a third source appears.

Applied from the coordinator's messages: `Decision.question` and
`core.answers.pending_questions` are used; wiring builds the Router from
`RouterConfig.from_toml(RIPPLE_LLM_CONFIG or config/llm.default.toml)`, uses
`ResolverChain(jobs_rules(), fallback=LLMResolver(router))` and passes
`MULTI_VALUED_PROFILE_ATTRIBUTES` to Intake.

## Open problems
- Postgres paths (stores, event log, migration 0003 drift test) run only in CI.
- `DELETE /me` leaves ChangeEvents (request 3); pinned in `test_me.py` with a comment.
- Confirm is not atomic: two concurrent confirms of one candidate both pass the
  pending check (m6). Needs a conditional update in `CandidateStore.replace_candidate`
  or a claim step; single-user pilot traffic makes this unlikely, not impossible.
- The uploaded PDF (or its text) is not persisted, so `resume:<upload>#start-end` does
  not resolve to a line yet (m14); a `resume_uploads` table is a later migration.
- Admin CLI writes the user and the token in two transactions (m10).
- Link codes: 48-bit, 15 minutes, one use; the bot side should rate-limit attempts.
- Edit has no `valid_to` and no Linker pass (request 2).
- `wiring.default_adapters()` raises NotImplementedError until integration (by design).

## Suggested commit message
```
api: identity, inspector, confirmation flow, export/delete behind FastAPI — FR-1, FR-7,
FR-12 and FR-15 need an HTTP boundary that enforces I1 and per-user scoping; users are
admin-created with hashed bearer tokens and one-time Telegram link codes (ADR-0040),
the app is built from an injectable Services object with WS-1/WS-2 behind protocols
(ADR-0041), the inspector lists through the I1 visibility rule and edits as user_edit
versions (ADR-0042), resume candidates wait in their own table until confirmed
(ADR-0043), and export/delete follow DPDP with forget as the only deletion (ADR-0044).
```
