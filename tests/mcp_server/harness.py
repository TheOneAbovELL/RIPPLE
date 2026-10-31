"""Build the MCP server from fakes and talk to it with the SDK's in-process client.

Mirrors tests/api/harness.py: InMemoryStore, FakeClock, RuleLinker, a scripted detector,
a ScriptedEngine with the given waves and a ScriptedResolver behind the real Intake and
RippleRunner. Retrieval is the real HybridRetriever over the in-memory backend, and the
Intake indexes every write into that backend, so a saved memory is searchable at once.
Identity comes from a TokenHolder the test sets before each call (ADR-0081: the token
source is per transport; in tests it is a holder).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from mcp import Client
from mcp.server import Server
from mcp.types import CallToolResult

from ripple.api.admin import create_user
from ripple.api.services import Services
from ripple.core.change_detection import ChangeDetector
from ripple.core.intake import Intake
from ripple.core.models import Link, Memory
from ripple.core.resolver import Resolver
from ripple.core.retrieval_contract import Retriever
from ripple.core.ripple import RippleRunner
from ripple.domains.jobs.vocabulary import jobs_registry
from ripple.linking.rules import RuleLinker
from ripple.mcp_server.server import build_server
from ripple.retrieval.hybrid import HybridRetriever
from ripple.retrieval.indexing import index_memory
from ripple.retrieval.inmemory_search import InMemorySearchBackend
from ripple.storage.users import User
from tests.api.fakes import (
    InMemoryCandidateStore,
    InMemoryUserStore,
    RecordingOpeningRecorder,
    ScriptedDetector,
    ScriptedOpeningParser,
    ScriptedRecommendations,
    ScriptedResumeParser,
    SimpleCandidateStatements,
)
from tests.fakes.clock import FakeClock
from tests.fakes.engine import ScriptedEngine
from tests.fakes.resolver import ScriptedResolver
from tests.fakes.store import InMemoryStore


class TokenHolder:
    """The TokenSource for tests: whatever token the test last set."""

    def __init__(self) -> None:
        self.token: str | None = None

    def __call__(self, ctx: Any) -> str | None:
        return self.token


class BackendIndexer:
    """MemoryIndexer over the in-memory backend (production lexical search needs none:
    the Postgres backend reads the memories table)."""

    def __init__(self, backend: InMemorySearchBackend) -> None:
        self._backend = backend

    async def index(self, memory: Memory) -> None:
        await index_memory(self._backend, None, memory)

    async def remove(self, memory_id: str) -> None:
        self._backend.remove(memory_id)


@dataclass
class McpHarness:
    server: Server[Any]
    services: Services
    store: InMemoryStore
    clock: FakeClock
    user_store: InMemoryUserStore
    backend: InMemorySearchBackend
    retriever: Retriever
    tokens: TokenHolder
    detector: ChangeDetector

    @classmethod
    def build(
        cls,
        *,
        waves: Sequence[Sequence[str]] = (),
        resolver: Resolver | None = None,
        detector: ChangeDetector | None = None,
        retriever: Retriever | None = None,
    ) -> "McpHarness":
        store, clock, backend = InMemoryStore(), FakeClock(), InMemorySearchBackend()
        scripted_waves = [tuple(w) for w in waves]

        class Factory(ScriptedEngine):
            def __init__(self, max_depth: int = 8) -> None:
                super().__init__(*scripted_waves, max_depth=max_depth)

        registry = jobs_registry()
        indexer = BackendIndexer(backend)
        runner = RippleRunner(
            store,
            resolver or ScriptedResolver({}),
            clock,
            engine_factory=Factory,  # type: ignore[arg-type]
            indexer=indexer,
        )
        detector = detector or ScriptedDetector()
        intake = Intake(store, clock, registry, RuleLinker(), detector, runner, indexer=indexer)
        user_store = InMemoryUserStore()
        services = Services(
            store=store,
            clock=clock,
            registry=registry,
            intake=intake,
            runner=runner,
            user_store=user_store,
            candidate_store=InMemoryCandidateStore(),
            resume_parser=ScriptedResumeParser(),
            candidate_statements=SimpleCandidateStatements(),
            opening_parser=ScriptedOpeningParser(),
            opening_recorder=RecordingOpeningRecorder(),
            recommendations=ScriptedRecommendations(),
        )
        tokens = TokenHolder()
        retriever = retriever or HybridRetriever(store, backend)
        return cls(
            server=build_server(services, retriever, tokens),
            services=services,
            store=store,
            clock=clock,
            user_store=user_store,
            backend=backend,
            retriever=retriever,
            tokens=tokens,
            detector=detector,
        )

    async def user(self, display_name: str = "Asha") -> tuple[User, str]:
        """A user with a minted token; the raw token authenticates as them."""
        return await create_user(self.user_store, self.clock, display_name)

    async def seed(self, *rows: Memory | Link) -> None:
        async with self.store.transaction() as tx:
            for row in rows:
                if isinstance(row, Memory):
                    await tx.add_memory(row)
                else:
                    await tx.add_link(row)
        for row in rows:
            if isinstance(row, Memory):
                await index_memory(self.backend, None, row)

    def client(self) -> Client:
        return Client(self.server)

    async def call(
        self,
        client: Client,
        name: str,
        arguments: dict[str, Any] | None = None,
        *,
        token: str | None,
    ) -> CallToolResult:
        self.tokens.token = token
        return await client.call_tool(name, arguments or {})


def out(result: CallToolResult) -> dict[str, Any]:
    """The structured content of a successful call."""
    assert not result.is_error, result.content
    assert isinstance(result.structured_content, dict)
    return result.structured_content


def error(result: CallToolResult) -> dict[str, Any]:
    """The structured error of a failed call: {"error": code, "detail": ...}."""
    assert result.is_error, result.structured_content
    assert isinstance(result.structured_content, dict)
    return result.structured_content
