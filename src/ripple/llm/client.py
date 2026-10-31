"""The one interface every LLM provider implements (ADR-0010).

A client returns raw text; the Router validates it (I4). Keeping clients dumb means
every provider, and FakeLLM, is interchangeable and nothing downstream sees
unvalidated output.
"""

from typing import Literal, Protocol

from pydantic import BaseModel, Field

Role = Literal["system", "user", "assistant"]


class Message(BaseModel):
    role: Role
    content: str


class CompletionRequest(BaseModel):
    model: str
    messages: list[Message]
    # JSON schema the provider is asked to conform to (structured output where supported).
    json_schema: dict[str, object]
    max_output_tokens: int = Field(default=2048, gt=0)
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)


class CompletionResult(BaseModel):
    text: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    # Filled by provider adapters that know their price table; None until then.
    cost_usd: float | None = None


class LLMClient(Protocol):
    async def complete(self, request: CompletionRequest) -> CompletionResult:
        """Return the model's raw text. Raise on transport or provider failure."""
        ...
