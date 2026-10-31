"""Schema the resolver prompt must satisfy (I4). Field rules mirror core.resolver.Resolution."""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ripple.core.models import DecisionAction


class ResolverVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: DecisionAction
    reason: str = Field(min_length=1)
    evidence_refs: list[str] = []
    new_content: str | None = None
    question: str | None = None

    @model_validator(mode="after")
    def _check(self) -> "ResolverVerdict":
        if self.action is DecisionAction.UPDATE and not self.new_content:
            raise ValueError("update needs new_content")
        if self.action is not DecisionAction.UPDATE and self.new_content:
            raise ValueError("only update carries new_content")
        if self.action is DecisionAction.ASK and not self.question:
            raise ValueError("ask needs question")
        return self
