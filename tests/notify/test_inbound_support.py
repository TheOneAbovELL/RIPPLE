"""Shared offline wiring for the inbound-channel tests (no tests in this module).

Builds the dispatcher over the API test harness (InMemoryStore, FakeClock, in-memory
UserStore, scripted parsers and recorder) with a scripted conversation agent, and
offers builders for updates and a recording sender. Lives beside the tests because
WS-10 owns only `tests/notify/test_inbound*.py`.
"""

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from ripple.agents.conversation import Citation, ConversationReply, PendingQuestion
from ripple.core.models import DecisionAction, Memory, Status
from ripple.notify.contracts import MessageReceipt
from ripple.notify.inbound.channel import TelegramChannel
from ripple.notify.inbound.dispatcher import (
    Conversation,
    InboundDispatcher,
    ScanningChatDirectory,
)
from ripple.notify.inbound.keyboards import InlineKeyboard
from ripple.notify.inbound.ledger import InMemoryUpdateLedger
from ripple.notify.inbound.ratelimit import InMemoryRateLimiter
from ripple.notify.inbound.updates import IncomingCallback, IncomingText
from ripple.storage.users import TelegramLinkCode, User, new_link_code
from tests.api.harness import Harness
from tests.builders import change_event, decision, memory

CHAT = 4242
OTHER_CHAT = 9999
DASHBOARD = "https://ripple.test/dashboard"
JD_TEXT = (
    "Software Engineer Intern at Acme Robotics. Job description: build data pipelines "
    "and internal tools in Python. Requirements: B.Tech in CS/IT 2027 batch, CGPA 7.5 "
    "or above, SQL and Python. Stipend: 40,000 per month. Location: Bengaluru. "
    "Apply by 2026-11-30 through the campus placement portal."
)


class ScriptedConversation:
    """Returns scripted replies in order and records every turn."""

    def __init__(self, *replies: ConversationReply) -> None:
        self._replies = list(replies)
        self.calls: list[tuple[str, str, str | None]] = []
        self.fail_with: Exception | None = None

    async def turn(
        self,
        user_id: str,
        message: str,
        *,
        message_id: str | None = None,
        trace_id: str | None = None,
    ) -> ConversationReply:
        self.calls.append((user_id, message, message_id))
        if self.fail_with is not None:
            raise self.fail_with
        if not self._replies:
            return ConversationReply(intent="ask", text=f"echo: {message}")
        return self._replies.pop(0)


def reply(
    text: str,
    *,
    intent: str = "ask",
    citations: tuple[Citation, ...] = (),
    questions: tuple[PendingQuestion, ...] = (),
    dropped: int = 0,
) -> ConversationReply:
    return ConversationReply(
        intent=intent,  # type: ignore[arg-type]
        text=text,
        citations=citations,
        questions=questions,
        dropped_claims=dropped,
    )


@dataclass
class RecordingSender:
    """What the channel delivers through; records both outbound calls in order."""

    sent: list[tuple[int | str, str, InlineKeyboard | None]] = field(default_factory=list)
    acks: list[tuple[str, str | None]] = field(default_factory=list)
    calls: list[str] = field(default_factory=list)
    fail_with: Exception | None = None

    async def send_message(
        self, chat_id: int | str, text: str, *, keyboard: InlineKeyboard | None = None
    ) -> MessageReceipt:
        if self.fail_with is not None:
            raise self.fail_with
        self.calls.append("sendMessage")
        self.sent.append((chat_id, text, keyboard))
        from tests.fakes.clock import DEFAULT_START

        return MessageReceipt(
            chat_id=str(chat_id), message_id=str(len(self.sent)), sent_at=DEFAULT_START
        )

    async def answer_callback_query(self, callback_id: str, text: str | None = None) -> None:
        self.calls.append("answerCallbackQuery")
        self.acks.append((callback_id, text))


@dataclass
class Bot:
    harness: Harness
    dispatcher: InboundDispatcher
    conversation: ScriptedConversation
    rate_limiter: InMemoryRateLimiter
    sender: RecordingSender
    ledger: InMemoryUpdateLedger
    channel: TelegramChannel

    async def user(self, display_name: str = "Asha", *, chat_id: int | None = CHAT) -> User:
        """A user; linked to `chat_id` directly unless it is None."""
        user, _ = await self.harness.user(display_name)
        if chat_id is None:
            return user
        linked = user.model_copy(update={"telegram_chat_id": chat_id})
        await self.harness.user_store.replace_user(linked)
        return linked

    async def link_code(self, user: User, *, ttl: timedelta = timedelta(minutes=15)) -> str:
        now = self.harness.clock.now()
        code = TelegramLinkCode(
            code=new_link_code(), user_id=user.id, created_at=now, expires_at=now + ttl
        )
        await self.harness.user_store.add_link_code(code)
        return code.code

    async def pending(self, user: User, content: str = "eligible for Acme (cutoff 7.5)") -> Memory:
        """A PENDING_USER memory with the ChangeEvent that asked about it."""
        parked = memory(content=content, user_id=user.id, status=Status.PENDING_USER)
        asked = change_event(
            parked,
            user_id=user.id,
            decisions=[
                decision(
                    parked, DecisionAction.ASK, reason="the cutoff may have changed"
                ).model_copy(update={"question": f"Does this still hold? {content}"})
            ],
            affected_ids=[parked.id],
        )
        async with self.harness.store.transaction() as tx:
            await tx.add_memory(parked)
            await tx.add_change_event(asked)
        return parked

    async def seed(self, *rows: Memory) -> None:
        await self.harness.seed(*rows)

    async def memory(self, memory_id: str) -> Memory:
        return await self.harness.store.get_memory(memory_id)

    async def text(self, text: str, *, chat_id: int = CHAT, forwarded: bool = False):
        return await self.dispatcher.handle(
            incoming_text(text, chat_id=chat_id, forwarded=forwarded)
        )

    async def tap(self, data: str, *, chat_id: int = CHAT):
        return await self.dispatcher.handle(incoming_callback(data, chat_id=chat_id))


_counter = {"update": 100, "message": 500, "callback": 0}


def incoming_text(text: str, *, chat_id: int = CHAT, forwarded: bool = False) -> IncomingText:
    _counter["update"] += 1
    _counter["message"] += 1
    return IncomingText(
        update_id=_counter["update"],
        chat_id=chat_id,
        sender_id=chat_id,
        message_id=_counter["message"],
        text=text,
        forwarded=forwarded,
    )


def incoming_callback(data: str, *, chat_id: int = CHAT) -> IncomingCallback:
    _counter["update"] += 1
    _counter["callback"] += 1
    return IncomingCallback(
        update_id=_counter["update"],
        chat_id=chat_id,
        sender_id=chat_id,
        callback_id=f"cb-{_counter['callback']}",
        data=data,
        message_id=_counter["message"],
    )


def raw_text_update(
    text: str,
    *,
    update_id: int,
    chat_id: int = CHAT,
    chat_type: str = "private",
    message_id: int = 1,
    forwarded: bool = False,
) -> dict[str, Any]:
    message: dict[str, Any] = {
        "message_id": message_id,
        "date": 1761300000,
        "chat": {"id": chat_id, "type": chat_type, "first_name": "Asha"},
        "from": {"id": chat_id, "is_bot": False, "first_name": "Asha"},
        "text": text,
        "entities": [],  # ignored
    }
    if forwarded:
        message["forward_origin"] = {"type": "hidden_user", "sender_user_name": "TPO"}
    return {"update_id": update_id, "message": message}


def raw_callback_update(
    data: str, *, update_id: int, chat_id: int = CHAT, callback_id: str = "cb-1"
) -> dict[str, Any]:
    return {
        "update_id": update_id,
        "callback_query": {
            "id": callback_id,
            "from": {"id": chat_id, "is_bot": False, "first_name": "Asha"},
            "chat_instance": "-1",
            "message": {
                "message_id": 77,
                "date": 1761300000,
                "chat": {"id": chat_id, "type": "private"},
                "text": "Does this still hold?",
            },
            "data": data,
        },
    }


def build(
    *,
    conversation: Conversation | None = None,
    harness: Harness | None = None,
    confirmation_ttl: timedelta = timedelta(minutes=5),
) -> Bot:
    harness = harness or Harness.build()
    scripted = ScriptedConversation()
    rate_limiter = InMemoryRateLimiter(harness.clock)
    dispatcher = InboundDispatcher(
        services=harness.services,
        conversation=conversation or scripted,
        chats=ScanningChatDirectory(harness.user_store),
        rate_limiter=rate_limiter,
        dashboard_url=DASHBOARD,
        confirmation_ttl=confirmation_ttl,
    )
    sender = RecordingSender()
    ledger = InMemoryUpdateLedger()
    channel = TelegramChannel(dispatcher=dispatcher, sender=sender, ledger=ledger)
    return Bot(harness, dispatcher, scripted, rate_limiter, sender, ledger, channel)
