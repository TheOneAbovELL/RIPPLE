"""Development long-poll loop over getUpdates (ADR-0077). Not for production.

Production delivers updates to `POST /telegram/webhook`; this loop exists so a
developer without a public URL can talk to the bot from a laptop:

    export PATH="$HOME/.local/bin:$PATH"
    uv run python -m ripple.worker.telegram_poll

It needs DATABASE_URL, TELEGRAM_BOT_TOKEN, ANTHROPIC_API_KEY and RIPPLE_DASHBOARD_URL,
and a bot with no webhook set (`python -m ripple.notify.inbound.register --remove`;
Telegram refuses getUpdates while a webhook exists). The agent runs on the in-memory
checkpointer, the ledger and rate limiter are in-memory: everything is forgotten when
the process stops, which is the point of a development loop and wrong for a pilot.
"""

import asyncio
import contextlib
import logging
import os
from collections.abc import Awaitable, Callable, Mapping

from ripple.notify.inbound.channel import TelegramChannel
from ripple.notify.inbound.telegram import POLL_TIMEOUT_SECONDS, TelegramBotApi

log = logging.getLogger("ripple.worker.telegram_poll")

ERROR_BACKOFF_SECONDS = 5.0


async def poll_once(
    api: TelegramBotApi,
    channel: TelegramChannel,
    offset: int | None,
    *,
    timeout_seconds: int = POLL_TIMEOUT_SECONDS,
) -> int | None:
    """Fetch one batch from `offset`, hand each update to the channel, return the next offset.

    The offset is advanced past every update in the batch whether or not it was
    handled: Telegram would otherwise resend it forever, and the ledger already makes a
    resend a no-op.
    """
    updates = await api.get_updates(offset=offset, timeout_seconds=timeout_seconds)
    next_offset = offset
    for raw in updates:
        await channel.receive(raw)
        update_id = raw.get("update_id")
        if isinstance(update_id, int) and (next_offset is None or update_id >= next_offset):
            next_offset = update_id + 1
    return next_offset


async def poll_forever(
    api: TelegramBotApi,
    channel: TelegramChannel,
    *,
    stop: asyncio.Event | None = None,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    timeout_seconds: int = POLL_TIMEOUT_SECONDS,
) -> None:
    """Loop until `stop` is set; a transport error waits ERROR_BACKOFF_SECONDS and retries."""
    offset: int | None = None
    while stop is None or not stop.is_set():
        try:
            offset = await poll_once(api, channel, offset, timeout_seconds=timeout_seconds)
        except Exception:
            log.exception("getUpdates failed; backing off")
            await sleep(ERROR_BACKOFF_SECONDS)


def main(env: Mapping[str, str] | None = None) -> int:  # pragma: no cover - needs services
    """Development entry point: real Postgres, real model, in-memory everything else."""
    from ripple.agents.checkpoints import memory_saver
    from ripple.api.wiring import Settings, build_services
    from ripple.core.clock import SystemClock
    from ripple.notify.inbound.wiring import (
        channel_from_env,
        development_conversation_agent,
    )

    logging.basicConfig(level=logging.INFO)
    env = os.environ if env is None else env
    log.warning("telegram long polling is for development only; production uses the webhook")
    settings = Settings.from_env(env)
    services = build_services(settings)
    api = TelegramBotApi.from_env(SystemClock(), env=env)
    conversation = development_conversation_agent(services, settings, checkpointer=memory_saver())
    channel = channel_from_env(services, conversation, api, env)
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(poll_forever(api, channel))
    return 0


if __name__ == "__main__":  # pragma: no cover - developer entry point
    raise SystemExit(main())
