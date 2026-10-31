# ADR-0081: MCP identity: one bearer token per connection, hashed through ADR-0040, bound per request
Status: Accepted under the autonomous mandate · Date: 2026-10-24 · Workstream WS-11
Applies ADR-0040 (admin-created users, hashed bearer tokens) to the MCP server of ADR-0080.

## Context
Every MCP call must be scoped to one user, with the same tokens the API and the
dashboard use, so the author enrols a student once. MCP has two transports with
different places for a credential: streamable HTTP carries headers, stdio carries
nothing but the environment of the process the client spawned. The SDK's own bearer
support is built for OAuth (issuer and resource metadata endpoints) and only covers HTTP.

## Decision
1. **One resolver.** `ripple.mcp_server.identity.resolve_user(user_store, raw_token)`
   hashes with `ripple.storage.users.hash_token` and looks the hash up in `UserStore`,
   exactly as `ripple.api.auth.current_user` does. No second token format, no new table.
2. **Token per transport, resolved on every request.** A `TokenSource` reads the raw
   token for the current request: on HTTP from the `Authorization: Bearer` header of
   the request the SDK attaches to the context; on stdio from `RIPPLE_MCP_TOKEN` in the
   server process's environment (the client launches one server per user and sets it);
   tests inject a holder. The `BearerIdentity` server middleware resolves the user for
   every inbound request and binds it to a contextvar the tools read. Because the
   lookup happens per call, deleting the token row (ADR-0040 revocation) takes effect
   on the next call even on a long-lived stdio process.
3. **What needs identity.** `tools/call` without a resolvable user is refused with a
   JSON-RPC `INVALID_REQUEST` error whose message says `unauthorized`; discovery
   (`initialize`, `tools/list`, ping) works without one, since it reveals no user data.
   On HTTP an ASGI gate in front of the whole app additionally answers 401 with
   `WWW-Authenticate: Bearer` before any JSON-RPC is parsed, so an unauthenticated
   client cannot even open a session. A stdio server refuses to start when
   `RIPPLE_MCP_TOKEN` is unset (ConfigurationError naming the variable).
4. **Scoping.** Every id-addressed tool dereferences the memory and compares its
   `user_id` to the caller's; another user's id answers `not_found`, never a
   distinguishable error (ADR-0040's 404-not-403 rule). List-shaped tools pass the
   caller's user id to the store and retriever and never accept a user id argument.

## Alternatives considered
- **The SDK's `AuthSettings` + `TokenVerifier`** — gives the 401 path and a contextvar
  for free, but requires an OAuth issuer URL and publishes protected-resource metadata
  pointing at an authorization server we do not run; it also does nothing for stdio.
  Lost; the gate reuses the same header parsing in twenty lines.
- **Resolving the stdio user once at startup** — one lookup instead of one per call,
  but revocation would not reach a running process until restart. Lost.
- **Token as a tool argument** — would put a credential in every model turn and its
  logs. Lost.
- **Requiring identity for `tools/list` too** — harmless either way; left open so
  clients can show the tool catalogue before the user pastes a token.

## Consequences
- A leaked `RIPPLE_MCP_TOKEN` in a client config file is a leaked API token; the
  admin revokes it by deleting the row, as for the API.
- Two lookups per HTTP call (gate and middleware); negligible at pilot scale and
  simpler than threading the gate's result into the JSON-RPC context.
- Tokens still never expire (ADR-0040); unchanged here.

## Revisit if
The pilot moves to OAuth for the dashboard, in which case the SDK's auth settings
should replace the gate on HTTP; or an MCP client standard for stdio credentials appears.
