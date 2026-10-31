"""TelegramBotApi over httpx.MockTransport: the four methods, their payloads, errors."""

import asyncio
import json
from collections.abc import Callable

import httpx
import pytest

from ripple.core.errors import ConfigurationError
from ripple.notify.errors import MessageTooLongError
from ripple.notify.inbound.errors import TelegramCallError
from ripple.notify.inbound.keyboards import question_keyboard
from ripple.notify.inbound.telegram import ALLOWED_UPDATES, TelegramBotApi
from ripple.notify.telegram import MAX_TEXT_LENGTH
from tests.fakes.clock import FakeClock

TOKEN = "123456:TEST-TOKEN-not-real"


class Recorder:
    def __init__(self, result: object = True) -> None:
        self.requests: list[httpx.Request] = []
        self.result = result

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return httpx.Response(200, json={"ok": True, "result": self.result})

    @property
    def methods(self) -> list[str]:
        return [r.url.path.rsplit("/", 1)[-1] for r in self.requests]

    def payload(self, index: int = -1) -> dict[str, object]:
        return json.loads(self.requests[index].content)


def api(handler: Callable[[httpx.Request], httpx.Response]) -> TelegramBotApi:
    return TelegramBotApi(
        TOKEN, FakeClock(), client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )


def test_bot_api_send_message_with_keyboard_posts_reply_markup():
    recorder = Recorder(result={"message_id": 5})

    receipt = asyncio.run(
        api(recorder.handler).send_message(4242, "Q?", keyboard=question_keyboard("m1"))
    )

    assert recorder.methods == ["sendMessage"]
    assert recorder.requests[0].url.path == f"/bot{TOKEN}/sendMessage"
    payload = recorder.payload()
    assert payload["chat_id"] == 4242 and payload["text"] == "Q?"
    assert payload["reply_markup"] == question_keyboard("m1").reply_markup()
    assert receipt.message_id == "5" and receipt.chat_id == "4242"


def test_bot_api_send_message_without_keyboard_uses_the_outbound_transport():
    recorder = Recorder(result={"message_id": 6})

    receipt = asyncio.run(api(recorder.handler).send_message(4242, "plain"))

    assert recorder.methods == ["sendMessage"]
    assert "reply_markup" not in recorder.payload()
    assert receipt.message_id == "6"


def test_bot_api_send_satisfies_the_transport_protocol_for_digests():
    recorder = Recorder(result={"message_id": 7})

    receipt = asyncio.run(api(recorder.handler).send("4242", "digest"))

    assert recorder.payload()["chat_id"] == "4242"
    assert receipt.message_id == "7"


def test_bot_api_send_message_refuses_text_over_the_limit_before_posting():
    recorder = Recorder()

    with pytest.raises(MessageTooLongError):
        asyncio.run(
            api(recorder.handler).send_message(
                1, "x" * (MAX_TEXT_LENGTH + 1), keyboard=question_keyboard("m")
            )
        )
    assert recorder.requests == []


def test_bot_api_answer_callback_query_posts_the_id_and_truncated_text():
    recorder = Recorder()

    asyncio.run(api(recorder.handler).answer_callback_query("cb-1", "y" * 250))

    assert recorder.methods == ["answerCallbackQuery"]
    assert recorder.payload() == {"callback_query_id": "cb-1", "text": "y" * 200}


def test_bot_api_get_updates_posts_offset_timeout_and_allowed_updates():
    recorder = Recorder(result=[{"update_id": 1}, {"update_id": 2}])

    updates = asyncio.run(api(recorder.handler).get_updates(offset=10, timeout_seconds=7))

    assert recorder.methods == ["getUpdates"]
    assert recorder.payload() == {
        "timeout": 7,
        "limit": 100,
        "allowed_updates": ALLOWED_UPDATES,
        "offset": 10,
    }
    assert updates == [{"update_id": 1}, {"update_id": 2}]


def test_bot_api_get_updates_without_an_offset_omits_it():
    recorder = Recorder(result=[])

    asyncio.run(api(recorder.handler).get_updates(offset=None))

    assert "offset" not in recorder.payload()


def test_bot_api_get_updates_rejects_a_result_that_is_not_a_list():
    recorder = Recorder(result={"unexpected": True})

    with pytest.raises(TelegramCallError, match="not a list"):
        asyncio.run(api(recorder.handler).get_updates(offset=None))


def test_bot_api_set_webhook_sends_url_secret_and_allowed_updates():
    recorder = Recorder(result=True)

    ok = asyncio.run(
        api(recorder.handler).set_webhook(
            "https://ripple.test/telegram/webhook", secret_token="s3cret"
        )
    )

    assert ok is True
    assert recorder.methods == ["setWebhook"]
    assert recorder.payload() == {
        "url": "https://ripple.test/telegram/webhook",
        "allowed_updates": ALLOWED_UPDATES,
        "drop_pending_updates": False,
        "secret_token": "s3cret",
    }


def test_bot_api_set_webhook_refuses_a_url_without_a_secret():
    recorder = Recorder()

    with pytest.raises(ConfigurationError, match="secret"):
        asyncio.run(api(recorder.handler).set_webhook("https://ripple.test/x", secret_token=""))
    assert recorder.requests == []


def test_bot_api_set_webhook_with_an_empty_url_removes_it_without_a_secret():
    recorder = Recorder(result=True)

    asyncio.run(api(recorder.handler).set_webhook("", secret_token=""))

    assert "secret_token" not in recorder.payload()
    assert recorder.payload()["url"] == ""


def test_bot_api_raises_call_error_with_method_and_description_never_the_token():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            json={
                "ok": False,
                "error_code": 429,
                "description": "Too Many Requests: retry after 3",
                "parameters": {"retry_after": 3},
            },
        )

    with pytest.raises(TelegramCallError) as info:
        asyncio.run(api(handler).answer_callback_query("cb"))

    assert info.value.method == "answerCallbackQuery"
    assert info.value.status_code == 429 and info.value.retry_after == 3
    assert TOKEN not in str(info.value)


def test_bot_api_wraps_transport_failures_without_the_token():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    with pytest.raises(TelegramCallError, match="ConnectError") as info:
        asyncio.run(api(handler).get_updates(offset=None))
    assert TOKEN not in str(info.value)


def test_bot_api_rejects_non_json_and_non_object_bodies():
    def html(request: httpx.Request) -> httpx.Response:
        return httpx.Response(502, text="<html>Bad Gateway</html>")

    def array(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=["ok"])

    with pytest.raises(TelegramCallError, match="not JSON"):
        asyncio.run(api(html).get_updates(offset=None))
    with pytest.raises(TelegramCallError, match="not an object"):
        asyncio.run(api(array).get_updates(offset=None))


def test_bot_api_from_env_requires_the_token():
    with pytest.raises(ConfigurationError, match="TELEGRAM_BOT_TOKEN"):
        TelegramBotApi.from_env(FakeClock(), env={})
    assert isinstance(
        TelegramBotApi.from_env(FakeClock(), env={"TELEGRAM_BOT_TOKEN": TOKEN}), TelegramBotApi
    )
