"""The published tool contract: seven named tools, strict input schemas, typed outputs."""

import asyncio

from ripple.mcp_server.server import TOOL_NAMES
from tests.mcp_server.harness import McpHarness, error

EXPECTED = {
    "ripple_search",
    "ripple_save",
    "ripple_update",
    "ripple_forget",
    "ripple_explain",
    "ripple_questions",
    "ripple_answer",
}

VALID_ARGUMENTS = {
    "ripple_search": {"query": "python"},
    "ripple_save": {"content": "CGPA is 7.6"},
    "ripple_update": {"memory_id": "m", "content": "x"},
    "ripple_forget": {"memory_id": "m"},
    "ripple_explain": {"memory_id": "m"},
    "ripple_questions": {},
    "ripple_answer": {"memory_id": "m", "reply": "still_holds"},
}


def test_tool_listing_publishes_strict_input_schemas_and_output_schemas():
    h = McpHarness.build()

    async def run():
        async with h.client() as c:
            return (await c.list_tools()).tools

    tools = asyncio.run(run())
    assert {t.name for t in tools} == EXPECTED == set(TOOL_NAMES)
    for tool in tools:
        assert tool.input_schema["type"] == "object", tool.name
        assert tool.input_schema.get("additionalProperties") is False, tool.name
        assert tool.output_schema is not None and tool.output_schema["type"] == "object"
        assert tool.description, tool.name


def test_every_tool_rejects_unknown_fields_before_touching_the_store():
    h = McpHarness.build()

    async def run():
        _, token = await h.user()
        results = {}
        async with h.client() as c:
            for name, arguments in VALID_ARGUMENTS.items():
                results[name] = await h.call(
                    c, name, {**arguments, "user_id": "someone-else"}, token=token
                )
        return results

    results = asyncio.run(run())
    for name, result in results.items():
        assert error(result)["error"] == "invalid_arguments", name
        assert "user_id" in error(result)["detail"], name
    assert h.store.all_memories() == [] and h.store.change_events() == []
