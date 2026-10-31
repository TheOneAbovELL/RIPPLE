"""Liveness and readiness (ADR-0098).

`/healthz` says the process answers HTTP; Compose and Caddy restart on its failure.
`/readyz` says the process can do work: every configured probe (Postgres `SELECT 1`,
Redis `PING`) must succeed within the timeout, or the answer is 503 naming the checks
that failed, so a deploy waits and a load balancer stops routing. Probes are injected
callables, so the endpoint is tested with fakes that succeed, fail and hang. Both
routes are unauthenticated and kept out of the OpenAPI document: they are for the
platform, not for the dashboard's generated client.
"""

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from datetime import timedelta

from arq.connections import ArqRedis
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

Probe = Callable[[], Awaitable[None]]

DEFAULT_PROBE_TIMEOUT = timedelta(seconds=2)
OK = "ok"
TIMEOUT = "timeout"

router = APIRouter(tags=["ops"], include_in_schema=False)


@dataclass(frozen=True)
class Readiness:
    probes: Mapping[str, Probe] = field(default_factory=dict)
    timeout: timedelta = DEFAULT_PROBE_TIMEOUT

    async def check(self) -> dict[str, str]:
        """Every probe's verdict: "ok", "timeout" or the failure's exception type."""
        names = list(self.probes)
        results = await asyncio.gather(
            *(self._run(self.probes[name]) for name in names), return_exceptions=False
        )
        return dict(zip(names, results, strict=True))

    async def _run(self, probe: Probe) -> str:
        try:
            await asyncio.wait_for(probe(), timeout=self.timeout.total_seconds())
        except TimeoutError:
            return TIMEOUT
        except Exception as exc:  # the verdict names the type, never the message
            return f"error: {type(exc).__name__}"
        return OK


def postgres_probe(engine: AsyncEngine) -> Probe:
    async def probe() -> None:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))

    return probe


def redis_probe(redis: Callable[[], Awaitable[ArqRedis]]) -> Probe:
    async def probe() -> None:
        client = await redis()
        await client.ping()  # pyright: ignore[reportUnknownMemberType]

    return probe


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": OK}


@router.get("/readyz")
async def readyz(request: Request) -> JSONResponse:
    readiness = getattr(request.app.state, "readiness", None)
    checks = await readiness.check() if isinstance(readiness, Readiness) else {}
    ready = all(verdict == OK for verdict in checks.values())
    return JSONResponse(
        status_code=200 if ready else 503,
        content={"status": "ready" if ready else "not ready", "checks": checks},
    )
