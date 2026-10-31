"""Production wiring of the JobContext: the integration seam (ADR-0017).

Everything a job needs comes from other workstreams: the Postgres store (storage), the
Router-backed resolver behind the jobs rules (llm, jobs adapter, ADR-0019), the ranking
source (jobs adapter), the user directory (identity) and the Telegram transport
(notify). Filled by the coordinator at integration checkpoint C1. Settings come from
the environment only; a missing one raises ConfigurationError before any job runs.
"""

import os
from collections.abc import Awaitable, Callable, Mapping
from datetime import timedelta
from pathlib import Path
from typing import Any

from arq.connections import ArqRedis
from sqlalchemy.ext.asyncio import AsyncEngine

from ripple.agents.scout import CriteriaChangeObserver, EnqueueingScoutTrigger
from ripple.api.directory import UserDirectoryAdapter
from ripple.core.clock import SystemClock
from ripple.core.errors import ConfigurationError
from ripple.core.resolver import ResolverChain
from ripple.core.ripple import RippleRunner
from ripple.core.sweep import NightlySweep
from ripple.domains.jobs.derive import ProfileDerivationObserver
from ripple.domains.jobs.ranking import JobsRecommender
from ripple.domains.jobs.rules import jobs_rules
from ripple.llm.config import RouterConfig
from ripple.llm.providers.anthropic import AnthropicClient
from ripple.llm.resolver import LLMResolver
from ripple.llm.router import Router
from ripple.llm.tracing import LangfuseTracer, Tracer, tracer_from_env
from ripple.notify.contracts import DeliveryLog, Transport
from ripple.notify.delivery_log import PostgresDeliveryLog
from ripple.notify.digest import DigestService
from ripple.notify.telegram import TelegramTransport
from ripple.storage.engine import ENV_VAR as DATABASE_URL_VAR
from ripple.storage.engine import engine_from_url
from ripple.storage.postgres import PostgresStore
from ripple.storage.users import PostgresUserStore
from ripple.worker.context import JobContext
from ripple.worker.lease import ChangeEventLease, InMemoryLease, Lease, RedisLease

LLM_CONFIG_VAR = "RIPPLE_LLM_CONFIG"
DEFAULT_LLM_CONFIG = "config/llm.default.toml"


def router_from_env(env: Mapping[str, str]) -> Router:
    path = Path(env.get(LLM_CONFIG_VAR, DEFAULT_LLM_CONFIG))
    config = RouterConfig.from_toml(path)
    global _TRACER
    _TRACER = tracer_from_env(env)
    return Router(config, {"anthropic": AnthropicClient()}, tracer=_TRACER)


_TRACER: Tracer | None = None


def shutdown_tracer() -> None:
    """Flush buffered spans at worker shutdown (ADR-0028); a no-op for the logging tracer."""
    tracer = _TRACER
    if isinstance(tracer, LangfuseTracer):
        tracer.shutdown()


# Several criteria changes in a burst (a resume with many facts) merge into one run:
# arq keeps one queued job per id, and the deferral lets the burst finish first.
SCOUT_USER_DEFER = timedelta(minutes=2)


async def enqueue_scout_user(redis: ArqRedis, user_id: str) -> None:
    """Queue scout_user_job once per user (ADR-0079); used by the API and the worker."""
    await redis.enqueue_job(
        "scout_user_job", user_id, _job_id=f"scout_user:{user_id}", _defer_by=SCOUT_USER_DEFER
    )


def job_context_from_env(
    env: Mapping[str, str] | None = None,
    *,
    lease: Lease | None = None,
    enqueue_scout: Callable[[str], Awaitable[None]] | None = None,
    engine: AsyncEngine | None = None,
    transport: Transport | None = None,
    delivery_log: DeliveryLog | None = None,
) -> JobContext:
    """Build the context from settings; `lease` is the Redis lease arq provides and
    `enqueue_scout` queues scout_user_job when a ripple changes the criteria. A local
    one-off run (ripple.worker.run_once) passes its own engine, transport and delivery
    log so it shares this wiring instead of mirroring it."""
    env = os.environ if env is None else env
    if engine is None:
        database_url = env.get(DATABASE_URL_VAR, "").strip()
        if not database_url:
            raise ConfigurationError(f"{DATABASE_URL_VAR} is not set")
        engine = engine_from_url(database_url)
    store = PostgresStore(engine)
    clock = SystemClock()
    router = router_from_env(env)
    leases = lease or InMemoryLease(clock)
    # The per-event lease shares the backend of the per-user one (ADR-0099), so every
    # ripple this worker drives (sweep, scout) excludes any other driver of that event.
    derivation = ProfileDerivationObserver(store, clock)  # ADR-0116
    runner = RippleRunner(
        store,
        ResolverChain(jobs_rules(), LLMResolver(router)),
        clock,
        event_lease=ChangeEventLease(leases),
        # An expiry the sweep ripples can change the criteria too (ADR-0079).
        observers=(
            derivation,
            *(
                [CriteriaChangeObserver(store, EnqueueingScoutTrigger(enqueue_scout))]
                if enqueue_scout is not None
                else []
            ),
        ),
    )
    derivation.attach(runner)
    users = UserDirectoryAdapter(PostgresUserStore(engine))
    if transport is None:
        transport = TelegramTransport.from_env(clock, env=env)
    if delivery_log is None:
        delivery_log = PostgresDeliveryLog(engine)
    # Postgres, so a worker restart on digest day cannot resend (ADR-0095).
    digest = DigestService(
        JobsRecommender(store),
        users,
        transport,
        clock,
        delivery_log=delivery_log,
    )
    return JobContext(
        store=store,
        runner=runner,
        clock=clock,
        users=users,
        sweep=NightlySweep(store, runner, clock),
        digest=digest,
        leases=leases,
        router=router,
    )


async def build_job_context(ctx: dict[str, Any]) -> JobContext:
    """arq startup hook: the Redis connection arq opened becomes the lease backend."""
    redis = ctx.get("redis")
    if redis is None:
        return job_context_from_env()

    async def enqueue_scout(user_id: str) -> None:
        await enqueue_scout_user(redis, user_id)

    return job_context_from_env(lease=RedisLease(redis), enqueue_scout=enqueue_scout)
