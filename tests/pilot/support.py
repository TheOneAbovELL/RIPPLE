"""A constructed pilot week with known answers, for the metrics and report tests.

Week 2026-W45 runs Mon 2026-11-02 00:00 UTC to Mon 2026-11-09 00:00 UTC. Every count
the tests assert is derived by hand in the comments below, not by running the code.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from ripple.core.models import ChangeEvent, DecisionAction, Memory, TriggerKind
from ripple.core.store import MemoryNotFoundError
from ripple.pilot.deliveries import DeliveryRecord
from ripple.pilot.report import PilotSources
from ripple.pilot.weeks import parse_week
from ripple.storage.feedback import Feedback, FeedbackKind, InMemoryFeedbackStore
from tests.builders import change_event, decision, memory

WEEK = parse_week("2026-W45")
MON = WEEK.start
BEFORE = MON - timedelta(hours=1)  # Sunday of W44
AFTER = WEEK.end  # Monday of W46, outside the half-open window
ASHA, BINA, CHETAN, DEV, ESHA = "asha", "bina", "chetan", "dev", "esha"
ACCOUNTS = [ASHA, BINA, CHETAN, DEV, ESHA]  # dev does nothing this week
NOTE_SENTINEL = "NOTE-SENTINEL my real CGPA is 7.2"


def at(days: float) -> datetime:
    return MON + timedelta(days=days)


def digest(user_id: str, day: int) -> DeliveryRecord:
    sent = (MON + timedelta(days=day)).astimezone(UTC)
    return DeliveryRecord(user_id, "digest", sent.date().isoformat(), sent)


def alert(user_id: str, opening: str, when: datetime, kind: str = "high_fit") -> DeliveryRecord:
    return DeliveryRecord(user_id, kind, opening, when)


def fb(
    user_id: str, target: str, kind: FeedbackKind, when: datetime, note: str | None = None
) -> Feedback:
    return Feedback(user_id=user_id, target_memory_id=target, kind=kind, created_at=when, note=note)


# Deliveries in W45: 5 digests (asha 3, bina 2); 5 alerts: asha o1, o2 (high_fit),
# asha o5 (deadline_soon), bina o3 (deadline_soon), bina o1 (high_fit).
# One alert (W44) and one digest (W46) fall outside.
DELIVERIES = [
    digest(ASHA, 0),
    digest(ASHA, 1),
    digest(ASHA, 2),
    digest(BINA, 0),
    digest(BINA, 6),
    alert(ASHA, "o1", at(0.5)),
    alert(ASHA, "o2", at(1.5)),
    alert(ASHA, "o5", at(1.8), kind="deadline_soon"),
    alert(BINA, "o3", at(2.5), kind="deadline_soon"),
    alert(BINA, "o1", at(3.5)),
    alert(ASHA, "o9", BEFORE),  # W44
    DeliveryRecord(CHETAN, "digest", AFTER.date().isoformat(), AFTER),  # W46
]

# o1v2 is the second version of o1 (VERSIONS below): a save on it is a save of o1.
# Recommendation feedback, by alerted pair in W45:
#   asha o1   saved (on o1v2, with a note)               → positive
#   asha o2   saved then dismissed                       → not positive (latest wins)
#   asha o5   dismissed then applied                     → positive (applied counts)
#   bina o3   applied in W44, before this week's alert   → positive (earlier statement)
#   bina o1   saved in W46, after the week               → not positive
#   bina o4   saved, never alerted                       → reaction without alert
# Share: 3 positive of 5 alerted pairs = 0.6.
# Question feedback, first rating per (student, asked memory):
#   chetan q1 not useful (W45), then useful (W45)       → first: not useful, W45
#   chetan q2 useful (W45)                               → useful, W45
#   asha   q3 useful (W45)                               → useful, W45
#   chetan q4 useful (W44), then not useful (W45)        → first rating in W44: excluded
#   chetan q5 useful (W46)                               → excluded
# Usefulness: 2 useful of 3 first rated this week = 0.6667.
FEEDBACK = [
    fb(BINA, "o3", FeedbackKind.APPLIED, BEFORE),
    fb(CHETAN, "q4", FeedbackKind.QUESTION_USEFUL, BEFORE),
    fb(ASHA, "o1v2", FeedbackKind.SAVED, at(0.6), note=NOTE_SENTINEL),
    fb(ASHA, "o2", FeedbackKind.SAVED, at(1.0)),
    fb(CHETAN, "q4", FeedbackKind.QUESTION_NOT_USEFUL, at(1.0)),
    fb(ASHA, "o2", FeedbackKind.DISMISSED, at(1.6)),
    fb(ASHA, "o5", FeedbackKind.DISMISSED, at(2.0)),
    fb(CHETAN, "q1", FeedbackKind.QUESTION_NOT_USEFUL, at(2.0)),
    fb(ASHA, "o5", FeedbackKind.APPLIED, at(2.5)),
    fb(CHETAN, "q1", FeedbackKind.QUESTION_USEFUL, at(3.0)),
    fb(CHETAN, "q2", FeedbackKind.QUESTION_USEFUL, at(3.1)),
    fb(BINA, "o4", FeedbackKind.SAVED, at(4.0)),
    fb(ASHA, "q3", FeedbackKind.QUESTION_USEFUL, at(5.0)),
    fb(BINA, "o1", FeedbackKind.SAVED, AFTER),
    fb(CHETAN, "q5", FeedbackKind.QUESTION_USEFUL, AFTER),
]
EXPECTED_SHARE = (3, 5, 0.6)
EXPECTED_USEFULNESS = (2, 3, 0.6667)
EXPECTED_REACTIONS_WITHOUT_ALERT = 1  # bina o4
# Rows created in W45 by kind: saved asha o1v2, asha o2, bina o4; applied asha o5;
# dismissed asha o2, asha o5; useful chetan q1, chetan q2, asha q3; not useful
# chetan q4, chetan q1.
EXPECTED_FEEDBACK_COUNTS = {
    "saved": 3,
    "applied": 1,
    "dismissed": 2,
    "question_useful": 3,
    "question_not_useful": 2,
}

# Asks in W45: chetan's event asks q1 and q2, asha's asks q3; the keep decision is not
# a question and bina's Sunday ask is in W44 → 3. Esha only answered a question
# (a user_answer event, no decisions): active, but nothing else.
EVENTS: dict[str, list[ChangeEvent]] = {
    CHETAN: [
        change_event(
            "cgpa",
            user_id=CHETAN,
            at=at(1.9),
            decisions=[
                decision("q1", DecisionAction.ASK),
                decision("q2", DecisionAction.ASK),
                decision("e1", DecisionAction.KEEP),
            ],
        )
    ],
    ASHA: [
        change_event(
            "batch", user_id=ASHA, at=at(4.9), decisions=[decision("q3", DecisionAction.ASK)]
        )
    ],
    BINA: [
        change_event(
            "skill", user_id=BINA, at=BEFORE, decisions=[decision("q5", DecisionAction.ASK)]
        )
    ],
    ESHA: [change_event("q9", user_id=ESHA, at=at(3.0), trigger_kind=TriggerKind.USER_ANSWER)],
}
EXPECTED_ASKED = 3
# Active in W45: asha, bina (deliveries), chetan (feedback), esha (answer) = 4 of 5
# accounts, below MIN_PUBLISHABLE_COHORT.
EXPECTED_ACTIVE = 4

O1 = memory(id="o1", kind="opening", content="SDE intern at Acme")
VERSIONS: dict[str, list[Memory]] = {
    "o1": [
        O1,
        memory(id="o1v2", kind="opening", content="SDE intern", version=2, supersedes_id="o1"),
    ]
}
VERSIONS["o1v2"] = VERSIONS["o1"]
CANONICAL = {"o1": "o1", "o1v2": "o1"}


@dataclass
class StaticDeliveries:
    records: Sequence[DeliveryRecord]

    async def deliveries_between(self, start: datetime, end: datetime) -> list[DeliveryRecord]:
        return sorted(
            (r for r in self.records if start <= r.sent_at < end), key=lambda r: r.sent_at
        )


@dataclass
class StaticHistory:
    events: dict[str, list[ChangeEvent]] = field(default_factory=dict)
    versions: dict[str, list[Memory]] = field(default_factory=dict)

    async def change_events_for_user(self, user_id: str) -> list[ChangeEvent]:
        return list(self.events.get(user_id, []))

    async def version_chain(self, memory_id: str) -> list[Memory]:
        if memory_id not in self.versions:
            raise MemoryNotFoundError(memory_id)
        return list(self.versions[memory_id])


async def constructed_sources(extra_active: int = 0) -> PilotSources:
    """The week above; `extra_active` adds that many accounts with one digest each."""
    store = InMemoryFeedbackStore()
    for row in FEEDBACK:
        await store.record(row)
    extra = [f"extra-{i}" for i in range(extra_active)]
    return PilotSources(
        account_ids=ACCOUNTS + extra,
        history=StaticHistory(EVENTS, VERSIONS),
        deliveries=StaticDeliveries(DELIVERIES + [digest(user_id, 3) for user_id in extra]),
        feedback=store,
        description="constructed test week (tests/pilot/support.py)",
    )
