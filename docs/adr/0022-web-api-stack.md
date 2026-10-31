# ADR-0022: Web API stack: FastAPI, uvicorn, httpx, python-multipart
Status: Accepted · Date: 2026-10-19 (under the autonomous mandate)

## Context
CLAUDE.md's stack names FastAPI + Pydantic v2 for the API (FR-12 to FR-15, the
dashboard's client is generated from its OpenAPI schema). No ADR pinned the server, the
test client or file uploads (FR-1 resume upload).

## Decision
`fastapi` with `uvicorn` as the ASGI server, `httpx` for the test client and as the
outbound HTTP client (also used by the Telegram transport, ADR-0025), and
`python-multipart` for multipart uploads. Exact pins in pyproject.toml. All endpoints
are async (ADR-0016). Every API test runs against the in-memory store with FakeLLM.

## Alternatives considered
- Litestar — comparable, smaller community; the author knows FastAPI. Lost.
- Django REST — synchronous by default, heavier than a single-developer pilot needs.
- Starlette alone — FastAPI's typed contracts and OpenAPI are the point.

## Consequences
- Four dependencies, all mainstream. uvicorn runs without uvloop on Windows.
- The API layer may import everything (docs/02 module table); core never imports it.

## Revisit if
OpenAPI generation or multipart handling blocks a requirement.
