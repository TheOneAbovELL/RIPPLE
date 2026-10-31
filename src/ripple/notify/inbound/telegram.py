"""Bot API calls the inbound channel needs, on the outbound transport's client (ADR-0077).

`TelegramBotApi` composes `TelegramTransport` (ADR-0025): same token, same httpx
client, same log redaction, so one object serves digests, alerts and replies ("one
transport" in the production plan). It adds the four methods the channel uses and no
other: sendMessage with an inline keyboard, answerCallbackQuery, getUpdates (long
polling, development) and setWebhook (registration). I6 is checked against exactly
that list. This module is named `telegram.py` because the notify-wide I6 scan allows
httpx only in modules of that name; nothing else here may import it.
"""

import logging
import os
from collections.abc import Mapping
from typing import Any

import httpx

from ripple.core.clock import Clock
from ripple.core.errors import ConfigurationError
from ripple.notify.contracts import MessageReceipt
from ripple.notify.errors import MessageTooLongError
from ripple.notify.inbound.errors import TelegramCallError
from ripple.notify.inbound.keyboards import InlineKeyboard
from ripple.notify.telegram import (
    BOT_API_BASE_URL,
    DEFAULT_TIMEOUT_SECONDS,
    ENV_TOKEN,
    MAX_TEXT_LENGTH,
    TelegramTransport,
)

log = logging.getLogger("ripple.notify.inbound.telegram")

METHOD_SEND_MESSAGE = "sendMessage"
METHOD_ANSWER_CALLBACK = "answerCallbackQuery"
METHOD_GET_UPDATES = "getUpdates"
METHOD_SET_WEBHOOK = "setWebhook"
ALLOWED_METHODS = frozenset(
    {METHOD_SEND_MESSAGE, METHOD_ANSWER_CALLBACK, METHOD_GET_UPDATES, METHOD_SET_WEBHOOK}
)
ALLOWED_UPDATES = ["message", "callback_query"]  # what getUpdates and setWebhook subscribe to
POLL_TIMEOUT_SECONDS = 30
POLL_LIMIT = 100


class TelegramBotApi:
    def __init__(
        self,
        token: str,
        clock: Clock,
        *,
        client: httpx.AsyncClient | None = None,
        base_url: str = BOT_API_BASE_URL,
    ) -> None:
        self._client = (
            client if client is not None else httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS)
        )
        # The transport validates the token and installs the log redaction filter.
        self._transport = TelegramTransport(token, clock, client=self._client, base_url=base_url)
        self._token = token
        self._clock = clock
        self._base_url = base_url.rstrip("/")

    @classmethod
    def from_env(
        cls,
        clock: Clock,
        *,
        env: Mapping[str, str] | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> "TelegramBotApi":
        token = (env if env is not None else os.environ).get(ENV_TOKEN, "")
        if not token:
            raise ConfigurationError(f"{ENV_TOKEN} is not set")
        return cls(token, clock, client=client)

    @property
    def transport(self) -> TelegramTransport:
        """The plain-text outbound transport, for the digest service."""
        return self._transport

    # ---- Transport protocol ------------------------------------------------------

    async def send(self, chat_id: str, text: str) -> MessageReceipt:
        return await self._transport.send(chat_id, text)

    # ---- the inbound channel's methods -------------------------------------------

    async def send_message(
        self, chat_id: int | str, text: str, *, keyboard: InlineKeyboard | None = None
    ) -> MessageReceipt:
        if keyboard is None:
            return await self._transport.send(str(chat_id), text)
        if len(text) > MAX_TEXT_LENGTH:
            raise MessageTooLongError(len(text), MAX_TEXT_LENGTH)
        result = await self._call(
            METHOD_SEND_MESSAGE,
            {
                "chat_id": chat_id,
                "text": text,
                "disable_web_page_preview": True,
                "reply_markup": keyboard.reply_markup(),
            },
        )
        message_id = _optional_int(_mapping(result).get("message_id"))
        receipt = MessageReceipt(
            chat_id=str(chat_id),
            message_id=str(message_id) if message_id is not None else None,
            sent_at=self._clock.now(),
        )
        log.info(
            "telegram message with keyboard sent",
            extra={"message_id": receipt.message_id, "text_length": len(text)},
        )
        return receipt

    async def answer_callback_query(self, callback_id: str, text: str | None = None) -> None:
        payload: dict[str, Any] = {"callback_query_id": callback_id}
        if text:
            payload["text"] = text[:200]  # Bot API limit for the toast
        await self._call(METHOD_ANSWER_CALLBACK, payload)

    async def get_updates(
        self,
        *,
        offset: int | None,
        timeout_seconds: int = POLL_TIMEOUT_SECONDS,
        limit: int = POLL_LIMIT,
    ) -> list[dict[str, Any]]:
        """One long-poll call; raw update objects, oldest first (development only)."""
        payload: dict[str, Any] = {
            "timeout": timeout_seconds,
            "limit": limit,
            "allowed_updates": ALLOWED_UPDATES,
        }
        if offset is not None:
            payload["offset"] = offset
        result = await self._call(
            METHOD_GET_UPDATES, payload, timeout=float(timeout_seconds) + DEFAULT_TIMEOUT_SECONDS
        )
        if not isinstance(result, list):
            raise TelegramCallError(METHOD_GET_UPDATES, None, "result is not a list")
        return [_mapping(item) for item in result]  # pyright: ignore[reportUnknownVariableType]

    async def set_webhook(
        self, url: str, *, secret_token: str, drop_pending_updates: bool = False
    ) -> bool:
        """Register (or, with an empty url, remove) the webhook. Never called by tests."""
        payload: dict[str, Any] = {
            "url": url,
            "allowed_updates": ALLOWED_UPDATES,
            "drop_pending_updates": drop_pending_updates,
        }
        if url:
            if not secret_token:
                raise ConfigurationError("a webhook needs a secret token")
            payload["secret_token"] = secret_token
        result = await self._call(METHOD_SET_WEBHOOK, payload)
        return result is True

    async def aclose(self) -> None:
        await self._client.aclose()

    # ---- plumbing ------------------------------------------------------------------

    async def _call(
        self, method: str, payload: Mapping[str, Any], *, timeout: float | None = None
    ) -> object:
        if method not in ALLOWED_METHODS:
            raise TelegramCallError(method, None, "method is not one the channel may call")
        url = f"{self._base_url}/bot{self._token}/{method}"
        try:
            if timeout is None:
                response = await self._client.post(url, json=payload)
            else:
                response = await self._client.post(url, json=payload, timeout=timeout)
        except httpx.HTTPError as exc:
            raise TelegramCallError(
                method, None, f"transport failure: {type(exc).__name__}"
            ) from exc
        body = _parse_body(method, response)
        if response.status_code >= 400 or not body.get("ok", False):
            raise TelegramCallError(
                method,
                response.status_code,
                str(body.get("description", "no description")),
                error_code=_optional_int(body.get("error_code")),
                retry_after=_optional_int(_mapping(body.get("parameters")).get("retry_after")),
            )
        return body.get("result")


def _parse_body(method: str, response: httpx.Response) -> dict[str, Any]:
    try:
        body: object = response.json()
    except ValueError as exc:
        raise TelegramCallError(
            method, response.status_code, "unparseable response body (not JSON)"
        ) from exc
    if not isinstance(body, dict):
        raise TelegramCallError(
            method, response.status_code, "unparseable response body (not an object)"
        )
    return _mapping(body)


def _mapping(value: object) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return {str(k): v for k, v in value.items()}  # pyright: ignore[reportUnknownVariableType, reportUnknownArgumentType]
    return {}


def _optional_int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None
