"""Token-bucket rate limiting on write endpoints (ADR-0098), driven by FakeClock."""

import asyncio
import re
from datetime import timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from ripple.api.app import create_app
from ripple.api.ratelimit import (
    WRITE_METHODS,
    Bucket,
    InMemoryRateLimiter,
    RateDecision,
    RateLimitGuard,
    RateLimits,
)
from tests.api.harness import BASE_URL, Harness, body
from tests.fakes.clock import FakeClock

TINY = RateLimits(
    per_user=Bucket(capacity=2, refill_per_second=1.0),
    per_ip=Bucket(capacity=5, refill_per_second=1.0),
)
STATEMENT = {"content": "CGPA is 7.6", "kind": "fact"}


# ---- the bucket -----------------------------------------------------------------------


def test_bucket_allows_a_burst_up_to_capacity_then_refuses():
    clock, limiter = FakeClock(), InMemoryRateLimiter()
    bucket = Bucket(capacity=3, refill_per_second=1.0)
    verdicts = [asyncio.run(limiter.take("k", bucket, clock.now())).allowed for _ in range(4)]
    assert verdicts == [True, True, True, False]


def test_bucket_refills_with_the_clock_and_never_above_capacity():
    clock, limiter = FakeClock(), InMemoryRateLimiter()
    bucket = Bucket(capacity=2, refill_per_second=0.5)  # one token per two seconds
    for _ in range(2):
        asyncio.run(limiter.take("k", bucket, clock.now()))
    assert asyncio.run(limiter.take("k", bucket, clock.now())).allowed is False
    clock.advance(timedelta(seconds=2))
    assert asyncio.run(limiter.take("k", bucket, clock.now())).allowed is True
    assert asyncio.run(limiter.take("k", bucket, clock.now())).allowed is False
    clock.advance(timedelta(hours=1))  # long idle: full again, not overfull
    verdicts = [asyncio.run(limiter.take("k", bucket, clock.now())).allowed for _ in range(3)]
    assert verdicts == [True, True, False]


def test_refusal_reports_how_long_until_the_next_token():
    clock, limiter = FakeClock(), InMemoryRateLimiter()
    bucket = Bucket(capacity=1, refill_per_second=0.25)
    asyncio.run(limiter.take("k", bucket, clock.now()))
    refused = asyncio.run(limiter.take("k", bucket, clock.now()))
    assert refused.allowed is False
    assert refused.retry_after_seconds == pytest.approx(4.0)
    assert refused.remaining == 0


def test_buckets_are_independent_per_key():
    clock, limiter = FakeClock(), InMemoryRateLimiter()
    bucket = Bucket(capacity=1, refill_per_second=1.0)
    assert asyncio.run(limiter.take("a", bucket, clock.now())).allowed
    assert asyncio.run(limiter.take("b", bucket, clock.now())).allowed
    assert not asyncio.run(limiter.take("a", bucket, clock.now())).allowed


def test_bucket_rejects_nonsense_parameters():
    with pytest.raises(ValueError):
        Bucket(capacity=0, refill_per_second=1.0)
    with pytest.raises(ValueError):
        Bucket(capacity=1, refill_per_second=0.0)


# ---- the guard on the app -------------------------------------------------------------


def _guarded(*, limits: RateLimits = TINY, trust_proxy: bool = False) -> tuple[Harness, FakeClock]:
    h = Harness.build()
    guard = RateLimitGuard(InMemoryRateLimiter(), h.clock, limits, trust_forwarded_for=trust_proxy)
    h.app = create_app(h.services, rate_limit=guard)
    return h, h.clock


def test_writes_over_the_user_limit_are_429_with_retry_after_and_reads_are_not():
    h, _ = _guarded()

    async def run():
        _, headers = await h.user()
        async with h.client() as c:
            writes = [
                await c.post("/statements", json=STATEMENT, headers=headers) for _ in range(3)
            ]
            reads = [await c.get("/memories", headers=headers) for _ in range(10)]
        return writes, reads

    writes, reads = asyncio.run(run())
    assert [w.status_code for w in writes] == [201, 201, 429]
    assert writes[2].headers["retry-after"] == "1"
    assert body(writes[2])["detail"] == "rate limit exceeded"
    assert {r.status_code for r in reads} == {200}


def test_the_user_bucket_refills_by_the_clock():
    h, clock = _guarded()

    async def run():
        _, headers = await h.user()
        async with h.client() as c:
            for _ in range(2):
                await c.post("/statements", json=STATEMENT, headers=headers)
            refused = await c.post("/statements", json=STATEMENT, headers=headers)
            clock.advance(timedelta(seconds=1))
            allowed = await c.post("/statements", json=STATEMENT, headers=headers)
        return refused, allowed

    refused, allowed = asyncio.run(run())
    assert (refused.status_code, allowed.status_code) == (429, 201)


def test_user_buckets_are_per_token_and_the_ip_bucket_is_shared():
    h, _ = _guarded()

    async def run():
        _, asha = await h.user("Asha")
        _, bina = await h.user("Bina")
        async with h.client() as c:
            first = [await c.post("/statements", json=STATEMENT, headers=asha) for _ in range(2)]
            second = [await c.post("/statements", json=STATEMENT, headers=bina) for _ in range(2)]
            # Both used the same client address: 4 of the 5 ip tokens are gone, then 1, then 0.
            fifth = await c.post("/statements", json=STATEMENT, headers=bina)
            sixth = await c.post("/statements", json=STATEMENT, headers=bina)
        return first, second, fifth, sixth

    first, second, fifth, sixth = asyncio.run(run())
    assert [r.status_code for r in first + second] == [201, 201, 201, 201]
    assert fifth.status_code == 429  # bina's own bucket is empty
    assert sixth.status_code == 429  # and so is the shared ip bucket now


def test_unauthenticated_writes_burn_the_ip_bucket_only():
    h, _ = _guarded(limits=RateLimits(per_user=TINY.per_user, per_ip=Bucket(2, 1.0)))

    async def run():
        async with h.client() as c:
            return [await c.post("/statements", json=STATEMENT) for _ in range(3)]

    responses = asyncio.run(run())
    assert [r.status_code for r in responses] == [401, 401, 429]


def test_forwarded_for_picks_the_bucket_only_when_the_proxy_is_trusted():
    untrusted, _ = _guarded(limits=RateLimits(per_user=Bucket(99, 1.0), per_ip=Bucket(1, 1.0)))
    trusted, _ = _guarded(
        limits=RateLimits(per_user=Bucket(99, 1.0), per_ip=Bucket(1, 1.0)), trust_proxy=True
    )

    async def run(h: Harness):
        _, headers = await h.user()
        async with h.client() as c:
            a = await c.post(
                "/statements", json=STATEMENT, headers={**headers, "X-Forwarded-For": "10.0.0.1"}
            )
            b = await c.post(
                "/statements", json=STATEMENT, headers={**headers, "X-Forwarded-For": "10.0.0.2"}
            )
        return a.status_code, b.status_code

    assert asyncio.run(run(untrusted)) == (201, 429)  # header ignored: one shared bucket
    assert asyncio.run(run(trusted)) == (201, 201)  # header honoured: two client buckets


def test_an_app_built_without_a_guard_never_limits():
    h = Harness.build()

    async def run():
        _, headers = await h.user()
        async with h.client() as c:
            return [
                (await c.post("/statements", json=STATEMENT, headers=headers)).status_code
                for _ in range(40)
            ]

    assert set(asyncio.run(run())) == {201}


class _RefusingLimiter:
    async def take(self, key, bucket, now):
        return RateDecision(allowed=False, remaining=0, retry_after_seconds=1.0)


def test_every_product_write_route_is_rate_limited():
    # Behavioural on purpose: FastAPI 0.146 wraps included routers lazily, so walking
    # app.routes for dependencies finds nothing and such a check passes vacuously.
    h = Harness.build()
    h.app = create_app(h.services, rate_limit=RateLimitGuard(_RefusingLimiter(), h.clock))
    writes = [
        (method.upper(), re.sub(r"\{[^}]+\}", "x", path))
        for path, item in h.app.openapi()["paths"].items()
        for method in item
        if method.upper() in WRITE_METHODS
    ]

    async def run():
        async with AsyncClient(transport=ASGITransport(app=h.app), base_url=BASE_URL) as c:
            return {(m, p): (await c.request(m, p, json={})).status_code for m, p in writes}

    codes = asyncio.run(run())
    assert len(codes) >= 10  # statements, memories, questions, resume, openings, me
    assert {route: code for route, code in codes.items() if code != 429} == {}


def test_health_endpoints_are_never_rate_limited():
    h, _ = _guarded(limits=RateLimits(per_user=Bucket(1, 1.0), per_ip=Bucket(1, 1.0)))

    async def run():
        async with AsyncClient(transport=ASGITransport(app=h.app), base_url=BASE_URL) as c:
            return [(await c.get("/healthz")).status_code for _ in range(5)]

    assert set(asyncio.run(run())) == {200}
