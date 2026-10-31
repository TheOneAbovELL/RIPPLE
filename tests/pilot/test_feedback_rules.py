"""`record_feedback`, the rules the API and the Telegram buttons share (ADR-0105)."""

import asyncio

import pytest

from ripple.core.models import ChangeEvent, DecisionAction
from ripple.pilot.feedback import (
    FeedbackKindMismatchError,
    FeedbackTargetNotFoundError,
    record_feedback,
)
from ripple.storage.feedback import FeedbackKind, InMemoryFeedbackStore
from tests.builders import USER, change_event, decision, fact, memory
from tests.fakes.clock import FakeClock
from tests.fakes.store import InMemoryStore

OPENING = memory(kind="opening", content="SDE intern at Acme")


def seeded(*events: ChangeEvent) -> InMemoryStore:
    store = InMemoryStore()

    async def seed():
        async with store.transaction() as tx:
            await tx.add_memory(OPENING)
            for event in events:
                await tx.add_change_event(event)

    asyncio.run(seed())
    return store


def record(store: InMemoryStore, target: str, kind: FeedbackKind, user_id: str = USER):
    return asyncio.run(
        record_feedback(
            store,
            InMemoryFeedbackStore(),
            FakeClock(),
            user_id=user_id,
            target_memory_id=target,
            kind=kind,
        )
    )


def test_record_feedback_stores_a_saved_opening_with_the_clock_time():
    row, created = record(seeded(), OPENING.id, FeedbackKind.SAVED)
    assert created
    assert (row.user_id, row.target_memory_id, row.created_at) == (
        USER,
        OPENING.id,
        FakeClock().now(),
    )


def test_record_feedback_hides_another_users_memory():
    with pytest.raises(FeedbackTargetNotFoundError):
        record(seeded(), OPENING.id, FeedbackKind.SAVED, user_id="student-2")


def test_record_feedback_rejects_an_unknown_memory():
    with pytest.raises(FeedbackTargetNotFoundError):
        record(seeded(), "missing", FeedbackKind.SAVED)


def test_record_feedback_rejects_a_question_kind_on_an_opening_nobody_asked_about():
    with pytest.raises(FeedbackKindMismatchError):
        record(seeded(), OPENING.id, FeedbackKind.QUESTION_USEFUL)


def test_record_feedback_accepts_a_question_kind_on_an_asked_memory():
    cgpa = fact("student", "cgpa", 7.6)
    store = seeded(change_event(cgpa, decisions=[decision(OPENING, DecisionAction.ASK)]))
    _, created = record(store, OPENING.id, FeedbackKind.QUESTION_NOT_USEFUL)
    assert created
