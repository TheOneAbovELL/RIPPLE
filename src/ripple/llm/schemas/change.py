"""Schema the change-detector prompt must satisfy (I4)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ripple.core.change_detection import ChangeKind


class ChangeVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: ChangeKind
    reason: str = Field(min_length=1)
    updates_memory_id: str | None = None
    valid_to: datetime | None = None

    @model_validator(mode="after")
    def _check(self) -> "ChangeVerdict":
        if (self.kind is ChangeKind.UPDATE) != (self.updates_memory_id is not None):
            raise ValueError("updates_memory_id is set exactly for an update")
        if self.kind is ChangeKind.TEMPORARY:
            if self.valid_to is None:
                raise ValueError("temporary needs valid_to")
            if self.valid_to.tzinfo is None:
                raise ValueError("valid_to must carry a timezone")
        return self
