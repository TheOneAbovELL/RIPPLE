# ripple.notify.inbound — the Telegram bot the student talks to
Written 2026-10-25 by WS-10 (ADR-0075, ADR-0076, ADR-0077).

## 1. What it does
Lets a pilot student do the product's daily work from Telegram: link the chat with a
one-time code, tell the agent facts and ask it questions, confirm or correct beliefs
the ripple parked, paste or forward a job description, start a deletion, and find the
export. In production Telegram posts each update to `POST /telegram/webhook` on the
API; on a developer's laptop a long-poll loop fetches them. Both feed one channel that
deduplicates, parses, dispatches and replies. The same Bot API client sends the
worker's digests, so the student sees one bot.

## 2. Why it exists
FR-7 (answer parked questions in conversation), FR-10 (answers with citations), FR-2
(JDs by paste or forward), FR-15 (export and delete reachable), ADR-0025 (Telegram over
httpx, no SDK), ADR-0040 (one-time link codes), ADR-0045 (the conversation agent is
where I5 lives). I6: the bot acts only in the student's own chat and never for a chat
it cannot tie to a user.

## 3. How it works
- `updates.py` (ADR-0075): Pydantic models of the Update subset Ripple reads, all
  `extra="ignore"`. `parse_update(raw, dropped)` gives `IncomingText` (private chat,
  human sender, non-empty text, forwarded flag, `source_ref =
  telegram:<chat>:<message>`) or `IncomingCallback` (button tap with its chat), or
  `None` with a counted reason. Groups, bots, media and other update kinds are dropped.
- `dispatcher.py` (ADR-0076): `InboundDispatcher.handle(update) -> Outcome(replies,
  ack, path)`. Pure: no client, no sending. Looks the chat up through `ChatDirectory`
  (`ScanningChatDirectory` over `UserStore.list_users`). Unlinked: `/start` explains,
  `/link <code>` calls `link_telegram` under `RateLimiter.allow("telegram-link:<chat>",
  5, 10 min)`, anything else gets the instructions. Linked: `/questions` (cards from
  `answers.pending_questions` with `question_keyboard`), `/forget <id>` (card with
  `forget_keyboard`, pending for `confirmation_ttl`), `/export` (dashboard URL),
  `/opening <text>` or the heuristic `looks_like_opening` (200+ characters, two job
  keywords, one if forwarded) into `Services.opening_parser` then `opening_recorder`,
  everything else into `Conversation.turn(user_id, text, message_id=source_ref)`.
  Button taps: `decode_callback` then an ownership and state check on the memory,
  then `confirm_still_holds` / `answer_no_longer_holds`; "Correct it" arms a pending
  correction and the next text goes to `answer_with_correction`; a forget confirm must
  match the pending request and its age, then `ripple.core.forget` runs.
- `render.py`: `render_reply` = agent text, blank line, `Sources:` and `[n] <memory
  id>` with `(unconfirmed)` for flagged citations; `QuestionCard.text()`; `split_text`
  keeps every piece under 4096 characters, cutting at line breaks.
- `keyboards.py`: `Button`, `InlineKeyboard.reply_markup()`, the codec
  `a:<s|n|c>:<id>` and `f:<y|n>:<id>` (64-byte cap enforced in `Button`).
- `ratelimit.py`: `RateLimiter` protocol and `InMemoryRateLimiter` (sliding window on
  the injected clock; refused attempts are not recorded). `ledger.py`: `UpdateLedger`
  protocol (`first_sight`) and the bounded in-memory LRU.
- `telegram.py` (ADR-0077): `TelegramBotApi(token, clock, client=…)` composes
  `TelegramTransport` and adds `send_message(keyboard=…)`, `answer_callback_query`,
  `get_updates`, `set_webhook`; `_call` allows exactly those four method names and
  raises `TelegramCallError` (method, status, description; never the token).
- `channel.py`: `TelegramChannel.receive(raw)`: ledger → parse → dispatch →
  `deliver` (toast first, then each reply split, keyboard on the last piece). Any
  exception is logged with its traceback, counted in `stats.failed`, and answered with
  a fixed apology to the same chat; never re-raised.
- `ripple.api.routers.telegram`: `install_telegram_webhook(app, TelegramWebhook(channel,
  secret, timeout))`; the route checks the secret header in constant time (401), parses
  JSON (200 `not_json` otherwise), runs `channel.receive` under `asyncio.wait_for`
  (200 `timeout`), else 200 with the receive result.
- `register.py`: `python -m ripple.notify.inbound.register --url … | --remove
  [--drop-pending]` calls `setWebhook` with `TELEGRAM_WEBHOOK_SECRET`.
- `ripple.worker.telegram_poll`: `poll_once` / `poll_forever` over `getUpdates`
  offsets; `main()` wires real services with in-memory saver, ledger and limiter.
- `wiring.py`: `channel_from_env(services, conversation, api, env)` and
  `development_conversation_agent(...)`; reads `RIPPLE_DASHBOARD_URL`.

## 4. Trade-offs
- Replies are returned, not sent, by the dispatcher. Every command is tested without
  a transport; the price is one more object (`TelegramChannel`) between route and logic.
- At-most-once on `update_id`: a failed update is lost rather than repeated. Wrong if
  students regularly see the apology; then move the record after success for the
  read-only paths only.
- Callback data carries the memory id and the dispatcher re-checks it each tap, rather
  than a server-side token per button: simpler, and the check is the same one the API
  does (`owned_memory`).
- The JD heuristic is cheap and sometimes wrong; `/opening` is always right, and the
  parser refuses non-JDs.
- The citation footer numbers memories, not claim lines: `ConversationReply` does not
  map lines to citations. Inline `[n]` markers need the agent to emit them (handover).
- `ScanningChatDirectory` is O(users) per update: right for 15 users, wrong for 1,500.
- Pending corrections and forget confirmations are in process memory: a restart costs
  the student one more tap.

## 5. Failure modes and tests
| Failure | Test |
|---|---|
| A stranger's chat makes the bot read or write | test_invariant_I6_unlinked_chat_cannot_trigger_any_write, test_dispatcher_unlinked_chat_gets_only_link_instructions_for_any_text |
| A reply goes to another user's chat, or an unlisted Bot API method is called | test_invariant_I6_bot_calls_only_allowed_methods_and_only_the_writing_chat, test_dispatcher_every_reply_is_addressed_to_the_chat_that_wrote |
| An invented claim reaches the student | test_invariant_I5_replies_never_carry_claims_without_a_retrieved_citation |
| Link code brute force | test_dispatcher_link_attempts_are_rate_limited_per_chat_five_per_ten_minutes |
| Code reused or used after expiry | test_dispatcher_link_code_works_once, test_dispatcher_link_code_expires_after_fifteen_minutes |
| A tap on another user's memory, a stale button, garbage data | test_dispatcher_answer_tap_on_another_users_memory_changes_nothing, test_dispatcher_answer_tap_on_a_memory_that_is_no_longer_pending_is_refused, test_dispatcher_answer_tap_with_garbage_callback_data_is_refused |
| One-tap or replayed deletion | test_dispatcher_forget_confirm_without_a_request_deletes_nothing, test_dispatcher_forget_confirmation_expires_after_the_ttl |
| Telegram redelivers an update | test_telegram_webhook_is_idempotent_on_update_id, test_channel_ignores_a_duplicate_update_id_without_dispatching |
| Wrong or missing secret | test_telegram_webhook_rejects_a_missing_secret_header_with_401, …wrong_secret… |
| Slow handler causes a retry storm | test_telegram_webhook_answers_200_when_processing_times_out |
| Handler crash leaks a traceback or a 500 | test_channel_logs_a_failure_and_apologises_to_the_same_chat |
| Reply over 4096 characters | test_channel_splits_a_long_reply_and_attaches_the_keyboard_to_the_last_piece |
| Group chat or bot sender accepted | test_parse_update_drops_a_group_chat_message_and_counts_it, test_parse_update_drops_messages_from_bots |
| Token in an error message | test_bot_api_raises_call_error_with_method_and_description_never_the_token |

## 6. Interview questions
1. *Where is I6 enforced for the bot?* Three places: `parse_update` accepts only
   private chats; the dispatcher refuses every action for a chat with no user and
   addresses replies only to the update's chat; `TelegramBotApi._call` allows four
   method names and the I6 test drives a whole session over a mock transport.
2. *Why answer 200 on failure?* Telegram treats non-2xx as "deliver again"; with
   at-most-once on the ledger the retry would be a no-op anyway, and a 5xx storm would
   only fill logs.
3. *Why is the dispatcher not a LangGraph graph?* Commands are deterministic; only
   free text needs a model, and that already has its graph (ADR-0045).
4. *What happens if the student taps "Still holds" twice?* The second tap finds the
   memory VALID, not PENDING_USER, and answers "already answered" without a write.
5. *Why does the webhook not use the bearer auth the API has?* Telegram cannot send a
   bearer token; its documented mechanism is the secret-token header, compared in
   constant time against a value only the operator and Telegram know.

## 7. Exercise
Add a `/pause` command that records nothing but replies with a fixed sentence. Predict
which tests fail before you change `_command`, and which named I6 test still passes
untouched, then run `uv run pytest tests/notify/test_inbound_dispatcher.py -q`.
