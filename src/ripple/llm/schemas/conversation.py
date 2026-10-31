"""Schemas the conversation agent's prompts must satisfy (I4, ADR-0045).

IntentVerdict ties its payload to the intent, so the Router retries a tell without a
statement or an answer without a memory id instead of the agent guessing. AnswerVerdict
is a list of claims with evidence ids: the agent keeps only claims whose evidence it
actually retrieved (I5), which is why the answer is not free text.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ripple.core.models import StructuredFact

Intent = Literal["ask", "tell", "plan", "answer_question"]
AnswerKind = Literal["still_holds", "no_longer_holds", "corrected"]


class IntentVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: Intent
    reason: str = Field(min_length=1)
    # tell: the fact to record, in the student's words.
    statement: str | None = None
    # tell, or a corrected answer: the structured form of the fact, when clear.
    structured: StructuredFact | None = None
    # answer_question: which PENDING_USER memory the message answers, and how.
    memory_id: str | None = None
    answer: AnswerKind | None = None
    correction: str | None = None

    @model_validator(mode="after")
    def _check(self) -> "IntentVerdict":
        if self.intent == "tell":
            if not self.statement:
                raise ValueError("tell needs statement")
        elif self.statement is not None:
            raise ValueError("only tell carries statement")
        corrected = self.intent == "answer_question" and self.answer == "corrected"
        if self.structured is not None and self.intent != "tell" and not corrected:
            raise ValueError("only tell or a corrected answer carries structured")
        if self.intent == "answer_question":
            if not self.memory_id or self.answer is None:
                raise ValueError("answer_question needs memory_id and answer")
            if (self.answer == "corrected") != bool(self.correction):
                raise ValueError("correction is set exactly when answer is corrected")
        elif self.memory_id is not None or self.answer is not None or self.correction:
            raise ValueError("only answer_question carries memory_id, answer and correction")
        return self


class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1)
    # Empty is schema-valid on purpose: the agent drops the claim and reports it, which
    # is more honest than retrying until the model invents an id.
    evidence_ids: list[str] = []


class AnswerVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claims: list[Claim] = []
