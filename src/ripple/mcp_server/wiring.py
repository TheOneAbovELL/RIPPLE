"""Production wiring: the API's `Services` plus a retriever, settings from the environment
(ADR-0082). Nothing here runs in tests, which inject a `Services` built from fakes."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, get_args

from ripple.api.services import Services
from ripple.api.wiring import Settings, build_services
from ripple.core.errors import ConfigurationError
from ripple.core.retrieval_contract import Retriever

TRANSPORT_VAR = "RIPPLE_MCP_TRANSPORT"
HOST_VAR = "RIPPLE_MCP_HOST"
PORT_VAR = "RIPPLE_MCP_PORT"
PATH_VAR = "RIPPLE_MCP_PATH"

Transport = Literal["stdio", "http"]
TRANSPORTS: tuple[str, ...] = get_args(Transport)


@dataclass(frozen=True)
class McpSettings:
    transport: Transport = "stdio"
    host: str = "127.0.0.1"
    port: int = 8765
    path: str = "/mcp"

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "McpSettings":
        transport = env.get(TRANSPORT_VAR, "").strip().lower() or cls.transport
        if transport not in TRANSPORTS:
            raise ConfigurationError(
                f"{TRANSPORT_VAR} must be one of {TRANSPORTS}, not {transport!r}"
            )
        port_text = env.get(PORT_VAR, "").strip()
        try:
            port = int(port_text) if port_text else cls.port
        except ValueError as exc:
            raise ConfigurationError(f"{PORT_VAR} must be an integer, not {port_text!r}") from exc
        return cls(
            transport=transport,  # type: ignore[arg-type]  # checked against TRANSPORTS above
            host=env.get(HOST_VAR, "").strip() or cls.host,
            port=port,
            path=env.get(PATH_VAR, "").strip() or cls.path,
        )


def production_services(env: Mapping[str, str]) -> tuple[Services, Retriever]:
    """The same Services the API runs on, including its retriever (one engine)."""
    services = build_services(Settings.from_env(env))
    if services.retriever is None:  # build_services always sets it; this guards a refactor
        raise ConfigurationError("build_services returned no retriever")
    return services, services.retriever
