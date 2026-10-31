"""One update in, replies out: the path both the webhook and the poll loop share (ADR-0077).

`receive(raw)`: ledger first (at most once per update_id), then parse, dispatch and
deliver. A failure inside dispatch or delivery is logged with its traceback, counted,
and turned into a short apology to the same chat when that is still possible; it is
never re-raised, because the caller must answer Telegram 200 or face a retry storm.
"""

import logging
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol

from ripple.notify.contracts import MessageReceipt
from ripple.notify.inbound.dispatcher import InboundDispatcher, Outcome
from ripple.notify.inbound.keyboards import InlineKeyboard
from ripple.notify.inbound.ledger import UpdateLedger
from ripple.notify.inbound.render import split_text
from ripple.notify.inbound.updates import DroppedUpdates, parse_update

log = logging.getLogger("ripple.notify.inbound.channel")

FAILURE_TEXT = "Something went wrong on my side and nothing was changed. Please send that again."


class ReceiveResult(StrEnum):
    HANDLED = "handled"
    DUPLICATE = "duplicate"
    DROPPED = "dropped"
    FAILED = "failed"


class BotSender(Protocol):
    """The two outbound calls delivery needs; `TelegramBotApi` implements them."""

    async def send_message(
        self, chat_id: int | str, text: str, *, keyboard: InlineKeyboard | None = None
    ) -> MessageReceipt: ...

    async def answer_callback_query(self, callback_id: str, text: str | None = None) -> None: ...


@dataclass
class ChannelStats:
    handled: int = 0
    duplicates: int = 0
    failed: int = 0
    dropped: DroppedUpdates = field(default_factory=DroppedUpdates)


class TelegramChannel:
    def __init__(
        self,
        *,
        dispatcher: InboundDispatcher,
        sender: BotSender,
        ledger: UpdateLedger,
    ) -> None:
        self._dispatcher = dispatcher
        self._sender = sender
        self._ledger = ledger
        self.stats = ChannelStats()

    async def receive(self, raw: object) -> ReceiveResult:
        update_id = _update_id(raw)
        if update_id is not None and not await self._ledger.first_sight(update_id):
            self.stats.duplicates += 1
            log.info("duplicate telegram update ignored", extra={"update_id": update_id})
            return ReceiveResult.DUPLICATE
        update = parse_update(raw, self.stats.dropped)
        if update is None:
            log.info("telegram update dropped", extra={"update_id": update_id})
            return ReceiveResult.DROPPED
        try:
            outcome = await self._dispatcher.handle(update)
            await self.deliver(outcome)
        except Exception:
            self.stats.failed += 1
            log.exception(
                "telegram update failed",
                extra={"update_id": update.update_id, "chat_id": update.chat_id},
            )
            await self._apologise(update.chat_id)
            return ReceiveResult.FAILED
        self.stats.handled += 1
        return ReceiveResult.HANDLED

    async def deliver(self, outcome: Outcome) -> None:
        # The toast first: Telegram shows a spinner on the button until it is answered.
        if outcome.ack is not None:
            await self._sender.answer_callback_query(outcome.ack.callback_id, outcome.ack.text)
        for reply in outcome.replies:
            pieces = split_text(reply.text)
            for index, piece in enumerate(pieces):
                last = index == len(pieces) - 1
                await self._sender.send_message(
                    reply.chat_id, piece, keyboard=reply.keyboard if last else None
                )

    async def _apologise(self, chat_id: int) -> None:
        try:
            await self._sender.send_message(chat_id, FAILURE_TEXT)
        except Exception:
            log.exception("could not send the failure notice", extra={"chat_id": chat_id})


def _update_id(raw: object) -> int | None:
    if isinstance(raw, dict):
        value: object = raw.get("update_id")  # pyright: ignore[reportUnknownMemberType]
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    return None
