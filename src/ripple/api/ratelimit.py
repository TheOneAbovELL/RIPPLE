"""Token-bucket rate limiting per user and per client address (ADR-0098).

Write endpoints cost a model call or a ripple; a stuck dashboard retry loop or a
leaked token must not be able to spend the pilot's budget. Every unsafe method (POST,
PUT, PATCH, DELETE) takes one token from the caller's address bucket and, when a
bearer token is present, one from that token's bucket; reads are not limited. The
user bucket is keyed by a prefix of the token's hash: it needs no store lookup, so an
invalid token still burns a bucket, and in the pilot one token is one user (ADR-0040).

`RateLimiter` is a protocol with two implementations: `InMemoryRateLimiter` for tests
and a single process, `RedisRateLimiter` for the deployed API, where several uvicorn
workers share the buckets through the Redis arq already uses. Both are driven by the
injected Clock, so a test can watch a bucket refill without sleeping.
"""

import hashlib
import math
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Protocol, cast

from arq.connections import ArqRedis
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ripple.core.clock import Clock

WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
FORWARDED_FOR = "x-forwarded-for"


@dataclass(frozen=True)
class Bucket:
    capacity: int  # burst size
    refill_per_second: float  # sustained rate

    def __post_init__(self) -> None:
        if self.capacity < 1 or self.refill_per_second <= 0:
            raise ValueError("a bucket needs capacity >= 1 and a positive refill rate")


@dataclass(frozen=True)
class RateLimits:
    """Pilot defaults: a person clicking cannot exceed them, a loop can."""

    per_user: Bucket = Bucket(capacity=30, refill_per_second=0.5)  # 30 burst, 30/min
    per_ip: Bucket = Bucket(capacity=60, refill_per_second=1.0)  # 60 burst, 60/min


@dataclass(frozen=True)
class RateDecision:
    allowed: bool
    remaining: int
    retry_after_seconds: float  # 0 when allowed


class RateLimiter(Protocol):
    async def take(self, key: str, bucket: Bucket, now: datetime) -> RateDecision:
        """Spend one token from `key`'s bucket as of `now`, refilling first."""
        ...


def _refill(tokens: float, updated: datetime, bucket: Bucket, now: datetime) -> float:
    elapsed = max(0.0, (now - updated).total_seconds())
    return min(float(bucket.capacity), tokens + elapsed * bucket.refill_per_second)


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._buckets: dict[str, tuple[float, datetime]] = {}

    async def take(self, key: str, bucket: Bucket, now: datetime) -> RateDecision:
        tokens, updated = self._buckets.get(key, (float(bucket.capacity), now))
        tokens = _refill(tokens, updated, bucket, now)
        if tokens >= 1.0:
            tokens -= 1.0
            self._buckets[key] = (tokens, now)
            return RateDecision(allowed=True, remaining=int(tokens), retry_after_seconds=0.0)
        self._buckets[key] = (tokens, now)
        wait = (1.0 - tokens) / bucket.refill_per_second
        return RateDecision(allowed=False, remaining=0, retry_after_seconds=wait)


# Atomic refill-and-take: HASH {tokens, updated_ms}; a bucket idle long enough to be
# full again is dropped by the expiry rather than stored forever.
_TAKE = """
local capacity = tonumber(ARGV[1])
local rate = tonumber(ARGV[2])
local now_ms = tonumber(ARGV[3])
local state = redis.call('HMGET', KEYS[1], 'tokens', 'updated_ms')
local tokens = tonumber(state[1])
local updated_ms = tonumber(state[2])
if tokens == nil then
    tokens = capacity
    updated_ms = now_ms
end
local elapsed = math.max(0, now_ms - updated_ms) / 1000.0
tokens = math.min(capacity, tokens + elapsed * rate)
local allowed = 0
local retry_ms = 0
if tokens >= 1 then
    tokens = tokens - 1
    allowed = 1
else
    retry_ms = math.ceil((1 - tokens) / rate * 1000)
end
redis.call('HSET', KEYS[1], 'tokens', tokens, 'updated_ms', now_ms)
redis.call('PEXPIRE', KEYS[1], math.ceil(capacity / rate * 1000) + 1000)
return {allowed, math.floor(tokens), retry_ms}
"""

RedisFactory = Callable[[], Awaitable[ArqRedis]]


class RedisRateLimiter:
    """Buckets in Redis, through the arq client (ADR-0017: nothing else talks to Redis).

    Takes a factory rather than a connection because the pool is opened at startup,
    after the app object exists; the first request opens it and later ones reuse it.
    """

    def __init__(self, redis: RedisFactory, *, prefix: str = "ripple:ratelimit:") -> None:
        self._factory = redis
        self._prefix = prefix
        self._redis: ArqRedis | None = None

    async def _client(self) -> ArqRedis:
        if self._redis is None:
            self._redis = await self._factory()
        return self._redis

    async def take(self, key: str, bucket: Bucket, now: datetime) -> RateDecision:
        redis = await self._client()
        now_ms = int(now.timestamp() * 1000)
        # redis-py types eval's arguments as str and its result as str | Awaitable[str];
        # the async client awaits and the script returns three integers.
        result = redis.eval(  # pyright: ignore[reportUnknownMemberType]
            _TAKE,
            1,
            self._prefix + key,
            str(bucket.capacity),
            repr(bucket.refill_per_second),
            str(now_ms),
        )
        if isinstance(result, Awaitable):
            result = await result
        allowed, remaining, retry_ms = (int(part) for part in cast(list[int], result))
        return RateDecision(
            allowed=bool(allowed), remaining=remaining, retry_after_seconds=retry_ms / 1000.0
        )


# ---- the FastAPI side -----------------------------------------------------------------


class RateLimitGuard:
    """What `create_app` stores on app.state and the dependency below consults."""

    def __init__(
        self,
        limiter: RateLimiter,
        clock: Clock,
        limits: RateLimits | None = None,
        *,
        trust_forwarded_for: bool = False,
    ) -> None:
        self._limiter = limiter
        self._clock = clock
        self._limits = limits or RateLimits()
        # Only behind our own reverse proxy (Caddy) is X-Forwarded-For trustworthy;
        # anywhere else a client could pick its own bucket.
        self._trust_forwarded_for = trust_forwarded_for

    @property
    def limits(self) -> RateLimits:
        return self._limits

    def client_key(self, request: Request) -> str:
        forwarded = request.headers.get(FORWARDED_FOR) if self._trust_forwarded_for else None
        if forwarded:
            return "ip:" + forwarded.split(",")[0].strip()
        return "ip:" + (request.client.host if request.client else "unknown")

    @staticmethod
    def user_key(token: str) -> str:
        return "user:" + hashlib.sha256(token.encode()).hexdigest()[:16]

    async def check(self, request: Request, token: str | None) -> None:
        now = self._clock.now()
        decision = await self._limiter.take(self.client_key(request), self._limits.per_ip, now)
        if decision.allowed and token:
            decision = await self._limiter.take(self.user_key(token), self._limits.per_user, now)
        if not decision.allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="rate limit exceeded",
                headers={"Retry-After": str(max(1, math.ceil(decision.retry_after_seconds)))},
            )


_bearer = HTTPBearer(auto_error=False)


async def enforce_rate_limit(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> None:
    """Router-level dependency: a no-op for reads and for apps built without a guard."""
    guard = getattr(request.app.state, "rate_limit", None)
    if not isinstance(guard, RateLimitGuard) or request.method not in WRITE_METHODS:
        return
    await guard.check(request, credentials.credentials if credentials else None)
