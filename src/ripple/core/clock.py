"""Injected time.

Core never calls datetime.now() directly (python.md): validity windows, expiry and
ChangeEvent timestamps all read a Clock, so tests can move time with FakeClock.
This module is the single place where the system clock is read.
"""

from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime:
        """Current time, always timezone-aware UTC."""
        ...


class SystemClock:
    """The real clock. Only production wiring instantiates it."""

    def now(self) -> datetime:
        return datetime.now(tz=UTC)
