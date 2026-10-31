"""Reading the delivery log for a reporting window (ADR-0106).

The `DeliveryLog` protocol (ADR-0056) answers the worker's questions about one user
("last digest day", "last alert for this opening"); the report needs every row in a
week. That read lives here, over the same `delivery_log` table, rather than widening a
protocol the worker depends on.

What a row can tell: a digest went to a user on a UTC day (`kind="digest"`, sent_at at
midnight UTC), or an alert of a kind went out for an opening. Alert rows are upserted
(ADR-0095), so a re-alert moves `sent_at` forward and the earlier send is no longer in
the table; a weekly report run after each week ends sees each send once.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from ripple.storage.delivery_tables import DIGEST_KIND, delivery_log


@dataclass(frozen=True)
class DeliveryRecord:
    user_id: str
    kind: str  # "digest" or an AlertKind value
    key: str  # ISO day for a digest, the opening memory id for an alert
    sent_at: datetime

    @property
    def is_digest(self) -> bool:
        return self.kind == DIGEST_KIND


class DeliveryReader(Protocol):
    async def deliveries_between(self, start: datetime, end: datetime) -> Sequence[DeliveryRecord]:
        """Rows with start <= sent_at < end, oldest first."""
        ...


class PostgresDeliveryReader:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def deliveries_between(self, start: datetime, end: datetime) -> list[DeliveryRecord]:
        stmt = (
            sa.select(delivery_log)
            .where(delivery_log.c.sent_at >= start, delivery_log.c.sent_at < end)
            .order_by(delivery_log.c.sent_at, delivery_log.c.user_id, delivery_log.c.key)
        )
        async with self._engine.connect() as conn:
            rows = (await conn.execute(stmt)).all()
        return [
            DeliveryRecord(
                user_id=row.user_id,
                kind=row.kind,
                key=row.key,
                sent_at=row.sent_at.astimezone(UTC),
            )
            for row in rows
        ]
