"""Security headers and the request body cap (ADR-0098)."""

import asyncio

from httpx import ASGITransport, AsyncClient

from ripple.api.app import create_app
from ripple.api.middleware import SECURITY_HEADERS, BodySizeLimitMiddleware
from tests.api.harness import BASE_URL, Harness, body

STATEMENT = {"content": "CGPA is 7.6", "kind": "fact"}


def test_every_response_carries_the_security_headers_including_errors():
    h = Harness.build()

    async def run():
        _, headers = await h.user()
        async with h.client() as c:
            ok = await c.get("/me", headers=headers)
            unauthorised = await c.get("/me")
            missing = await c.get("/memories/nope", headers=headers)
        return ok, unauthorised, missing

    for response in asyncio.run(run()):
        for name, value in SECURITY_HEADERS:
            assert response.headers[name.decode()] == value.decode(), (response.status_code, name)
        assert response.headers["content-security-policy"] == (
            "default-src 'none'; frame-ancestors 'none'"
        )
        assert "strict-transport-security" not in response.headers  # Caddy's job (ADR-0029)


def test_the_interactive_docs_keep_the_headers_but_not_the_csp():
    h = Harness.build()

    async def run():
        async with h.client() as c:
            return await c.get("/docs")

    response = asyncio.run(run())
    assert response.status_code == 200
    assert response.headers["x-frame-options"] == "DENY"
    assert "content-security-policy" not in response.headers


def _capped(max_bytes: int):
    h = Harness.build()
    h.app = create_app(h.services, max_body_bytes=max_bytes)
    return h


def test_a_declared_body_over_the_cap_is_413_before_the_handler_runs():
    h = _capped(64)

    async def run():
        _, headers = await h.user()
        async with h.client() as c:
            big = await c.post(
                "/statements", json={"content": "x" * 200, "kind": "fact"}, headers=headers
            )
            small = await c.post("/statements", json=STATEMENT, headers=headers)
        return big, small

    big, small = asyncio.run(run())
    assert big.status_code == 413
    assert body(big)["error"] == "BodyTooLarge"
    assert small.status_code == 201
    assert len(h.store.all_memories()) == 1


def test_a_streamed_body_over_the_cap_is_413_too():
    h = _capped(64)

    async def chunks():
        for _ in range(10):
            yield b'{"content":"' + b"y" * 20 + b'"}'

    async def run():
        _, headers = await h.user()
        async with AsyncClient(transport=ASGITransport(app=h.app), base_url=BASE_URL) as c:
            return await c.post(
                "/statements",
                content=chunks(),
                headers={**headers, "content-type": "application/json"},
            )

    response = asyncio.run(run())
    assert response.status_code == 413
    assert h.store.all_memories() == []


def test_the_cap_does_not_touch_non_http_scopes_or_small_uploads():
    h = _capped(4096)
    pdf = b"%PDF-1.4 " + b"z" * 500

    async def run():
        _, headers = await h.user()
        async with h.client() as c:
            return await c.post(
                "/resume", files={"file": ("r.pdf", pdf, "application/pdf")}, headers=headers
            )

    assert asyncio.run(run()).status_code == 201


def test_body_limit_rejects_a_non_positive_cap():
    try:
        BodySizeLimitMiddleware(lambda s, r, w: None, max_bytes=0)  # type: ignore[arg-type]
    except ValueError:
        return
    raise AssertionError("a zero cap would refuse every request")


def test_the_413_from_the_body_cap_carries_the_security_headers():
    h = _capped(64)

    async def run():
        _, headers = await h.user()
        async with h.client() as c:
            return await c.post(
                "/statements", json={"content": "x" * 200, "kind": "fact"}, headers=headers
            )

    big = asyncio.run(run())
    assert big.status_code == 413
    assert big.headers["x-content-type-options"] == "nosniff"
