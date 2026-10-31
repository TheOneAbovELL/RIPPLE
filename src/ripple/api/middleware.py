"""Boundary middleware (ADR-0098): security headers and a request body cap.

Both are pure ASGI so they wrap everything FastAPI does, including error responses.
HSTS is deliberately absent: Caddy terminates TLS and sets it (ADR-0029); an API that
sets it behind plain HTTP in development would poison browsers against localhost.
"""

from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]

DEFAULT_MAX_BODY_BYTES = 8 * 1024 * 1024  # above the 5 MB resume cap plus multipart framing

SECURITY_HEADERS: tuple[tuple[bytes, bytes], ...] = (
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"referrer-policy", b"no-referrer"),
    (b"cache-control", b"no-store"),
    (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
)
# A JSON API renders nothing; the interactive docs are the one page that loads scripts.
CONTENT_SECURITY_POLICY = (
    b"content-security-policy",
    b"default-src 'none'; frame-ancestors 'none'",
)
DOCS_PREFIXES = ("/docs", "/redoc")


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        path = str(scope.get("path", ""))
        skip_csp = any(path == p or path.startswith(p + "/") for p in DOCS_PREFIXES)

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                present = {key.lower() for key, _ in message.get("headers", [])}
                extra = [h for h in SECURITY_HEADERS if h[0] not in present]
                if not skip_csp and CONTENT_SECURITY_POLICY[0] not in present:
                    extra.append(CONTENT_SECURITY_POLICY)
                message["headers"] = [*message.get("headers", []), *extra]
            await send(message)

        await self._app(scope, receive, send_with_headers)


class BodyTooLargeError(Exception):
    """Raised inside the wrapped receive once the body passes the cap."""


class BodySizeLimitMiddleware:
    """413 before a handler reads past the cap, whether or not Content-Length was sent.

    A declared length over the cap is refused without reading. A streamed body is
    counted as it arrives; crossing the cap raises inside `receive`. FastAPI catches
    that while parsing the body and answers 400, so the response the app sends after
    the cap was crossed is replaced by the 413 here; an app that lets the error
    propagate gets the same 413 from the except below. A handler that already started
    responding keeps its response, and the error then surfaces in the server log.
    """

    def __init__(self, app: ASGIApp, *, max_bytes: int = DEFAULT_MAX_BODY_BYTES) -> None:
        if max_bytes < 1:
            raise ValueError("max_bytes must be positive")
        self._app = app
        self._max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        declared = _content_length(scope)
        if declared is not None and declared > self._max_bytes:
            await _send_413(send, self._max_bytes)
            return

        received = 0
        exceeded = False
        response_started = False
        replaced = False

        async def counting_receive() -> Message:
            nonlocal received, exceeded
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self._max_bytes:
                    exceeded = True
                    raise BodyTooLargeError
            return message

        async def tracking_send(message: Message) -> None:
            nonlocal response_started, replaced
            if replaced:
                return  # the app's own answer to the oversized body; the 413 went out
            if message["type"] == "http.response.start":
                if exceeded:
                    replaced = True
                    await _send_413(send, self._max_bytes)
                    return
                response_started = True
            await send(message)

        try:
            await self._app(scope, counting_receive, tracking_send)
        except BodyTooLargeError:
            if response_started or replaced:
                raise
            await _send_413(send, self._max_bytes)


def _content_length(scope: Scope) -> int | None:
    for key, value in scope.get("headers", []):
        if key.lower() == b"content-length":
            try:
                return int(value)
            except ValueError:
                return None
    return None


async def _send_413(send: Send, max_bytes: int) -> None:
    body = b'{"detail":"request body larger than %d bytes","error":"BodyTooLarge"}' % max_bytes
    await send(
        {
            "type": "http.response.start",
            "status": 413,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})
