"""Per-source token bucket (ADR-0070, point 3).

The default bucket holds one token, so `per_minute=6` means one request every ten
seconds rather than six at once and then silence: a spacing a small career site never
notices. Time comes from the injected Clock and waiting from the injected sleeper, so
tests advance a FakeClock instead of sleeping.
"""

import asyncio
from collections.abc import Awaitable, Callable

from ripple.core.clock import Clock

Sleeper = Callable[[float], Awaitable[None]]

# Float remainders: a deficit of a few nanoseconds must neither block nor sleep for 0 s.
_TOLERANCE = 1e-9
_MIN_SLEEP_SECONDS = 0.001


class TokenBucket:
    def __init__(
        self,
        per_minute: float,
        clock: Clock,
        *,
        sleeper: Sleeper | None = None,
        burst: int = 1,
    ) -> None:
        if per_minute <= 0:
            raise ValueError("per_minute must be positive")
        if burst < 1:
            raise ValueError("burst must be at least 1")
        self._rate = per_minute / 60.0  # tokens per second
        self._capacity = float(burst)
        self._tokens = float(burst)
        self._clock = clock
        self._sleep: Sleeper = sleeper or asyncio.sleep
        self._updated = clock.now()

    def _refill(self) -> None:
        now = self._clock.now()
        elapsed = (now - self._updated).total_seconds()
        if elapsed > 0:
            self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)
            self._updated = now

    async def acquire(self) -> float:
        """Take one token, sleeping until one is available; returns the seconds waited."""
        waited = 0.0
        while True:
            self._refill()
            if self._tokens >= 1.0 - _TOLERANCE:
                self._tokens -= 1.0
                return waited
            needed = max((1.0 - self._tokens) / self._rate, _MIN_SLEEP_SECONDS)
            before = self._clock.now()
            await self._sleep(needed)
            waited += needed
            if self._clock.now() <= before:
                # A sleeper that does not move the clock would spin here forever.
                raise RuntimeError("TokenBucket: the clock did not advance while sleeping")
