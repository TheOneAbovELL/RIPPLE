"""RecordingTransport: the Transport every offline notify test uses (ADR-0025).

Records every (chat_id, text) so a test can assert what the user would have read, and
can be told to fail so delivery-failure paths are covered without a network.
"""

from dataclasses import dataclass
from datetime import datetime

from ripple.core.clock import Clock
from ripple.notify.contracts import MessageReceipt
from ripple.notify.errors import TelegramSendError
from tests.fakes.clock import FakeClock


@dataclass(frozen=True)
class SentMessage:
    chat_id: str
    text: str
    sent_at: datetime


class RecordingTransport:
    def __init__(self, clock: Clock | None = None, *, fail_with: Exception | None = None) -> None:
        self._clock = clock if clock is not None else FakeClock()
        self.sent: list[SentMessage] = []
        self.fail_with = fail_with
        self._counter = 0

    async def send(self, chat_id: str, text: str) -> MessageReceipt:
        if self.fail_with is not None:
            raise self.fail_with
        self._counter += 1
        now = self._clock.now()
        self.sent.append(SentMessage(chat_id=chat_id, text=text, sent_at=now))
        return MessageReceipt(chat_id=chat_id, message_id=str(self._counter), sent_at=now)

    def texts_for(self, chat_id: str) -> list[str]:
        return [message.text for message in self.sent if message.chat_id == chat_id]


def failing_transport(description: str = "Bad Request: chat not found") -> RecordingTransport:
    return RecordingTransport(fail_with=TelegramSendError(400, description, error_code=400))
