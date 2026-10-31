"""Anthropic adapter (ADR-0027): structured output through one forced tool call.

The adapter transports; it never validates (the Router does, I4). The SDK client is
injected through a factory so tests pass a fake object and no network is touched.
"""

import json
import os
from collections.abc import Callable
from typing import Any, Protocol, cast

from ripple.core.errors import ConfigurationError, LLMOutputInvalidError
from ripple.llm.client import CompletionRequest, CompletionResult

TOOL_NAME = "emit"
ENV_API_KEY = "ANTHROPIC_API_KEY"


class _Messages(Protocol):
    async def create(self, **kwargs: Any) -> Any: ...


class AnthropicLike(Protocol):
    """The slice of anthropic.AsyncAnthropic the adapter uses."""

    @property
    def messages(self) -> _Messages: ...


ClientFactory = Callable[[], AnthropicLike]


def _default_factory() -> AnthropicLike:
    api_key = os.environ.get(ENV_API_KEY)
    if not api_key:
        raise ConfigurationError(f"{ENV_API_KEY} is not set")
    # Imported here so the SDK is loaded only when a real client is built.
    from anthropic import AsyncAnthropic

    # The SDK's overloaded signature is wider than the slice we use; the cast is honest.
    return cast(AnthropicLike, AsyncAnthropic(api_key=api_key))


class AnthropicClient:
    def __init__(self, client_factory: ClientFactory | None = None) -> None:
        self._factory = client_factory or _default_factory
        self._client: AnthropicLike | None = None

    def _get(self) -> AnthropicLike:
        if self._client is None:
            self._client = self._factory()
        return self._client

    async def complete(self, request: CompletionRequest) -> CompletionResult:
        system = "\n\n".join(m.content for m in request.messages if m.role == "system")
        turns = [
            {"role": m.role, "content": m.content}
            for m in request.messages
            if m.role in ("user", "assistant")
        ]
        kwargs: dict[str, Any] = {
            "model": request.model,
            "max_tokens": request.max_output_tokens,
            "messages": turns,
            # No temperature: the pinned SDK (anthropic==1.15.0) has no such argument and
            # raises TypeError on it. Repeatability comes from the forced tool schema and
            # validation (I4), not from sampling settings (ADR-0117).
            "tools": [
                {
                    "name": TOOL_NAME,
                    "description": "Return the answer as JSON matching the schema.",
                    "input_schema": request.json_schema,
                }
            ],
            "tool_choice": {"type": "tool", "name": TOOL_NAME},
        }
        if system:
            kwargs["system"] = system
        response = await self._get().messages.create(**kwargs)
        payload = _tool_input(response)
        usage = getattr(response, "usage", None)
        return CompletionResult(
            text=json.dumps(payload),
            model=str(getattr(response, "model", request.model)),
            input_tokens=int(getattr(usage, "input_tokens", 0) or 0),
            output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
        )


def _tool_input(response: Any) -> dict[str, Any]:
    for block in getattr(response, "content", []) or []:
        if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == TOOL_NAME:
            payload = getattr(block, "input", None)
            if isinstance(payload, dict):
                return payload
    # The model answered with prose instead of the tool: hand the Router something it
    # will reject and retry rather than inventing a payload.
    raise LLMOutputInvalidError("anthropic", 1, "no tool_use block in the response")
