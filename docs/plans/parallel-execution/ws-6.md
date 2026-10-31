# WS-6 handover: Worker, scheduler, notifications, digest
Status: **Locally verified**, wiring filled by the coordinator (status board: Integrated and
verified); review findings applied 2026-10-20.
Last update: 2026-10-20

## What was built
- `src/ripple/notify/contracts.py`: `Transport`, `MessageReceipt`, `UserDirectory`,
  `DeliveryLog`, `AlertKind`, `Thresholds`.
- `src/ripple/notify/render.py`: `render_digest` (fits 4096 chars by dropping trailing
  items whole), `alert_kinds`, `alerts_for`, `Alert`, `render_alert`, `hours_left`.
- `src/ripple/notify/telegram.py`: `TelegramTransport` over httpx (`sendMessage` only),
  `from_env` reading `TELEGRAM_BOT_TOKEN`, redaction filter on the `httpx` logger so
  the token in the request URL never reaches a log; errors in `notify/errors.py`.
- `src/ripple/notify/digest.py`: `DigestService.send_daily`, `send_alerts`
  (`delivery_log` is a required argument); `notify/delivery_log.py`:
  `InMemoryDeliveryLog`.
- `src/ripple/worker/jobs.py`: `nightly_sweep`, `daily_digest`, `hourly_alerts`,
  `scout_run` (NotImplementedError, Phase 3); `worker/context.py`: `JobContext`;
  `worker/lease.py`: `Lease`, `InMemoryLease`, `RedisLease` (token + compare-and-delete),
  `leased`; `worker/settings.py`: arq `WorkerSettings` with four cron slots;
  `worker/wiring.py`: `job_context_from_env` and `build_job_context` (filled by the
  coordinator at integration; `tests/worker/test_wiring.py` is the coordinator's).
- `tests/fakes/transport.py`: `RecordingTransport(clock)`, `failing_transport`.
- Tests: `tests/notify/` (render, DigestService, Telegram transport with
  `httpx.MockTransport`, invariant I6), `tests/worker/` (jobs, lease incl. one slow
  Redis test, settings, wiring).
- Docs: ADR-0055 (thresholds, rendering, what never alerts), ADR-0056 (idempotency,
  leases, schedule), `docs/learning/worker-and-notify.md`.

## Review (code-reviewer subagent, 2026-10-20) and what changed
- Blocker, fixed: httpx logs `HTTP Request: POST <url>` at INFO and the URL carries the
  bot token. `TelegramTransport` now installs a redacting filter on the `httpx` logger;
  the test captures the root logger and asserts the line appears redacted.
- Fixed: fit percent truncation (0.57 rendered "56%"); alert kinds now rendered and
  recorded per due kind only (a second kind no longer repeats the first or restarts its
  cooldown); `RedisLease.release` compares a per-acquisition token before deleting;
  digests over 4096 characters drop trailing items instead of failing forever; alerts
  scan `alert_scan_limit = 50` ranked items instead of the digest's 10.
- Fixed minors: lease acquisition inside the per-user try; `JobFailedForUsersError`
  carries an `ExceptionGroup` cause; `delivery_log` required; `functions` lists all four
  jobs; `%Z`/tz-aware precondition documented; `math.floor`; `is None`; tests split one
  behaviour each; lease ttl pinned above the sweep cron timeout; flaky-transport test
  raises `TelegramSendError`; `FORBIDDEN_IMPORTS` extended with `http`, `socket`,
  `websockets`; `RecordingTransport` takes a Clock.
- Not done: the slow `RedisLease` test is written but skipped here (no Redis locally);
  runs under `TEST_REDIS_URL` in CI.

## Contracts

### UserDirectory (defined here, implemented by the identity module)
```python
class UserDirectory(Protocol):
    async def active_user_ids(self) -> Sequence[str]: ...  # stable order
    async def telegram_chat_id(self, user_id: str) -> str | None: ...  # None = not linked
```
Implemented by `ripple.api.directory.UserDirectoryAdapter` over `PostgresUserStore`
(coordinator, integration).

### RecommendationSource (C1, consumed as-is)
`recommendations_for(user_id, *, now, limit)`; the digest passes
`limit = Thresholds.digest_limit` (10), alerts pass `alert_scan_limit` (50).
`Recommendation.flagged` items render as `[unconfirmed]` and never alert; `fit_reasons`
are printed verbatim, so I5 is WS-1's to enforce at the source.

### Contract change requests to the coordinator
None required. Two observations for C1:
- `Recommendation.hours_to_deadline` returns the epoch hours of the deadline, not hours
  from now; the digest uses `render.hours_left(recommendation, now)` and never calls the
  property. Consider renaming or removing it.
- Alerts would be cheaper and complete with a source method that returns every
  eligible opening whose deadline falls inside a window, instead of scanning the top 50
  by fit. Proposed as an optional extension, not required.

## Integration checklist (coordinator)
1. `worker.wiring.job_context_from_env` is filled (coordinator). It still passes
   `InMemoryDeliveryLog()`; swap for the Postgres one when it exists (follow-up).
2. Compose `worker` service command: `arq ripple.worker.settings.WorkerSettings`
   (needs `REDIS_URL`, `DATABASE_URL`, `TELEGRAM_BOT_TOKEN`, optional `RIPPLE_LLM_CONFIG`).
3. Index ADR-0055 and ADR-0056 in docs/adr/README.md.
4. DEVLOG lines (coordinator-owned file): see "Open problems" 1 and 2 below.
5. Roadmap: Phase 2 "Telegram daily digest" is built offline; tick after a real send.
6. CI: set `TEST_REDIS_URL` so the slow `RedisLease` test runs.

## Follow-ups (not in this round)
- Postgres `DeliveryLog` (table `delivery_log`, migration after 0004) so a worker
  restart on digest day cannot resend; `InMemoryDeliveryLog` is per process.
- Per-ChangeEvent lease inside `RippleRunner.resume` (core, coordinator-owned).
- Email transport (ADR-0025 deferred): one class implementing `Transport`.
- Alerts longer than 4096 characters still raise `MessageTooLongError` (digest is
  bounded; alerts are not); bound them the same way if the pilot ever hits it.

## Open problems
1. **Resume double-resolution risk** (for DEVLOG): the per-user lease stops two sweeps
   colliding, not a sweep colliding with a live ripple slower than `stale_after` (1 h),
   e.g. an LLM retry storm or an `ask` the user has not answered. `RippleRunner.resume`
   only resolves still-SUSPECT, undecided members, so the damage is bounded to one
   extra resolution of the outstanding wave, but the guard belongs in the runner.
2. **DeliveryLog durability** (for DEVLOG): in-memory until the Postgres implementation.
3. **Time zone**: "once per day" is a UTC day; the digest cron at 02:30 UTC is 08:00 IST;
   deadlines render in UTC with the zone name. Fine for one cron a day and a pilot in one
   zone; wrong if a user-local hour is ever offered.
4. `on_startup` checks `REDIS_URL` after arq has already tried its localhost default once;
   no job runs before the check, but the first log line is arq's connection error.

## Verification (2026-10-20, real output, after the review fixes)
```
$ uv run ruff check src/ripple/worker src/ripple/notify tests/worker tests/notify tests/fakes/transport.py
All checks passed!
$ uv run ruff format --check src/ripple/worker src/ripple/notify tests/worker tests/notify tests/fakes/transport.py
26 files already formatted
$ uv run pyright src/ripple/worker src/ripple/notify tests/worker tests/notify tests/fakes/transport.py
0 errors, 0 warnings, 0 informations
$ uv run pytest tests/worker tests/notify -q
SKIPPED [1] tests\worker\test_lease.py:75: TEST_REDIS_URL/REDIS_URL not set
87 passed, 1 skipped in 2.69s
```
Full fast suite at the same moment (`uv run pytest -m "not slow" -q`): `864 passed,
1 failed, 43 deselected, 31 xfailed`; the failure is
tests/domains/jobs/test_openings.py::test_record_opening_writes_anchor_and_one_fact_per_field_with_opening_subject
(WS-1 path, not WS-6).

## Suggested commit message
worker+notify: Telegram digest and alerts, arq schedule with per-user sweep leases — FR-9
offline-testable (ADR-0055, ADR-0056); token redaction in httpx logs; Scout slot
registered as NotImplemented for Phase 3
