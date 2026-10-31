"""TelegramChannel.receive (ADR-0077): dedupe, drop, deliver, fail safely."""

import asyncio
import logging

import pytest

from ripple.notify.inbound import dispatcher as d
from ripple.notify.inbound.channel import FAILURE_TEXT, ReceiveResult
from ripple.notify.inbound.keyboards import answer_data
from ripple.notify.telegram import MAX_TEXT_LENGTH
from tests.notify.test_inbound_support import (
    CHAT,
    build,
    raw_callback_update,
    raw_text_update,
    reply,
)


def test_channel_handles_a_text_update_and_sends_the_reply_to_that_chat():
    bot = build()

    async def run():
        await bot.user()
        return await bot.channel.receive(raw_text_update("/export", update_id=1))

    assert asyncio.run(run()) is ReceiveResult.HANDLED
    [(chat_id, text, keyboard)] = bot.sender.sent
    assert chat_id == CHAT and text.startswith("Export and deletion") and keyboard is None
    assert bot.channel.stats.handled == 1


def test_channel_ignores_a_duplicate_update_id_without_dispatching():
    bot = build()

    async def run():
        await bot.user()
        first = await bot.channel.receive(raw_text_update("/export", update_id=5))
        second = await bot.channel.receive(raw_text_update("/export", update_id=5))
        return first, second

    assert asyncio.run(run()) == (ReceiveResult.HANDLED, ReceiveResult.DUPLICATE)
    assert len(bot.sender.sent) == 1
    assert bot.channel.stats.duplicates == 1


def test_channel_drops_an_update_it_does_not_handle_and_counts_the_reason():
    bot = build()

    result = asyncio.run(bot.channel.receive({"update_id": 2, "edited_message": {}}))

    assert result is ReceiveResult.DROPPED
    assert bot.channel.stats.dropped.by_reason == {"unsupported_kind": 1}
    assert bot.sender.sent == []


def test_channel_answers_the_callback_before_sending_replies():
    bot = build()

    async def run():
        user = await bot.user()
        pending = await bot.pending(user)
        data = answer_data(pending.id, "still_holds")
        return await bot.channel.receive(raw_callback_update(data, update_id=3, callback_id="cb-3"))

    assert asyncio.run(run()) is ReceiveResult.HANDLED
    assert bot.sender.calls == ["answerCallbackQuery", "sendMessage"]
    assert bot.sender.acks == [("cb-3", None)]


def test_channel_splits_a_long_reply_and_attaches_the_keyboard_to_the_last_piece():
    long_text = "\n".join(f"line {i} " + "x" * 80 for i in range(80))  # > 4096 characters
    bot = build()
    bot.conversation._replies.append(  # pyright: ignore[reportPrivateUsage]
        reply(long_text, intent="tell")
    )

    async def run():
        await bot.user()
        return await bot.channel.receive(raw_text_update("tell me everything", update_id=4))

    asyncio.run(run())

    assert len(bot.sender.sent) >= 2
    assert all(len(text) <= MAX_TEXT_LENGTH for _, text, _ in bot.sender.sent)
    assert "".join(t.replace("\n", "") for _, t, _ in bot.sender.sent) == long_text.replace(
        "\n", ""
    )


def test_channel_logs_a_failure_and_apologises_to_the_same_chat(caplog: pytest.LogCaptureFixture):
    bot = build()
    bot.conversation.fail_with = RuntimeError("database exploded")

    async def run():
        await bot.user()
        with caplog.at_level(logging.ERROR, logger="ripple.notify.inbound.channel"):
            return await bot.channel.receive(raw_text_update("hello", update_id=6))

    result = asyncio.run(run())

    assert result is ReceiveResult.FAILED
    assert bot.sender.sent == [(CHAT, FAILURE_TEXT, None)]
    assert any("telegram update failed" in r.message for r in caplog.records)
    assert bot.channel.stats.failed == 1


def test_channel_failure_is_recorded_in_the_ledger_so_a_retry_is_not_reprocessed():
    bot = build()
    bot.conversation.fail_with = RuntimeError("once")

    async def run():
        await bot.user()
        first = await bot.channel.receive(raw_text_update("hello", update_id=8))
        bot.conversation.fail_with = None
        second = await bot.channel.receive(raw_text_update("hello", update_id=8))
        return first, second

    assert asyncio.run(run()) == (ReceiveResult.FAILED, ReceiveResult.DUPLICATE)
    assert bot.conversation.calls == [] or len(bot.conversation.calls) == 1


def test_channel_unlinked_chat_receives_only_the_link_instructions():
    bot = build()

    asyncio.run(bot.channel.receive(raw_text_update("my cgpa is 9", update_id=9)))

    assert bot.sender.sent == [(CHAT, d.UNLINKED_TEXT, None)]
