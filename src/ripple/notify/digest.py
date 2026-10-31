"""DigestService: FR-9 delivery on top of the ranking contract (ADR-0055, ADR-0056).

`send_daily` sends one digest per user per UTC day; `send_alerts` sends one batched
alert for the (opening, kind) pairs that crossed a threshold and were not alerted
within the cooldown. Both are idempotent through the DeliveryLog: a retried cron job
never sends a duplicate, and two workers never do either as long as they share the
same log (the in-memory log is per process; see the WS-6 handover for the Postgres
one). The service reads rankings; it never ranks.
"""

import logging
from datetime import datetime

from ripple.core.clock import Clock
from ripple.domains.jobs.vocabulary import Recommendation, RecommendationSource
from ripple.notify.contracts import (
    AlertKind,
    DeliveryLog,
    MessageReceipt,
    Thresholds,
    Transport,
    UserDirectory,
)
from ripple.notify.render import Alert, alert_kinds, render_alert, render_digest

log = logging.getLogger("ripple.notify.digest")


class DigestService:
    def __init__(
        self,
        recommendations: RecommendationSource,
        users: UserDirectory,
        transport: Transport,
        clock: Clock,
        *,
        delivery_log: DeliveryLog,
        thresholds: Thresholds | None = None,
    ) -> None:
        self._recommendations = recommendations
        self._users = users
        self._transport = transport
        self._clock = clock
        self._thresholds = thresholds or Thresholds()
        self._log = delivery_log

    @property
    def thresholds(self) -> Thresholds:
        return self._thresholds

    @property
    def transport(self) -> Transport:
        """Where messages go; a local dry run checks it is not Telegram (ADR-0134)."""
        return self._transport

    @property
    def delivery_log(self) -> DeliveryLog | None:
        return self._log

    async def send_daily(self, user_id: str) -> MessageReceipt | None:
        """The day's digest, or None when it was already sent, nothing ranks or no chat."""
        now = self._clock.now()
        today = now.date()
        if await self._log.last_digest_day(user_id) == today:
            log.info("digest already sent today", extra={"user_id": user_id})
            return None
        chat_id = await self._users.telegram_chat_id(user_id)
        if chat_id is None:
            log.info("digest skipped: no telegram chat linked", extra={"user_id": user_id})
            return None
        ranked = await self._recommendations.recommendations_for(
            user_id, now=now, limit=self._thresholds.digest_limit
        )
        if not ranked:
            log.info("digest skipped: nothing to show", extra={"user_id": user_id})
            return None
        receipt = await self._transport.send(chat_id, render_digest(ranked, now))
        await self._log.record_digest(user_id, today)
        log.info(
            "digest sent",
            extra={"user_id": user_id, "items": len(ranked), "message_id": receipt.message_id},
        )
        return receipt

    async def send_alerts(self, user_id: str, since: datetime) -> MessageReceipt | None:
        """Alert on openings over the fit threshold or inside the deadline window.

        `since` is the cooldown cutoff: an alert recorded at or after it suppresses the
        same (opening, kind) pair; one recorded before it does not. Only the kinds that
        are due appear in the message and are recorded, so a kind still in cooldown is
        neither repeated nor has its cooldown restarted.
        """
        now = self._clock.now()
        chat_id = await self._users.telegram_chat_id(user_id)
        if chat_id is None:
            log.info("alerts skipped: no telegram chat linked", extra={"user_id": user_id})
            return None
        # Scanned deeper than the digest: a low-fit opening with a deadline tomorrow sits
        # far down a fit-ordered ranking and is exactly what FR-9 must not miss.
        ranked = await self._recommendations.recommendations_for(
            user_id, now=now, limit=self._thresholds.alert_scan_limit
        )
        due: list[Alert] = []
        for recommendation in ranked:
            kinds = await self._due_kinds(user_id, recommendation, now, since)
            if kinds:
                due.append(Alert(recommendation, kinds))
        if not due:
            return None
        receipt = await self._transport.send(chat_id, render_alert(due, now))
        for alert in due:
            for kind in alert.kinds:
                await self._log.record_alert(
                    user_id, alert.recommendation.opening_memory_id, kind, now
                )
        log.info(
            "alert sent",
            extra={"user_id": user_id, "items": len(due), "message_id": receipt.message_id},
        )
        return receipt

    async def _due_kinds(
        self, user_id: str, recommendation: Recommendation, now: datetime, since: datetime
    ) -> tuple[AlertKind, ...]:
        due: list[AlertKind] = []
        for kind in alert_kinds(recommendation, now, self._thresholds):
            last = await self._log.last_alert_at(user_id, recommendation.opening_memory_id, kind)
            if last is None or last < since:
                due.append(kind)
        return tuple(due)
