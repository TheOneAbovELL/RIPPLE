import asyncio

import pytest

from ripple.llm.client import CompletionRequest, Message
from ripple.llm.providers.openai import OpenAIClient


def test_openai_client_is_not_built_yet():
    request = CompletionRequest(
        model="x", messages=[Message(role="user", content="hi")], json_schema={}
    )
    with pytest.raises(NotImplementedError, match="roadmap Phase 3"):
        asyncio.run(OpenAIClient().complete(request))
