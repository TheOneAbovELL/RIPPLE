"""Production wiring: environment in, `Services` out (ADR-0041).

No setting lives in code. `DATABASE_URL` is required; `RIPPLE_LLM_CONFIG` names the
router's TOML (default config/llm.default.toml, coordinator-owned). A missing or
unreadable value raises ConfigurationError naming it. The domain adapters (parsers,
opening recorder, recommendation source) are built by other workstreams and passed in;
`default_adapters()` is the one place the coordinator fills at integration.

    uvicorn ripple.api.app:create_production_app --factory
"""

import asyncio
import os
from collections.abc import AsyncIterator, Callable, Mapping
from contextlib import AbstractAsyncContextManager, AsyncExitStack, asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from arq.connections import ArqRedis, RedisSettings, create_pool
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine

from ripple.agents.scout import CriteriaChangeObserver, EnqueueingScoutTrigger
from ripple.api.app import create_app
from ripple.api.contracts import (
    CandidateStatements,
    OpeningParser,
    OpeningRecorder,
    RecommendationSource,
    ResumeParser,
)
from ripple.api.health import Readiness, postgres_probe, redis_probe
from ripple.api.logging import configure_logging
from ripple.api.ratelimit import (
    InMemoryRateLimiter,
    RateLimiter,
    RateLimitGuard,
    RedisRateLimiter,
)
from ripple.api.routers.telegram import (
    TelegramWebhook,
    attach_telegram_webhook,
    mount_telegram_route,
    webhook_secret_from_env,
)
from ripple.api.services import Services
from ripple.core.clock import Clock, SystemClock
from ripple.core.errors import ConfigurationError
from ripple.core.intake import Intake
from ripple.core.lease import EventLease
from ripple.core.resolver import ResolverChain
from ripple.core.ripple import EventObserver, RippleRunner
from ripple.core.store import Store
from ripple.domains.jobs.derive import ProfileDerivationObserver
from ripple.domains.jobs.linker import JobsStructureLinker
from ripple.domains.jobs.rules import jobs_rules
from ripple.domains.jobs.vocabulary import (
    MULTI_VALUED_PROFILE_ATTRIBUTES,
    PERMANENT_PROFILE_FACTS,
    jobs_registry,
)
from ripple.linking.composite import StructuredFirstLinker
from ripple.linking.llm import LLMLinker
from ripple.linking.rules import RuleLinker
from ripple.linking.trained import LINKER_VAR, MODEL_VAR, select_linker
from ripple.llm.change_detector import LLMChangeDetector
from ripple.llm.config import RouterConfig
from ripple.llm.providers.anthropic import AnthropicClient
from ripple.llm.resolver import LLMResolver
from ripple.llm.router import Router
from ripple.llm.tracing import LangfuseTracer, Tracer, tracer_from_env
from ripple.notify.delivery_log import PostgresDeliveryLog
from ripple.retrieval.hybrid import HybridRetriever
from ripple.retrieval.postgres_search import PostgresSearchBackend
from ripple.storage.candidates import PostgresCandidateStore
from ripple.storage.engine import DRIVER_PREFIX, engine_from_url
from ripple.storage.engine import ENV_VAR as DATABASE_URL_VAR
from ripple.storage.feedback import PostgresFeedbackStore
from ripple.storage.postgres import PostgresStore
from ripple.storage.uploads import PostgresUploadStore
from ripple.storage.users import PostgresUserStore
from ripple.worker.lease import ChangeEventLease, LazyRedisLease
from ripple.worker.wiring import enqueue_scout_user

if TYPE_CHECKING:
    from ripple.notify.inbound.channel import TelegramChannel

LLM_CONFIG_VAR = "RIPPLE_LLM_CONFIG"
DEFAULT_LLM_CONFIG = Path("config/llm.default.toml")
# Hardening settings (ADR-0098). REDIS_URL is the worker's variable too; the API uses it
# for shared rate-limit buckets and the readiness probe, and runs per-process buckets
# without it (one uvicorn worker, development).
REDIS_URL_VAR = "REDIS_URL"
LOG_LEVEL_VAR = "RIPPLE_LOG_LEVEL"
LOG_JSON_VAR = "RIPPLE_LOG_JSON"
TRUST_PROXY_VAR = "RIPPLE_TRUST_PROXY"
CORS_ORIGINS_VAR = "RIPPLE_CORS_ORIGINS"  # development only; comma-separated
TELEGRAM_TOKEN_VAR = "TELEGRAM_BOT_TOKEN"
_TRUE = {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    database_url: str
    llm_config: Path
    redis_url: str | None = None
    log_level: str = "INFO"
    log_json: bool = True
    trust_proxy: bool = False  # X-Forwarded-For is honoured only behind Caddy (ADR-0029)
    cors_origins: tuple[str, ...] = ()
    # The Telegram channel runs inside the API when a bot token is set (ADR-0077).
    telegram: bool = False
    # RIPPLE_LINKER and RIPPLE_TRAINED_LINKER_MODEL, read by select_linker (ADR-0128).
    linker: Mapping[str, str] = field(default_factory=dict[str, str])

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "Settings":
        database_url = env.get(DATABASE_URL_VAR, "").strip()
        if not database_url:
            raise ConfigurationError(f"{DATABASE_URL_VAR} is not set")
        llm_config = env.get(LLM_CONFIG_VAR, "").strip()
        return cls(
            database_url=database_url,
            llm_config=Path(llm_config) if llm_config else DEFAULT_LLM_CONFIG,
            redis_url=env.get(REDIS_URL_VAR, "").strip() or None,
            log_level=env.get(LOG_LEVEL_VAR, "").strip() or "INFO",
            log_json=env.get(LOG_JSON_VAR, "true").strip().lower() in _TRUE,
            trust_proxy=env.get(TRUST_PROXY_VAR, "").strip().lower() in _TRUE,
            cors_origins=tuple(
                o.strip() for o in env.get(CORS_ORIGINS_VAR, "").split(",") if o.strip()
            ),
            telegram=bool(env.get(TELEGRAM_TOKEN_VAR, "").strip()),
            linker={k: env[k] for k in (LINKER_VAR, MODEL_VAR) if env.get(k, "").strip()},
        )


@dataclass(frozen=True)
class DomainAdapters:
    """What the jobs workstreams provide; the coordinator fills this at integration."""

    resume_parser: ResumeParser
    candidate_statements: CandidateStatements
    opening_parser: OpeningParser
    opening_recorder: OpeningRecorder
    recommendations: RecommendationSource


def router_from_settings(settings: Settings) -> Router:
    # One provider today (ADR-0010); the config's fallbacks are models, not vendors.
    return Router(
        RouterConfig.from_toml(settings.llm_config),
        {"anthropic": AnthropicClient()},
        tracer=tracer_from_env(),  # Langfuse when configured, structured logs otherwise (ADR-0028)
    )


def build_services(
    settings: Settings,
    adapters: DomainAdapters | None = None,
    *,
    engine: AsyncEngine | None = None,
) -> Services:
    engine = engine if engine is not None else engine_from_url(settings.database_url)
    store = PostgresStore(engine)
    clock = SystemClock()
    registry = jobs_registry()
    router = router_from_settings(settings)
    shared = _shared_with_the_worker(settings, store)
    # Derivation first: a first CGPA can create the criteria, whose own event then
    # reaches the criteria-change trigger (ADR-0116, ADR-0079).
    derivation = ProfileDerivationObserver(store, clock)
    runner = RippleRunner(
        store,
        ResolverChain(jobs_rules(), fallback=LLMResolver(router)),
        clock,
        event_lease=shared.event_lease,
        observers=(derivation, *shared.observers),
    )
    derivation.attach(runner)
    intake = Intake(
        store,
        clock,
        registry,
        # Structured facts link by domain rule; prose by the LLM, or by the trained link
        # finder when RIPPLE_LINKER=trained (ADR-0116, ADR-0128).
        StructuredFirstLinker(
            [JobsStructureLinker(), RuleLinker()],
            select_linker(settings.linker, llm=LLMLinker(router, registry), registry=registry),
        ),
        LLMChangeDetector(router, clock),
        runner,
        multi_valued_attributes=MULTI_VALUED_PROFILE_ATTRIBUTES,
        permanent_facts=PERMANENT_PROFILE_FACTS,
    )
    if adapters is None:
        adapters = default_adapters(store, clock, runner, router)
    return Services(
        store=store,
        clock=clock,
        registry=registry,
        intake=intake,
        runner=runner,
        user_store=PostgresUserStore(engine),
        candidate_store=PostgresCandidateStore(engine),
        upload_store=PostgresUploadStore(engine),
        resume_parser=adapters.resume_parser,
        candidate_statements=adapters.candidate_statements,
        opening_parser=adapters.opening_parser,
        opening_recorder=adapters.opening_recorder,
        recommendations=adapters.recommendations,
        retriever=HybridRetriever(store, PostgresSearchBackend(engine)),
        router=router,
        delivery_log=PostgresDeliveryLog(engine),
        feedback_store=PostgresFeedbackStore(engine),
    )


@dataclass(frozen=True)
class SharedWithTheWorker:
    event_lease: EventLease | None = None
    observers: tuple[EventObserver, ...] = ()


def _shared_with_the_worker(settings: Settings, store: Store) -> SharedWithTheWorker:
    """The per-event lease (ADR-0099) and the criteria-change trigger (ADR-0079).

    Both need the Redis the worker uses: the lease so a live ripple here and the
    worker's sweep never drive one event at once, the trigger to enqueue
    scout_user_job. Without REDIS_URL (development) the runner runs without either.
    """
    if not settings.redis_url:
        return SharedWithTheWorker()
    pool = redis_factory(settings.redis_url)

    async def enqueue_scout(user_id: str) -> None:
        await enqueue_scout_user(await pool(), user_id)

    return SharedWithTheWorker(
        event_lease=ChangeEventLease(LazyRedisLease(pool)),
        observers=(CriteriaChangeObserver(store, EnqueueingScoutTrigger(enqueue_scout)),),
    )


def default_adapters(
    store: Store, clock: Clock, runner: RippleRunner, router: Router
) -> DomainAdapters:
    """The real jobs workstreams behind the API protocols (integration checkpoint C2)."""
    from ripple.api.adapters import (
        CandidateStatementsAdapter,
        OpeningParserAdapter,
        OpeningRecorderAdapter,
        ResumeParserAdapter,
    )
    from ripple.domains.jobs.ranking import JobsRecommender

    return DomainAdapters(
        resume_parser=ResumeParserAdapter(router),
        candidate_statements=CandidateStatementsAdapter(),
        opening_parser=OpeningParserAdapter(router),
        opening_recorder=OpeningRecorderAdapter(store, clock, runner),
        recommendations=JobsRecommender(store),
    )


_POOLS: dict[str, "RedisPool"] = {}


def redis_factory(redis_url: str) -> "RedisPool":
    """One lazily opened arq pool per URL per process, shared by the limiter and the probe."""
    pool = _POOLS.get(redis_url)
    if pool is None:
        pool = _POOLS[redis_url] = RedisPool(RedisSettings.from_dsn(redis_url))
    return pool


class RedisPool:
    def __init__(self, settings: RedisSettings) -> None:
        self._settings = settings
        self._pool: ArqRedis | None = None
        self._opening = asyncio.Lock()

    async def __call__(self) -> ArqRedis:
        async with self._opening:  # two first callers must not open two pools
            if self._pool is None:
                self._pool = await create_pool(self._settings)
        return self._pool

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.aclose()
            self._pool = None


async def close_redis_pools() -> None:
    """Close every pool this process opened; the API lifespan calls it at shutdown."""
    for pool in list(_POOLS.values()):
        await pool.close()


def rate_limit_guard(settings: Settings, clock: Clock) -> RateLimitGuard:
    limiter: RateLimiter = (
        RedisRateLimiter(redis_factory(settings.redis_url))
        if settings.redis_url
        else InMemoryRateLimiter()
    )
    return RateLimitGuard(limiter, clock, trust_forwarded_for=settings.trust_proxy)


def readiness_probes(settings: Settings, engine: AsyncEngine) -> Readiness:
    probes = {"postgres": postgres_probe(engine)}
    if settings.redis_url:
        probes["redis"] = redis_probe(redis_factory(settings.redis_url))
    return Readiness(probes)


def app_from_env(env: Mapping[str, str] | None = None) -> FastAPI:
    env = os.environ if env is None else env
    settings = Settings.from_env(env)
    configure_logging(settings.log_level, json_lines=settings.log_json)
    engine = engine_from_url(settings.database_url)
    services = build_services(settings, engine=engine)
    # Fail at start-up, not on the first delivery, when the webhook secret is missing.
    secret = webhook_secret_from_env(env) if settings.telegram else None
    app = create_app(
        services,
        rate_limit=rate_limit_guard(settings, services.clock),
        readiness=readiness_probes(settings, engine),
        lifespan=api_lifespan(settings, services, env, webhook_secret=secret),
        cors_origins=settings.cors_origins,
    )
    if settings.telegram:
        mount_telegram_route(app)
    return app


def api_lifespan(
    settings: Settings,
    services: Services,
    env: Mapping[str, str],
    *,
    webhook_secret: str | None,
) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    """What the API opens at start-up and closes at shutdown.

    With Telegram on: the Postgres checkpointer (ADR-0023), the Conversation agent over
    the API's own services, the bot client and the channel behind the webhook. Always:
    flush buffered tracer spans on the way out (ADR-0028).
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with AsyncExitStack() as stack:
            stack.push_async_callback(close_redis_pools)  # last out: after the channel
            if webhook_secret is not None:
                channel = await _open_telegram_channel(stack, settings, services, env)
                attach_telegram_webhook(app, TelegramWebhook(channel, webhook_secret))
            try:
                yield
            finally:
                if services.router is not None:
                    flush_tracer(services.router.tracer)

    return lifespan


async def _open_telegram_channel(
    stack: AsyncExitStack, settings: Settings, services: Services, env: Mapping[str, str]
) -> "TelegramChannel":
    # Imported here: the agent and bot modules import this one (Settings, Services).
    from ripple.agents.checkpoints import postgres_saver
    from ripple.agents.conversation import ConversationAgent
    from ripple.notify.inbound.telegram import TelegramBotApi
    from ripple.notify.inbound.wiring import channel_from_env

    if services.router is None or services.retriever is None:
        raise ConfigurationError("the Telegram channel needs Services.router and .retriever")
    saver = await stack.enter_async_context(postgres_saver(psycopg_dsn(settings.database_url)))
    agent = ConversationAgent(
        store=services.store,
        clock=services.clock,
        router=services.router,
        intake=services.intake,
        retriever=services.retriever,
        runner=services.runner,
        checkpointer=saver,
        domain=services.domain,
    )
    api = TelegramBotApi.from_env(services.clock, env=env)
    stack.push_async_callback(api.aclose)
    return channel_from_env(services, agent, api, env)


def psycopg_dsn(database_url: str) -> str:
    """LangGraph's saver takes a libpq DSN, not SQLAlchemy's driver-qualified URL."""
    return database_url.replace(DRIVER_PREFIX, "postgresql://", 1)


def flush_tracer(tracer: Tracer) -> None:
    if isinstance(tracer, LangfuseTracer):
        tracer.shutdown()
