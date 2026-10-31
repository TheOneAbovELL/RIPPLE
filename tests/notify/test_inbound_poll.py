"""Development long-poll loop: offsets advance, updates reach the channel, errors back off."""

import asyncio
import json

import httpx

from ripple.notify.inbound.channel import TelegramChannel
from ripple.notify.inbound.ledger import InMemoryUpdateLedger
from ripple.notify.inbound.telegram import TelegramBotApi
from ripple.worker.telegram_poll import ERROR_BACKOFF_SECONDS, poll_forever, poll_once
from tests.fakes.clock import FakeClock
from tests.notify.test_inbound_support import build, raw_text_update
from tests.notify.test_inbound_telegram_api import TOKEN


class FakeBotServer:
    """Answers getUpdates from a queue of batches and records every call's payload."""

    def __init__(self, *batches: list[dict[str, object]]) -> None:
        self.batches = list(batches)
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.fail_next = False
        # Set when the batches run out: poll_forever reads it before its next call. A
        # mock transport never yields to the event loop, so a concurrent "stopper" task
        # would not get to run; the server itself ends the loop instead.
        self.exhausted = asyncio.Event()

    def handler(self, request: httpx.Request) -> httpx.Response:
        method = request.url.path.rsplit("/", 1)[-1]
        payload = json.loads(request.content)
        self.calls.append((method, payload))
        if method != "getUpdates":
            return httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})
        if self.fail_next:
            self.fail_next = False
            return httpx.Response(502, text="bad gateway")
        if not self.batches:
            self.exhausted.set()
            return httpx.Response(200, json={"ok": True, "result": []})
        return httpx.Response(200, json={"ok": True, "result": self.batches.pop(0)})

    def api(self) -> TelegramBotApi:
        client = httpx.AsyncClient(transport=httpx.MockTransport(self.handler))
        return TelegramBotApi(TOKEN, FakeClock(), client=client)


def test_poll_once_feeds_each_update_to_the_channel_and_returns_the_next_offset():
    server = FakeBotServer(
        [raw_text_update("/export", update_id=10), raw_text_update("/export", update_id=11)]
    )
    bot = build()
    channel = TelegramChannel(
        dispatcher=bot.dispatcher, sender=server.api(), ledger=InMemoryUpdateLedger()
    )

    async def run():
        await bot.user()
        return await poll_once(server.api(), channel, None, timeout_seconds=1)

    offset = asyncio.run(run())

    assert offset == 12
    assert channel.stats.handled == 2
    assert server.calls[0][1]["timeout"] == 1 and "offset" not in server.calls[0][1]


def test_poll_once_with_an_empty_batch_keeps_the_offset():
    server = FakeBotServer([])
    bot = build()
    channel = TelegramChannel(
        dispatcher=bot.dispatcher, sender=server.api(), ledger=InMemoryUpdateLedger()
    )

    assert asyncio.run(poll_once(server.api(), channel, 42, timeout_seconds=0)) == 42
    assert server.calls[0][1]["offset"] == 42


def test_poll_forever_passes_the_advanced_offset_and_stops_on_the_event():
    server = FakeBotServer(
        [raw_text_update("/export", update_id=20)], [raw_text_update("/export", update_id=21)]
    )
    bot = build()
    api = server.api()
    channel = TelegramChannel(dispatcher=bot.dispatcher, sender=api, ledger=InMemoryUpdateLedger())

    async def run():
        await bot.user()
        await poll_forever(api, channel, stop=server.exhausted, timeout_seconds=0)

    asyncio.run(run())

    offsets = [payload.get("offset") for method, payload in server.calls if method == "getUpdates"]
    assert offsets == [None, 21, 22]
    assert channel.stats.handled == 2


def test_poll_forever_backs_off_after_a_transport_error_and_continues():
    server = FakeBotServer([raw_text_update("/export", update_id=30)])
    server.fail_next = True
    bot = build()
    api = server.api()
    channel = TelegramChannel(dispatcher=bot.dispatcher, sender=api, ledger=InMemoryUpdateLedger())
    slept: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        slept.append(seconds)

    async def run():
        await bot.user()
        await poll_forever(api, channel, stop=server.exhausted, sleep=fake_sleep, timeout_seconds=0)

    asyncio.run(run())

    assert slept == [ERROR_BACKOFF_SECONDS]
    assert channel.stats.handled == 1
