"""Schema the jd_parser prompt must satisfy (I4, FR-2, ADR-0035).

The model returns fields, each with the exact substring of the JD it came from. The
parser (ripple.domains.jobs.parsers.jd) locates every quote in the text afterwards; a
quote that is not found makes the field disappear, so nothing reaches a memory without
a span. The attribute set is the shared jobs vocabulary, which pydantic turns into a
JSON-schema enum the model is shown.
"""

from pydantic import BaseModel, ConfigDict, Field

from ripple.domains.jobs.vocabulary import OpeningAttribute


class JDField(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attribute: OpeningAttribute
    # Dates stay as written in the JD; the parser normalises them deterministically.
    value: str | int | float | bool
    quote: str = Field(min_length=1, description="exact substring of the JD the value comes from")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class JDParse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fields: list[JDField] = []
