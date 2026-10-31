"""Resume uploads: the text layer a parser read, kept so span references resolve
(ADR-0097, FR-12).

A confirmed resume fact carries `source_ref = "resume:<upload id>#<start>-<end>"`
(WS-2's candidate_to_statement). Without the text those offsets point at nothing; with
it the inspector can quote the exact line the belief rests on. `parse_resume_ref` and
`quote` are pure so the API and tests share one reading of the format.
"""

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

import sqlalchemy as sa
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncEngine

from ripple.core.ids import new_id
from ripple.storage import uploads_tables as t

RESUME_REF_PREFIX = "resume:"
MAX_RESUME_TEXT_CHARS = 200_000  # a 10-page resume is ~30k; anything near this is not one
_REF = re.compile(r"^resume:(?P<upload_id>[^#\s]+)(?:#(?P<start>\d+)-(?P<end>\d+))?$")


class ResumeUpload(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=new_id)
    user_id: str = Field(min_length=1)
    filename: str = Field(min_length=1, max_length=255)
    sha256: str = Field(min_length=64, max_length=64)
    text: str = Field(max_length=MAX_RESUME_TEXT_CHARS)
    uploaded_at: datetime

    def model_post_init(self, _context: Any) -> None:
        if self.uploaded_at.tzinfo is None:
            raise ValueError("uploaded_at must be timezone-aware")


def sha256_of(pdf: bytes) -> str:
    return hashlib.sha256(pdf).hexdigest()


def resume_source_ref(upload_id: str) -> str:
    return f"{RESUME_REF_PREFIX}{upload_id}"


@dataclass(frozen=True)
class ResumeRef:
    upload_id: str
    start: int | None = None
    end: int | None = None


def parse_resume_ref(source_ref: str | None) -> ResumeRef | None:
    """`resume:<id>` or `resume:<id>#<start>-<end>`; None for anything else."""
    if source_ref is None:
        return None
    match = _REF.match(source_ref)
    if match is None:
        return None
    start, end = match.group("start"), match.group("end")
    if start is None or end is None:
        return ResumeRef(upload_id=match.group("upload_id"))
    if int(start) > int(end):
        return None
    return ResumeRef(upload_id=match.group("upload_id"), start=int(start), end=int(end))


@dataclass(frozen=True)
class Quote:
    start: int
    end: int
    text: str  # exactly text[start:end]
    line: str  # the whole line(s) the span sits on, for display


def quote(text: str, start: int, end: int) -> Quote | None:
    """The span and its surrounding line; None when the span is outside the text."""
    if start < 0 or end > len(text) or start > end:
        return None
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", max(end, line_start))
    if line_end == -1:
        line_end = len(text)
    return Quote(start=start, end=end, text=text[start:end], line=text[line_start:line_end])


class UploadStore(Protocol):
    async def add_upload(self, upload: ResumeUpload) -> None: ...

    async def get_upload(self, upload_id: str) -> ResumeUpload | None: ...

    async def uploads_for_user(self, user_id: str) -> list[ResumeUpload]:
        """Oldest first, then by id."""
        ...

    async def delete_for_user(self, user_id: str) -> None: ...


class InMemoryUploadStore:
    """Per-process store for tests and development; the Postgres one is the product's."""

    def __init__(self) -> None:
        self.uploads: dict[str, ResumeUpload] = {}

    async def add_upload(self, upload: ResumeUpload) -> None:
        if upload.id in self.uploads:
            raise ValueError(f"upload {upload.id!r} already exists")
        self.uploads[upload.id] = upload

    async def get_upload(self, upload_id: str) -> ResumeUpload | None:
        return self.uploads.get(upload_id)

    async def uploads_for_user(self, user_id: str) -> list[ResumeUpload]:
        return sorted(
            (u for u in self.uploads.values() if u.user_id == user_id),
            key=lambda u: (u.uploaded_at, u.id),
        )

    async def delete_for_user(self, user_id: str) -> None:
        self.uploads = {k: v for k, v in self.uploads.items() if v.user_id != user_id}


class PostgresUploadStore:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def add_upload(self, upload: ResumeUpload) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(sa.insert(t.resume_uploads).values(**upload.model_dump()))

    async def get_upload(self, upload_id: str) -> ResumeUpload | None:
        async with self._engine.connect() as conn:
            row = (
                await conn.execute(
                    sa.select(t.resume_uploads).where(t.resume_uploads.c.id == upload_id)
                )
            ).first()
        return None if row is None else ResumeUpload.model_validate(dict(row._mapping))

    async def uploads_for_user(self, user_id: str) -> list[ResumeUpload]:
        stmt = (
            sa.select(t.resume_uploads)
            .where(t.resume_uploads.c.user_id == user_id)
            .order_by(t.resume_uploads.c.uploaded_at, t.resume_uploads.c.id)
        )
        async with self._engine.connect() as conn:
            rows = (await conn.execute(stmt)).all()
        return [ResumeUpload.model_validate(dict(row._mapping)) for row in rows]

    async def delete_for_user(self, user_id: str) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(
                sa.delete(t.resume_uploads).where(t.resume_uploads.c.user_id == user_id)
            )
