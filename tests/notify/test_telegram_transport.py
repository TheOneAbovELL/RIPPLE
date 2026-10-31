import asyncio
import json
import logging

import httpx
import pytest

from ripple.core.errors import ConfigurationError
from ripple.notify.errors import MessageTooLongError, TelegramSendError
from ripple.notify.telegram import MAX_TEXT_LENGTH, TelegramTransport
from tests.fakes.clock import DEFAULT_START, FakeClock

TOKEN = "123456:TEST-TOKEN-not-real"
CHAT = "4242"


def _transport(handler):
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return TelegramTransport(TOKEN, FakeClock(), client=client)


def _ok(message_id: int = 77):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True, "result": {"message_id": message_id}})

    return handler


def test_telegram_transport_posts_send_message_with_chat_id_and_text():
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return _ok()(request)

    receipt = asyncio.run(_transport(handler).send(CHAT, "hello"))

    assert len(seen) == 1
    request = seen[0]
    assert request.method == "POST"
    assert str(request.url) == f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    assert json.loads(request.content) == {
        "chat_id": CHAT,
        "text": "hello",
        "disable_web_page_preview": True,
    }
    assert receipt.chat_id == CHAT
    assert receipt.message_id == "77"
    assert receipt.sent_at == DEFAULT_START


def test_telegram_transport_raises_on_bot_api_error_with_description_and_retry_after():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            json={
                "ok": False,
                "error_code": 429,
                "description": "Too Many Requests: retry after 7",
                "parameters": {"retry_after": 7},
            },
        )

    with pytest.raises(TelegramSendError) as info:
        asyncio.run(_transport(handler).send(CHAT, "hello"))
    assert info.value.status_code == 429
    assert info.value.error_code == 429
    assert info.value.retry_after == 7
    assert "retry after 7" in str(info.value)


def test_telegram_transport_raises_when_ok_is_false_even_with_http_200():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": False, "description": "Bad Request: chat not found"})

    with pytest.raises(TelegramSendError, match="chat not found"):
        asyncio.run(_transport(handler).send(CHAT, "hello"))


def test_telegram_transport_raises_on_unparseable_response_body():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(502, text="<html>Bad Gateway</html>")

    with pytest.raises(TelegramSendError) as info:
        asyncio.run(_transport(handler).send(CHAT, "hello"))
    assert info.value.status_code == 502
    assert "unparseable" in info.value.description


def test_telegram_transport_raises_on_json_that_is_not_an_object():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=["ok"])

    with pytest.raises(TelegramSendError, match="not an object"):
        asyncio.run(_transport(handler).send(CHAT, "hello"))


def test_telegram_transport_wraps_connection_errors_without_the_token():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    with pytest.raises(TelegramSendError) as info:
        asyncio.run(_transport(handler).send(CHAT, "hello"))
    assert info.value.status_code is None
    assert TOKEN not in str(info.value)


def test_telegram_transport_refuses_text_over_the_bot_api_limit_without_sending():
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return _ok()(request)

    with pytest.raises(MessageTooLongError):
        asyncio.run(_transport(handler).send(CHAT, "x" * (MAX_TEXT_LENGTH + 1)))
    assert seen == []


def test_telegram_transport_never_logs_token_or_text_at_info_on_any_logger(caplog):
    # Root at INFO: this captures httpx's own "HTTP Request: POST <url>" line too, which
    # would carry the token in the URL path without the transport's redaction filter.
    caplog.set_level(logging.INFO)
    asyncio.run(_transport(_ok()).send(CHAT, "the secret digest text"))

    messages = [f"{r.name}: {r.getMessage()} {r.__dict__}" for r in caplog.records]
    assert any(r.name == "httpx" for r in caplog.records), "httpx request line not captured"
    assert any("<redacted>" in m for m in messages)
    assert all(TOKEN not in m for m in messages)
    assert all("secret digest" not in m for m in messages)
    assert any("telegram message sent" in m for m in messages)


def test_telegram_transport_from_env_reads_the_token():
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return _ok()(request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    transport = TelegramTransport.from_env(
        FakeClock(), env={"TELEGRAM_BOT_TOKEN": TOKEN}, client=client
    )
    asyncio.run(transport.send(CHAT, "hi"))
    assert str(seen[0].url).endswith(f"/bot{TOKEN}/sendMessage")


def test_telegram_transport_from_env_refuses_a_missing_token():
    with pytest.raises(ConfigurationError, match="TELEGRAM_BOT_TOKEN"):
        TelegramTransport.from_env(FakeClock(), env={})


def test_telegram_transport_refuses_an_empty_token():
    with pytest.raises(ConfigurationError):
        TelegramTransport("", FakeClock())
