"""POST /telegram/webhook: Telegram's delivery of updates in production (ADR-0077).

Not part of the dashboard's API surface (no bearer token, hidden from the OpenAPI
schema). Authentication is Telegram's secret token header, compared in constant time
against TELEGRAM_WEBHOOK_SECRET; a wrong or missing header is 401 and nothing is read.
After that the answer is always 200: the update is processed inside the request under
a hard timeout (one VPS, no queue), and a failure or timeout is logged, not returned,
because a non-2xx makes Telegram redeliver the same update until it gives up.

Wiring: `ripple.api.wiring.app_from_env` mounts the route when TELEGRAM_BOT_TOKEN is
set and attaches the channel in the app's lifespan (checkpoint C3).
"""

import asyncio
import logging
import secrets
from collections.abc import Mapping
from dataclasses import dataclass

from fastapi import APIRouter, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse

from ripple.core.errors import ConfigurationError
from ripple.notify.inbound.channel import TelegramChannel

log = logging.getLogger("ripple.api.telegram")

SECRET_HEADER = "X-Telegram-Bot-Api-Secret-Token"
ENV_WEBHOOK_SECRET = "TELEGRAM_WEBHOOK_SECRET"
DEFAULT_TIMEOUT_SECONDS = 25.0  # under Telegram's own webhook timeout, so we answer first
STATE_KEY = "telegram_webhook"
MOUNTED_KEY = "telegram_webhook_mounted"
RESULT_TIMEOUT = "timeout"
RESULT_NOT_JSON = "not_json"

router = APIRouter(prefix="/telegram", tags=["telegram"], include_in_schema=False)


@dataclass(frozen=True)
class TelegramWebhook:
    channel: TelegramChannel
    secret: str
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS

    def __post_init__(self) -> None:
        if not self.secret:
            raise ConfigurationError(f"{ENV_WEBHOOK_SECRET} is empty; the webhook refuses to start")
        if self.timeout_seconds <= 0:
            raise ConfigurationError("webhook timeout must be positive")


def webhook_secret_from_env(env: Mapping[str, str]) -> str:
    secret = env.get(ENV_WEBHOOK_SECRET, "").strip()
    if not secret:
        raise ConfigurationError(f"{ENV_WEBHOOK_SECRET} is not set")
    return secret


def install_telegram_webhook(app: FastAPI, webhook: TelegramWebhook) -> None:
    """Attach the channel to the app and mount the route; idempotent per app."""
    attach_telegram_webhook(app, webhook)
    mount_telegram_route(app)


def mount_telegram_route(app: FastAPI) -> None:
    """Mount the route without a channel yet; it answers 503 until one is attached.

    Production mounts at build time and attaches in the app's lifespan, because the
    channel's agent needs the Postgres checkpointer that only the lifespan can open.
    """
    # FastAPI mounts included routers lazily, so the route list cannot be inspected
    # for the path; a marker on the app records that the router was mounted.
    if not getattr(app.state, MOUNTED_KEY, False):
        app.include_router(router)
        setattr(app.state, MOUNTED_KEY, True)


def attach_telegram_webhook(app: FastAPI, webhook: TelegramWebhook) -> None:
    setattr(app.state, STATE_KEY, webhook)


def _webhook_of(request: Request) -> TelegramWebhook:
    webhook = getattr(request.app.state, STATE_KEY, None)
    if not isinstance(webhook, TelegramWebhook):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="telegram webhook is not configured",
        )
    return webhook


@router.post("/webhook")
async def receive_update(request: Request) -> JSONResponse:
    webhook = _webhook_of(request)
    presented = request.headers.get(SECRET_HEADER, "")
    if not presented or not secrets.compare_digest(
        presented.encode("utf-8"), webhook.secret.encode("utf-8")
    ):
        log.warning("telegram webhook refused: bad secret token")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="bad secret token")
    try:
        raw: object = await request.json()
    except ValueError:
        log.warning("telegram webhook body was not JSON")
        return JSONResponse({"ok": True, "result": RESULT_NOT_JSON})
    try:
        result = await asyncio.wait_for(webhook.channel.receive(raw), webhook.timeout_seconds)
    except TimeoutError:
        log.error("telegram update timed out", extra={"timeout_seconds": webhook.timeout_seconds})
        return JSONResponse({"ok": True, "result": RESULT_TIMEOUT})
    return JSONResponse({"ok": True, "result": result.value})
