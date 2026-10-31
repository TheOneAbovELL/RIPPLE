# WS-9 handover: Scout agent
Status: **Locally verified**, reconciled and integrated at checkpoint C3 · 2026-10-26 · ADR-0070, ADR-0071, ADR-0072

## What was built
- `src/ripple/domains/jobs/sources/` (new package)
  - `registry.py` — `SourceRegistry`, `SourceSpec`, `SourceKind`, `ExtractionHint`,
    `parse_registry`, `load_registry`, `registry_from_env` (`RIPPLE_SOURCES_CONFIG`,
    default `config/sources.yaml`), `SourceRegistryError` (a `ConfigurationError`).
    Refuses a missing or blank terms note, `robots_respected: false`, credentials in a
    URL, unknown fields, a career page without a hint, a public API without JSON hints.
  - `canonical.py` — `canonical_url`, `fingerprint(company, title)`, `short_digest`.
  - `ratelimit.py` — `TokenBucket(per_minute, clock, sleeper=, burst=1)`.
  - `cache.py` — `FetchCache` protocol, `CachedPage`, `InMemoryFetchCache`.
  - `robots.py` — `RobotsPolicy` (stdlib parser; one fetch per host per run; 4xx allow,
    5xx/timeout closed; `crawl_delay`).
  - `fetcher.py` — `SourceFetcher.fetch(source, url=None) -> FetchResult`,
    `FetchRefusedError`, `FetchFailedError`. GET only, registered host only, robots,
    rate limit (slower of registry and Crawl-delay), cookies cleared, ETag /
    Last-Modified revalidation, same-host redirects (max 3), 401/403/407 refused,
    backoff on 429/5xx/transport, 2 MB body cap.
  - `extract.py` — `extract_candidates`, `html_candidates`, `json_candidates`,
    `page_text`, `Candidate`. Stdlib `html.parser` plus a CSS selector subset.
  - `dedupe.py` — `ScoutLedger` protocol, `InMemoryScoutLedger`, `OpeningDeduplicator`
    (`known_url`, `known_fingerprint`, `remember`), `scout_source_ref`,
    `canonical_of_source_ref`.
  - `report.py` — `SourceCount`, `ScoutError`, `ScoutReport`, `ScoutRunReport`,
    `SCOUT_LEASE_TTL`, `scout_lease_key`.
  - `wiring.py` — `open_fetcher(clock, user_agent=...)`: the one place an httpx client
    is built.
- `src/ripple/agents/scout.py` — `ScoutAgent.run_for_user(user_id, trace_id=None) ->
  ScoutReport`, `ScoutCriteria` (parsed from the criteria memory content),
  `criteria_for`, `ScoutTrigger` protocol with `ImmediateScoutTrigger` and
  `EnqueueingScoutTrigger`, `event_changed_criteria(store, event)`, `open_scout(...)`,
  `process_ledger()`. No httpx, hashlib or datetime import (agents I6 import scan).
- `src/ripple/worker/jobs.py` — imports and the `scout_run(context, *, scout=None) ->
  ScoutRunReport` body only. Builds the agent from the environment per run unless one
  is injected; one lease per user; failures isolated and raised as
  `JobFailedForUsersError("scout_run", ...)`.
- `config/sources.yaml` — the forwarded-email source and one example career page,
  `enabled: false`, PLACEHOLDER terms note.
- Tests: `tests/domains/jobs_sources/` (support.py, fixtures/{careers.html, job-42.html,
  job-43.html, api.json, robots.txt}, test_registry, test_canonical, test_ratelimit,
  test_robots, test_fetcher, test_extract, test_dedupe: 91 tests) and
  `tests/domains/jobs_sources/scout_support.py` and `tests/agents/{test_scout.py, test_scout_invariants.py}` (25 tests,
  including `test_invariant_I5_scout_records_only_parsed_fields_with_spans_into_the_page_text`
  and `test_invariant_I6_scout_only_gets_allowed_sources`).
- Docs: `docs/adr/0070-allowed-sources-registry.md`,
  `docs/adr/0071-scout-dedupe-canonical-url-and-fingerprint.md`,
  `docs/adr/0072-scout-agent-plain-loop-no-graph.md`, `docs/learning/scout.md`.

## How consumers call it
```python
from ripple.agents.scout import ScoutAgent, open_scout, event_changed_criteria, ScoutTrigger
from ripple.domains.jobs.sources import registry_from_env

async with open_scout(store=store, clock=clock, runner=runner, router=router,
                      registry=registry_from_env()) as scout:
    report = await scout.run_for_user(user_id)   # ScoutReport: per_source counts, errors
# daily: ripple.worker.jobs.scout_run(context)   (already on the 01:00 UTC cron slot)
# on a criteria change (coordinator hook, see below):
if await event_changed_criteria(store, completed_event):
    await trigger.on_criteria_changed(user_id)
```
Router config needs task `jd_parser` (already in config/llm.default.toml).

## Verification (coordinator, 2026-10-26, after reconciling the review pass)
The WS-9 sessions stopped at the session limit on 2026-10-25 mid-way through their
review fixes: the code renamed `SourceCount.fetched` to `candidates`, added `refused`
(policy refusals are no longer errors), kept `ref` as a job id in canonical URLs and
stopped parsing skills into `ScoutCriteria`, but six tests and the learning doc still
used the old shape. The coordinator aligned the tests and docs with the code (the code's
choices are the reviewed ones; ADR-0072 points 3 and 4 amended), replaced the two
worker stub tests as requested below, and added the Scout's capability declaration.
```
$ uv run pytest tests/agents/test_scout.py tests/agents/test_scout_invariants.py tests/domains/jobs_sources tests/worker -q
156 passed, 1 skipped in 2.13s      (the skip needs REDIS_URL)
$ uv run ruff check <WS-9 paths>
All checks passed!
$ uv run ruff format --check <WS-9 paths>
25 files already formatted
$ uv run pyright <WS-9 paths>
0 errors, 0 warnings, 0 informations
```

## Coordinator actions requested
1. **tests/worker (WS-6):** two tests assert the old `NotImplementedError` and now fail
   by design: `tests/worker/test_jobs.py::test_scout_run_is_not_built_yet_and_names_the_roadmap_task`
   and the last two lines of
   `tests/worker/test_settings.py::test_arq_wrappers_delegate_to_the_plain_jobs_and_summarise`.
   Replacement for the first (the second just drops its `pytest.raises` block, or asserts
   the wrapper returns `None`):
   ```python
   def test_scout_run_with_the_default_registry_fetches_nothing(monkeypatch):
       repo = Path(__file__).resolve().parents[2]
       monkeypatch.setenv("RIPPLE_SOURCES_CONFIG", str(repo / "config" / "sources.yaml"))
       monkeypatch.setenv("RIPPLE_LLM_CONFIG", str(repo / "config" / "llm.default.toml"))
       report = asyncio.run(scout_run(context(users={"u1": "c1"})))
       assert report.by_user["u1"].per_source == {}
   ```
   (The same test exists in tests/agents/test_scout.py.) `scout_run_job` may return
   `{"users": len(report.by_user), "new": sum(r.new for r in report.by_user.values())}`
   like its siblings.
2. **Criteria-change hook (FR-8, coordinator-owned code):** after a ChangeEvent
   completes in the write flow (`Intake.ingest` / `RippleRunner.run` callers in the API
   and the Conversation agent), call
   `if await event_changed_criteria(store, event): await scout_trigger.on_criteria_changed(user_id)`.
   Production trigger: `EnqueueingScoutTrigger(lambda uid: redis.enqueue_job("scout_user_job", uid))`;
   WS-6 registers `scout_user_job(ctx, user_id)` in `worker/settings.py` as
   `async with open_scout(...) as scout: await scout.run_for_user(user_id)` under the
   same lease key (`scout_lease_key`). Development: `ImmediateScoutTrigger(agent)`.
   `derive_criteria` itself is the usual producer of such an event.
3. **Capability enum (WS-4 file `src/ripple/agents/capabilities.py`):** add
   `SOURCE_FETCH = "source.read"`? The enum's forbidden-word test rejects "fetch";
   suggested name `SOURCES_READ = "sources.read"` and `MEMORY_WRITE_OPENING =
   "memory.write_opening"`, so `ScoutAgent.capabilities` can be declared and checked
   like the other agents. Not blocking.
4. **docs/02-architecture.md agents table:** Scout row → "plain loop over injected
   parts (ADR-0072); fetch only through ripple.domains.jobs.sources".
5. **Dependency/version note:** no new dependency. httpx 0.28.1 and pyyaml 6.0.3 from
   pyproject are used.

## Follow-ups (specified, not built)
- **Postgres `ScoutLedger`, migration id 0007 reserved** (`infra/migrations/versions/
  0007_scout_ledger.py`, down_revision "0006"): table `scout_ledger(user_id text,
  key text, seen_at timestamptz, primary key (user_id, key))`; implementation
  `ripple.storage.scout_ledger.PostgresScoutLedger` with the two protocol methods;
  `forget` for a user deletes their rows (DELETE /me). Until then `process_ledger()`
  is one in-memory ledger per worker process; recorded openings are still deduplicated
  across restarts through the store.
- **Redis `FetchCache`:** keys `scout:cache:<canonical url>` holding etag,
  last_modified, content_type, body (capped) with a 3-day TTL; needs no table.
- **Pagination / search templates** per source (ADR-0072 "revisit if").
- **Closing openings the Scout no longer finds:** depends on the opening lifecycle
  decision (WS-1 handover open problem); the Scout records, never retires.

## Open problems
- `scout_run` builds a Router per run from `RIPPLE_LLM_CONFIG` through
  `ripple.worker.wiring.router_from_env`; when the coordinator gives `JobContext` a
  `router` (or a ready `ScoutAgent` factory), the body should take it from there instead
  (one-line change in the body).
- A candidate without a title after parsing is marked `url:` (never parsed again) even
  though a later, better model might read it; acceptable for the pilot, noted.
- The `user_agent` in config/sources.yaml names the project but carries no contact
  address yet; the author should add one before enabling any career page (sites expect
  to be able to reach the operator).

## Suggested commit message
scout: allowed-sources registry, fetcher, dedupe and ScoutAgent — FR-8 daily and
criteria-triggered scouting over permitted sources only (ADR-0070..0072)
