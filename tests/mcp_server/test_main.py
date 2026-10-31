"""`python -m ripple.mcp_server`: settings from the environment, transport choice, the
stdio token requirement. No database is touched: the builders are injected."""

import io

import pytest

from ripple.core.errors import ConfigurationError
from ripple.mcp_server.__main__ import main
from ripple.mcp_server.identity import TOKEN_VAR
from ripple.mcp_server.wiring import McpSettings
from tests.mcp_server.harness import McpHarness


def test_settings_default_to_stdio_on_loopback():
    settings = McpSettings.from_env({})
    assert (settings.transport, settings.host, settings.port, settings.path) == (
        "stdio",
        "127.0.0.1",
        8765,
        "/mcp",
    )


def test_settings_read_the_environment_and_name_a_bad_value():
    settings = McpSettings.from_env(
        {
            "RIPPLE_MCP_TRANSPORT": "http",
            "RIPPLE_MCP_HOST": "0.0.0.0",
            "RIPPLE_MCP_PORT": "9000",
            "RIPPLE_MCP_PATH": "/ripple",
        }
    )
    assert (settings.transport, settings.host, settings.port, settings.path) == (
        "http",
        "0.0.0.0",
        9000,
        "/ripple",
    )
    with pytest.raises(ConfigurationError, match="RIPPLE_MCP_PORT"):
        McpSettings.from_env({"RIPPLE_MCP_PORT": "many"})
    with pytest.raises(ConfigurationError, match="RIPPLE_MCP_TRANSPORT"):
        McpSettings.from_env({"RIPPLE_MCP_TRANSPORT": "sse"})


def _fakes():
    h = McpHarness.build()
    served: list[tuple[str, object]] = []

    def build(env):
        return h.services, h.retriever

    def run_stdio(server):
        served.append(("stdio", None))

    def run_http(app, settings):
        served.append(("http", (settings.host, settings.port)))

    return served, {"build_services": build, "run_stdio": run_stdio, "run_http": run_http}


def test_main_serves_stdio_only_with_a_token_in_the_environment():
    served, fakes = _fakes()
    err = io.StringIO()
    assert main([], env={}, err=err, **fakes) == 2
    assert TOKEN_VAR in err.getvalue()
    assert served == []
    assert main([], env={TOKEN_VAR: "t"}, err=err, **fakes) == 0
    assert served == [("stdio", None)]


def test_main_serves_http_from_flags_over_environment():
    served, fakes = _fakes()
    code = main(
        ["--transport", "http", "--port", "9100"],
        env={"RIPPLE_MCP_PORT": "9000"},
        err=io.StringIO(),
        **fakes,
    )
    assert code == 0
    assert served == [("http", ("127.0.0.1", 9100))]
