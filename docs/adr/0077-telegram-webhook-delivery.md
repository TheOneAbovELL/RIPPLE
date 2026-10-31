# ADR-0077: Telegram delivery: secret-token webhook into the API, at-most-once by update_id, long polling for development only
Status: Accepted under the autonomous mandate · Date: 2026-10-24

## Context
Round 2 (docs/plans/round-2.md) sketched long polling for the pilot VPS; the production
plan (docs/plans/production-plan.md) fixed the opposite: a webhook into the API behind
Caddy with Telegram's secret token header, polling only on a developer's laptop, and
one transport for digests and replies. Telegram redelivers an update whose webhook call
did not answer 2xx quickly, so a slow or failing handler turns into a retry storm; the
dispatcher can write memory, link accounts and delete, so a redelivered update must
not run twice. ADR-0025 put the only httpx code in `notify/telegram.py` and the I6
scan enforces that by file name.

## Decision
1. **Production: `POST /telegram/webhook`** in `ripple.api.routers.telegram`, mounted
   by `install_telegram_webhook(app, TelegramWebhook(channel, secret))`, hidden from
   the OpenAPI schema and outside bearer auth. The route compares the
   `X-Telegram-Bot-Api-Secret-Token` header to `TELEGRAM_WEBHOOK_SECRET` with
   `secrets.compare_digest`; a missing or wrong header is 401 and the body is not read.
   `TelegramWebhook` refuses an empty secret at construction (ConfigurationError), so
   production cannot start without one.
2. **Answer 200, process inside the request, under a hard timeout.** One VPS and no
   queue (ADR-0029): the update is handled in the request task with
   `asyncio.wait_for(…, 25 s)`, under Telegram's own limit. A timeout or a non-JSON
   body is logged and still answered 200, because a non-2xx only makes Telegram
   resend the same update.
3. **At most once per `update_id`.** `TelegramChannel.receive` asks the
   `UpdateLedger` (`first_sight(update_id) -> bool`) before parsing; a seen id is a
   no-op. The id is recorded before the work, so a redelivery after a timeout or crash
   does not repeat a write; the cost is that an update whose processing failed is
   lost, and the student sees no reply or the apology and sends again. In-memory
   ledger now (bounded LRU, per process); a Postgres table `telegram_updates` is the
   production implementation with migration id 0008 reserved.
4. **One Bot API client, composed over the outbound transport.**
   `ripple.notify.inbound.telegram.TelegramBotApi` holds a `TelegramTransport` (token
   validation, log redaction, plain `sendMessage`) on a shared httpx client and adds
   exactly four methods: `sendMessage` with `reply_markup`, `answerCallbackQuery`,
   `getUpdates`, `setWebhook`; `_call` refuses any other method name. It implements
   `Transport.send`, so the worker's digest and the bot's replies can share one object.
   The module is named `telegram.py` because the notify I6 scan allows httpx only under
   that name; the handover asks the coordinator to turn that rule into an explicit
   path list.
5. **Registration is an operator command:** `python -m ripple.notify.inbound.register
   --url https://<host>/telegram/webhook` calls `setWebhook` with the secret from the
   environment and `allowed_updates = ["message", "callback_query"]`; `--remove`
   clears it. Never run by tests.
6. **Development only: long polling.** `ripple.worker.telegram_poll` loops over
   `getUpdates` with offsets through the same `TelegramChannel`; in-memory saver,
   ledger and limiter; documented as unfit for the pilot. Telegram refuses polling
   while a webhook is set, so the two modes cannot run at once by accident.

## Alternatives considered
- Long polling in the worker for production too (round-2 sketch) — no public URL
  needed, but the poller holds a 30 s connection open forever, competes with cron
  jobs for the worker, needs its own leader election with two workers, and the
  production plan already pays for Caddy and TLS. Lost.
- Webhook that enqueues to arq and returns — the right shape with several workers;
  on one VPS it adds a Redis round trip and a second failure mode (queued, never
  processed) for no gain. Revisit with a second node.
- Recording the update_id after success (at-least-once) — a timeout then redelivers
  and repeats a link, a forget confirmation or an agent write. The dispatcher's writes
  are not all idempotent, so at-most-once is the safer side for a memory system.
- Extending `TelegramTransport` with the new methods — the cleanest shape, but
  `notify/telegram.py` is outside WS-10's ownership; composition keeps the single
  token and redaction path and lets the coordinator fold the two together later.
- A random path segment instead of the secret header — Telegram's header is the
  documented mechanism and keeps the URL stable for Caddy.

## Consequences
- `app.py` is untouched: the route is mounted by `install_telegram_webhook` from the
  production wiring, with `TelegramWebhook` kept on `app.state`. The dashboard client
  never sees it.
- The per-process ledger forgets on restart; Telegram's redelivery window is short, so
  the exposure is a restart during a retry. Closed by the Postgres ledger (0008).
- The wait_for cancellation can interrupt a dispatch between two committed writes
  (each core write is its own transaction); the student sees the apology and the
  state is consistent, if incomplete. Measured by the `timeout` result in logs.
- Caddy must forward `/telegram/webhook` to the API with the header intact (it does
  by default); the handover gives the compose and Caddy lines.

## Revisit if
A second API process is deployed (the ledger and the dispatcher's short-lived state
must move to Postgres or Redis first), or update processing regularly exceeds the
timeout (then the enqueue-and-return shape).
