"""DeliveryLog contract (ADR-0095): what the in-memory and the Postgres log must agree
on. The Postgres run is tests/storage/test_hardening_delivery_log_postgres.py (slow).
"""

import asyncio
from datetime import date, timedelta

import pytest

from ripple.notify.contracts import AlertKind, DeliveryLog
from ripple.notify.delivery_log import InMemoryDeliveryLog
from ripple.notify.digest import DigestService
from tests.builders import USER
from tests.fakes.clock import DEFAULT_START, FakeClock
from tests.fakes.transport import RecordingTransport
from tests.notify.fakes import CHAT, FakeRecommendationSource, FakeUserDirectory, recommendation

DAY = DEFAULT_START.date()


class DeliveryLogContract:
    """Subclass with a `delivery_log` fixture."""

    def test_digest_day_is_none_until_recorded(self, delivery_log: DeliveryLog):
        assert asyncio.run(delivery_log.last_digest_day(USER)) is None
        asyncio.run(delivery_log.record_digest(USER, DAY))
        assert asyncio.run(delivery_log.last_digest_day(USER)) == DAY

    def test_digest_days_are_per_user(self, delivery_log: DeliveryLog):
        asyncio.run(delivery_log.record_digest(USER, DAY))
        assert asyncio.run(delivery_log.last_digest_day("someone-else")) is None

    def test_recording_the_same_day_twice_is_idempotent(self, delivery_log: DeliveryLog):
        asyncio.run(delivery_log.record_digest(USER, DAY))
        asyncio.run(delivery_log.record_digest(USER, DAY))  # a retried job
        assert asyncio.run(delivery_log.last_digest_day(USER)) == DAY

    def test_last_digest_day_is_the_newest_day_recorded(self, delivery_log: DeliveryLog):
        asyncio.run(delivery_log.record_digest(USER, DAY + timedelta(days=1)))
        asyncio.run(delivery_log.record_digest(USER, DAY))  # an out-of-order replay
        assert asyncio.run(delivery_log.last_digest_day(USER)) == DAY + timedelta(days=1)

    def test_alert_is_none_until_recorded_then_keyed_by_user_opening_and_kind(
        self, delivery_log: DeliveryLog
    ):
        at = DEFAULT_START
        assert asyncio.run(delivery_log.last_alert_at(USER, "o1", AlertKind.HIGH_FIT)) is None
        asyncio.run(delivery_log.record_alert(USER, "o1", AlertKind.HIGH_FIT, at))
        assert asyncio.run(delivery_log.last_alert_at(USER, "o1", AlertKind.HIGH_FIT)) == at
        assert asyncio.run(delivery_log.last_alert_at(USER, "o1", AlertKind.DEADLINE_SOON)) is None
        assert asyncio.run(delivery_log.last_alert_at(USER, "o2", AlertKind.HIGH_FIT)) is None
        assert asyncio.run(delivery_log.last_alert_at("other", "o1", AlertKind.HIGH_FIT)) is None

    def test_delete_for_user_erases_only_that_users_records(self, delivery_log: DeliveryLog):
        asyncio.run(delivery_log.record_digest(USER, DAY))
        asyncio.run(delivery_log.record_alert(USER, "o1", AlertKind.HIGH_FIT, DEFAULT_START))
        asyncio.run(delivery_log.record_digest("other", DAY))
        asyncio.run(delivery_log.delete_for_user(USER))
        assert asyncio.run(delivery_log.last_digest_day(USER)) is None
        assert asyncio.run(delivery_log.last_alert_at(USER, "o1", AlertKind.HIGH_FIT)) is None
        assert asyncio.run(delivery_log.last_digest_day("other")) == DAY

    def test_recording_an_alert_again_moves_its_time_forward(self, delivery_log: DeliveryLog):
        first = DEFAULT_START
        later = DEFAULT_START + timedelta(days=8)
        asyncio.run(delivery_log.record_alert(USER, "o1", AlertKind.HIGH_FIT, first))
        asyncio.run(delivery_log.record_alert(USER, "o1", AlertKind.HIGH_FIT, later))
        assert asyncio.run(delivery_log.last_alert_at(USER, "o1", AlertKind.HIGH_FIT)) == later

    def test_alert_times_come_back_timezone_aware(self, delivery_log: DeliveryLog):
        asyncio.run(delivery_log.record_alert(USER, "o1", AlertKind.HIGH_FIT, DEFAULT_START))
        found = asyncio.run(delivery_log.last_alert_at(USER, "o1", AlertKind.HIGH_FIT))
        assert found is not None and found.tzinfo is not None

    def test_digest_service_rebuilt_over_the_same_log_does_not_resend(
        self, delivery_log: DeliveryLog
    ):
        """A worker restart builds a new DigestService; the log, not the service, remembers."""
        clock = FakeClock()
        transport = RecordingTransport(clock)
        first = _service(delivery_log, clock, transport)
        assert asyncio.run(first.send_daily(USER)) is not None
        restarted = _service(delivery_log, clock, transport)
        clock.advance(timedelta(hours=3))
        assert asyncio.run(restarted.send_daily(USER)) is None
        assert len(transport.sent) == 1


def _service(log: DeliveryLog, clock: FakeClock, transport: RecordingTransport) -> DigestService:
    return DigestService(
        FakeRecommendationSource({USER: [recommendation()]}),
        FakeUserDirectory({USER: CHAT}),
        transport,
        clock,
        delivery_log=log,
    )


class TestInMemoryDeliveryLog(DeliveryLogContract):
    @pytest.fixture
    def delivery_log(self) -> InMemoryDeliveryLog:
        return InMemoryDeliveryLog()


def test_digest_day_is_a_date_not_a_datetime():
    log = InMemoryDeliveryLog()
    asyncio.run(log.record_digest(USER, DAY))
    found = asyncio.run(log.last_digest_day(USER))
    assert type(found) is date
