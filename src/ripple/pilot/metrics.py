"""The docs/04 pilot metrics for one week, from rows already read (ADR-0106).

Pure: no I/O, no clock. Every rate keeps its numerator and denominator next to it so a
reader can recompute it from metrics.json (I8). A metric the data cannot support is
reported as TBD with the reason, never estimated:

- saved or applied share of recommendations — computed over the (student, opening)
  pairs alerted this week: the share the student has saved or applied to by the end of
  the week, whenever they said so. "Applied" counts once said; "saved" counts unless a
  later "dismissed" replaced it. Openings are compared by their first version, so an
  alert on one version and a save on the next are one pair. Known biases, repeated in
  every output: digests record no items (ADR-0095), so digest-only openings are not in
  the denominator; reactions to openings that were not alerted this week (dashboard,
  digest, self-pasted) are counted apart, not in the share.
- question usefulness — computed: of the asked memories first rated this week, the
  share rated useful. First rating, because the feedback store keeps the first
  statement of each kind (ADR-0105) and a later tap may be invisible.
- days earlier than self-discovery, stale recommendation rate, self-reported trust —
  TBD (pending data); docs/pilot/metrics.md says what each needs.
"""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from ripple.core.models import ChangeEvent, DecisionAction, TriggerKind
from ripple.pilot.deliveries import DeliveryRecord
from ripple.pilot.weeks import Week
from ripple.storage.feedback import (
    QUESTION_KINDS,
    RECOMMENDATION_KINDS,
    Feedback,
    FeedbackKind,
)

TBD = "TBD (pending data)"
# Below this many active students an aggregate can single one out; such a week is
# written under results/pilot/raw/ (gitignored) and marked not for publication. A
# policy choice (consent: "no student is identifiable"), not a measurement.
MIN_PUBLISHABLE_COHORT = 5

SHARE_DEFINITION = (
    "(student, opening) pairs alerted this week that the student had saved or applied "
    "to by the week's end / pairs alerted this week; openings compared by first version; "
    "digest-only openings are not counted (digests record no items)"
)
USEFULNESS_DEFINITION = (
    "asked memories whose first rating falls in this week and is useful / asked "
    "memories first rated this week"
)
NEEDS_SELF_DISCOVERY_DATE = (
    "needs each student's own discovery date per opening (weekly survey item S1, "
    "docs/pilot/metrics.md); the product does not record it"
)
NEEDS_BELIEF_SNAPSHOT = (
    "needs the beliefs each delivered recommendation rested on at send time; the "
    "delivery log keeps only (user, kind, opening id, time) and digests record no "
    "items (docs/pilot/metrics.md)"
)
NEEDS_TRUST_SURVEY = (
    "needs the weekly self-report survey (item S2, docs/pilot/metrics.md); the product "
    "does not collect it"
)

# ChangeEvents a student's own action starts; a ripple may also come from the Scout.
_STUDENT_TRIGGERS = frozenset({TriggerKind.USER_EDIT, TriggerKind.USER_ANSWER})


@dataclass(frozen=True)
class Rate:
    numerator: int
    denominator: int

    def as_json(self, definition: str, empty_reason: str) -> dict[str, Any]:
        if self.denominator == 0:
            return {"value": TBD, "reason": empty_reason, "definition": definition}
        return {
            "value": round(self.numerator / self.denominator, 4),
            "numerator": self.numerator,
            "denominator": self.denominator,
            "definition": definition,
        }


def pending(reason: str) -> dict[str, Any]:
    return {"value": TBD, "reason": reason}


def _ordered(feedback: Iterable[Feedback]) -> list[Feedback]:
    return sorted(feedback, key=lambda f: (f.created_at, f.id))


def _opening(canonical: Mapping[str, str], memory_id: str) -> str:
    return canonical.get(memory_id, memory_id)


def alerted_pairs(
    week: Week, deliveries: Iterable[DeliveryRecord], canonical: Mapping[str, str]
) -> set[tuple[str, str]]:
    return {
        (d.user_id, _opening(canonical, d.key))
        for d in deliveries
        if not d.is_digest and week.contains(d.sent_at)
    }


def positive_pairs(
    week: Week, feedback: Iterable[Feedback], canonical: Mapping[str, str]
) -> set[tuple[str, str]]:
    """Pairs saved or applied to by the end of the week, by the rule in the docstring."""
    applied: set[tuple[str, str]] = set()
    latest_save_or_dismiss: dict[tuple[str, str], FeedbackKind] = {}
    for row in _ordered(feedback):
        if row.created_at >= week.end or row.kind not in RECOMMENDATION_KINDS:
            continue
        pair = (row.user_id, _opening(canonical, row.target_memory_id))
        if row.kind is FeedbackKind.APPLIED:
            applied.add(pair)
        else:
            latest_save_or_dismiss[pair] = row.kind
    saved = {p for p, kind in latest_save_or_dismiss.items() if kind is FeedbackKind.SAVED}
    return applied | saved


def saved_or_applied_share(
    week: Week,
    deliveries: Iterable[DeliveryRecord],
    feedback: Iterable[Feedback],
    canonical: Mapping[str, str],
) -> Rate:
    alerted = alerted_pairs(week, deliveries, canonical)
    positive = positive_pairs(week, feedback, canonical)
    return Rate(numerator=len(alerted & positive), denominator=len(alerted))


def reactions_without_alert(
    week: Week,
    deliveries: Iterable[DeliveryRecord],
    feedback: Iterable[Feedback],
    canonical: Mapping[str, str],
) -> int:
    reacted = {
        (f.user_id, _opening(canonical, f.target_memory_id))
        for f in feedback
        if f.kind in RECOMMENDATION_KINDS and week.contains(f.created_at)
    }
    return len(reacted - alerted_pairs(week, deliveries, canonical))


def question_usefulness(week: Week, feedback: Iterable[Feedback]) -> Rate:
    first: dict[tuple[str, str], Feedback] = {}
    for row in _ordered(feedback):
        if row.kind in QUESTION_KINDS:
            first.setdefault((row.user_id, row.target_memory_id), row)
    rated = [row for row in first.values() if week.contains(row.created_at)]
    useful = sum(1 for row in rated if row.kind is FeedbackKind.QUESTION_USEFUL)
    return Rate(numerator=useful, denominator=len(rated))


def questions_asked(week: Week, events: Iterable[ChangeEvent]) -> int:
    return len(
        {
            (event.id, d.memory_id)
            for event in events
            if week.contains(event.created_at)
            for d in event.decisions
            if d.action is DecisionAction.ASK
        }
    )


def week_metrics(
    week: Week,
    account_ids: Sequence[str],
    deliveries: Sequence[DeliveryRecord],
    feedback: Sequence[Feedback],
    events: Sequence[ChangeEvent],
    canonical: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """metrics.json's body.

    `feedback` must hold every row up to the week's end (earlier weeks too: a save
    before an alert counts); deliveries and events outside the week are ignored.
    `canonical` maps a memory id to its first version's id; ids not in it stand alone.
    """
    canonical = canonical or {}
    in_week_deliveries = [d for d in deliveries if week.contains(d.sent_at)]
    in_week_feedback = [f for f in feedback if week.contains(f.created_at)]
    active = (
        {d.user_id for d in in_week_deliveries}
        | {f.user_id for f in in_week_feedback}
        | {
            e.user_id
            for e in events
            if e.trigger_kind in _STUDENT_TRIGGERS and week.contains(e.created_at)
        }
    )
    alerts: dict[str, int] = {}
    for d in in_week_deliveries:
        if not d.is_digest:
            alerts[d.kind] = alerts.get(d.kind, 0) + 1
    return {
        "week": week.label,
        "window": {"start": week.start.isoformat(), "end": week.end.isoformat(), "tz": "UTC"},
        "cohort": {
            "accounts": len(set(account_ids)),
            "active_users": len(active),
            "publishable": len(active) >= MIN_PUBLISHABLE_COHORT,
            "min_publishable_cohort": MIN_PUBLISHABLE_COHORT,
        },
        "activity": {
            "digests_sent": sum(1 for d in in_week_deliveries if d.is_digest),
            "alerts_sent": dict(sorted(alerts.items())),
            "feedback": {
                kind.value: sum(1 for f in in_week_feedback if f.kind is kind)
                for kind in FeedbackKind
            },
            "recommendation_reactions_without_alert": reactions_without_alert(
                week, deliveries, feedback, canonical
            ),
            "questions_asked": questions_asked(week, events),
        },
        "pilot_metrics": {
            "saved_or_applied_share": saved_or_applied_share(
                week, deliveries, feedback, canonical
            ).as_json(SHARE_DEFINITION, "no recommendation was alerted this week"),
            "days_earlier_than_self_discovery": pending(NEEDS_SELF_DISCOVERY_DATE),
            "stale_recommendation_rate": pending(NEEDS_BELIEF_SNAPSHOT),
            "question_usefulness": question_usefulness(week, feedback).as_json(
                USEFULNESS_DEFINITION, "no question was first rated this week"
            ),
            "self_reported_trust": pending(NEEDS_TRUST_SURVEY),
        },
    }
