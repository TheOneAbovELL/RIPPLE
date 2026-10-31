"""FakeClock: time that only moves when a test says so."""

from datetime import UTC, datetime, timedelta

DEFAULT_START = datetime(2026, 10, 19, 9, 0, tzinfo=UTC)


class FakeClock:
    def __init__(self, start: datetime = DEFAULT_START) -> None:
        if start.tzinfo is None:
            raise ValueError("FakeClock needs a timezone-aware start")
        self._now = start

    def now(self) -> datetime:
        return self._now

    def advance(self, delta: timedelta) -> datetime:
        self._now += delta
        return self._now

    def set(self, moment: datetime) -> None:
        if moment.tzinfo is None:
            raise ValueError("FakeClock needs a timezone-aware moment")
        self._now = moment
