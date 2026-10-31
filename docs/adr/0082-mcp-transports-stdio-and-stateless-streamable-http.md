# ADR-0082: MCP transports: stdio for local clients, stateless streamable HTTP for the VPS, one wiring
Status: Accepted under the autonomous mandate · Date: 2026-10-24 · Workstream WS-11
Completes ADR-0080 and ADR-0081; deployment context in ADR-0029.

## Context
The production plan fixes "stdio and streamable HTTP". A desktop agent spawns a local
process and talks over pipes; a hosted agent needs an HTTP endpoint on the pilot VPS
behind Caddy (ADR-0029). Both must be built from the same `Services` the API uses
(ADR-0041) plus a `Retriever`, which `Services` does not carry today.

## Decision
1. **Entry point.** `python -m ripple.mcp_server` serves stdio by default; `--transport
   http` (or `RIPPLE_MCP_TRANSPORT=http`) serves streamable HTTP on `RIPPLE_MCP_HOST`
   (default 127.0.0.1), `RIPPLE_MCP_PORT` (default 8765) and path `/mcp`, overridable
   by flags. Settings come from the environment only, as everywhere else.
2. **Streamable HTTP is stateless with JSON responses.** No server-held sessions, no
   SSE streams, no event store: the tools are short request/response calls, Caddy
   can proxy them like any route, and a worker restart loses nothing. The SDK's
   DNS-rebinding protection stays on for loopback hosts.
3. **One wiring.** `ripple.mcp_server.wiring.production_services(env)` calls
   `ripple.api.wiring.build_services(Settings.from_env(env))` and builds the retriever
   as `HybridRetriever(services.store, PostgresSearchBackend(engine))` with a second
   engine from the same `DATABASE_URL` (the store does not expose its engine; the
   handover requests that `Services` carry the retriever so both transports and the
   API share one). Tests pass a `Services` built from fakes and a retriever over the
   in-memory backend.
4. **Transport-specific identity.** stdio uses the environment token source, HTTP the
   header source (ADR-0081); nothing else differs between the two.

## Alternatives considered
- **SSE transport** — deprecated in the MCP spec in favour of streamable HTTP. Lost.
- **Stateful streamable HTTP with sessions and resumability** — needed only for
  long-running tools and server-initiated requests; none exist here. Lost for now.
- **Mounting the MCP app inside the FastAPI API process** — one port and one process,
  but a different lifecycle (the MCP app needs its session manager task group) and the
  API's error handlers do not apply to JSON-RPC. Lost; Caddy routes `/mcp` to the MCP
  container instead (deployment follow-up for WS-0).

## Consequences
- Two database engines in the MCP process until `Services` carries the retriever.
- Elicitation and sampling (server-to-client requests) are unavailable in stateless
  mode; none of the seven tools needs them.
- The SDK's DNS-rebinding guard is tied to the bind host: on 127.0.0.1 it rejects any
  `Host` header that is not localhost (421), which a reverse proxy forwarding the
  public host name would trip. Deployed behind Caddy the server binds 0.0.0.0 inside
  its container (guard off, Caddy is the boundary); the loopback default is for a
  developer's machine.
- The stdio path is exercised in tests through the SDK's in-memory transport, which
  runs the same `Server.run` loop over memory streams; the pipe wrapper itself is the
  SDK's and is not unit-tested here.

## Revisit if
A tool needs progress or elicitation, or the deployment prefers one process for API
and MCP.
