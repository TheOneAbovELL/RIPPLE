"""Streamable HTTP behind the bearer gate (ADR-0081, ADR-0082), served in-process."""

import asyncio

import httpx2 as httpx  # the SDK's client transport is built on httpx2, not httpx
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

from ripple.mcp_server.http import streamable_http_app
from ripple.mcp_server.identity import header_token_source
from ripple.mcp_server.server import build_server
from tests.builders import memory
from tests.mcp_server.harness import McpHarness, out

URL = "http://ripple.test/mcp"


def _app(h: McpHarness):
    """The production shape: identity from the Authorization header, not a holder."""
    server = build_server(h.services, h.retriever, header_token_source)
    return streamable_http_app(server, h.user_store, host="ripple.test")


def test_http_requests_without_a_valid_bearer_token_are_401():
    h = McpHarness.build()
    app = _app(h)

    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=URL) as c:
            missing = await c.post("/mcp", json={})
            basic = await c.post("/mcp", json={}, headers={"Authorization": "Basic abc"})
            wrong = await c.post("/mcp", json={}, headers={"Authorization": "Bearer nope"})
            get = await c.get("/mcp")
        return missing, basic, wrong, get

    for response in asyncio.run(run()):
        assert response.status_code == 401
        assert response.headers["www-authenticate"].startswith("Bearer")


def test_http_client_with_a_valid_token_calls_tools_as_that_user():
    h = McpHarness.build()
    app = _app(h)

    async def run():
        user, token = await h.user()
        await h.seed(memory(content="knows python", user_id=user.id))
        async with (
            app.router.lifespan_context(app),  # httpx's ASGITransport runs no lifespan
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                headers={"Authorization": f"Bearer {token}"},
            ) as http,
            Client(streamable_http_client(URL, http_client=http)) as mcp,
        ):
            return await mcp.call_tool("ripple_search", {"query": "python"})

    [hit] = out(asyncio.run(run()))["results"]
    assert hit["memory"]["content"] == "knows python"
