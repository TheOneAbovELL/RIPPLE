"""The subset of Telegram's Update type Ripple reads, parsed strictly (ADR-0075).

Telegram sends many update kinds and dozens of fields; Ripple needs a private-chat
text message and a callback query from one of its own inline keyboards. Everything is
modelled with `extra="ignore"` so new Bot API fields never break parsing, and every
update that is not one of the two shapes is dropped with a counted reason instead of
an exception: the webhook must answer 200 whatever Telegram sends.
"""

from collections import Counter
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

PRIVATE_CHAT = "private"


class TelegramUser(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    is_bot: bool = False
    first_name: str = ""


class TelegramChat(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    type: str


class TelegramMessage(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    message_id: int
    chat: TelegramChat
    sender: TelegramUser | None = Field(default=None, alias="from")
    text: str | None = None
    # Either field marks a forwarded message, depending on the Bot API version.
    forward_origin: object | None = None
    forward_date: int | None = None

    @property
    def forwarded(self) -> bool:
        return self.forward_origin is not None or self.forward_date is not None


class TelegramCallbackQuery(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str
    sender: TelegramUser = Field(alias="from")
    message: TelegramMessage | None = None
    data: str | None = None


class TelegramUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    update_id: int
    message: TelegramMessage | None = None
    callback_query: TelegramCallbackQuery | None = None


@dataclass(frozen=True)
class IncomingText:
    """A text message from a private chat."""

    update_id: int
    chat_id: int
    sender_id: int
    message_id: int
    text: str
    forwarded: bool = False

    @property
    def source_ref(self) -> str:
        return f"telegram:{self.chat_id}:{self.message_id}"


@dataclass(frozen=True)
class IncomingCallback:
    """A tap on one of Ripple's inline keyboard buttons."""

    update_id: int
    chat_id: int
    sender_id: int
    callback_id: str
    data: str
    message_id: int | None = None


IncomingUpdate = IncomingText | IncomingCallback

DropReason = Literal[
    "not_an_object",
    "invalid",
    "unsupported_kind",
    "no_text",
    "not_private_chat",
    "from_bot",
    "no_sender",
    "no_callback_data",
    "no_callback_chat",
]


@dataclass
class DroppedUpdates:
    """How many updates were ignored and why; read by logs and the handover report."""

    by_reason: Counter[str] = field(default_factory=Counter)

    def drop(self, reason: DropReason) -> None:
        self.by_reason[reason] += 1

    @property
    def total(self) -> int:
        return sum(self.by_reason.values())


def parse_update(raw: object, dropped: DroppedUpdates) -> IncomingUpdate | None:
    """The update as Ripple sees it, or None (counted) when it is not one Ripple handles."""
    if not isinstance(raw, dict):
        dropped.drop("not_an_object")
        return None
    try:
        update = TelegramUpdate.model_validate(raw)
    except ValidationError:
        dropped.drop("invalid")
        return None
    if update.message is not None:
        return _text(update.update_id, update.message, dropped)
    if update.callback_query is not None:
        return _callback(update.update_id, update.callback_query, dropped)
    dropped.drop("unsupported_kind")
    return None


def _text(update_id: int, message: TelegramMessage, dropped: DroppedUpdates) -> IncomingText | None:
    # Group chats are refused outright: the bot acts only in the student's own chat
    # (I6), and a group would let one member read another's memory.
    if message.chat.type != PRIVATE_CHAT:
        dropped.drop("not_private_chat")
        return None
    if message.sender is None:
        dropped.drop("no_sender")
        return None
    if message.sender.is_bot:
        dropped.drop("from_bot")
        return None
    if message.text is None or not message.text.strip():
        dropped.drop("no_text")  # photos, stickers, documents, voice
        return None
    return IncomingText(
        update_id=update_id,
        chat_id=message.chat.id,
        sender_id=message.sender.id,
        message_id=message.message_id,
        text=message.text,
        forwarded=message.forwarded,
    )


def _callback(
    update_id: int, query: TelegramCallbackQuery, dropped: DroppedUpdates
) -> IncomingCallback | None:
    if not query.data:
        dropped.drop("no_callback_data")
        return None
    if query.message is None:
        dropped.drop("no_callback_chat")  # inline-mode queries carry no chat; unsupported
        return None
    if query.message.chat.type != PRIVATE_CHAT:
        dropped.drop("not_private_chat")
        return None
    return IncomingCallback(
        update_id=update_id,
        chat_id=query.message.chat.id,
        sender_id=query.sender.id,
        callback_id=query.id,
        data=query.data,
        message_id=query.message.message_id,
    )
