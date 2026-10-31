"""Streamable HTTP behind a bearer gate (ADR-0081, ADR-0082).

The SDK's Starlette app serves `/mcp` stateless with JSON responses; the gate in front
answers 401 with `WWW-Authenticate: Bearer` to any request without a token that maps to
a user, so an unauthenticated client never opens a session. Inside, `BearerIdentity`
resolves the same header per JSON-RPC request.
"""

from typing import Any

from mcp.server import Server
from starlette.applications import Starlette
from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from ripple.mcp_server.identity import bearer_token, resolve_user
from ripple.storage.users import UserStore

DEFAULT_PATH = "/mcp"
WWW_AUTHENTICATE = 'Bearer realm="ripple"'


class BearerGate:
    def __init__(self, app: ASGIApp, user_store: UserStore) -> None:
        self._app = app
        self._user_store = user_store

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        token = bearer_token(Headers(scope=scope).get("authorization"))
        if await resolve_user(self._user_store, token) is None:
            response = JSONResponse(
                {"error": "invalid_token", "error_description": "a valid bearer token is required"},
                status_code=401,
                headers={"WWW-Authenticate": WWW_AUTHENTICATE},
            )
            await response(scope, receive, send)
            return
        await self._app(scope, receive, send)


def streamable_http_app(
    server: Server[Any],
    user_store: UserStore,
    *,
    host: str = "127.0.0.1",
    path: str = DEFAULT_PATH,
) -> Starlette:
    """The ASGI app to serve; its lifespan runs the SDK's session manager."""
    app = server.streamable_http_app(
        streamable_http_path=path, json_response=True, stateless_http=True, host=host
    )
    app.add_middleware(BearerGate, user_store=user_store)
    return app
