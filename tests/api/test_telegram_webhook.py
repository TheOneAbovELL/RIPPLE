"""POST /telegram/webhook (ADR-0077): secret header, fast 200, idempotency, timeout."""

import asyncio

import pytest

from ripple.api.routers.telegram import (
    SECRET_HEADER,
    TelegramWebhook,
    install_telegram_webhook,
    webhook_secret_from_env,
)
from ripple.core.errors import ConfigurationError
from ripple.notify.inbound.channel import ReceiveResult
from tests.api.harness import body
from tests.notify.test_inbound_support import CHAT, Bot, build, raw_text_update

SECRET = "a-long-random-secret"
PATH = "/telegram/webhook"


def webhook_bot(*, timeout_seconds: float = 5.0) -> Bot:
    bot = build()
    install_telegram_webhook(bot.harness.app, TelegramWebhook(bot.channel, SECRET, timeout_seconds))
    return bot


def test_telegram_webhook_rejects_a_missing_secret_header_with_401():
    bot = webhook_bot()

    async def run():
        async with bot.harness.client() as client:
            return await client.post(PATH, json=raw_text_update("/start", update_id=1))

    response = asyncio.run(run())

    assert response.status_code == 401
    assert bot.sender.sent == []


def test_telegram_webhook_rejects_a_wrong_secret_header_with_401():
    bot = webhook_bot()

    async def run():
        async with bot.harness.client() as client:
            return await client.post(
                PATH, json=raw_text_update("/start", update_id=1), headers={SECRET_HEADER: "nope"}
            )

    assert asyncio.run(run()).status_code == 401
    assert bot.sender.sent == []


def test_telegram_webhook_processes_the_update_and_answers_200():
    bot = webhook_bot()

    async def run():
        async with bot.harness.client() as client:
            return await client.post(
                PATH, json=raw_text_update("/start", update_id=1), headers={SECRET_HEADER: SECRET}
            )

    response = asyncio.run(run())

    assert response.status_code == 200
    assert body(response) == {"ok": True, "result": ReceiveResult.HANDLED.value}
    [(chat_id, text, _)] = bot.sender.sent
    assert chat_id == CHAT and text.startswith("Hi, I am Ripple")


def test_telegram_webhook_is_idempotent_on_update_id():
    bot = webhook_bot()

    async def run():
        async with bot.harness.client() as client:
            first = await client.post(
                PATH, json=raw_text_update("/start", update_id=7), headers={SECRET_HEADER: SECRET}
            )
            second = await client.post(
                PATH, json=raw_text_update("/start", update_id=7), headers={SECRET_HEADER: SECRET}
            )
            return first, second

    first, second = asyncio.run(run())

    assert body(first)["result"] == "handled" and body(second)["result"] == "duplicate"
    assert len(bot.sender.sent) == 1


def test_telegram_webhook_answers_200_for_a_body_that_is_not_json():
    bot = webhook_bot()

    async def run():
        async with bot.harness.client() as client:
            return await client.post(
                PATH, content=b"<xml/>", headers={SECRET_HEADER: SECRET, "content-type": "text/xml"}
            )

    response = asyncio.run(run())

    assert response.status_code == 200 and body(response)["result"] == "not_json"


def test_telegram_webhook_answers_200_when_processing_times_out():
    bot = webhook_bot(timeout_seconds=0.05)

    async def slow_turn(*args: object, **kwargs: object):
        await asyncio.sleep(1)
        raise AssertionError("should have been cancelled")

    bot.conversation.turn = slow_turn  # type: ignore[method-assign]

    async def run():
        await bot.user()
        async with bot.harness.client() as client:
            return await client.post(
                PATH, json=raw_text_update("hello", update_id=9), headers={SECRET_HEADER: SECRET}
            )

    response = asyncio.run(run())

    assert response.status_code == 200 and body(response)["result"] == "timeout"


def test_telegram_webhook_without_installation_is_503():
    bot = build()
    install_telegram_webhook(bot.harness.app, TelegramWebhook(bot.channel, SECRET))
    bot.harness.app.state.telegram_webhook = None  # simulate a route mounted without a channel

    async def run():
        async with bot.harness.client() as client:
            return await client.post(PATH, json={}, headers={SECRET_HEADER: SECRET})

    assert asyncio.run(run()).status_code == 503


def test_telegram_webhook_is_hidden_from_the_openapi_schema():
    bot = webhook_bot()

    assert PATH not in bot.harness.app.openapi()["paths"]


def test_telegram_webhook_refuses_an_empty_secret_at_construction():
    bot = build()

    with pytest.raises(ConfigurationError, match="TELEGRAM_WEBHOOK_SECRET"):
        TelegramWebhook(bot.channel, "")


def test_webhook_secret_from_env_requires_the_variable():
    with pytest.raises(ConfigurationError, match="TELEGRAM_WEBHOOK_SECRET"):
        webhook_secret_from_env({})
    assert webhook_secret_from_env({"TELEGRAM_WEBHOOK_SECRET": " s "}) == "s"


def test_install_telegram_webhook_twice_mounts_the_route_once():
    bot = build()
    webhook = TelegramWebhook(bot.channel, SECRET)
    install_telegram_webhook(bot.harness.app, webhook)
    mounted_once = len(bot.harness.app.routes)
    install_telegram_webhook(bot.harness.app, webhook)

    assert len(bot.harness.app.routes) == mounted_once
