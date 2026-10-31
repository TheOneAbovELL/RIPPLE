"""Per-user leases so two workers never sweep the same user at once (ADR-0056).

A sweep resumes open ChangeEvents; two concurrent resumes of one event would resolve
the same wave twice. The lease is advisory and time-limited: a crashed holder frees it
when the ttl passes, which is why the ttl must exceed a sweep's longest run. A holder
that outlives its ttl must not free the *next* holder's lease, so release compares a
per-acquisition token before deleting.

The same backend also guards single ChangeEvents (ADR-0099): `ChangeEventLease` adapts
it to core's `EventLease`, so a live ripple and the sweep never drive one event at once.
"""

import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Protocol
from uuid import uuid4

from arq.connections import ArqRedis

from ripple.core.clock import Clock

log = logging.getLogger("ripple.worker.lease")


class Lease(Protocol):
    async def acquire(self, key: str, ttl: timedelta) -> bool:
        """True when this caller now holds the lease; False when someone else does."""
        ...

    async def release(self, key: str) -> None:
        """Free the lease if this instance still holds it; a no-op otherwise."""
        ...


class InMemoryLease:
    """Single-process lease that expires by the injected clock; for tests and dev."""

    def __init__(self, clock: Clock) -> None:
        self._clock = clock
        self._held_until: dict[str, datetime] = {}

    async def acquire(self, key: str, ttl: timedelta) -> bool:
        now = self._clock.now()
        expiry = self._held_until.get(key)
        if expiry is not None and expiry > now:
            return False
        self._held_until[key] = now + ttl
        return True

    async def release(self, key: str) -> None:
        self._held_until.pop(key, None)

    def holds(self, key: str) -> bool:
        expiry = self._held_until.get(key)
        return expiry is not None and expiry > self._clock.now()


# Delete only if the value is still our token: a holder past its ttl must not free a
# lease another worker has since acquired.
_RELEASE_IF_OWNER = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
end
return 0
"""


class RedisLease:
    """SET NX PX on the worker's own Redis connection (the one arq already holds)."""

    def __init__(self, redis: ArqRedis, *, prefix: str = "ripple:lease:") -> None:
        self._redis = redis
        self._prefix = prefix
        self._tokens: dict[str, str] = {}

    async def acquire(self, key: str, ttl: timedelta) -> bool:
        token = uuid4().hex
        ttl_ms = max(1, int(ttl.total_seconds() * 1000))
        acquired = await self._redis.set(self._prefix + key, token, nx=True, px=ttl_ms)
        if acquired:
            self._tokens[key] = token
        return bool(acquired)

    async def release(self, key: str) -> None:
        token = self._tokens.pop(key, None)
        if token is None:
            return
        # redis-py types eval as returning str | Awaitable[str]; the async client awaits.
        result = self._redis.eval(_RELEASE_IF_OWNER, 1, self._prefix + key, token)  # pyright: ignore[reportUnknownMemberType]
        if isinstance(result, Awaitable):
            await result


class LazyRedisLease:
    """A RedisLease over a connection opened on first use.

    The API builds its Services before any event loop runs, so it cannot hold an
    open connection yet; the first acquire opens the shared pool (ADR-0099, ADR-0079).
    """

    def __init__(
        self, redis: Callable[[], Awaitable[ArqRedis]], *, prefix: str = "ripple:lease:"
    ) -> None:
        self._factory = redis
        self._prefix = prefix
        self._lease: RedisLease | None = None
        self._opening = asyncio.Lock()

    async def _get(self) -> RedisLease:
        # Two first acquires at once must share one RedisLease, or the second would
        # replace the first's token table and its release would free nothing.
        async with self._opening:
            if self._lease is None:
                self._lease = RedisLease(await self._factory(), prefix=self._prefix)
        return self._lease

    async def acquire(self, key: str, ttl: timedelta) -> bool:
        return await (await self._get()).acquire(key, ttl)

    async def release(self, key: str) -> None:
        if self._lease is not None:  # nothing was acquired through an unopened pool
            await self._lease.release(key)


def sweep_lease_key(user_id: str) -> str:
    return f"sweep:{user_id}"


# A live ripple is bounded by its resolver calls; two hours is far above any observed
# run and above the sweep's cron timeout (1 h, pinned by a test). Too short and a slow
# run loses its exclusion; too long only delays recovery of a crashed holder's event.
EVENT_LEASE_TTL = timedelta(hours=2)


def event_lease_key(event_id: str) -> str:
    return f"ripple-event:{event_id}"


class ChangeEventLease:
    """Core's EventLease over a keyed Lease: one key per ChangeEvent, a fixed ttl."""

    def __init__(self, lease: Lease, *, ttl: timedelta = EVENT_LEASE_TTL) -> None:
        self._lease = lease
        self._ttl = ttl

    async def acquire(self, event_id: str) -> bool:
        return await self._lease.acquire(event_lease_key(event_id), self._ttl)

    async def release(self, event_id: str) -> None:
        # Called after the ripple committed. A failing release must not turn that write
        # into an error (a client would retry and write it twice); the ttl frees the
        # key anyway, so the failure is logged with its traceback and dropped.
        try:
            await self._lease.release(event_lease_key(event_id))
        except Exception:
            log.exception("event lease release failed", extra={"event_id": event_id})


@asynccontextmanager
async def leased(lease: Lease, key: str, ttl: timedelta) -> AsyncIterator[bool]:
    """Yield whether the lease was taken; release it on exit only if it was."""
    acquired = await lease.acquire(key, ttl)
    try:
        yield acquired
    finally:
        if acquired:
            await lease.release(key)
