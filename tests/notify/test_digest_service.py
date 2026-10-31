import asyncio
from datetime import timedelta

import pytest

from ripple.notify.contracts import AlertKind, Thresholds
from ripple.notify.delivery_log import InMemoryDeliveryLog
from ripple.notify.digest import DigestService
from ripple.notify.errors import TelegramSendError
from tests.builders import USER
from tests.fakes.clock import DEFAULT_START, FakeClock
from tests.fakes.transport import RecordingTransport, failing_transport
from tests.notify.fakes import CHAT, FakeRecommendationSource, FakeUserDirectory, recommendation

WEEK = timedelta(days=7)


def _service(ranked, *, clock=None, transport=None, thresholds=None, chats=None, log=None):
    clock = clock or FakeClock()
    transport = transport if transport is not None else RecordingTransport(clock)
    source = FakeRecommendationSource({USER: ranked})
    users = FakeUserDirectory(chats if chats is not None else {USER: CHAT})
    service = DigestService(
        source,
        users,
        transport,
        clock,
        thresholds=thresholds,
        delivery_log=log if log is not None else InMemoryDeliveryLog(),
    )
    return service, transport, source


# ---- daily digest --------------------------------------------------------------------


def test_send_daily_sends_rendered_digest_to_the_users_own_chat():
    service, transport, source = _service([recommendation()])
    receipt = asyncio.run(service.send_daily(USER))

    assert receipt is not None and receipt.chat_id == CHAT
    assert [m.chat_id for m in transport.sent] == [CHAT]
    assert transport.sent[0].text.startswith("Ripple digest for 2026-10-19")
    assert source.calls == [(USER, DEFAULT_START, Thresholds().digest_limit)]


def test_send_daily_is_sent_once_per_user_per_day():
    clock = FakeClock()
    service, transport, _ = _service([recommendation()], clock=clock)
    assert asyncio.run(service.send_daily(USER)) is not None
    clock.advance(timedelta(hours=5))
    assert asyncio.run(service.send_daily(USER)) is None
    assert len(transport.sent) == 1


def test_send_daily_sends_again_on_the_next_day():
    clock = FakeClock()
    service, transport, _ = _service([recommendation()], clock=clock)
    asyncio.run(service.send_daily(USER))
    clock.advance(timedelta(days=1))
    assert asyncio.run(service.send_daily(USER)) is not None
    assert len(transport.sent) == 2


def test_send_daily_does_not_record_the_day_when_the_transport_fails():
    log = InMemoryDeliveryLog()
    service, _, _ = _service([recommendation()], transport=failing_transport(), log=log)
    with pytest.raises(TelegramSendError):
        asyncio.run(service.send_daily(USER))
    assert asyncio.run(log.last_digest_day(USER)) is None


def test_send_daily_skips_users_without_a_linked_chat():
    service, transport, _ = _service([recommendation()], chats={USER: None})
    assert asyncio.run(service.send_daily(USER)) is None
    assert transport.sent == []


def test_send_daily_skips_when_nothing_ranks_and_leaves_the_day_open():
    service, transport, source = _service([])
    assert asyncio.run(service.send_daily(USER)) is None
    assert transport.sent == []
    source.by_user[USER] = [recommendation()]
    assert asyncio.run(service.send_daily(USER)) is not None


def test_send_daily_passes_the_digest_limit_to_the_ranking_source():
    service, _, source = _service([recommendation()], thresholds=Thresholds(digest_limit=3))
    asyncio.run(service.send_daily(USER))
    assert source.calls[0][2] == 3


def test_send_daily_stays_under_the_telegram_limit_with_long_reasons():
    long_reasons = tuple(f"JD line {i}: " + "x" * 200 for i in range(5))
    ranked = [recommendation(opening_id=str(i), fit_reasons=long_reasons) for i in range(10)]
    service, transport, _ = _service(ranked)
    assert asyncio.run(service.send_daily(USER)) is not None
    assert len(transport.sent[0].text) <= 4096


# ---- alerts --------------------------------------------------------------------------


def test_send_alerts_sends_one_batched_message_for_qualifying_openings():
    clock = FakeClock()
    ranked = [
        recommendation(
            opening_id="hot", title="Hot", fit_score=0.9, deadline=clock.now() + timedelta(days=9)
        ),
        recommendation(
            opening_id="soon",
            title="Soon",
            fit_score=0.2,
            deadline=clock.now() + timedelta(hours=20),
        ),
        recommendation(
            opening_id="cold", title="Cold", fit_score=0.2, deadline=clock.now() + timedelta(days=9)
        ),
    ]
    service, transport, _ = _service(ranked, clock=clock)
    receipt = asyncio.run(service.send_alerts(USER, clock.now() - WEEK))

    assert receipt is not None
    assert len(transport.sent) == 1
    text = transport.sent[0].text
    assert "1. Hot at Acme" in text and "2. Soon at Acme" in text and "Cold" not in text


def test_send_alerts_scans_deeper_than_the_digest_so_a_low_ranked_deadline_is_not_missed():
    clock = FakeClock()
    filler = [
        recommendation(opening_id=f"f{i}", fit_score=0.5, deadline=clock.now() + timedelta(days=9))
        for i in range(10)
    ]
    urgent = recommendation(
        opening_id="urgent",
        title="Urgent",
        fit_score=0.1,
        deadline=clock.now() + timedelta(hours=2),
    )
    service, transport, source = _service([*filler, urgent], clock=clock)

    receipt = asyncio.run(service.send_alerts(USER, clock.now() - WEEK))

    assert receipt is not None
    assert "1. Urgent at Acme" in transport.sent[0].text
    assert source.calls[-1][2] == Thresholds().alert_scan_limit > Thresholds().digest_limit


def test_send_alerts_does_not_repeat_an_alert_within_the_cooldown():
    clock = FakeClock()
    service, transport, _ = _service([recommendation(fit_score=0.9, deadline=None)], clock=clock)
    assert asyncio.run(service.send_alerts(USER, clock.now() - WEEK)) is not None
    clock.advance(timedelta(hours=1))
    assert asyncio.run(service.send_alerts(USER, clock.now() - WEEK)) is None
    assert len(transport.sent) == 1


def test_send_alerts_repeats_once_the_last_alert_is_older_than_since():
    clock = FakeClock()
    log = InMemoryDeliveryLog()
    asyncio.run(
        log.record_alert(USER, "opening-1", AlertKind.HIGH_FIT, clock.now() - timedelta(days=8))
    )
    service, transport, _ = _service(
        [recommendation(fit_score=0.9, deadline=None)], clock=clock, log=log
    )
    assert asyncio.run(service.send_alerts(USER, clock.now() - WEEK)) is not None
    assert len(transport.sent) == 1


def test_send_alerts_fires_a_deadline_alert_when_the_opening_enters_the_48h_window():
    clock = FakeClock()
    deadline = clock.now() + timedelta(hours=60)
    service, transport, _ = _service(
        [recommendation(fit_score=0.2, deadline=deadline)], clock=clock
    )
    since = clock.now() - WEEK
    assert asyncio.run(service.send_alerts(USER, since)) is None  # 60h out: nothing yet
    clock.advance(timedelta(hours=13))  # 47h out
    receipt = asyncio.run(service.send_alerts(USER, since))
    assert receipt is not None
    assert "deadline in 47h" in transport.sent[0].text


def test_send_alerts_second_kind_is_sent_alone_and_leaves_the_first_kinds_cooldown_untouched():
    clock = FakeClock()
    log = InMemoryDeliveryLog()
    deadline = clock.now() + timedelta(hours=60)
    service, transport, _ = _service(
        [recommendation(fit_score=0.9, deadline=deadline)], clock=clock, log=log
    )
    since = clock.now() - WEEK
    asyncio.run(service.send_alerts(USER, since))  # high fit
    first_fit_alert = asyncio.run(log.last_alert_at(USER, "opening-1", AlertKind.HIGH_FIT))
    clock.advance(timedelta(hours=13))
    asyncio.run(service.send_alerts(USER, since))  # now also deadline soon

    assert len(transport.sent) == 2
    assert "   Why now: deadline in 47h" in transport.sent[1].text
    assert "high fit" not in transport.sent[1].text
    assert asyncio.run(log.last_alert_at(USER, "opening-1", AlertKind.HIGH_FIT)) == first_fit_alert
    assert asyncio.run(log.last_alert_at(USER, "opening-1", AlertKind.DEADLINE_SOON)) == clock.now()


def test_send_alerts_skips_flagged_openings_even_when_urgent():
    clock = FakeClock()
    ranked = [
        recommendation(fit_score=0.95, deadline=clock.now() + timedelta(hours=2), flagged=True)
    ]
    service, transport, _ = _service(ranked, clock=clock)
    assert asyncio.run(service.send_alerts(USER, clock.now() - WEEK)) is None
    assert transport.sent == []


def test_send_alerts_skips_users_without_a_linked_chat():
    clock = FakeClock()
    service, transport, _ = _service(
        [recommendation(fit_score=0.95)], clock=clock, chats={USER: None}
    )
    assert asyncio.run(service.send_alerts(USER, clock.now())) is None
    assert transport.sent == []


def test_send_alerts_does_not_record_when_the_transport_fails():
    clock = FakeClock()
    log = InMemoryDeliveryLog()
    service, _, _ = _service(
        [recommendation(fit_score=0.95, deadline=None)],
        clock=clock,
        transport=failing_transport(),
        log=log,
    )
    with pytest.raises(TelegramSendError):
        asyncio.run(service.send_alerts(USER, clock.now() - timedelta(days=1)))
    assert asyncio.run(log.last_alert_at(USER, "opening-1", AlertKind.HIGH_FIT)) is None
