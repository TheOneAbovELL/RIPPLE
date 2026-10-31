"""Ripple over the Model Context Protocol (FR-14, ADR-0006, ADR-0080 to ADR-0082).

`build_server` turns a `Services` plus a `Retriever` into the SDK's low-level server
with seven tools; `streamable_http_app` puts it behind a bearer gate for HTTP;
`python -m ripple.mcp_server` serves stdio or HTTP from the environment.
"""

from ripple.mcp_server.http import streamable_http_app
from ripple.mcp_server.server import TOOL_NAMES, build_server
from ripple.mcp_server.wiring import McpSettings, production_services

__all__ = [
    "TOOL_NAMES",
    "McpSettings",
    "build_server",
    "production_services",
    "streamable_http_app",
]
