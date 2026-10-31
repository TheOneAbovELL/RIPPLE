"""Schema the resume_parser prompt must satisfy (I4, FR-1, ADR-0024, ADR-0035).

One candidate per profile fact, each quoting the resume substring it came from. Only
the attributes a resume can state are allowed: `accepted_offer`, `looking` and `resume`
are decisions the student makes in conversation, never facts read off a document, so
a reply naming them fails validation rather than becoming a candidate (I5). The model
does not write the memory sentence: the parser builds `content` from attribute and
value, which leaves the model no field in which to embellish.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ripple.domains.jobs.vocabulary import ProfileAttribute

ResumeAttribute = Literal[
    ProfileAttribute.CGPA,
    ProfileAttribute.BATCH,
    ProfileAttribute.BRANCH,
    ProfileAttribute.SKILL,
    ProfileAttribute.PROJECT,
    ProfileAttribute.PREFERENCE,
    ProfileAttribute.AVAILABILITY,
]


class ResumeCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attribute: ResumeAttribute
    value: str | int | float | bool
    quote: str = Field(
        min_length=1, description="exact substring of the resume the value comes from"
    )
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class ResumeParse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidates: list[ResumeCandidate] = []
