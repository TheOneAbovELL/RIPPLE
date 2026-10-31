# ADR-0041: API composition: `create_app(services)`, a `Services` object, environment-only wiring
Status: Accepted under the autonomous mandate · Date: 2026-10-19

## Context
ADR-0022 fixed the stack (FastAPI, uvicorn, httpx). The API depends on the core write
flow, two stores, and three pieces other workstreams build concurrently (parsers,
opening recorder, recommendation source). Tests must run fully offline (NFR-1) and
settings must never live in code (docs/02 Security).

## Decision
- `ripple.api.app.create_app(services: Services) -> FastAPI` is the only constructor.
  There is no module-level app. `Services` is a frozen dataclass holding the store,
  clock, link registry, Intake, RippleRunner, UserStore, CandidateStore, EventLog and
  the injected contracts; routers read it from `request.app.state`, never from a
  global, so two apps in one process share nothing.
- `ripple.api.contracts` declares the protocols the API consumes but does not own:
  `ResumeParser`, `CandidateStatements`, `OpeningParser`, `OpeningRecorder`, `EventLog`,
  and re-exports `RecommendationSource`. Tests inject fakes; the coordinator injects
  the real implementations in `ripple.api.wiring.default_adapters()` at integration.
- `ripple.api.wiring.Settings.from_env(env)` reads `DATABASE_URL`, `LLM_PROVIDER`,
  `LLM_MODEL`, optional `LLM_MAX_RETRIES`; a missing value raises `ConfigurationError`
  naming the variable. `build_services(settings, adapters)` composes Postgres stores,
  the LLM router, resolver, linker and change detector. `app_from_env` is the uvicorn
  factory and raises `NotImplementedError` with a TODO until the adapters are wired.
- Ripple exceptions map to HTTP statuses in one table (`ripple.api.errors.STATUS_FOR`):
  not found 404, `NotPendingError` 409, unparseable input 422, LLM failures 503.

## Alternatives considered
- FastAPI `Depends` per collaborator with module-level singletons — idiomatic, but
  globals make two test apps share state and hide the dependency graph. Lost.
- pydantic-settings — convenient, a new dependency for five variables. Lost.
- Importing WS-1/WS-2 modules directly — would block this workstream on theirs and
  couple the API to one domain's module names; protocols keep the API buildable and
  testable alone. Lost.

## Consequences
- Every API test builds the app from fakes in milliseconds (tests/api/harness.py).
- Integration is one function (`default_adapters`) plus error-table entries for the
  siblings' exception types; the handover spells it out.
- `EventLog` duplicates two small queries that belong in the Store protocol; it is a
  requested contract change and disappears once accepted.

## Revisit if
The Store gains per-user event queries (remove `EventLog`), or the number of injected
collaborators makes `Services` unwieldy.
