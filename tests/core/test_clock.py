from datetime import UTC, datetime, timedelta

import pytest

from ripple.core.clock import Clock, SystemClock
from tests.fakes.clock import FakeClock


def test_fake_clock_advance_moves_now():
    clock = FakeClock(datetime(2026, 11, 1, tzinfo=UTC))
    clock.advance(timedelta(days=30))
    assert clock.now() == datetime(2026, 12, 1, tzinfo=UTC)


def test_fake_clock_set_jumps_to_moment():
    clock = FakeClock()
    clock.set(datetime(2027, 2, 1, tzinfo=UTC))
    assert clock.now() == datetime(2027, 2, 1, tzinfo=UTC)


def test_fake_clock_rejects_naive_datetimes():
    with pytest.raises(ValueError):
        FakeClock(datetime(2026, 11, 1))


def test_fake_clock_satisfies_clock_protocol():
    clock: Clock = FakeClock()
    assert clock.now().tzinfo is not None


def test_system_clock_returns_aware_utc():
    now = SystemClock().now()
    assert now.tzinfo is UTC
