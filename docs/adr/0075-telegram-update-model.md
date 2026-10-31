# ADR-0075: Telegram inbound: a strict subset of the Update type, private chats only, drops counted
Status: Accepted under the autonomous mandate · Date: 2026-10-24

## Context
ADR-0025 chose the Telegram Bot API over httpx with no SDK for outbound digests. The
production plan makes Telegram the student's inbound channel too: commands, free text
to the conversation agent (ADR-0045), answers to parked questions (FR-7), pasted or
forwarded job descriptions (FR-2). Telegram's `Update` type has dozens of kinds and
fields and changes with every Bot API release. Without an SDK, Ripple must decide how
much of it to understand and what to do with the rest. I6 forbids acting outside the
student's own chat; I4 says boundary input is parsed into a schema before use.

## Decision
1. `ripple.notify.inbound.updates` models exactly what Ripple reads, as Pydantic
   models with `extra="ignore"`: `update_id`; `message` with `message_id`, `chat`
   (`id`, `type`), `from` (`id`, `is_bot`), `text`, and the two forward markers
   (`forward_origin`, `forward_date`); `callback_query` with `id`, `from`, `message`
   and `data`. Nothing else is modelled.
2. `parse_update(raw, dropped)` returns a normalised `IncomingText` or
   `IncomingCallback`, or `None`. Every `None` increments a counter with a reason
   (`invalid`, `unsupported_kind`, `no_text`, `not_private_chat`, `from_bot`,
   `no_sender`, `no_callback_data`, `no_callback_chat`, `not_an_object`). Parsing
   never raises: the webhook must answer 200 whatever Telegram sends.
3. Only `chat.type == "private"` is accepted, for messages and for the message a
   callback query belongs to. Group and channel updates are dropped before any
   lookup. Messages from bots are dropped.
4. `IncomingText.source_ref` is `telegram:<chat id>:<message id>`; it becomes the
   `source_ref` of memories written from that message and the opening's source.

## Alternatives considered
- A Telegram SDK (python-telegram-bot, aiogram) with complete types — rejected in
  ADR-0025 for weight; nothing has changed, and the SDK's dispatcher would replace the
  one Ripple needs to test offline.
- Modelling the full Update type by hand — hundreds of lines nobody maintains; the
  fields Ripple does not read would still be ignored.
- `extra="forbid"` for strictness — a Bot API release adding one field would stop the
  pilot's bot until a code change. Strictness belongs on the fields used, not on the
  envelope.
- Accepting group chats with per-member scoping — a group lets one member read what
  another's memory says through the bot's replies; a private chat is the scope I6 asks
  for and the only one the pilot needs.

## Consequences
- Edited messages, media, locations, polls, reactions and inline-mode queries are
  dropped and counted; a student who sends a photo of a JD gets no reply. The handover
  lists OCR of images as out of scope.
- The drop counters are per process and exposed on `TelegramChannel.stats` for logs;
  a metrics endpoint can read them later (WS-13 health).
- `forward_origin` is held as an opaque object, so forwarded-from identities are never
  stored (no third-party personal data from forwarded mails).

## Revisit if
The pilot shows students sending JDs as images or documents often enough to want
document text extraction, or Telegram deprecates the message/callback shapes used.
