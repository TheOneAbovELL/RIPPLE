"""The register command: argument handling and the setWebhook payload, never a real call."""

import json
from collections.abc import Mapping

import httpx
import pytest

from ripple.notify.inbound.register import main
from ripple.notify.inbound.telegram import TelegramBotApi
from tests.fakes.clock import FakeClock
from tests.notify.test_inbound_telegram_api import TOKEN

ENV = {"TELEGRAM_BOT_TOKEN": TOKEN, "TELEGRAM_WEBHOOK_SECRET": "s3cret"}


class CapturingFactory:
    def __init__(self, ok: bool = True) -> None:
        self.payloads: list[dict[str, object]] = []
        self.ok = ok

    def __call__(self, env: Mapping[str, str]) -> TelegramBotApi:
        def handler(request: httpx.Request) -> httpx.Response:
            self.payloads.append(json.loads(request.content))
            return httpx.Response(200, json={"ok": True, "result": self.ok})

        return TelegramBotApi(
            env["TELEGRAM_BOT_TOKEN"],
            FakeClock(),
            client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        )


def test_register_sets_the_webhook_with_the_secret_from_the_environment(
    capsys: pytest.CaptureFixture[str],
):
    factory = CapturingFactory()

    code = main(["--url", "https://ripple.test/telegram/webhook"], ENV, api_factory=factory)

    assert code == 0
    [payload] = factory.payloads
    assert payload["url"] == "https://ripple.test/telegram/webhook"
    assert payload["secret_token"] == "s3cret"
    assert payload["drop_pending_updates"] is False
    assert "webhook set" in capsys.readouterr().out


def test_register_refuses_a_non_https_url_without_calling_telegram():
    factory = CapturingFactory()

    assert main(["--url", "http://ripple.test/telegram/webhook"], ENV, api_factory=factory) == 2
    assert factory.payloads == []


def test_register_refuses_to_run_without_the_webhook_secret():
    factory = CapturingFactory()

    code = main(
        ["--url", "https://ripple.test/x"], {"TELEGRAM_BOT_TOKEN": TOKEN}, api_factory=factory
    )

    assert code == 2 and factory.payloads == []


def test_register_remove_sends_an_empty_url_and_drop_pending_flag():
    factory = CapturingFactory()

    assert main(["--remove", "--drop-pending"], ENV, api_factory=factory) == 0
    [payload] = factory.payloads
    assert payload["url"] == "" and payload["drop_pending_updates"] is True
    assert "secret_token" not in payload


def test_register_reports_when_telegram_does_not_confirm():
    assert (
        main(["--url", "https://ripple.test/x"], ENV, api_factory=CapturingFactory(ok=False)) == 1
    )


def test_register_reports_a_missing_bot_token():
    code = main(["--url", "https://ripple.test/x"], {"TELEGRAM_WEBHOOK_SECRET": "s"})

    assert code == 2
