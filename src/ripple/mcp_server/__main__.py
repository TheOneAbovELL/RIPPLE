"""Serve Ripple over MCP (ADR-0082).

    python -m ripple.mcp_server                      # stdio; needs RIPPLE_MCP_TOKEN
    python -m ripple.mcp_server --transport http     # streamable HTTP on RIPPLE_MCP_PORT

Settings come from the environment (McpSettings) and flags override them. A stdio
server refuses to start without the token that names its user (ADR-0081).
"""

import argparse
import os
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
from typing import Any, TextIO

import anyio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from starlette.applications import Starlette

from ripple.api.services import Services
from ripple.core.errors import ConfigurationError
from ripple.core.retrieval_contract import Retriever
from ripple.mcp_server.http import streamable_http_app
from ripple.mcp_server.identity import TOKEN_VAR, env_token_source, header_token_source
from ripple.mcp_server.server import build_server
from ripple.mcp_server.wiring import TRANSPORTS, McpSettings, production_services

ServicesBuilder = Callable[[Mapping[str, str]], tuple[Services, Retriever]]
StdioRunner = Callable[[Server[Any]], None]
HttpRunner = Callable[[Starlette, McpSettings], None]


async def _serve_stdio(server: Server[Any]) -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def serve_stdio(server: Server[Any]) -> None:
    anyio.run(_serve_stdio, server)


def serve_http(app: Starlette, settings: McpSettings) -> None:
    import uvicorn

    uvicorn.run(app, host=settings.host, port=settings.port, log_level="info")


def main(
    argv: Sequence[str] | None = None,
    *,
    env: Mapping[str, str] | None = None,
    err: TextIO = sys.stderr,
    build_services: ServicesBuilder = production_services,
    run_stdio: StdioRunner = serve_stdio,
    run_http: HttpRunner = serve_http,
) -> int:
    env = os.environ if env is None else env
    parser = argparse.ArgumentParser(prog="python -m ripple.mcp_server")
    parser.add_argument("--transport", choices=TRANSPORTS)
    parser.add_argument("--host")
    parser.add_argument("--port", type=int)
    parser.add_argument("--path")
    args = parser.parse_args(argv)
    try:
        settings = replace(
            McpSettings.from_env(env), **{k: v for k, v in vars(args).items() if v is not None}
        )
        if settings.transport == "stdio" and not env.get(TOKEN_VAR, "").strip():
            raise ConfigurationError(
                f"{TOKEN_VAR} is not set; a stdio server serves exactly one user's token"
            )
        services, retriever = build_services(env)
    except ConfigurationError as exc:
        print(f"error: {exc}", file=err)
        return 2
    if settings.transport == "stdio":
        run_stdio(build_server(services, retriever, env_token_source(env)))
    else:
        server = build_server(services, retriever, header_token_source)
        run_http(
            streamable_http_app(
                server, services.user_store, host=settings.host, path=settings.path
            ),
            settings,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
