# ADR-0025: Notifications: Telegram Bot API over httpx; email deferred
Status: Accepted · Date: 2026-10-19 (under the autonomous mandate)

## Context
FR-9: a daily digest and alerts for high-fit openings or deadlines within 48 hours.
The proposal names Telegram first and email second. No SDK was chosen.

## Decision
A thin transport over the Telegram Bot API using `httpx` (already a dependency,
ADR-0022): `sendMessage` with a bot token from the environment, chat ids stored per
user (identity workstream). No Telegram SDK. A `Transport` protocol with a recording
fake makes digests testable offline; a real message is sent only by the worker in
production (I6 forbids acting on external sites; a message to the user's own chat is
not that). Email is deferred until the pilot asks for it; the digest renderer is
transport-agnostic so adding SMTP later is one transport class.

## Alternatives considered
- python-telegram-bot — full framework (polling, handlers) for what is one POST per
  digest. Lost on weight.
- Email first — needs an SMTP provider account and deliverability work; students read
  Telegram. Lost for now.

## Consequences
- Linking a Telegram chat to a user needs a one-time code flow (identity workstream).
- Rate limits: one message per user per digest; alerts batched per run.

## Revisit if
Telegram's Bot API terms change, or the pilot needs rich interactions that justify a
framework.
