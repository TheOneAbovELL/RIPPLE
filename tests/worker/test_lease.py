import asyncio
import contextlib
import os
from datetime import timedelta

import pytest

from ripple.worker.lease import InMemoryLease, RedisLease, leased
from tests.fakes.clock import FakeClock

TTL = timedelta(minutes=30)


def test_lease_second_acquire_fails_while_held():
    lease = InMemoryLease(FakeClock())
    assert asyncio.run(lease.acquire("sweep:u1", TTL)) is True
    assert asyncio.run(lease.acquire("sweep:u1", TTL)) is False


def test_lease_acquire_succeeds_after_release():
    lease = InMemoryLease(FakeClock())
    asyncio.run(lease.acquire("sweep:u1", TTL))
    asyncio.run(lease.release("sweep:u1"))
    assert asyncio.run(lease.acquire("sweep:u1", TTL)) is True


def test_lease_expires_by_the_clock_so_a_crashed_holder_does_not_block_forever():
    clock = FakeClock()
    lease = InMemoryLease(clock)
    asyncio.run(lease.acquire("sweep:u1", TTL))
    clock.advance(TTL - timedelta(seconds=1))
    assert asyncio.run(lease.acquire("sweep:u1", TTL)) is False
    clock.advance(timedelta(seconds=1))
    assert asyncio.run(lease.acquire("sweep:u1", TTL)) is True


def test_lease_keys_are_independent_per_user():
    lease = InMemoryLease(FakeClock())
    assert asyncio.run(lease.acquire("sweep:u1", TTL)) is True
    assert asyncio.run(lease.acquire("sweep:u2", TTL)) is True


def test_leased_context_releases_only_what_it_acquired():
    lease = InMemoryLease(FakeClock())
    asyncio.run(lease.acquire("sweep:u1", TTL))

    async def contend():
        async with leased(lease, "sweep:u1", TTL) as held:
            assert held is False
        return lease.holds("sweep:u1")

    assert asyncio.run(contend()) is True  # the outer holder keeps it


def test_leased_context_releases_on_exception():
    lease = InMemoryLease(FakeClock())

    async def crash():
        async with leased(lease, "sweep:u1", TTL) as held:
            assert held is True
            raise RuntimeError("boom")

    with contextlib.suppress(RuntimeError):
        asyncio.run(crash())
    assert lease.holds("sweep:u1") is False


# ---- RedisLease (slow: needs a Redis at TEST_REDIS_URL or REDIS_URL) ----------------


@pytest.mark.slow
def test_redis_lease_acquire_release_expiry_and_foreign_release():
    url = os.environ.get("TEST_REDIS_URL") or os.environ.get("REDIS_URL")
    if not url:
        pytest.skip("TEST_REDIS_URL/REDIS_URL not set")
    from arq.connections import RedisSettings, create_pool

    async def scenario():
        redis = await create_pool(RedisSettings.from_dsn(url))
        try:
            prefix = "ripple:test-lease:"
            a, b = RedisLease(redis, prefix=prefix), RedisLease(redis, prefix=prefix)
            await redis.delete(prefix + "sweep:u1")
            assert await a.acquire("sweep:u1", timedelta(seconds=30)) is True
            assert await b.acquire("sweep:u1", timedelta(seconds=30)) is False
            await b.release("sweep:u1")  # b never held it: must not free a's lease
            assert await b.acquire("sweep:u1", timedelta(seconds=30)) is False
            await a.release("sweep:u1")
            assert await b.acquire("sweep:u1", timedelta(milliseconds=200)) is True
            await asyncio.sleep(0.3)  # ttl passed: a crashed holder frees it
            assert await a.acquire("sweep:u1", timedelta(seconds=30)) is True
            await b.release("sweep:u1")  # b's token is stale: a keeps the lease
            assert await b.acquire("sweep:u1", timedelta(seconds=30)) is False
            await a.release("sweep:u1")
        finally:
            await redis.aclose()

    asyncio.run(scenario())
