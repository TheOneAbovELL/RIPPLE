"""PostgresStore: the Store over SQLAlchemy Core on the async engine (ADR-0016).

A `transaction()` opens one database transaction; the PostgresTransaction bound to it
serves both reads and writes so the runner sees its own uncommitted rows. Reads outside
a transaction use a fresh connection each. The contract is tests/core/store_contract.py,
shared with the in-memory store.
"""

from collections.abc import AsyncIterator, Awaitable, Callable, Iterable
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from ripple.core.models import (
    ChangeEvent,
    Decision,
    DecisionAction,
    ForgetEvent,
    Link,
    Memory,
    Status,
)
from ripple.core.store import ChangeEventNotFoundError, MemoryNotFoundError, Transaction
from ripple.storage import tables as t

# ---- row <-> model ----------------------------------------------------------------

type ReadOp[R] = Callable[["_Reads"], Awaitable[R]]


def _memory_row(memory: Memory) -> dict[str, Any]:
    row = memory.model_dump(mode="json")
    # Keep real datetimes for timestamptz columns; model_dump(mode="json") made them strings.
    for field in ("valid_from", "valid_to", "recorded_at"):
        row[field] = getattr(memory, field)
    return row


def _memory(row: sa.Row[Any]) -> Memory:
    return Memory.model_validate(dict(row._mapping))


def _link_row(link: Link) -> dict[str, Any]:
    row = link.model_dump(mode="json")
    row["created_at"] = link.created_at
    row["verified_at"] = link.verified_at
    return row


def _link(row: sa.Row[Any]) -> Link:
    return Link.model_validate(dict(row._mapping))


def _event_row(event: ChangeEvent) -> dict[str, Any]:
    row = event.model_dump(mode="json")
    row["created_at"] = event.created_at
    row["completed_at"] = event.completed_at
    return row


def _event(row: sa.Row[Any]) -> ChangeEvent:
    data = dict(row._mapping)
    data["decisions"] = [Decision.model_validate(d) for d in data["decisions"]]
    return ChangeEvent.model_validate(data)


def _forget_row(event: ForgetEvent) -> dict[str, Any]:
    row = event.model_dump(mode="json")
    row["created_at"] = event.created_at
    return row


# ---- reads shared by store and transaction ------------------------------------------


class _Reads:
    def __init__(self, conn: AsyncConnection) -> None:
        self._conn = conn

    async def get_memory(self, memory_id: str) -> Memory:
        row = (
            await self._conn.execute(sa.select(t.memories).where(t.memories.c.id == memory_id))
        ).first()
        if row is None:
            raise MemoryNotFoundError(memory_id)
        return _memory(row)

    async def get_memories(self, memory_ids: Iterable[str]) -> list[Memory]:
        return [await self.get_memory(memory_id) for memory_id in memory_ids]

    async def memories_for_user(
        self, user_id: str, statuses: Iterable[Status] | None = None
    ) -> list[Memory]:
        query = sa.select(t.memories).where(t.memories.c.user_id == user_id)
        if statuses is not None:
            query = query.where(t.memories.c.status.in_([s.value for s in statuses]))
        query = query.order_by(t.memories.c.recorded_at, t.memories.c.id)
        return [_memory(row) for row in await self._conn.execute(query)]

    async def version_chain(self, memory_id: str) -> list[Memory]:
        current = await self.get_memory(memory_id)
        chain = [current]
        while current.supersedes_id is not None:
            current = await self.get_memory(current.supersedes_id)
            chain.append(current)
        chain.reverse()
        tail = chain[-1]
        while True:
            row = (
                await self._conn.execute(
                    sa.select(t.memories).where(t.memories.c.supersedes_id == tail.id)
                )
            ).first()
            if row is None:
                return chain
            tail = _memory(row)
            chain.append(tail)

    async def latest_version(self, memory_id: str) -> Memory:
        return (await self.version_chain(memory_id))[-1]

    async def dependents_of(self, memory_id: str) -> list[Link]:
        query = (
            sa.select(t.links)
            .where(t.links.c.parent_id == memory_id)
            .order_by(t.links.c.created_at, t.links.c.id)
        )
        return [_link(row) for row in await self._conn.execute(query)]

    async def parents_of(self, memory_id: str) -> list[Link]:
        query = (
            sa.select(t.links)
            .where(t.links.c.dependent_id == memory_id)
            .order_by(t.links.c.created_at, t.links.c.id)
        )
        return [_link(row) for row in await self._conn.execute(query)]

    async def links_for_user(self, user_id: str) -> list[Link]:
        query = (
            sa.select(t.links)
            .join(t.memories, t.memories.c.id == t.links.c.parent_id)
            .where(t.memories.c.user_id == user_id)
            .order_by(t.links.c.created_at, t.links.c.id)
        )
        return [_link(row) for row in await self._conn.execute(query)]

    async def get_change_event(self, event_id: str) -> ChangeEvent:
        row = (
            await self._conn.execute(
                sa.select(t.change_events).where(t.change_events.c.id == event_id)
            )
        ).first()
        if row is None:
            raise ChangeEventNotFoundError(event_id)
        return _event(row)

    async def open_change_events(self, user_id: str) -> list[ChangeEvent]:
        query = (
            sa.select(t.change_events)
            .where(t.change_events.c.user_id == user_id)
            .where(t.change_events.c.completed_at.is_(None))
            .order_by(t.change_events.c.created_at, t.change_events.c.id)
        )
        return [_event(row) for row in await self._conn.execute(query)]

    async def events_asking(self, memory_id: str) -> list[ChangeEvent]:
        query = (
            sa.select(t.change_events)
            .where(
                t.change_events.c.decisions.contains(
                    [{"memory_id": memory_id, "action": DecisionAction.ASK.value}]
                )
            )
            .order_by(t.change_events.c.created_at, t.change_events.c.id)
        )
        return [_event(row) for row in await self._conn.execute(query)]

    async def change_events_for_user(self, user_id: str) -> list[ChangeEvent]:
        query = (
            sa.select(t.change_events)
            .where(t.change_events.c.user_id == user_id)
            .order_by(t.change_events.c.created_at, t.change_events.c.id)
        )
        return [_event(row) for row in await self._conn.execute(query)]

    async def forget_events_for_user(self, user_id: str) -> list[ForgetEvent]:
        query = (
            sa.select(t.forget_events)
            .where(t.forget_events.c.user_id == user_id)
            .order_by(t.forget_events.c.created_at, t.forget_events.c.id)
        )
        return [
            ForgetEvent.model_validate(dict(row._mapping))
            for row in await self._conn.execute(query)
        ]

    async def memories_expiring_at(self, user_id: str, now: datetime) -> list[Memory]:
        query = (
            sa.select(t.memories)
            .where(t.memories.c.user_id == user_id)
            .where(t.memories.c.status == Status.VALID.value)
            .where(t.memories.c.valid_to.is_not(None))
            .where(t.memories.c.valid_to <= now)
            .order_by(t.memories.c.recorded_at, t.memories.c.id)
        )
        return [_memory(row) for row in await self._conn.execute(query)]


class PostgresTransaction(_Reads):
    async def add_memory(self, memory: Memory) -> None:
        await self._conn.execute(sa.insert(t.memories).values(**_memory_row(memory)))

    async def replace_memory(self, memory: Memory) -> None:
        result = await self._conn.execute(
            sa.update(t.memories).where(t.memories.c.id == memory.id).values(**_memory_row(memory))
        )
        if result.rowcount == 0:
            raise MemoryNotFoundError(memory.id)

    async def delete_memories(self, memory_ids: Iterable[str]) -> None:
        ids = list(memory_ids)
        if ids:
            await self._conn.execute(sa.delete(t.memories).where(t.memories.c.id.in_(ids)))

    async def add_link(self, link: Link) -> None:
        for endpoint in (link.parent_id, link.dependent_id):
            await self.get_memory(endpoint)  # MemoryNotFoundError before the FK would fire
        await self._conn.execute(sa.insert(t.links).values(**_link_row(link)))

    async def delete_links(self, link_ids: Iterable[str]) -> None:
        ids = list(link_ids)
        if ids:
            await self._conn.execute(sa.delete(t.links).where(t.links.c.id.in_(ids)))

    async def add_change_event(self, event: ChangeEvent) -> None:
        await self._conn.execute(sa.insert(t.change_events).values(**_event_row(event)))

    async def replace_change_event(self, event: ChangeEvent) -> None:
        result = await self._conn.execute(
            sa.update(t.change_events)
            .where(t.change_events.c.id == event.id)
            .values(**_event_row(event))
        )
        if result.rowcount == 0:
            raise ChangeEventNotFoundError(event.id)

    async def add_forget_event(self, event: ForgetEvent) -> None:
        await self._conn.execute(sa.insert(t.forget_events).values(**_forget_row(event)))

    async def delete_change_events_for_user(self, user_id: str) -> int:
        result = await self._conn.execute(
            sa.delete(t.change_events).where(t.change_events.c.user_id == user_id)
        )
        return int(result.rowcount or 0)

    async def delete_forget_events_for_user(self, user_id: str) -> int:
        result = await self._conn.execute(
            sa.delete(t.forget_events).where(t.forget_events.c.user_id == user_id)
        )
        return int(result.rowcount or 0)


class PostgresStore:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[Transaction]:
        async with self._engine.begin() as conn:
            yield PostgresTransaction(conn)

    async def _read[R](self, op: ReadOp[R]) -> R:
        async with self._engine.connect() as conn:
            return await op(_Reads(conn))

    # Each read opens a short-lived connection; the runner's hot path is inside
    # transactions anyway, so this keeps the store simple rather than pooling sessions.

    async def get_memory(self, memory_id: str) -> Memory:
        return await self._read(lambda r: r.get_memory(memory_id))

    async def get_memories(self, memory_ids: Iterable[str]) -> list[Memory]:
        ids = list(memory_ids)
        return await self._read(lambda r: r.get_memories(ids))

    async def memories_for_user(
        self, user_id: str, statuses: Iterable[Status] | None = None
    ) -> list[Memory]:
        wanted = list(statuses) if statuses is not None else None
        return await self._read(lambda r: r.memories_for_user(user_id, wanted))

    async def version_chain(self, memory_id: str) -> list[Memory]:
        return await self._read(lambda r: r.version_chain(memory_id))

    async def latest_version(self, memory_id: str) -> Memory:
        return await self._read(lambda r: r.latest_version(memory_id))

    async def dependents_of(self, memory_id: str) -> list[Link]:
        return await self._read(lambda r: r.dependents_of(memory_id))

    async def parents_of(self, memory_id: str) -> list[Link]:
        return await self._read(lambda r: r.parents_of(memory_id))

    async def links_for_user(self, user_id: str) -> list[Link]:
        return await self._read(lambda r: r.links_for_user(user_id))

    async def get_change_event(self, event_id: str) -> ChangeEvent:
        return await self._read(lambda r: r.get_change_event(event_id))

    async def open_change_events(self, user_id: str) -> list[ChangeEvent]:
        return await self._read(lambda r: r.open_change_events(user_id))

    async def events_asking(self, memory_id: str) -> list[ChangeEvent]:
        return await self._read(lambda r: r.events_asking(memory_id))

    async def change_events_for_user(self, user_id: str) -> list[ChangeEvent]:
        return await self._read(lambda r: r.change_events_for_user(user_id))

    async def forget_events_for_user(self, user_id: str) -> list[ForgetEvent]:
        return await self._read(lambda r: r.forget_events_for_user(user_id))

    async def memories_expiring_at(self, user_id: str, now: datetime) -> list[Memory]:
        return await self._read(lambda r: r.memories_expiring_at(user_id, now))
