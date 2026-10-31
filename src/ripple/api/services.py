"""Everything the API needs, in one injectable object (ADR-0041).

Tests build a `Services` from fakes; `ripple.api.wiring` builds the production one
from the environment. Routers reach it through `request.app.state.services`, never
through module globals, so two apps in one process (two tests) never share state.
"""

from dataclasses import dataclass, field
from datetime import timedelta

from fastapi import Request

from ripple.api.contracts import (
    CandidateStatements,
    DomainVocabulary,
    OpeningParser,
    OpeningRecorder,
    RecommendationSource,
    ResumeParser,
    jobs_vocabulary,
)
from ripple.core.clock import Clock
from ripple.core.intake import Intake
from ripple.core.links import LinkTypeRegistry
from ripple.core.retrieval_contract import Retriever
from ripple.core.ripple import RippleRunner
from ripple.core.store import Store
from ripple.domains.jobs.vocabulary import DOMAIN
from ripple.llm.router import Router
from ripple.notify.contracts import DeliveryLog
from ripple.storage.candidates import CandidateStore
from ripple.storage.feedback import FeedbackStore, InMemoryFeedbackStore
from ripple.storage.uploads import InMemoryUploadStore, UploadStore
from ripple.storage.users import UserStore

DEFAULT_LINK_CODE_TTL = timedelta(minutes=15)
DEFAULT_MAX_RESUME_BYTES = 5 * 1024 * 1024


@dataclass(frozen=True)
class Services:
    store: Store
    clock: Clock
    registry: LinkTypeRegistry
    intake: Intake
    runner: RippleRunner
    user_store: UserStore
    candidate_store: CandidateStore
    resume_parser: ResumeParser
    candidate_statements: CandidateStatements
    opening_parser: OpeningParser
    opening_recorder: OpeningRecorder
    recommendations: RecommendationSource
    domain: str = DOMAIN
    link_code_ttl: timedelta = DEFAULT_LINK_CODE_TTL
    max_resume_bytes: int = DEFAULT_MAX_RESUME_BYTES
    # Per-process default for tests and development; wiring passes the Postgres store
    # (ADR-0097) and tests/api/test_hardening_uploads.py pins that it does.
    upload_store: UploadStore = field(default_factory=InMemoryUploadStore)
    vocabulary: DomainVocabulary = field(default_factory=jobs_vocabulary)
    # Validity-aware retrieval for the agents and the MCP server; built once in wiring
    # (one engine). None in tests that do not exercise retrieval.
    retriever: Retriever | None = None
    # The production router, shared by the agents the API hosts (Telegram channel) so
    # one tracer sees every call. None in tests that build no agent.
    router: Router | None = None
    # What the worker sent the user; DELETE /me erases it (FR-15). None in tests
    # that do not exercise deletion of delivery records.
    delivery_log: DeliveryLog | None = None
    # Pilot feedback (ADR-0105); wiring passes the Postgres store (migration 0009).
    feedback_store: FeedbackStore = field(default_factory=InMemoryFeedbackStore)


def services_of(request: Request) -> Services:
    services = getattr(request.app.state, "services", None)
    if not isinstance(services, Services):
        raise RuntimeError("app was not built by ripple.api.app.create_app")
    return services
