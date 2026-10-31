"""Plain-text rendering of digests and alerts (FR-9, ADR-0055).

Every number in the text comes from the Recommendation or from the injected `now`:
fit as the source's score, hours left as deadline minus now. Nothing is estimated or
rounded up (I5 applies to the agent; the renderer holds itself to the same rule). A
flagged recommendation is built on a SUSPECT or PENDING_USER memory (I1) and is marked
"unconfirmed" so the user does not act on a belief the system itself doubts.

Precondition: `Recommendation.deadline` and `now` are timezone-aware (the jobs
vocabulary stores deadlines as ISO strings with a zone); a naive deadline raises
TypeError in the subtraction rather than silently shifting hours.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from ripple.domains.jobs.vocabulary import Recommendation
from ripple.notify.contracts import AlertKind, Thresholds

UNCONFIRMED = "unconfirmed"
NO_DEADLINE = "not stated"
DIGEST_MAX_LENGTH = 4096  # Telegram's per-message limit; the renderer stays under it


@dataclass(frozen=True)
class Alert:
    """One opening and the kinds it is being alerted for right now."""

    recommendation: Recommendation
    kinds: tuple[AlertKind, ...]


def hours_left(recommendation: Recommendation, now: datetime) -> float | None:
    """Hours between now and the deadline, negative once it has passed."""
    if recommendation.deadline is None:
        return None
    return (recommendation.deadline - now).total_seconds() / 3600.0


def alert_kinds(
    recommendation: Recommendation, now: datetime, thresholds: Thresholds
) -> tuple[AlertKind, ...]:
    """Why this opening deserves an alert right now; empty when it does not.

    Only eligible, confirmed openings alert: an alert is a push to act, and pushing on
    an ineligible or doubted belief is the failure mode FR-9 exists to avoid.
    """
    if not recommendation.eligible or recommendation.flagged:
        return ()
    kinds: list[AlertKind] = []
    if recommendation.fit_score >= thresholds.fit_alert:
        kinds.append(AlertKind.HIGH_FIT)
    left = hours_left(recommendation, now)
    window_hours = thresholds.deadline_window.total_seconds() / 3600.0
    if left is not None and 0 < left <= window_hours:
        kinds.append(AlertKind.DEADLINE_SOON)
    return tuple(kinds)


def alerts_for(
    recommendations: Sequence[Recommendation], now: datetime, thresholds: Thresholds
) -> list[Alert]:
    """The openings in the batch that qualify, with their kinds, in ranking order."""
    alerts: list[Alert] = []
    for recommendation in recommendations:
        kinds = alert_kinds(recommendation, now, thresholds)
        if kinds:
            alerts.append(Alert(recommendation, kinds))
    return alerts


def render_digest(
    recommendations: Sequence[Recommendation],
    now: datetime,
    *,
    max_length: int = DIGEST_MAX_LENGTH,
) -> str:
    """The day's digest; trailing items are dropped, never truncated mid-item, to fit.

    The closing line counts what was left out so the user knows the list is cut, but
    the omitted openings are not described (nothing is summarised or invented).
    """
    header = f"Ripple digest for {now.date().isoformat()}"
    if not recommendations:
        return f"{header}\n\nNo openings to show today."
    items = [
        _render_item(index, recommendation, now)
        for index, recommendation in enumerate(recommendations, start=1)
    ]
    shown = len(items)
    while shown > 0:
        text = "\n\n".join([header, *items[:shown]])
        omitted = len(items) - shown
        if omitted:
            text += f"\n\n{omitted} more not shown (message limit)."
        if len(text) <= max_length:
            return text
        shown -= 1
    return header


def render_alert(alerts: Sequence[Alert], now: datetime) -> str:
    """One message for the batch (ADR-0025: alerts batched); empty when there is none."""
    if not alerts:
        return ""
    items = [
        _render_item(index, alert.recommendation, now)
        + "\n   Why now: "
        + "; ".join(_alert_reason(kind, alert.recommendation, now) for kind in alert.kinds)
        for index, alert in enumerate(alerts, start=1)
    ]
    return "\n\n".join(["Ripple alert", *items])


def _render_item(index: int, recommendation: Recommendation, now: datetime) -> str:
    title = f"{index}. {recommendation.title} at {recommendation.company}"
    if recommendation.flagged:
        title += f" [{UNCONFIRMED}]"
    eligible = "yes" if recommendation.eligible else "no"
    lines = [title, f"   Eligible: {eligible}", f"   Fit: {_percent(recommendation.fit_score)}"]
    lines.extend(f"   - {reason}" for reason in recommendation.fit_reasons)
    lines.append(f"   Deadline: {_deadline(recommendation, now)}")
    return "\n".join(lines)


def _alert_reason(kind: AlertKind, recommendation: Recommendation, now: datetime) -> str:
    if kind is AlertKind.HIGH_FIT:
        return f"high fit ({_percent(recommendation.fit_score)})"
    left = hours_left(recommendation, now)
    return f"deadline in {_hours(left)}" if left is not None else "deadline soon"


def _deadline(recommendation: Recommendation, now: datetime) -> str:
    if recommendation.deadline is None:
        return NO_DEADLINE
    left = hours_left(recommendation, now)
    stamp = recommendation.deadline.strftime("%Y-%m-%d %H:%M %Z")
    if left is None or left <= 0:
        return f"{stamp} (passed)"
    return f"{stamp} ({_hours(left)} left)"


def _hours(hours: float | None) -> str:
    # Floor, never round up: "2h" must not be claimed when 1h50 is left.
    return f"{math.floor(hours) if hours is not None else 0}h"


def _percent(score: float) -> str:
    # Round away binary noise first (0.57 * 100 is 56.999…), then floor.
    return f"{math.floor(round(score * 100, 6))}%"
