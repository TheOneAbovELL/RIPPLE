"""Protocols the notify package depends on and the records it produces.

The digest never talks to a database, a ranking engine or Telegram directly: it reads
ranked openings through `RecommendationSource` (contract C1), finds users through
`UserDirectory` (wired to the identity module at integration), sends through
`Transport` (ADR-0025) and remembers what it sent through `DeliveryLog`. Every one of
them has an offline implementation, so FR-9 is tested without a network.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import StrEnum
from typing import Protocol


@dataclass(frozen=True)
class MessageReceipt:
    """What a transport returns once the user's chat accepted a message."""

    chat_id: str
    message_id: str | None
    sent_at: datetime


class Transport(Protocol):
    """One outbound channel to the user's own chat (I6: never anything else)."""

    async def send(self, chat_id: str, text: str) -> MessageReceipt: ...


class UserDirectory(Protocol):
    """Who gets a digest and where. The identity module (WS-3) implements it."""

    async def active_user_ids(self) -> Sequence[str]:
        """Users whose scheduled jobs should run, in a stable order."""
        ...

    async def telegram_chat_id(self, user_id: str) -> str | None:
        """The linked Telegram chat, or None when the user has not linked one yet."""
        ...


class AlertKind(StrEnum):
    HIGH_FIT = "high_fit"
    DEADLINE_SOON = "deadline_soon"


class DeliveryLog(Protocol):
    """What was already sent, so a retried job never sends twice (ADR-0056)."""

    async def last_digest_day(self, user_id: str) -> date | None: ...

    async def record_digest(self, user_id: str, day: date) -> None: ...

    async def last_alert_at(
        self, user_id: str, opening_memory_id: str, kind: AlertKind
    ) -> datetime | None: ...

    async def record_alert(
        self, user_id: str, opening_memory_id: str, kind: AlertKind, at: datetime
    ) -> None: ...

    async def delete_for_user(self, user_id: str) -> None:
        """FR-15: account deletion erases what was sent to the user, too."""
        ...


@dataclass(frozen=True)
class Thresholds:
    """FR-9 numbers, fixed in ADR-0055. Every one is a policy choice, not a measurement."""

    fit_alert: float = 0.8  # fit_score at or above this triggers a HIGH_FIT alert
    deadline_window: timedelta = timedelta(hours=48)  # FR-9: "deadlines within 48 hours"
    alert_cooldown: timedelta = timedelta(days=7)  # an opening is alerted once per kind within it
    digest_limit: int = 10  # items asked from the RecommendationSource per digest
    alert_scan_limit: int = 50  # ranked items scanned for alerts; deeper than the digest
