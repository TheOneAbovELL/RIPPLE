"""/healthz and /readyz (ADR-0098) with probes that succeed, fail and hang."""

import asyncio
from datetime import timedelta

from httpx import ASGITransport, AsyncClient

from ripple.api.app import create_app
from ripple.api.health import Readiness
from tests.api.harness import BASE_URL, Harness, body


async def _ok() -> None:
    return None


async def _broken() -> None:
    raise ConnectionRefusedError("postgres down")


async def _hangs() -> None:
    await asyncio.sleep(60)


def _app(readiness: Readiness | None):
    return create_app(Harness.build().services, readiness=readiness)


async def _get(app, path: str):
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as c:
        return await c.get(path)


def test_healthz_answers_without_a_token():
    response = asyncio.run(_get(_app(None), "/healthz"))
    assert response.status_code == 200
    assert body(response) == {"status": "ok"}


def test_readyz_is_200_when_every_probe_passes():
    app = _app(Readiness({"postgres": _ok, "redis": _ok}))
    response = asyncio.run(_get(app, "/readyz"))
    assert response.status_code == 200
    assert body(response) == {"status": "ready", "checks": {"postgres": "ok", "redis": "ok"}}


def test_readyz_is_503_naming_the_failing_probe_by_exception_type_only():
    app = _app(Readiness({"postgres": _broken, "redis": _ok}))
    response = asyncio.run(_get(app, "/readyz"))
    assert response.status_code == 503
    out = body(response)
    assert out["status"] == "not ready"
    assert out["checks"] == {"postgres": "error: ConnectionRefusedError", "redis": "ok"}
    assert "postgres down" not in response.text  # messages may carry hosts or credentials


def test_readyz_times_out_a_hanging_probe_instead_of_hanging_itself():
    app = _app(Readiness({"redis": _hangs}, timeout=timedelta(milliseconds=50)))
    response = asyncio.run(asyncio.wait_for(_get(app, "/readyz"), timeout=5))
    assert response.status_code == 503
    assert body(response)["checks"] == {"redis": "timeout"}


def test_readyz_with_no_probes_configured_is_ready_with_empty_checks():
    response = asyncio.run(_get(_app(None), "/readyz"))
    assert response.status_code == 200
    assert body(response)["checks"] == {}


def test_health_routes_stay_out_of_the_openapi_document():
    paths = _app(None).openapi()["paths"]
    assert "/healthz" not in paths and "/readyz" not in paths
