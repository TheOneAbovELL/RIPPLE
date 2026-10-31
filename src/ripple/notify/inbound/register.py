"""Register the production webhook with Telegram (ADR-0077).

    python -m ripple.notify.inbound.register --url <public https url>/telegram/webhook
    python -m ripple.notify.inbound.register --remove

Reads TELEGRAM_BOT_TOKEN and TELEGRAM_WEBHOOK_SECRET from the environment and calls
setWebhook once, so the secret Telegram will send in every request is the one the API
compares against. Run from the operator's shell (docs/ops), never by tests: the suite
only exercises argument handling against a mock transport.
"""

import argparse
import asyncio
import os
import sys
from collections.abc import Callable, Mapping, Sequence

from ripple.core.clock import SystemClock
from ripple.core.errors import ConfigurationError
from ripple.notify.inbound.telegram import TelegramBotApi

ENV_WEBHOOK_SECRET = "TELEGRAM_WEBHOOK_SECRET"

ApiFactory = Callable[[Mapping[str, str]], TelegramBotApi]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m ripple.notify.inbound.register",
        description="Point Telegram at this deployment's webhook (or remove the webhook).",
    )
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--url", help="public https URL ending in /telegram/webhook")
    target.add_argument(
        "--remove", action="store_true", help="remove the webhook (switch to long polling)"
    )
    parser.add_argument(
        "--drop-pending",
        action="store_true",
        help="discard updates Telegram queued while no webhook was set",
    )
    return parser


def _default_api(env: Mapping[str, str]) -> TelegramBotApi:
    return TelegramBotApi.from_env(SystemClock(), env=env)


async def register(api: TelegramBotApi, *, url: str, secret: str, drop_pending: bool) -> bool:
    try:
        return await api.set_webhook(url, secret_token=secret, drop_pending_updates=drop_pending)
    finally:
        await api.aclose()


def main(
    argv: Sequence[str] | None = None,
    env: Mapping[str, str] | None = None,
    *,
    api_factory: ApiFactory = _default_api,
) -> int:
    args = build_parser().parse_args(argv)
    env = os.environ if env is None else env
    url = "" if args.remove else str(args.url)
    if url and not url.lower().startswith("https:"):
        print("the webhook URL must be https (Telegram refuses anything else)", file=sys.stderr)
        return 2
    secret = env.get(ENV_WEBHOOK_SECRET, "").strip()
    if url and not secret:
        print(f"{ENV_WEBHOOK_SECRET} is not set; refusing to register without it", file=sys.stderr)
        return 2
    try:
        api = api_factory(env)
    except ConfigurationError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    ok = asyncio.run(register(api, url=url, secret=secret, drop_pending=bool(args.drop_pending)))
    if not ok:
        print("telegram did not confirm the webhook change", file=sys.stderr)
        return 1
    print("webhook removed" if not url else f"webhook set: {url}")
    return 0


if __name__ == "__main__":  # pragma: no cover - operator entry point
    raise SystemExit(main())
