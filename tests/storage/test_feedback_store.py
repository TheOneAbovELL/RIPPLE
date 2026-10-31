"""Pilot feedback store contract (ADR-0105).

FeedbackStoreContract runs here against the in-memory store and, under the slow marker,
in tests/storage/test_feedback_postgres.py against Postgres.
"""

import asyncio
from datetime import timedelta

import pytest
from pydantic import ValidationError

from ripple.storage.feedback import (
    Feedback,
    FeedbackKind,
    FeedbackStore,
    InMemoryFeedbackStore,
)
from ripple.storage.feedback_tables import NOTE_MAX_CHARS
from tests.fakes.clock import DEFAULT_START

# Memory ids the contract's rows point at. In Postgres target_memory_id is a foreign key
# to memories, so the Postgres subclass creates memories with these ids first.
TARGETS = (
    "00000000-0000-4000-8000-000000000000",
    "00000000-0000-4000-8000-000000000001",
    "00000000-0000-4000-8000-000000000002",
)


def feedback(
    user_id: str,
    target: str = TARGETS[1],
    kind: FeedbackKind = FeedbackKind.SAVED,
    *,
    hours: float = 0,
    note: str | None = None,
) -> Feedback:
    return Feedback(
        user_id=user_id,
        target_memory_id=target,
        kind=kind,
        note=note,
        created_at=DEFAULT_START + timedelta(hours=hours),
    )


class FeedbackStoreContract:
    """Subclass with a `feedback_store` fixture and an `owner` fixture (a user id)."""

    @pytest.fixture
    def owner(self) -> str:
        return "student-1"

    @pytest.fixture
    def other(self) -> str:
        return "student-2"

    def test_feedback_store_round_trip_when_new(self, feedback_store: FeedbackStore, owner: str):
        row = feedback(owner, note="looks right for me")
        stored, created = asyncio.run(feedback_store.record(row))
        assert (stored, created) == (row, True)
        assert asyncio.run(feedback_store.feedback_for_user(owner)) == [row]

    def test_feedback_store_record_returns_existing_row_when_repeated(
        self, feedback_store: FeedbackStore, owner: str
    ):
        first = feedback(owner, note="first")
        asyncio.run(feedback_store.record(first))
        stored, created = asyncio.run(feedback_store.record(feedback(owner, hours=1, note="2nd")))
        assert (stored, created) == (first, False)
        assert asyncio.run(feedback_store.feedback_for_user(owner)) == [first]

    def test_feedback_store_keeps_each_kind_for_one_target(
        self, feedback_store: FeedbackStore, owner: str
    ):
        asyncio.run(feedback_store.record(feedback(owner, kind=FeedbackKind.SAVED)))
        asyncio.run(feedback_store.record(feedback(owner, kind=FeedbackKind.APPLIED, hours=1)))
        kinds = [f.kind for f in asyncio.run(feedback_store.feedback_for_user(owner))]
        assert kinds == [FeedbackKind.SAVED, FeedbackKind.APPLIED]

    def test_feedback_store_for_user_is_oldest_first_and_scoped(
        self, feedback_store: FeedbackStore, owner: str, other: str
    ):
        newer = feedback(owner, TARGETS[2], hours=2)
        older = feedback(owner, TARGETS[1])
        for row in (newer, older, feedback(other)):
            asyncio.run(feedback_store.record(row))
        assert asyncio.run(feedback_store.feedback_for_user(owner)) == [older, newer]

    def test_feedback_store_between_is_half_open_and_spans_users(
        self, feedback_store: FeedbackStore, owner: str, other: str
    ):
        before = feedback(owner, TARGETS[0], hours=-1)
        at_start = feedback(owner, TARGETS[1])
        others = feedback(other, TARGETS[1], hours=1)
        at_end = feedback(owner, TARGETS[2], hours=2)
        for row in (before, at_start, others, at_end):
            asyncio.run(feedback_store.record(row))
        start, end = DEFAULT_START, DEFAULT_START + timedelta(hours=2)
        assert asyncio.run(feedback_store.feedback_between(start, end)) == [at_start, others]

    def test_feedback_store_delete_for_user_removes_only_theirs_and_is_idempotent(
        self, feedback_store: FeedbackStore, owner: str, other: str
    ):
        asyncio.run(feedback_store.record(feedback(owner)))
        kept = feedback(other)
        asyncio.run(feedback_store.record(kept))
        asyncio.run(feedback_store.delete_for_user(owner))
        asyncio.run(feedback_store.delete_for_user(owner))
        assert asyncio.run(feedback_store.feedback_for_user(owner)) == []
        assert asyncio.run(feedback_store.feedback_for_user(other)) == [kept]


class TestInMemoryFeedbackStore(FeedbackStoreContract):
    @pytest.fixture
    def feedback_store(self) -> FeedbackStore:
        return InMemoryFeedbackStore()


def test_feedback_rejects_naive_timestamp():
    with pytest.raises(ValidationError):
        Feedback(
            user_id="u",
            target_memory_id="m",
            kind=FeedbackKind.SAVED,
            created_at=DEFAULT_START.replace(tzinfo=None),
        )


def test_feedback_rejects_note_over_the_column_limit():
    with pytest.raises(ValidationError):
        feedback("u", note="x" * (NOTE_MAX_CHARS + 1))


def test_feedback_rejects_unknown_kind():
    with pytest.raises(ValidationError):
        Feedback.model_validate(
            {"user_id": "u", "target_memory_id": "m", "kind": "liked", "created_at": DEFAULT_START}
        )
