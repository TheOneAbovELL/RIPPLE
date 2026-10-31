"""Pilot feedback: what a student said about a recommendation or a question (ADR-0105).

Feedback is the student's statement, nothing more. "applied" records that the student
says they applied; nothing is applied anywhere (I6). The rows feed the weekly pilot
report (`ripple.pilot.report`, docs/04 "Pilot metrics") and are erased with the
account (FR-15).

`record` is first-statement-wins per (user, target, kind): a double-tapped Telegram
button or a retried request returns the row that already exists, so the report never
counts one tap twice. A student who changes their mind records another kind.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol

import sqlalchemy as sa
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncEngine

from ripple.core.errors import RippleError
from ripple.core.ids import new_id
from ripple.storage import feedback_tables as t
from ripple.storage.feedback_tables import NOTE_MAX_CHARS


class FeedbackKind(StrEnum):
    SAVED = "saved"
    APPLIED = "applied"
    DISMISSED = "dismissed"
    QUESTION_USEFUL = "question_useful"
    QUESTION_NOT_USEFUL = "question_not_useful"


# What each kind is about: an opening that was recommended, or a memory the resolver
# asked the student about (FR-7). The API checks the target against this split.
RECOMMENDATION_KINDS = frozenset({FeedbackKind.SAVED, FeedbackKind.APPLIED, FeedbackKind.DISMISSED})
QUESTION_KINDS = frozenset({FeedbackKind.QUESTION_USEFUL, FeedbackKind.QUESTION_NOT_USEFUL})


class Feedback(BaseModel):
    # Serialized output always carries every field, as for Memory, so the dashboard's
    # generated client sees them as required.
    model_config = ConfigDict(frozen=True, json_schema_serialization_defaults_required=True)

    id: str = Field(default_factory=new_id)
    user_id: str = Field(min_length=1)
    target_memory_id: str = Field(min_length=1, max_length=36)  # a memory id (uuid4)
    kind: FeedbackKind
    note: str | None = Field(default=None, max_length=NOTE_MAX_CHARS)
    created_at: datetime

    def model_post_init(self, _context: Any) -> None:
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")


class FeedbackStore(Protocol):
    async def record(self, feedback: Feedback) -> tuple[Feedback, bool]:
        """Store the row unless (user, target, kind) exists. Returns the stored row
        and whether this call created it."""
        ...

    async def feedback_for_user(self, user_id: str) -> list[Feedback]:
        """Oldest first, then by id."""
        ...

    async def feedback_between(self, start: datetime, end: datetime) -> list[Feedback]:
        """Every user's rows with start <= created_at < end, oldest first, then by id."""
        ...

    async def delete_for_user(self, user_id: str) -> None: ...


class FeedbackRecordRaceError(RippleError):
    """The row the insert conflicted with was deleted before it could be read (a
    concurrent DELETE /me or forget). Nothing was stored; the caller may retry."""


def _order(rows: list[Feedback]) -> list[Feedback]:
    return sorted(rows, key=lambda f: (f.created_at, f.id))


class InMemoryFeedbackStore:
    """Per-process store for tests and development; the Postgres one is the product's."""

    def __init__(self) -> None:
        self.rows: dict[tuple[str, str, FeedbackKind], Feedback] = {}

    async def record(self, feedback: Feedback) -> tuple[Feedback, bool]:
        key = (feedback.user_id, feedback.target_memory_id, feedback.kind)
        existing = self.rows.get(key)
        if existing is not None:
            return existing, False
        self.rows[key] = feedback
        return feedback, True

    async def feedback_for_user(self, user_id: str) -> list[Feedback]:
        return _order([f for f in self.rows.values() if f.user_id == user_id])

    async def feedback_between(self, start: datetime, end: datetime) -> list[Feedback]:
        return _order([f for f in self.rows.values() if start <= f.created_at < end])

    async def delete_for_user(self, user_id: str) -> None:
        self.rows = {k: v for k, v in self.rows.items() if v.user_id != user_id}


class PostgresFeedbackStore:
    """One short transaction per call, like the other Postgres stores (ADR-0016)."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def record(self, feedback: Feedback) -> tuple[Feedback, bool]:
        table = t.pilot_feedback
        # The unique key decides, not a prior read: two racing taps both reach the
        # insert and exactly one of them creates the row.
        insert = (
            pg_insert(table)
            .values(**feedback.model_dump())
            .on_conflict_do_nothing(constraint="uq_pilot_feedback_user_target_kind")
            .returning(table.c.id)
        )
        existing = sa.select(table).where(
            table.c.user_id == feedback.user_id,
            table.c.target_memory_id == feedback.target_memory_id,
            table.c.kind == feedback.kind.value,
        )
        async with self._engine.begin() as conn:
            created = (await conn.execute(insert)).first() is not None
            if created:
                return feedback, True
            row = (await conn.execute(existing)).one_or_none()
        if row is None:
            raise FeedbackRecordRaceError(feedback.target_memory_id)
        return Feedback.model_validate(dict(row._mapping)), False

    async def feedback_for_user(self, user_id: str) -> list[Feedback]:
        table = t.pilot_feedback
        stmt = (
            sa.select(table)
            .where(table.c.user_id == user_id)
            .order_by(table.c.created_at, table.c.id)
        )
        return await self._rows(stmt)

    async def feedback_between(self, start: datetime, end: datetime) -> list[Feedback]:
        table = t.pilot_feedback
        stmt = (
            sa.select(table)
            .where(table.c.created_at >= start, table.c.created_at < end)
            .order_by(table.c.created_at, table.c.id)
        )
        return await self._rows(stmt)

    async def delete_for_user(self, user_id: str) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(
                sa.delete(t.pilot_feedback).where(t.pilot_feedback.c.user_id == user_id)
            )

    async def _rows(self, stmt: sa.Select[Any]) -> list[Feedback]:
        async with self._engine.connect() as conn:
            rows = (await conn.execute(stmt)).all()
        return [Feedback.model_validate(dict(row._mapping)) for row in rows]
