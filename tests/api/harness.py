"""Build the API from fakes and talk to it over httpx (ADR-0022).

`Harness.build()` wires InMemoryStore, FakeClock, RuleLinker, a scripted detector, a
ScriptedEngine with the given waves and a ScriptedResolver into `create_app`. Tests
run their coroutine with `asyncio.run`, matching the rest of the suite.
"""

from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from ripple.api.admin import create_user
from ripple.api.app import create_app
from ripple.api.services import Services
from ripple.core.change_detection import ChangeDetector
from ripple.core.intake import Intake
from ripple.core.models import Link, Memory
from ripple.core.resolver import Resolver
from ripple.core.ripple import RippleRunner
from ripple.domains.jobs.vocabulary import jobs_registry
from ripple.linking.rules import RuleLinker
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

BASE_URL = "http://ripple.test"


@dataclass
class Harness:
    app: FastAPI
    services: Services
    store: InMemoryStore
    clock: FakeClock
    user_store: InMemoryUserStore
    candidate_store: InMemoryCandidateStore
    resume_parser: ScriptedResumeParser
    opening_parser: ScriptedOpeningParser
    opening_recorder: RecordingOpeningRecorder
    recommendations: ScriptedRecommendations
    detector: ChangeDetector

    @classmethod
    def build(
        cls,
        *,
        waves: Sequence[Sequence[str]] = (),
        resolver: Resolver | None = None,
        detector: ChangeDetector | None = None,
        resume_parser: ScriptedResumeParser | None = None,
        opening_parser: ScriptedOpeningParser | None = None,
        recommendations: ScriptedRecommendations | None = None,
    ) -> "Harness":
        store, clock = InMemoryStore(), FakeClock()
        scripted_waves = [tuple(w) for w in waves]

        class Factory(ScriptedEngine):
            def __init__(self, max_depth: int = 8) -> None:
                super().__init__(*scripted_waves, max_depth=max_depth)

        registry = jobs_registry()
        runner = RippleRunner(
            store,
            resolver or ScriptedResolver({}),
            clock,
            engine_factory=Factory,  # type: ignore[arg-type]
        )
        detector = detector or ScriptedDetector()
        intake = Intake(store, clock, registry, RuleLinker(), detector, runner)
        user_store = InMemoryUserStore()
        candidate_store = InMemoryCandidateStore()
        resume_parser = resume_parser or ScriptedResumeParser()
        opening_parser = opening_parser or ScriptedOpeningParser()
        opening_recorder = RecordingOpeningRecorder()
        recommendations = recommendations or ScriptedRecommendations()
        services = Services(
            store=store,
            clock=clock,
            registry=registry,
            intake=intake,
            runner=runner,
            user_store=user_store,
            candidate_store=candidate_store,
            resume_parser=resume_parser,
            candidate_statements=SimpleCandidateStatements(),
            opening_parser=opening_parser,
            opening_recorder=opening_recorder,
            recommendations=recommendations,
            max_resume_bytes=1024,
        )
        return cls(
            app=create_app(services),
            services=services,
            store=store,
            clock=clock,
            user_store=user_store,
            candidate_store=candidate_store,
            resume_parser=resume_parser,
            opening_parser=opening_parser,
            opening_recorder=opening_recorder,
            recommendations=recommendations,
            detector=detector,
        )

    async def user(self, display_name: str = "Asha") -> tuple[User, dict[str, str]]:
        """A user with a minted token, and the headers that authenticate as them."""
        user, raw_token = await create_user(self.user_store, self.clock, display_name)
        return user, {"Authorization": f"Bearer {raw_token}"}

    async def seed(self, *rows: Memory | Link) -> None:
        async with self.store.transaction() as tx:
            for row in rows:
                if isinstance(row, Memory):
                    await tx.add_memory(row)
                else:
                    await tx.add_link(row)

    @asynccontextmanager
    async def client(self) -> AsyncIterator[AsyncClient]:
        async with AsyncClient(transport=ASGITransport(app=self.app), base_url=BASE_URL) as c:
            yield c


def body(response: Any) -> dict[str, Any]:
    assert response.headers["content-type"].startswith("application/json"), response.text
    return response.json()
