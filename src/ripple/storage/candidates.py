"""Resume candidates: extracted profile facts awaiting the user's decision (ADR-0024,
ADR-0043, I5).

A candidate is not a memory. It is held here, outside the memory store, until the
user confirms it (then Intake writes the memory and the candidate records which one)
or rejects it (then it stays as a record of what was declined). The in-memory
implementation lives in tests/api/fakes.py; the conversion from the parsers'
CandidateFact lives in ripple.api.candidates, because storage imports only core.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol

import sqlalchemy as sa
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncEngine

from ripple.core.errors import RippleError
from ripple.core.ids import new_id
from ripple.storage import users_tables as t


class CandidateStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class CandidateAlreadyDecidedError(RippleError):
    """A conditional replace found the candidate in another status than expected: a
    concurrent confirm or reject got there first (ADR-0043, atomic confirm)."""

    def __init__(self, candidate_id: str, actual: "CandidateStatus") -> None:
        self.candidate_id = candidate_id
        self.actual = actual
        super().__init__(f"candidate {candidate_id!r} is already {actual.value}")


class ResumeCandidate(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=new_id)
    user_id: str = Field(min_length=1)
    upload_id: str = Field(min_length=1)
    attribute: str = Field(min_length=1)
    value: str | int | float | bool
    span_start: int = Field(ge=0)
    span_end: int = Field(ge=0)
    span_text: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    content: str
    status: CandidateStatus = CandidateStatus.PENDING
    created_at: datetime
    decided_at: datetime | None = None
    memory_id: str | None = None

    def model_post_init(self, _context: Any) -> None:
        for name in ("created_at", "decided_at"):
            value = getattr(self, name)
            if value is not None and value.tzinfo is None:
                raise ValueError(f"{name} must be timezone-aware")


class CandidateStore(Protocol):
    async def add_candidates(self, candidates: list[ResumeCandidate]) -> None: ...

    async def get_candidate(self, candidate_id: str) -> ResumeCandidate | None: ...

    async def candidates_for_user(
        self, user_id: str, status: CandidateStatus | None = None
    ) -> list[ResumeCandidate]:
        """Oldest first, then by id, so a list is stable across calls."""
        ...

    async def replace_candidate(
        self, candidate: ResumeCandidate, *, expected_status: CandidateStatus | None = None
    ) -> None:
        """Overwrite the row. With `expected_status`, only if the stored row still has
        that status; otherwise raise CandidateAlreadyDecidedError and change nothing.
        The check and the write are one atomic step, so two confirms cannot both win."""
        ...

    async def delete_for_user(self, user_id: str) -> None: ...


# ---- Postgres -----------------------------------------------------------------------


def _row(candidate: ResumeCandidate) -> dict[str, Any]:
    row = candidate.model_dump(mode="json")
    row["created_at"] = candidate.created_at
    row["decided_at"] = candidate.decided_at
    return row


def _candidate(row: sa.Row[Any]) -> ResumeCandidate:
    return ResumeCandidate.model_validate(dict(row._mapping))


class PostgresCandidateStore:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def add_candidates(self, candidates: list[ResumeCandidate]) -> None:
        if not candidates:
            return
        async with self._engine.begin() as conn:
            await conn.execute(sa.insert(t.resume_candidates), [_row(c) for c in candidates])

    async def get_candidate(self, candidate_id: str) -> ResumeCandidate | None:
        async with self._engine.connect() as conn:
            row = (
                await conn.execute(
                    sa.select(t.resume_candidates).where(t.resume_candidates.c.id == candidate_id)
                )
            ).first()
        return None if row is None else _candidate(row)

    async def candidates_for_user(
        self, user_id: str, status: CandidateStatus | None = None
    ) -> list[ResumeCandidate]:
        stmt = (
            sa.select(t.resume_candidates)
            .where(t.resume_candidates.c.user_id == user_id)
            .order_by(t.resume_candidates.c.created_at, t.resume_candidates.c.id)
        )
        if status is not None:
            stmt = stmt.where(t.resume_candidates.c.status == status.value)
        async with self._engine.connect() as conn:
            rows = (await conn.execute(stmt)).all()
        return [_candidate(row) for row in rows]

    async def replace_candidate(
        self, candidate: ResumeCandidate, *, expected_status: CandidateStatus | None = None
    ) -> None:
        row = _row(candidate)
        row.pop("id")
        stmt = (
            sa.update(t.resume_candidates)
            .where(t.resume_candidates.c.id == candidate.id)
            .values(**row)
        )
        if expected_status is not None:
            # The WHERE makes the compare-and-set one statement: a concurrent confirm that
            # committed first leaves rowcount 0 here instead of being overwritten.
            stmt = stmt.where(t.resume_candidates.c.status == expected_status.value)
        async with self._engine.begin() as conn:
            result = await conn.execute(stmt)
            if expected_status is None or result.rowcount != 0:
                return
            current = (
                await conn.execute(
                    sa.select(t.resume_candidates.c.status).where(
                        t.resume_candidates.c.id == candidate.id
                    )
                )
            ).scalar_one_or_none()
        if current is not None:
            raise CandidateAlreadyDecidedError(candidate.id, CandidateStatus(current))

    async def delete_for_user(self, user_id: str) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(
                sa.delete(t.resume_candidates).where(t.resume_candidates.c.user_id == user_id)
            )
