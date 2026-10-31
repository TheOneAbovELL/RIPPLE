"""Schema the tailor prompt must satisfy (I4, ADR-0046)."""

from pydantic import BaseModel, ConfigDict, Field


class Highlight(BaseModel):
    model_config = ConfigDict(extra="forbid")

    memory_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    opening_evidence_ids: list[str] = []


class TailorVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    highlights: list[Highlight] = []
