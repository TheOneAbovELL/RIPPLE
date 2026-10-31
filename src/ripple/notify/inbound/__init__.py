"""Telegram inbound channel (ADR-0075, ADR-0076, ADR-0077): the student talks back.

Updates arrive either through the webhook route (`ripple.api.routers.telegram`,
production) or the development long-poll loop (`ripple.worker.telegram_poll`). Both
hand the raw update to `TelegramChannel.receive`, which deduplicates it, parses the
subset of the Update type Ripple uses, lets the `InboundDispatcher` decide what to
answer, and delivers the replies through `TelegramBotApi`. The dispatcher never sends:
it returns replies addressed to the chat that wrote (I6).
"""

from ripple.notify.inbound.channel import ReceiveResult, TelegramChannel
from ripple.notify.inbound.dispatcher import InboundDispatcher, Outcome, Reply
from ripple.notify.inbound.ledger import InMemoryUpdateLedger, UpdateLedger
from ripple.notify.inbound.ratelimit import InMemoryRateLimiter, RateLimiter
from ripple.notify.inbound.telegram import TelegramBotApi
from ripple.notify.inbound.updates import (
    DroppedUpdates,
    IncomingCallback,
    IncomingText,
    IncomingUpdate,
    parse_update,
)

__all__ = [
    "DroppedUpdates",
    "InMemoryRateLimiter",
    "InMemoryUpdateLedger",
    "InboundDispatcher",
    "IncomingCallback",
    "IncomingText",
    "IncomingUpdate",
    "Outcome",
    "RateLimiter",
    "ReceiveResult",
    "Reply",
    "TelegramBotApi",
    "TelegramChannel",
    "UpdateLedger",
    "parse_update",
]
