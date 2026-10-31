# ADR-0040: Identity for the pilot: admin-created users, hashed bearer tokens, one-time Telegram link codes
Status: Accepted under the autonomous mandate · Date: 2026-10-19

## Context
docs/02 listed identity and auth as open. The pilot is 10 to 15 students the author
enrols personally (consent collected offline, NFR-3). Every API call must be scoped to
one user; ADR-0025 needs a chat id per user and a one-time code to link it; ADR-0006
says invariants and auth are enforced at the server boundary.

## Decision
- A `User` (id, display_name, created_at, telegram_chat_id nullable) and a `UserStore`
  protocol live in `ripple.storage.users` (storage may import only core, so the API
  imports storage, not the other way round). Postgres implementation beside it;
  in-memory implementation in tests/api/fakes.py; one shared contract test.
- **No sign-up endpoint.** `python -m ripple.api.admin create-user <name>` creates the
  user and prints a bearer token once. The token is `secrets.token_urlsafe(32)`; only
  its sha256 is stored (`api_tokens.token_hash`, unique). A database dump therefore
  grants no access, and the author can revoke by deleting the row.
- Every endpoint requires `Authorization: Bearer <token>`; a missing or unknown token
  is 401. Data is scoped by the token's user at the point an id is dereferenced; a
  memory or candidate belonging to another user answers **404**, not 403, so the API
  does not confirm that the id exists.
- Telegram linking: `POST /me/telegram/link` issues an 8-hex-character code that
  expires in 15 minutes and can be used once (`telegram_link_codes`). The worker
  (WS-6) calls `ripple.storage.users.link_telegram(store, code, chat_id, now)`, which
  consumes the code and stores the chat id. `ripple.api.directory.UserDirectoryAdapter`
  gives the worker the `UserDirectory` view it asked for.

## Alternatives considered
- OAuth / email magic links — right for a public product; for a hand-enrolled pilot it
  adds a mail provider and a login UI before the first student can use anything. Lost.
- Plain API keys stored in clear — simpler lookup, but one leaked dump leaks every
  account. Lost.
- 403 for other users' resources — leaks id existence across tenants. Lost.
- JWTs — stateless, but revocation needs a denylist anyway at this scale. Lost.

## Consequences
- One admin step per student; acceptable for the pilot, revisit for a public beta.
- `users.id` is a plain string on memories (no foreign key), so the memory tables did
  not change; deleting a user cascades tokens, codes and candidates explicitly
  (ADR-0044) and memories through the forget API (I7).
- Tokens have no expiry; the pilot ends in months and the author can rotate by hand.

## Revisit if
The pilot grows past what the author can enrol by hand, or a token leak is suspected.
