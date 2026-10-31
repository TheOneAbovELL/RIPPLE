"""The one place that builds a real HTTP client for the Scout (ADR-0072).

The agents package never imports httpx (tests/agents/test_invariants_agents.py scans
its imports for I6); it receives a SourceFetcher. This module opens the client for a
run and closes it afterwards, so a worker job never leaks connections.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx

from ripple.core.clock import Clock
from ripple.domains.jobs.sources.cache import FetchCache
from ripple.domains.jobs.sources.fetcher import SourceFetcher
from ripple.domains.jobs.sources.ratelimit import Sleeper

DEFAULT_TIMEOUT_SECONDS = 15.0


@asynccontextmanager
async def open_fetcher(
    clock: Clock,
    *,
    user_agent: str,
    cache: FetchCache | None = None,
    sleeper: Sleeper | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> AsyncIterator[SourceFetcher]:
    """A SourceFetcher over an httpx client that lives for the block."""
    # trust_env=False: an HTTPS_PROXY in the worker's environment must not reroute the
    # Scout's requests through a host the registry never named (I6).
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(timeout_seconds), follow_redirects=False, trust_env=False
    ) as client:
        yield SourceFetcher(client, clock, user_agent=user_agent, cache=cache, sleeper=sleeper)
