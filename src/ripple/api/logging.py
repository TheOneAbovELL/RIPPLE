"""JSON structured logging and request ids (ADR-0018, ADR-0098).

One trace id per request: `RequestIdMiddleware` takes the client's `X-Request-ID` when
it looks like one, mints a uuid otherwise, binds it to a context variable for the life
of the request and echoes it in the response. `TraceIdFilter` copies that value onto
every log record emitted meanwhile, so a Router log line, an Intake event and the
access log of one request all carry the same id without any of them being told. Code
that already sets `trace_id` in `extra` (the Router, the parsers) is left alone unless it
set None. Handlers pass `current_trace_id()` on to Intake so the ChangeEvent's trace_id
matches the logs (I2: events and their evidence stay findable).

The formatter never adds content: what is logged is whatever the caller put in the
record, and python.md forbids secrets and full user messages at INFO at the call site.
"""

import json
import logging
import logging.config
import re
from collections.abc import Awaitable, Callable, MutableMapping
from contextvars import ContextVar, Token
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

TRACE_ID_HEADER = "x-request-id"
_TRACE_ID_SHAPE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")

_trace_id: ContextVar[str | None] = ContextVar("ripple_trace_id", default=None)


def current_trace_id() -> str | None:
    """The request's id, or None outside a request (worker jobs bind their own)."""
    return _trace_id.get()


def bind_trace_id(trace_id: str) -> Token[str | None]:
    return _trace_id.set(trace_id)


def reset_trace_id(token: Token[str | None]) -> None:
    _trace_id.reset(token)


def new_trace_id() -> str:
    return uuid4().hex


def accept_trace_id(candidate: str | None) -> str:
    """The client's id when it is a plain token, else a fresh one: a header is input."""
    if candidate is not None and _TRACE_ID_SHAPE.match(candidate):
        return candidate
    return new_trace_id()


# ---- records --------------------------------------------------------------------------


class TraceIdFilter(logging.Filter):
    """Stamp the bound trace id on records that do not carry one of their own."""

    def filter(self, record: logging.LogRecord) -> bool:
        if getattr(record, "trace_id", None) is None:
            record.trace_id = current_trace_id()
        return True


# Attributes every LogRecord has; anything else on the record came from `extra`.
_STANDARD_ATTRS = frozenset(
    {
        *vars(logging.LogRecord("", 0, "", 0, "", None, None)),
        "message",
        "asctime",
        "taskName",
    }
)


class JsonFormatter(logging.Formatter):
    """One JSON object per line: timestamp, level, logger, message, trace_id, extras."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": getattr(record, "trace_id", None),
        }
        for key, value in record.__dict__.items():
            if key not in _STANDARD_ATTRS and key not in payload:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


def logging_config(level: str = "INFO", *, json_lines: bool = True) -> dict[str, Any]:
    """A logging.config dict: stderr handler, trace-id filter, JSON or plain lines."""
    formatter = "json" if json_lines else "plain"
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {"trace_id": {"()": "ripple.api.logging.TraceIdFilter"}},
        "formatters": {
            "json": {"()": "ripple.api.logging.JsonFormatter"},
            "plain": {"format": "%(asctime)s %(levelname)s %(name)s [%(trace_id)s] %(message)s"},
        },
        "handlers": {
            "stderr": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr",
                "formatter": formatter,
                "filters": ["trace_id"],
            }
        },
        "root": {"level": level.upper(), "handlers": ["stderr"]},
        # uvicorn's own loggers keep their records but go through the same handler.
        "loggers": {
            "uvicorn": {"level": level.upper(), "handlers": ["stderr"], "propagate": False},
            "uvicorn.error": {"level": level.upper(), "handlers": ["stderr"], "propagate": False},
            "uvicorn.access": {"level": level.upper(), "handlers": ["stderr"], "propagate": False},
        },
    }


def configure_logging(level: str = "INFO", *, json_lines: bool = True) -> None:
    logging.config.dictConfig(logging_config(level, json_lines=json_lines))


# ---- middleware -----------------------------------------------------------------------

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]

log = logging.getLogger("ripple.api.access")


class RequestIdMiddleware:
    """Pure ASGI, so it runs before FastAPI's routing and after it for the response."""

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        trace_id = accept_trace_id(_header(scope, TRACE_ID_HEADER))
        token = bind_trace_id(trace_id)

        async def send_with_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((TRACE_ID_HEADER.encode(), trace_id.encode()))
                message["headers"] = headers
                log.info(
                    "request",
                    extra={
                        "method": scope.get("method"),
                        "path": scope.get("path"),
                        "status": message.get("status"),
                    },
                )
            await send(message)

        try:
            await self._app(scope, receive, send_with_id)
        finally:
            reset_trace_id(token)


def _header(scope: Scope, name: str) -> str | None:
    wanted = name.encode()
    for key, value in scope.get("headers", []):
        if key.lower() == wanted:
            return value.decode("latin-1")
    return None
