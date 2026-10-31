"""InMemoryRateLimiter: a sliding window over the FakeClock (ADR-0076)."""

import asyncio
from datetime import timedelta

from ripple.notify.inbound.ratelimit import InMemoryRateLimiter
from tests.fakes.clock import FakeClock

WINDOW = timedelta(minutes=10)


def test_rate_limiter_allows_up_to_the_limit_then_refuses():
    limiter = InMemoryRateLimiter(FakeClock())

    async def run():
        return [await limiter.allow("chat:1", 5, WINDOW) for _ in range(6)]

    assert asyncio.run(run()) == [True] * 5 + [False]


def test_rate_limiter_releases_once_the_window_has_passed():
    clock = FakeClock()
    limiter = InMemoryRateLimiter(clock)

    async def run():
        for _ in range(5):
            await limiter.allow("chat:1", 5, WINDOW)
        refused = await limiter.allow("chat:1", 5, WINDOW)
        clock.advance(WINDOW - timedelta(seconds=1))
        still_refused = await limiter.allow("chat:1", 5, WINDOW)
        clock.advance(timedelta(seconds=1))
        allowed = await limiter.allow("chat:1", 5, WINDOW)
        return refused, still_refused, allowed

    assert asyncio.run(run()) == (False, False, True)


def test_rate_limiter_refused_attempts_do_not_extend_the_lockout():
    clock = FakeClock()
    limiter = InMemoryRateLimiter(clock)

    async def run():
        for _ in range(5):
            await limiter.allow("chat:1", 5, WINDOW)
        clock.advance(timedelta(minutes=9))
        await limiter.allow("chat:1", 5, WINDOW)  # refused; must not count
        clock.advance(timedelta(minutes=1))
        return await limiter.allow("chat:1", 5, WINDOW)

    assert asyncio.run(run()) is True


def test_rate_limiter_keys_are_independent():
    limiter = InMemoryRateLimiter(FakeClock())

    async def run():
        for _ in range(5):
            await limiter.allow("chat:1", 5, WINDOW)
        return await limiter.allow("chat:2", 5, WINDOW)

    assert asyncio.run(run()) is True


def test_rate_limiter_forget_idle_drops_keys_older_than_the_window():
    clock = FakeClock()
    limiter = InMemoryRateLimiter(clock)

    async def run():
        await limiter.allow("old", 5, WINDOW)
        clock.advance(WINDOW)
        await limiter.allow("fresh", 5, WINDOW)

    asyncio.run(run())
    limiter.forget_idle(WINDOW)

    assert set(limiter._attempts) == {"fresh"}  # pyright: ignore[reportPrivateUsage]
