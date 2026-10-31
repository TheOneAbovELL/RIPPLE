"""I6 for the delivery side: the worker and notify packages never act on an external
site for the user. The only outbound call is Telegram sendMessage to the user's own
chat. Checked two ways: statically (no other HTTP target or HTTP library in the
modules) and at runtime (a digest run sends only to the directory's chat for that user).
"""

import ast
import asyncio
from datetime import timedelta
from pathlib import Path

import ripple.notify
import ripple.worker
from ripple.notify.delivery_log import InMemoryDeliveryLog
from ripple.notify.digest import DigestService
from ripple.notify.telegram import BOT_API_BASE_URL
from tests.fakes.clock import FakeClock
from tests.fakes.transport import RecordingTransport
from tests.notify.fakes import FakeRecommendationSource, FakeUserDirectory, recommendation

PACKAGES = [Path(ripple.notify.__file__).parent, Path(ripple.worker.__file__).parent]
ALLOWED_URLS = {BOT_API_BASE_URL}
# Libraries that could reach a site other than Telegram; httpx is allowed only in telegram.py.
FORBIDDEN_IMPORTS = {
    "requests",
    "urllib",
    "urllib3",
    "aiohttp",
    "playwright",
    "selenium",
    "http",
    "socket",
    "websockets",
}


def _sources() -> list[tuple[Path, ast.AST]]:
    return [
        (path, ast.parse(path.read_text(encoding="utf-8")))
        for package in PACKAGES
        for path in sorted(package.rglob("*.py"))
    ]


def _url_literals(tree: ast.AST) -> set[str]:
    return {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and ("http://" in node.value or "https://" in node.value)
    }


def _imports(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".", 1)[0])
    return names


def test_invariant_I6_worker_and_notify_never_act_on_external_sites():
    breaches: list[str] = []
    for path, tree in _sources():
        for url in sorted(_url_literals(tree) - ALLOWED_URLS):
            breaches.append(f"{path.name} names URL {url}")
        imports = _imports(tree)
        for name in sorted(imports & FORBIDDEN_IMPORTS):
            breaches.append(f"{path.name} imports {name}")
        if "httpx" in imports and path.name != "telegram.py":
            breaches.append(f"{path.name} imports httpx outside the Telegram transport")
    assert breaches == []

    # Runtime: every message a digest run produces goes to that user's own chat.
    clock = FakeClock()
    transport = RecordingTransport()
    users = FakeUserDirectory({"u1": "chat-1", "u2": "chat-2"})
    hot = recommendation(fit_score=0.95, deadline=clock.now() + timedelta(hours=3))
    service = DigestService(
        FakeRecommendationSource({"u1": [hot], "u2": [hot]}),
        users,
        transport,
        clock,
        delivery_log=InMemoryDeliveryLog(),
    )

    async def run():
        for user_id in await users.active_user_ids():
            await service.send_daily(user_id)
            await service.send_alerts(user_id, clock.now() - timedelta(days=1))

    asyncio.run(run())
    assert {m.chat_id for m in transport.sent} == {"chat-1", "chat-2"}


def test_i6_checker_detects_a_foreign_url_and_a_forbidden_import():
    tree = ast.parse('import requests\nURL = "https://jobs.example.com/apply"\n')
    assert _url_literals(tree) == {"https://jobs.example.com/apply"}
    assert "requests" in _imports(tree) & FORBIDDEN_IMPORTS
