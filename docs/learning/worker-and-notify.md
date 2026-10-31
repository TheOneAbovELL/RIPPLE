# ripple.worker and ripple.notify — scheduled jobs, digest and alerts
Written 2026-10-19 by WS-6 (parallel round 1).

## 1. What it does
`ripple.notify` turns a user's ranked openings into one plain-text Telegram digest a day
and a batched alert when an opening is high-fit or its deadline is within 48 hours,
without ever sending twice. `ripple.worker` runs the nightly sweep, the digest and the
alerts on an arq schedule, one user at a time, with a lease so two workers never sweep
the same user together. Both packages only read rankings and memory; they never rank,
never resolve and never touch any site but the user's own Telegram chat.

## 2. Why it exists
FR-9 (digest and alerts), FR-8's schedule slot for the Scout, the Curator's nightly
sweep (docs/02 Agents table). ADR-0017 (arq on Redis, jobs idempotent and tested as
plain functions), ADR-0025 (Telegram over httpx, recording fake), ADR-0055 (thresholds
and rendering), ADR-0056 (idempotency, leases, schedule). I6: nothing here acts on an
external site for the user.

## 3. How it works
- `notify.contracts`: `Transport.send(chat_id, text) -> MessageReceipt`;
  `UserDirectory` (active user ids, telegram chat id per user; implemented by the
  identity module at integration); `DeliveryLog` (last digest day, last alert per
  opening and kind); `Thresholds`; `AlertKind`.
- `notify.render`: `render_digest(recommendations, now, max_length=4096)` drops
  trailing items whole to fit and counts what it left out; `alert_kinds` decides
  HIGH_FIT and DEADLINE_SOON and returns nothing for flagged or ineligible openings;
  `alerts_for` pairs each qualifying opening with its kinds as an `Alert`;
  `render_alert(alerts, now)` prints exactly the kinds it is given. Numbers are the
  source's score (rounded to six decimals, then floored to a percent) and deadline
  minus the injected clock, floored.
- `notify.telegram.TelegramTransport`: one POST to
  `https://api.telegram.org/bot<token>/sendMessage` over httpx; token from
  `TELEGRAM_BOT_TOKEN`; refuses text over 4096 characters before sending; raises
  `TelegramSendError` on HTTP errors, `ok: false`, non-JSON or non-object bodies, with the
  description and `retry_after` but never the token; INFO logs carry message id and
  length only. httpx logs its own request line (method and full URL) at INFO, and the
  token sits in that URL, so the transport installs a redacting filter on the `httpx`
  logger; the test captures the root logger to prove the line comes out redacted.
- `notify.digest.DigestService.send_daily(user_id)`: skip if today's digest is
  recorded, if no chat is linked or if nothing ranks; otherwise send, then record the
  day. `send_alerts(user_id, since)`: scan `alert_scan_limit` (50) ranked openings,
  keep the kinds not alerted at or after `since`, send one message listing only those
  kinds, then record each due (opening, kind) at `now`. The `DeliveryLog` is a required
  argument so production wiring cannot forget it.
- `worker.jobs`: `nightly_sweep` (lease per user, `NightlySweep.run`, failures
  isolated, `JobFailedForUsersError` at the end), `daily_digest`, `hourly_alerts`
  (`since = now - alert_cooldown`), `scout_run` (NotImplementedError until Phase 3).
- `worker.lease`: `InMemoryLease` expires by the clock; `RedisLease` is `SET NX PX`
  with a per-acquisition token and a compare-and-delete release on arq's connection;
  `leased()` releases only what it acquired.
- `worker.settings.WorkerSettings`: cron list (UTC: Scout 01:00, sweep 21:00, digest
  02:30, alerts :15 hourly), `on_startup` builds the `JobContext` via
  `worker.wiring.job_context_from_env` (filled by the coordinator at integration:
  PostgresStore, Router-backed resolver, jobs recommender, identity directory,
  Telegram transport, Redis lease) and refuses to start without `REDIS_URL`.

## 4. Trade-offs
- Plain functions plus a thin arq layer instead of arq-native jobs everywhere: the
  cost is one wrapper per job; the gain is a test suite that never needs Redis.
- Lease per user, not per ChangeEvent: the runner is frozen core this round. The lease
  stops concurrent sweeps but not a sweep colliding with a slow live ripple (ADR-0056
  open problem).
- Fail loud at the end rather than per user: one user's Telegram error must not stop
  the other nine, but the scheduler must still see a failed run.
- Plain text, no Telegram SDK, no parse_mode: nothing to escape, nothing to upgrade.
- In-memory DeliveryLog ships first: honest about forgetting on restart; the Postgres
  one is a follow-up with a table and a migration in the storage package.

## 5. Failure modes and tests
| Failure | Test |
|---|---|
| Digest sent twice on one day (cron retry) | test_send_daily_is_sent_once_per_user_per_day, test_daily_digest_rerun_the_same_day_sends_nothing |
| Day recorded though Telegram refused | test_send_daily_does_not_record_the_day_when_the_transport_fails |
| Alert spam every hour | test_send_alerts_does_not_repeat_an_alert_within_the_cooldown, test_hourly_alerts_rerun_within_the_cooldown_sends_nothing |
| Deadline alert misses the window edge or fires on a past deadline | test_alert_kinds_deadline_inside_48h_window_but_not_past_or_beyond |
| Alert on a doubted belief | test_alert_kinds_never_alert_on_flagged_or_ineligible_openings, test_send_alerts_skips_flagged_openings_even_when_urgent |
| Invented deadline or rounded-up hours | test_render_digest_never_invents_a_deadline_when_none_is_known, test_render_digest_floors_hours_left_instead_of_rounding_up |
| Two sweeps of one user | test_nightly_sweep_skips_a_user_whose_lease_is_held_and_sweeps_the_rest, test_lease_second_acquire_fails_while_held |
| Lease stuck after a crash | test_lease_expires_by_the_clock_so_a_crashed_holder_does_not_block_forever, test_nightly_sweep_releases_the_lease_when_a_user_fails_and_raises_at_the_end |
| Sweep misses expiry or stranded ripples | test_nightly_sweep_runs_expiry_and_resume_for_each_active_user |
| Token or digest text in logs, including httpx's request line | test_telegram_transport_never_logs_token_or_text_at_info_on_any_logger |
| Fit percent below the source's score (float noise) | test_render_digest_fit_percent_matches_the_source_score_despite_float_noise |
| Digest over Telegram's limit is undeliverable forever | test_render_digest_drops_trailing_items_to_stay_under_the_message_limit, test_send_daily_stays_under_the_telegram_limit_with_long_reasons |
| Second alert kind repeats the first and restarts its cooldown | test_send_alerts_second_kind_is_sent_alone_and_leaves_the_first_kinds_cooldown_untouched |
| Low-ranked near-deadline opening never alerts | test_send_alerts_scans_deeper_than_the_digest_so_a_low_ranked_deadline_is_not_missed |
| Stale holder frees another worker's lease | test_redis_lease_acquire_release_expiry_and_foreign_release (slow) |
| Redis blip aborts the whole sweep job | test_nightly_sweep_isolates_a_lease_backend_failure_too |
| Bot API answers HTML or garbage | test_telegram_transport_raises_on_unparseable_response_body |
| Something reaches a site other than Telegram | test_invariant_I6_worker_and_notify_never_act_on_external_sites |

## 6. Interview questions
1. *Why is the digest idempotent in the service and not in the cron?* arq's `unique`
   stops a second copy running concurrently, not a retry after a timeout or a second
   worker on a later tick; only a recorded "sent on this day" survives both.
2. *Why record the day after sending, not before?* Recording first and failing to send
   loses the day's digest; sending first and failing to record sends twice at worst.
   A missed digest is the worse failure for a job-hunt tool.
3. *What does the lease protect, exactly?* Two sweeps of one user; each would resume
   the same open event and resolve the same wave twice. It does not protect against a
   live slow ripple; that needs a per-event lease in the runner.
4. *Why can a flagged opening appear in the digest but never in an alert?* The digest
   is information with an "unconfirmed" label; an alert is a push to act now. Acting on
   a belief the system doubts is the failure FR-9's consistency story exists to avoid.
5. *Where is the only outbound HTTP call, and how is that enforced?* `TelegramTransport`
   to api.telegram.org; the I6 test walks both packages' ASTs for URL literals and HTTP
   libraries and runs a digest to check every message goes to that user's own chat.

## 7. Exercise
Take `Thresholds(deadline_window=timedelta(hours=72))` and an opening whose deadline is
in 50 hours. Write down which alerts `send_alerts` sends at hour 0, hour 1 and hour 8
with the default cooldown, then with `since = now` on every call. Check against
`alert_kinds` and `_is_due` by hand before running the tests.
