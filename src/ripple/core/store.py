"""Store protocols (docs/02-architecture.md, module core).

Reads are available everywhere; writes only inside a Transaction, so that every
caller commits a whole unit (a wave, an update with its link copies, a forget cascade)
or nothing. The in-memory implementation lives in tests/fakes; the Postgres one in
ripple.storage (ADR-0016). Both must pass tests/core/store_contract.py.
"""

from collections.abc import Iterable
from contextlib import AbstractAsyncContextManager
from datetime import datetime
from typing import Protocol

from ripple.core.errors import RippleError
from ripple.core.models import ChangeEvent, ForgetEvent, Link, Memory, Status


class MemoryNotFoundError(RippleError):
    def __init__(self, memory_id: str) -> None:
        self.memory_id = memory_id
        super().__init__(f"memory {memory_id!r} not found")


class ChangeEventNotFoundError(RippleError):
    def __init__(self, event_id: str) -> None:
        self.event_id = event_id
        super().__init__(f"change event {event_id!r} not found")


class StoreReader(Protocol):
    async def get_memory(self, memory_id: str) -> Memory: ...

    async def get_memories(self, memory_ids: Iterable[str]) -> list[Memory]:
        """Memories in the given order; raises MemoryNotFoundError on the first miss."""
        ...

    async def memories_for_user(
        self, user_id: str, statuses: Iterable[Status] | None = None
    ) -> list[Memory]: ...

    async def version_chain(self, memory_id: str) -> list[Memory]:
        """Every version of the memory, oldest first."""
        ...

    async def latest_version(self, memory_id: str) -> Memory: ...

    async def dependents_of(self, memory_id: str) -> list[Link]:
        """Links where this memory is the parent."""
        ...

    async def parents_of(self, memory_id: str) -> list[Link]:
        """Links where this memory is the dependent."""
        ...

    async def links_for_user(self, user_id: str) -> list[Link]:
        """Every link between this user's memories; the runner builds its graph from it."""
        ...

    async def get_change_event(self, event_id: str) -> ChangeEvent: ...

    async def open_change_events(self, user_id: str) -> list[ChangeEvent]:
        """Events with no completed_at, oldest first (ADR-0013: the sweep resumes them)."""
        ...

    async def events_asking(self, memory_id: str) -> list[ChangeEvent]:
        """Events holding an `ask` decision for this memory, oldest first."""
        ...

    async def change_events_for_user(self, user_id: str) -> list[ChangeEvent]:
        """Every ChangeEvent of the user, oldest first (inspector history, export)."""
        ...

    async def forget_events_for_user(self, user_id: str) -> list[ForgetEvent]:
        """Every ForgetEvent of the user, oldest first."""
        ...

    async def memories_expiring_at(self, user_id: str, now: datetime) -> list[Memory]:
        """VALID memories whose valid_to has passed at `now`."""
        ...


class Transaction(StoreReader, Protocol):
    async def add_memory(self, memory: Memory) -> None: ...

    async def replace_memory(self, memory: Memory) -> None:
        """Overwrite the row with the same id (status changes, completed updates)."""
        ...

    async def delete_memories(self, memory_ids: Iterable[str]) -> None: ...

    async def add_link(self, link: Link) -> None: ...

    async def delete_links(self, link_ids: Iterable[str]) -> None: ...

    async def add_change_event(self, event: ChangeEvent) -> None: ...

    async def replace_change_event(self, event: ChangeEvent) -> None: ...

    async def add_forget_event(self, event: ForgetEvent) -> None: ...

    async def delete_change_events_for_user(self, user_id: str) -> int:
        """Erase the user's ChangeEvents (DELETE /me, FR-15); returns the count."""
        ...

    async def delete_forget_events_for_user(self, user_id: str) -> int: ...


class Store(StoreReader, Protocol):
    def transaction(self) -> AbstractAsyncContextManager[Transaction]:
        """All writes inside commit together on exit; any exception rolls them all back."""
        ...
