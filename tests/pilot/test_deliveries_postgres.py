"""PostgresDeliveryReader reads what PostgresDeliveryLog wrote (slow; needs a database)."""

import asyncio
from datetime import date, timedelta

import pytest
import sqlalchemy as sa

from ripple.notify.contracts import AlertKind
from ripple.notify.delivery_log import PostgresDeliveryLog
from ripple.pilot.deliveries import DeliveryRecord, PostgresDeliveryReader
from ripple.storage.engine import engine_from_url
from tests.pilot.support import AFTER, MON, WEEK
from tests.storage.test_users_postgres import migrated  # noqa: F401 - fixture

pytestmark = pytest.mark.slow


@pytest.fixture
def engine(migrated: str):  # noqa: F811 - pytest fixture by name
    engine = engine_from_url(migrated)

    async def run():
        async with engine.begin() as conn:
            await conn.execute(sa.text("TRUNCATE TABLE delivery_log"))

    asyncio.run(run())
    yield engine
    asyncio.run(engine.dispose())


def test_postgres_delivery_reader_returns_the_weeks_rows_in_utc(engine):
    log = PostgresDeliveryLog(engine)
    alert_at = MON + timedelta(hours=10)

    async def run():
        await log.record_digest("asha", MON.date())
        await log.record_alert("asha", "o1", AlertKind.HIGH_FIT, alert_at)
        await log.record_digest("asha", AFTER.date())  # next week
        await log.record_digest("asha", MON.date() - timedelta(days=1))  # last week
        return await PostgresDeliveryReader(engine).deliveries_between(WEEK.start, WEEK.end)

    rows = asyncio.run(run())
    assert rows == [
        DeliveryRecord("asha", "digest", date(2026, 11, 2).isoformat(), MON),
        DeliveryRecord("asha", "high_fit", "o1", alert_at),
    ]
