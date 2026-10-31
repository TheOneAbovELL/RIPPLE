"""Who is calling (ADR-0081): one bearer token per connection, resolved on every request.

The token is read by a transport-specific `TokenSource` (the Authorization header on
HTTP, `RIPPLE_MCP_TOKEN` on stdio, a holder in tests), hashed exactly as the API does
(ADR-0040) and looked up in the UserStore. `BearerIdentity` is server middleware: it
binds the resolved user to a contextvar for the duration of the request, refuses
`tools/call` without one, and lets discovery through.
"""

import contextvars
from collections.abc import Callable, Mapping
from typing import Any

from mcp.server.context import CallNext, HandlerResult, ServerRequestContext
from mcp.shared.exceptions import MCPError
from mcp.types import INVALID_REQUEST

from ripple.storage.users import User, UserStore, hash_token

TOKEN_VAR = "RIPPLE_MCP_TOKEN"
UNAUTHORIZED = "unauthorized: a valid bearer token is required"
TOOLS_CALL = "tools/call"

TokenSource = Callable[[ServerRequestContext[Any, Any]], str | None]

_current_user: contextvars.ContextVar[User | None] = contextvars.ContextVar(
    "ripple_mcp_user", default=None
)


def bearer_token(authorization: str | None) -> str | None:
    """The token of an `Authorization: Bearer <token>` value; None for anything else."""
    if not authorization:
        return None
    scheme, _, token = authorization.strip().partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


async def resolve_user(user_store: UserStore, raw_token: str | None) -> User | None:
    if not raw_token:
        return None
    return await user_store.user_for_token_hash(hash_token(raw_token))


def env_token_source(env: Mapping[str, str]) -> TokenSource:
    """stdio: the client launched this process for one user and set the token in its
    environment. Read per call, so a revoked token stops working without a restart."""

    def source(ctx: ServerRequestContext[Any, Any]) -> str | None:
        return env.get(TOKEN_VAR, "").strip() or None

    return source


def header_token_source(ctx: ServerRequestContext[Any, Any]) -> str | None:
    """Streamable HTTP: the SDK attaches the Starlette request to the context."""
    headers = getattr(ctx.request, "headers", None)
    if headers is None:
        return None
    return bearer_token(headers.get("authorization"))


def current_user() -> User:
    """The user bound by BearerIdentity for this request."""
    user = _current_user.get()
    if user is None:
        raise MCPError(INVALID_REQUEST, UNAUTHORIZED)
    return user


class BearerIdentity:
    """Server middleware (outermost-first on `Server.middleware`)."""

    def __init__(self, user_store: UserStore, token_source: TokenSource) -> None:
        self._user_store = user_store
        self._token_source = token_source

    async def __call__(
        self, ctx: ServerRequestContext[Any, Any], call_next: CallNext
    ) -> HandlerResult:
        user = await resolve_user(self._user_store, self._token_source(ctx))
        if user is None and ctx.method == TOOLS_CALL:
            raise MCPError(INVALID_REQUEST, UNAUTHORIZED)
        reset = _current_user.set(user)
        try:
            return await call_next(ctx)
        finally:
            _current_user.reset(reset)
