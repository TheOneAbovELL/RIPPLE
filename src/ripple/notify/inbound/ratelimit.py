"""Per-key attempt limits for the bot boundary (ADR-0076).

The protocol is the seam: the in-memory limiter below serves tests and a single
process; WS-13's Redis-backed limiter implements the same `allow` for a deployment
with more than one process. Limit and window travel with the call so one limiter can
enforce several policies (link attempts now, messages per minute later).
"""

from collections import deque
from datetime import datetime, timedelta
from typing import Protocol

from ripple.core.clock import Clock


class RateLimiter(Protocol):
    async def allow(self, key: str, limit: int, window: timedelta) -> bool:
        """Record one attempt for `key` and say whether it is within `limit` per `window`.

        A refused attempt is not recorded, so a client hammering the limit does not
        push its own unlock further away than `window` after its last allowed try.
        """
        ...


class InMemoryRateLimiter:
    """Sliding window over the injected clock; keys with no recent attempts are dropped."""

    def __init__(self, clock: Clock) -> None:
        self._clock = clock
        self._attempts: dict[str, deque[datetime]] = {}

    async def allow(self, key: str, limit: int, window: timedelta) -> bool:
        now = self._clock.now()
        attempts = self._attempts.setdefault(key, deque())
        cutoff = now - window
        while attempts and attempts[0] <= cutoff:
            attempts.popleft()
        if len(attempts) >= limit:
            return False
        attempts.append(now)
        return True

    def forget_idle(self, window: timedelta) -> None:
        """Housekeeping for a long-running process: drop keys idle for a whole window."""
        cutoff = self._clock.now() - window
        for key in [k for k, a in self._attempts.items() if not a or a[-1] <= cutoff]:
            del self._attempts[key]
