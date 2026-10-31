import asyncio
from datetime import timedelta

import pytest

from ripple.domains.jobs.sources.ratelimit import TokenBucket
from tests.domains.jobs_sources.support import advancing_sleeper
from tests.fakes.clock import FakeClock


def test_token_bucket_first_request_is_immediate_and_the_second_waits_the_interval():
    clock = FakeClock()
    sleep, slept = advancing_sleeper(clock)
    bucket = TokenBucket(2, clock, sleeper=sleep)  # one request every 30 s

    assert asyncio.run(bucket.acquire()) == 0.0
    waited = asyncio.run(bucket.acquire())

    assert waited == pytest.approx(30.0)
    assert slept == [pytest.approx(30.0)]
    assert clock.now() == FakeClock().now() + timedelta(seconds=30)


def test_token_bucket_does_not_wait_when_enough_time_has_passed():
    clock = FakeClock()
    sleep, slept = advancing_sleeper(clock)
    bucket = TokenBucket(6, clock, sleeper=sleep)  # every 10 s
    asyncio.run(bucket.acquire())
    clock.advance(timedelta(seconds=10))

    assert asyncio.run(bucket.acquire()) == 0.0
    assert slept == []


def test_token_bucket_waits_only_the_remaining_part_of_the_interval():
    clock = FakeClock()
    sleep, _ = advancing_sleeper(clock)
    bucket = TokenBucket(6, clock, sleeper=sleep)
    asyncio.run(bucket.acquire())
    clock.advance(timedelta(seconds=4))

    assert asyncio.run(bucket.acquire()) == pytest.approx(6.0)


def test_token_bucket_default_burst_of_one_never_lets_two_requests_through_at_once():
    clock = FakeClock()
    sleep, slept = advancing_sleeper(clock)
    bucket = TokenBucket(60, clock, sleeper=sleep)
    clock.advance(timedelta(minutes=10))  # idle for a long time: still one token

    asyncio.run(bucket.acquire())
    asyncio.run(bucket.acquire())

    assert slept == [pytest.approx(1.0)]


def test_token_bucket_raises_instead_of_spinning_when_the_sleeper_does_not_advance_time():
    clock = FakeClock()

    async def frozen(seconds: float) -> None:
        return None

    bucket = TokenBucket(60, clock, sleeper=frozen)
    asyncio.run(bucket.acquire())
    with pytest.raises(RuntimeError, match="did not advance"):
        asyncio.run(bucket.acquire())


def test_token_bucket_rejects_a_non_positive_rate():
    with pytest.raises(ValueError):
        TokenBucket(0, FakeClock())
