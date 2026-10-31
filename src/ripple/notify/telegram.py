"""Telegram Bot API transport (ADR-0025): one POST per message, over httpx.

The token comes from the environment and appears only in the request URL; it is never
logged and never part of an exception message. The only endpoint this module knows is
`sendMessage` on api.telegram.org, which is the one outbound call I6 permits: a message
to the user's own chat.
"""

import logging
import os
from collections.abc import Mapping
from typing import Any

import httpx

from ripple.core.clock import Clock
from ripple.core.errors import ConfigurationError
from ripple.notify.contracts import MessageReceipt
from ripple.notify.errors import MessageTooLongError, TelegramSendError

log = logging.getLogger("ripple.notify.telegram")

ENV_TOKEN = "TELEGRAM_BOT_TOKEN"
BOT_API_BASE_URL = "https://api.telegram.org"
SEND_MESSAGE_METHOD = "sendMessage"
MAX_TEXT_LENGTH = 4096  # Bot API limit per message
DEFAULT_TIMEOUT_SECONDS = 10.0


class _RedactToken(logging.Filter):
    """httpx logs its request line (method and full URL) at INFO; the URL carries the
    token, so every send would write the secret to the log without this filter."""

    def __init__(self, token: str) -> None:
        super().__init__()
        self._token = token

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, tuple) and any(self._token in str(a) for a in record.args):
            record.args = tuple(
                str(a).replace(self._token, "<redacted>") if self._token in str(a) else a
                for a in record.args
            )
        if isinstance(record.msg, str) and self._token in record.msg:
            record.msg = record.msg.replace(self._token, "<redacted>")
        return True


class TelegramTransport:
    def __init__(
        self,
        token: str,
        clock: Clock,
        *,
        client: httpx.AsyncClient | None = None,
        base_url: str = BOT_API_BASE_URL,
    ) -> None:
        if not token:
            raise ConfigurationError("telegram bot token is empty")
        self._token = token
        self._clock = clock
        self._client = (
            client if client is not None else httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS)
        )
        self._base_url = base_url.rstrip("/")
        logging.getLogger("httpx").addFilter(_RedactToken(token))

    @classmethod
    def from_env(
        cls,
        clock: Clock,
        *,
        env: Mapping[str, str] | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> "TelegramTransport":
        token = (env if env is not None else os.environ).get(ENV_TOKEN, "")
        if not token:
            raise ConfigurationError(f"{ENV_TOKEN} is not set")
        return cls(token, clock, client=client)

    async def send(self, chat_id: str, text: str) -> MessageReceipt:
        if len(text) > MAX_TEXT_LENGTH:
            raise MessageTooLongError(len(text), MAX_TEXT_LENGTH)
        payload = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
        try:
            response = await self._client.post(self._method_url(SEND_MESSAGE_METHOD), json=payload)
        except httpx.HTTPError as exc:
            raise TelegramSendError(None, f"transport failure: {type(exc).__name__}") from exc
        body = _parse_body(response)
        if response.status_code >= 400 or not body.get("ok", False):
            raise TelegramSendError(
                response.status_code,
                str(body.get("description", "no description")),
                error_code=_optional_int(body.get("error_code")),
                retry_after=_optional_int(_mapping(body, "parameters").get("retry_after")),
            )
        message_id = _optional_int(_mapping(body, "result").get("message_id"))
        receipt = MessageReceipt(
            chat_id=chat_id,
            message_id=str(message_id) if message_id is not None else None,
            sent_at=self._clock.now(),
        )
        log.info(
            "telegram message sent",
            extra={"message_id": receipt.message_id, "text_length": len(text)},
        )
        return receipt

    async def aclose(self) -> None:
        await self._client.aclose()

    def _method_url(self, method: str) -> str:
        return f"{self._base_url}/bot{self._token}/{method}"


def _parse_body(response: httpx.Response) -> dict[str, Any]:
    try:
        body: object = response.json()
    except ValueError as exc:
        raise TelegramSendError(
            response.status_code, "unparseable response body (not JSON)"
        ) from exc
    if not isinstance(body, dict):
        raise TelegramSendError(response.status_code, "unparseable response body (not an object)")
    return {str(key): value for key, value in body.items()}  # pyright: ignore[reportUnknownVariableType, reportUnknownArgumentType]


def _mapping(body: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value: object = body.get(key)
    if isinstance(value, Mapping):
        return {str(k): v for k, v in value.items()}  # pyright: ignore[reportUnknownVariableType, reportUnknownArgumentType]
    return {}


def _optional_int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None
