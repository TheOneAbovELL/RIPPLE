"""Build the inbound channel from settings (ADR-0077): the integration seam.

The coordinator calls `channel_from_env` from the API's start-up (production, with the
Postgres checkpointer kept open for the app's lifetime) and the development poll loop
calls it with the in-memory saver. Nothing here reads a setting the handover does not
list: TELEGRAM_BOT_TOKEN (transport), TELEGRAM_WEBHOOK_SECRET (route, not here) and
RIPPLE_DASHBOARD_URL (where /export points).
"""

from collections.abc import Mapping

from langgraph.checkpoint.base import BaseCheckpointSaver

from ripple.agents.conversation import ConversationAgent
from ripple.api.services import Services
from ripple.api.wiring import Settings, router_from_settings
from ripple.core.errors import ConfigurationError
from ripple.notify.inbound.channel import TelegramChannel
from ripple.notify.inbound.dispatcher import Conversation, InboundDispatcher, ScanningChatDirectory
from ripple.notify.inbound.ledger import InMemoryUpdateLedger, UpdateLedger
from ripple.notify.inbound.ratelimit import InMemoryRateLimiter, RateLimiter
from ripple.notify.inbound.telegram import TelegramBotApi

ENV_DASHBOARD_URL = "RIPPLE_DASHBOARD_URL"


def dashboard_url_from_env(env: Mapping[str, str]) -> str:
    url = env.get(ENV_DASHBOARD_URL, "").strip()
    if not url:
        raise ConfigurationError(f"{ENV_DASHBOARD_URL} is not set")
    return url


def channel_from_env(
    services: Services,
    conversation: Conversation,
    api: TelegramBotApi,
    env: Mapping[str, str],
    *,
    ledger: UpdateLedger | None = None,
    rate_limiter: RateLimiter | None = None,
) -> TelegramChannel:
    """The channel over the given services and agent.

    `ledger` and `rate_limiter` default to the in-memory implementations; production
    passes WS-13's Redis rate limiter and, once migration 0008 exists, the Postgres
    ledger (ADR-0077 consequences).
    """
    dispatcher = InboundDispatcher(
        services=services,
        conversation=conversation,
        chats=ScanningChatDirectory(services.user_store),
        rate_limiter=rate_limiter or InMemoryRateLimiter(services.clock),
        dashboard_url=dashboard_url_from_env(env),
    )
    return TelegramChannel(
        dispatcher=dispatcher, sender=api, ledger=ledger or InMemoryUpdateLedger()
    )


def development_conversation_agent(
    services: Services, settings: Settings, *, checkpointer: BaseCheckpointSaver
) -> ConversationAgent:
    """A ConversationAgent over the API's services for the poll loop.

    Production builds the agent once at API start-up with the Postgres checkpointer
    (ADR-0023) and the production retriever; that wiring is the coordinator's and lives
    beside `build_services`. This helper uses the Postgres lexical backend without an
    embedder, which is what the retrieval workstream ships today (ADR-0026).
    """
    from ripple.retrieval.hybrid import HybridRetriever
    from ripple.retrieval.postgres_search import PostgresSearchBackend
    from ripple.storage.engine import engine_from_url

    engine = engine_from_url(settings.database_url)
    return ConversationAgent(
        store=services.store,
        clock=services.clock,
        router=router_from_settings(settings),
        intake=services.intake,
        retriever=HybridRetriever(services.store, PostgresSearchBackend(engine)),
        runner=services.runner,
        checkpointer=checkpointer,
        domain=services.domain,
    )
