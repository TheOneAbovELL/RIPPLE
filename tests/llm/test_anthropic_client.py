"""AnthropicClient against a fake SDK object: request shape, response parsing, failures."""

import asyncio
import json
from types import SimpleNamespace

import pytest

from ripple.core.errors import ConfigurationError, LLMOutputInvalidError
from ripple.llm.client import CompletionRequest, Message
from ripple.llm.providers.anthropic import ENV_API_KEY, TOOL_NAME, AnthropicClient


class FakeMessages:
    def __init__(self, response):
        self.response = response
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


class FakeSDK:
    def __init__(self, response):
        self.messages = FakeMessages(response)


def _response(payload, *, model="claude-haiku-5-5", in_tokens=12, out_tokens=7, prose=False):
    block = (
        SimpleNamespace(type="text", text="Sure, here you go")
        if prose
        else SimpleNamespace(type="tool_use", name=TOOL_NAME, input=payload)
    )
    return SimpleNamespace(
        content=[block],
        model=model,
        usage=SimpleNamespace(input_tokens=in_tokens, output_tokens=out_tokens),
    )


def _request():
    return CompletionRequest(
        model="claude-haiku-5-5",
        messages=[
            Message(role="system", content="You are the resolver."),
            Message(role="user", content="Decide."),
        ],
        json_schema={"type": "object", "properties": {"action": {"type": "string"}}},
    )


def test_anthropic_client_forces_the_schema_tool_and_splits_system_prompt():
    sdk = FakeSDK(_response({"action": "keep"}))
    client = AnthropicClient(client_factory=lambda: sdk)
    result = asyncio.run(client.complete(_request()))

    [call] = sdk.messages.calls
    assert call["system"] == "You are the resolver."
    assert call["messages"] == [{"role": "user", "content": "Decide."}]
    assert call["tool_choice"] == {"type": "tool", "name": TOOL_NAME}
    assert call["tools"][0]["input_schema"]["properties"]["action"]["type"] == "string"
    assert call["model"] == "claude-haiku-5-5"
    assert json.loads(result.text) == {"action": "keep"}
    assert (result.input_tokens, result.output_tokens) == (12, 7)
    assert result.cost_usd is None  # priced by the Router from config, never guessed here


def test_anthropic_client_prose_reply_is_invalid_output_not_a_guess():
    sdk = FakeSDK(_response(None, prose=True))
    client = AnthropicClient(client_factory=lambda: sdk)
    with pytest.raises(LLMOutputInvalidError, match="tool_use"):
        asyncio.run(client.complete(_request()))


def test_anthropic_client_reuses_one_sdk_client():
    built = []

    def factory():
        built.append(1)
        return FakeSDK(_response({"action": "keep"}))

    client = AnthropicClient(client_factory=factory)
    asyncio.run(client.complete(_request()))
    asyncio.run(client.complete(_request()))
    assert built == [1]


def test_anthropic_default_factory_requires_api_key(monkeypatch):
    monkeypatch.delenv(ENV_API_KEY, raising=False)
    with pytest.raises(ConfigurationError, match=ENV_API_KEY):
        asyncio.run(AnthropicClient().complete(_request()))


def test_anthropic_client_sends_only_arguments_the_installed_sdk_accepts():
    """The pinned SDK's signature is the contract; an unknown keyword is a TypeError live."""
    import inspect

    from anthropic.resources.messages import AsyncMessages

    accepted = set(inspect.signature(AsyncMessages.create).parameters) - {"self"}
    sdk = FakeSDK(_response({"action": "keep"}))
    asyncio.run(AnthropicClient(client_factory=lambda: sdk).complete(_request()))

    [call] = sdk.messages.calls
    assert set(call) <= accepted, set(call) - accepted
