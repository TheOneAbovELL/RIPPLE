"""InMemoryStore: the Store every offline test uses.

A transaction snapshots the dicts on entry and restores them if the block raises, which
gives the same all-or-nothing behaviour the Postgres store gets from a real transaction.
Single writer at a time, which is all the test suite needs.
"""

from collections.abc import AsyncIterator, Iterable
from contextlib import asynccontextmanager
from datetime import datetime

from ripple.core.models import ChangeEvent, DecisionAction, ForgetEvent, Link, Memory, Status
from ripple.core.store import ChangeEventNotFoundError, MemoryNotFoundError, Transaction


class InMemoryStore:
    def __init__(self) -> None:
        self._memories: dict[str, Memory] = {}
        self._links: dict[str, Link] = {}
        self._change_events: dict[str, ChangeEvent] = {}
        self._forget_events: dict[str, ForgetEvent] = {}
        self._in_transaction = False

    # ---- reads ---------------------------------------------------------------

    async def get_memory(self, memory_id: str) -> Memory:
        try:
            return self._memories[memory_id]
        except KeyError as exc:
            raise MemoryNotFoundError(memory_id) from exc

    async def get_memories(self, memory_ids: Iterable[str]) -> list[Memory]:
        return [await self.get_memory(memory_id) for memory_id in memory_ids]

    async def memories_for_user(
        self, user_id: str, statuses: Iterable[Status] | None = None
    ) -> list[Memory]:
        wanted = set(statuses) if statuses is not None else None
        return sorted(
            (
                m
                for m in self._memories.values()
                if m.user_id == user_id and (wanted is None or m.status in wanted)
            ),
            key=lambda m: (m.recorded_at, m.id),
        )

    async def version_chain(self, memory_id: str) -> list[Memory]:
        current = await self.get_memory(memory_id)
        chain = [current]
        while current.supersedes_id is not None:
            current = await self.get_memory(current.supersedes_id)
            chain.append(current)
        chain.reverse()
        newer = {m.supersedes_id: m for m in self._memories.values() if m.supersedes_id}
        tail = chain[-1]
        while tail.id in newer:
            tail = newer[tail.id]
            chain.append(tail)
        return chain

    async def latest_version(self, memory_id: str) -> Memory:
        return (await self.version_chain(memory_id))[-1]

    async def dependents_of(self, memory_id: str) -> list[Link]:
        return sorted(
            (link for link in self._links.values() if link.parent_id == memory_id),
            key=lambda link: (link.created_at, link.id),
        )

    async def parents_of(self, memory_id: str) -> list[Link]:
        return sorted(
            (link for link in self._links.values() if link.dependent_id == memory_id),
            key=lambda link: (link.created_at, link.id),
        )

    async def links_for_user(self, user_id: str) -> list[Link]:
        owned = {m.id for m in self._memories.values() if m.user_id == user_id}
        return sorted(
            (link for link in self._links.values() if link.parent_id in owned),
            key=lambda link: (link.created_at, link.id),
        )

    async def get_change_event(self, event_id: str) -> ChangeEvent:
        try:
            return self._change_events[event_id]
        except KeyError as exc:
            raise ChangeEventNotFoundError(event_id) from exc

    async def open_change_events(self, user_id: str) -> list[ChangeEvent]:
        return sorted(
            (e for e in self._change_events.values() if e.user_id == user_id and e.is_open),
            key=lambda e: (e.created_at, e.id),
        )

    async def events_asking(self, memory_id: str) -> list[ChangeEvent]:
        return sorted(
            (
                e
                for e in self._change_events.values()
                if any(
                    d.memory_id == memory_id and d.action is DecisionAction.ASK for d in e.decisions
                )
            ),
            key=lambda e: (e.created_at, e.id),
        )

    async def change_events_for_user(self, user_id: str) -> list[ChangeEvent]:
        return sorted(
            (e for e in self._change_events.values() if e.user_id == user_id),
            key=lambda e: (e.created_at, e.id),
        )

    async def forget_events_for_user(self, user_id: str) -> list[ForgetEvent]:
        return sorted(
            (e for e in self._forget_events.values() if e.user_id == user_id),
            key=lambda e: (e.created_at, e.id),
        )

    async def memories_expiring_at(self, user_id: str, now: datetime) -> list[Memory]:
        return [
            m for m in await self.memories_for_user(user_id, [Status.VALID]) if m.expired_at(now)
        ]

    # ---- test-only inspection ------------------------------------------------

    def change_events(self) -> list[ChangeEvent]:
        return sorted(self._change_events.values(), key=lambda e: (e.created_at, e.id))

    def forget_events(self) -> list[ForgetEvent]:
        return sorted(self._forget_events.values(), key=lambda e: (e.created_at, e.id))

    def all_links(self) -> list[Link]:
        return sorted(self._links.values(), key=lambda link: (link.created_at, link.id))

    def all_memories(self) -> list[Memory]:
        return sorted(self._memories.values(), key=lambda m: (m.recorded_at, m.id))

    # ---- writes (transaction only) ---------------------------------------------

    def _require_transaction(self) -> None:
        if not self._in_transaction:
            raise RuntimeError("writes must happen inside store.transaction()")

    async def add_memory(self, memory: Memory) -> None:
        self._require_transaction()
        if memory.id in self._memories:
            raise ValueError(f"memory {memory.id!r} already exists")
        self._memories[memory.id] = memory

    async def replace_memory(self, memory: Memory) -> None:
        self._require_transaction()
        if memory.id not in self._memories:
            raise MemoryNotFoundError(memory.id)
        self._memories[memory.id] = memory

    async def delete_memories(self, memory_ids: Iterable[str]) -> None:
        self._require_transaction()
        for memory_id in memory_ids:
            for link in self._links.values():
                if memory_id in (link.parent_id, link.dependent_id):
                    # Mirrors the Postgres foreign key: delete links first (forget does).
                    raise ValueError(f"memory {memory_id!r} still has links")
            self._memories.pop(memory_id, None)

    async def add_link(self, link: Link) -> None:
        self._require_transaction()
        if link.id in self._links:
            raise ValueError(f"link {link.id!r} already exists")
        for endpoint in (link.parent_id, link.dependent_id):
            if endpoint not in self._memories:
                raise MemoryNotFoundError(endpoint)
        edge = (link.parent_id, link.dependent_id, link.link_type)
        for existing in self._links.values():
            if (existing.parent_id, existing.dependent_id, existing.link_type) == edge:
                raise ValueError("duplicate link")  # mirrors uq_links_edge
        self._links[link.id] = link

    async def delete_links(self, link_ids: Iterable[str]) -> None:
        self._require_transaction()
        for link_id in link_ids:
            self._links.pop(link_id, None)

    async def add_change_event(self, event: ChangeEvent) -> None:
        self._require_transaction()
        if event.id in self._change_events:
            raise ValueError(f"change event {event.id!r} already exists")
        self._change_events[event.id] = event

    async def replace_change_event(self, event: ChangeEvent) -> None:
        self._require_transaction()
        if event.id not in self._change_events:
            raise ChangeEventNotFoundError(event.id)
        self._change_events[event.id] = event

    async def add_forget_event(self, event: ForgetEvent) -> None:
        self._require_transaction()
        self._forget_events[event.id] = event

    async def delete_change_events_for_user(self, user_id: str) -> int:
        self._require_transaction()
        doomed = [i for i, e in self._change_events.items() if e.user_id == user_id]
        for event_id in doomed:
            del self._change_events[event_id]
        return len(doomed)

    async def delete_forget_events_for_user(self, user_id: str) -> int:
        self._require_transaction()
        doomed = [i for i, e in self._forget_events.items() if e.user_id == user_id]
        for event_id in doomed:
            del self._forget_events[event_id]
        return len(doomed)

    # ---- transaction -----------------------------------------------------------

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[Transaction]:
        if self._in_transaction:
            raise RuntimeError("nested transactions are not supported")
        snapshot = (
            dict(self._memories),
            dict(self._links),
            dict(self._change_events),
            dict(self._forget_events),
        )
        self._in_transaction = True
        try:
            yield self
        except BaseException:
            self._memories, self._links, self._change_events, self._forget_events = snapshot
            raise
        finally:
            self._in_transaction = False
