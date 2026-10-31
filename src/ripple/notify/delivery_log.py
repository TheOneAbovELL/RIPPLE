"""DeliveryLog implementations (ADR-0056, ADR-0095).

`InMemoryDeliveryLog` is per process: tests and single-worker development. A worker
restart with it forgets what it sent and may resend one digest. `PostgresDeliveryLog`
writes one row per delivery into `delivery_log` (migration 0005) keyed by
(user_id, kind, key), so the DigestService's "once per day" and "once per cooldown"
survive restarts and hold across two workers sharing the database. Both satisfy the
same contract test (tests/notify/test_hardening_delivery_log.py).
"""

from datetime import UTC, date, datetime, time

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncEngine

from ripple.notify.contracts import AlertKind
from ripple.storage.delivery_tables import DIGEST_KIND, delivery_log


class InMemoryDeliveryLog:
    def __init__(self) -> None:
        self._digest_days: dict[str, date] = {}
        self._alerts: dict[tuple[str, str, AlertKind], datetime] = {}

    async def last_digest_day(self, user_id: str) -> date | None:
        return self._digest_days.get(user_id)

    async def record_digest(self, user_id: str, day: date) -> None:
        # The latest day wins, as in Postgres, where the newest row is read back.
        current = self._digest_days.get(user_id)
        if current is None or day > current:
            self._digest_days[user_id] = day

    async def last_alert_at(
        self, user_id: str, opening_memory_id: str, kind: AlertKind
    ) -> datetime | None:
        return self._alerts.get((user_id, opening_memory_id, kind))

    async def record_alert(
        self, user_id: str, opening_memory_id: str, kind: AlertKind, at: datetime
    ) -> None:
        self._alerts[(user_id, opening_memory_id, kind)] = at

    async def delete_for_user(self, user_id: str) -> None:
        self._digest_days.pop(user_id, None)
        for key in [k for k in self._alerts if k[0] == user_id]:
            del self._alerts[key]


def _day_start(day: date) -> datetime:
    # The contract knows the day, not the moment; midnight UTC is the stored instant.
    return datetime.combine(day, time(), tzinfo=UTC)


class PostgresDeliveryLog:
    """One short transaction per call, like the other Postgres stores (ADR-0016)."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def last_digest_day(self, user_id: str) -> date | None:
        stmt = sa.select(sa.func.max(delivery_log.c.sent_at)).where(
            delivery_log.c.user_id == user_id, delivery_log.c.kind == DIGEST_KIND
        )
        async with self._engine.connect() as conn:
            sent_at = (await conn.execute(stmt)).scalar_one_or_none()
        return None if sent_at is None else sent_at.astimezone(UTC).date()

    async def record_digest(self, user_id: str, day: date) -> None:
        # One row per day; a retried job hits the primary key and changes nothing.
        stmt = (
            pg_insert(delivery_log)
            .values(user_id=user_id, kind=DIGEST_KIND, key=day.isoformat(), sent_at=_day_start(day))
            .on_conflict_do_nothing(index_elements=["user_id", "kind", "key"])
        )
        async with self._engine.begin() as conn:
            await conn.execute(stmt)

    async def last_alert_at(
        self, user_id: str, opening_memory_id: str, kind: AlertKind
    ) -> datetime | None:
        stmt = sa.select(delivery_log.c.sent_at).where(
            delivery_log.c.user_id == user_id,
            delivery_log.c.kind == kind.value,
            delivery_log.c.key == opening_memory_id,
        )
        async with self._engine.connect() as conn:
            sent_at = (await conn.execute(stmt)).scalar_one_or_none()
        return None if sent_at is None else sent_at.astimezone(UTC)

    async def record_alert(
        self, user_id: str, opening_memory_id: str, kind: AlertKind, at: datetime
    ) -> None:
        # A re-alert after the cooldown moves sent_at forward; the row is the pair's state.
        stmt = pg_insert(delivery_log).values(
            user_id=user_id, kind=kind.value, key=opening_memory_id, sent_at=at
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["user_id", "kind", "key"], set_={"sent_at": stmt.excluded.sent_at}
        )
        async with self._engine.begin() as conn:
            await conn.execute(stmt)

    async def delete_for_user(self, user_id: str) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(sa.delete(delivery_log).where(delivery_log.c.user_id == user_id))
