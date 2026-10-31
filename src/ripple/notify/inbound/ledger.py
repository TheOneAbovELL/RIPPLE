"""Idempotency on Telegram's update_id (ADR-0077).

Telegram retries a webhook delivery it did not see answered with 200 in time, and a
long-poll restart can re-fetch the last batch. An update is processed at most once:
the ledger records the id before any work, so a retry after a timeout sees it as
already handled. The price is a lost update when processing fails after the record;
the student sees no reply and sends again, which is the safer failure for a channel
that can write memory, link accounts and delete.

The in-memory ledger is per process. A Postgres table (`telegram_updates(update_id
bigint primary key, received_at timestamptz)`) is the production implementation;
migration id 0008 is reserved for it and the coordinator adds it in storage.
"""

from collections import OrderedDict
from typing import Protocol

DEFAULT_CAPACITY = 10_000  # update_ids increase; the window only needs to cover retries


class UpdateLedger(Protocol):
    async def first_sight(self, update_id: int) -> bool:
        """True and recorded when the id was not seen before; False when it was."""
        ...


class InMemoryUpdateLedger:
    def __init__(self, capacity: int = DEFAULT_CAPACITY) -> None:
        if capacity < 1:
            raise ValueError("capacity must be at least 1")
        self._capacity = capacity
        self._seen: OrderedDict[int, None] = OrderedDict()

    async def first_sight(self, update_id: int) -> bool:
        if update_id in self._seen:
            self._seen.move_to_end(update_id)
            return False
        self._seen[update_id] = None
        while len(self._seen) > self._capacity:
            self._seen.popitem(last=False)
        return True

    def __len__(self) -> int:
        return len(self._seen)
