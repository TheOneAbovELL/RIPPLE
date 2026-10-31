"""Schema the linker prompt must satisfy (I4)."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ProposedLink(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(min_length=1)
    candidate_is: Literal["parent", "dependent"]
    link_type: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(min_length=1)


class LinkProposals(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposals: list[ProposedLink] = []
