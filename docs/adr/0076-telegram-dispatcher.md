# ADR-0076: Telegram dispatcher: commands, link flow, keyboards for answers, two-step forget, agent for the rest
Status: Accepted under the autonomous mandate · Date: 2026-10-24

## Context
A linked chat must let the student do what the product promises without the dashboard:
link (ADR-0040 codes), confirm or correct parked beliefs (FR-7, `ripple.core.answers`),
record pasted or forwarded JDs (FR-2, the API's `OpeningParser`/`OpeningRecorder`
through `Services`), ask and tell (ADR-0045 agent), start deletion (I7 forget API) and
find export (FR-15). I5 forbids claims without evidence, I6 forbids acting for anyone
but the user in their own chat. Rate limiting at the bot boundary is a production-plan
decision (WS-13 provides the Redis backend).

## Decision
1. **`InboundDispatcher.handle(update) -> Outcome` is pure.** It decides replies and
   the callback acknowledgement; it never sends, holds no HTTP client, and takes its
   collaborators injected: `Services` (store, clock, runner, user store, opening
   parser and recorder), a `Conversation` protocol (`turn`), a `ChatDirectory`
   (chat id to user), a `RateLimiter` and the dashboard URL. Every reply carries the
   chat id of the update that caused it and nothing else can be addressed.
2. **Unlinked chats get link instructions only.** `/start` explains; `/link <code>`
   calls `ripple.storage.users.link_telegram` (one use, 15 minutes, ADR-0040) under a
   limit of 5 attempts per chat per 10 minutes through the `RateLimiter` protocol
   (`allow(key, limit, window)`; in-memory implementation here, Redis one from WS-13).
   Any other text or button from an unlinked chat answers with the instructions and
   touches nothing. A chat already linked cannot be relinked from Telegram.
3. **Commands for linked chats:** `/questions` lists `answers.pending_questions` as
   one card per question with an inline keyboard (Still holds / No longer / Correct
   it); `/forget <memory id>` shows the memory and a Delete / Keep keyboard;
   `/export` points to the dashboard; `/opening <text>` records a JD; `/help`.
   Unknown commands show help and never reach the agent.
4. **Callback data is a hint, not an authorisation.** Buttons carry
   `a:<s|n|c>:<memory id>` or `f:<y|n>:<memory id>` (64-byte cap). On every tap the
   dispatcher loads the memory, checks it belongs to the user and, for answers, that it
   is still PENDING_USER; then routes to `confirm_still_holds`, `answer_no_longer_holds`
   or, for a correction, asks for the next message and routes it to
   `answer_with_correction`. A race (`NotPendingError`) is reported, never retried.
5. **Forget is two steps with a time limit.** The confirm button works only if
   `/forget` for the same memory was issued in this chat within `confirmation_ttl`
   (5 minutes); then `ripple.core.forget` runs (whole chain, cascade, ForgetEvent;
   I7). A stale, replayed or unrequested confirm deletes nothing.
6. **Openings:** `/opening` always; otherwise a heuristic gate (at least 200
   characters and two job keywords, one if the message was forwarded) sends the text to
   the opening parser with `source_ref = telegram:<chat>:<message>`; an unparseable
   text is reported and nothing recorded.
7. **Everything else is one `Conversation.turn(user_id, text, message_id=source_ref)`**
   with thread id = user id. The reply is rendered as the agent's text plus a
   `Sources:` footer, `[n] <memory id>`, with `(unconfirmed)` after flagged citations;
   questions the turn raised become keyboard cards. The dispatcher adds no claim of
   its own, so I5 stays where ADR-0045 put it. A model outage is a fixed apology.

## Alternatives considered
- Reply keyboards (bottom-of-screen buttons) instead of inline keyboards — the answer
  would arrive as plain text and need re-parsing; inline callback data names the memory.
- Letting the agent classify `/commands` too — spends a model call on `/help` and
  makes command behaviour non-deterministic. Commands are parsed by code.
- Single-tap forget — a mis-tap deletes a whole chain; the dashboard asks twice and so
  does the bot.
- A free-text correction parsed by the agent's classifier — the agent's
  `answer_question` path exists, but after a "Correct it" tap the next message is
  unambiguous; the direct route avoids a model call and a wrong intent.
- Looking the user up by `from.id` rather than `chat.id` — in a private chat they are
  equal; `telegram_chat_id` is what the digest sends to, so one identity serves both.

## Consequences
- `ScanningChatDirectory` scans `UserStore.list_users` per update: linear in users,
  fine for the pilot. Contract request: `UserStore.user_for_telegram_chat(chat_id)`.
- Pending corrections and forget confirmations live in dispatcher memory: a restart
  forgets them and the student taps again. A Redis-backed table is not worth it until
  there is more than one API process.
- The heuristic can send a long chat message with job words to the parser; the parser
  refuses what is not a JD (`OpeningUnparseableError`), and `/opening` is explicit.
- The `[n]` footer numbers citations, not claim lines: the agent's reply does not map
  lines to citations (`ConversationReply.citations` is a set per reply). Inline markers
  need a contract change in the agent; requested in the handover.

## Revisit if
The pilot shows students tapping stale buttons or losing corrections to restarts more
than once a week, or a second API process makes in-memory state wrong.
