"""Fetching one allowed source over httpx (ADR-0070, points 2 and 3; I6).

Every request the Scout makes goes through `SourceFetcher.fetch`, which only ever
sends GET, only to the host the registry lists for that source, only after robots.txt
allowed the path, and only at the source's rate. A login page (401, 403, a
WWW-Authenticate header), a redirect to another host or a POST-only flow is refused,
never worked around. Retries cover transport failures, 429 and 5xx with exponential
backoff; a 4xx is final. ETag / Last-Modified revalidation goes through FetchCache.
"""

import asyncio
import contextlib
import logging
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

import httpx

from ripple.core.clock import Clock
from ripple.core.errors import RippleError
from ripple.domains.jobs.sources.cache import CachedPage, FetchCache, InMemoryFetchCache
from ripple.domains.jobs.sources.canonical import canonical_url
from ripple.domains.jobs.sources.ratelimit import Sleeper, TokenBucket
from ripple.domains.jobs.sources.registry import SourceKind, SourceSpec
from ripple.domains.jobs.sources.robots import RobotsPolicy

log = logging.getLogger("ripple.domains.jobs.sources.fetcher")

_REDIRECTS = {301, 302, 303, 307, 308}
_RETRY_STATUSES = {429, 500, 502, 503, 504}
_MAX_RETRY_AFTER_SECONDS = 60.0
_ROBOTS_LIMIT_PER_MINUTE = 30.0


class FetchRefusedError(RippleError):
    """We may not fetch this: wrong host, robots disallow, a login, an off-host redirect.

    Never retried: the refusal is policy (ADR-0008, I6), not a transport problem.
    """

    def __init__(self, url: str, reason: str) -> None:
        self.url = url
        self.reason = reason
        super().__init__(f"fetch of {url!r} refused: {reason}")


class FetchFailedError(RippleError):
    """The site did not give us the page: a final 4xx, or retries exhausted."""

    def __init__(self, url: str, reason: str, *, status: int | None = None) -> None:
        self.url = url
        self.reason = reason
        self.status = status
        super().__init__(f"fetch of {url!r} failed: {reason}")


@dataclass(frozen=True)
class FetchResult:
    url: str  # canonical URL of the page the body belongs to (after same-host redirects)
    status: int
    body: bytes
    content_type: str
    from_cache: bool = False

    @property
    def text(self) -> str:
        charset = "utf-8"
        for part in self.content_type.split(";")[1:]:
            key, _, value = part.strip().partition("=")
            if key.lower() == "charset" and value:
                charset = value.strip().strip('"')
        try:
            return self.body.decode(charset, errors="replace")
        except LookupError:
            return self.body.decode("utf-8", errors="replace")


class SourceFetcher:
    def __init__(
        self,
        client: httpx.AsyncClient,
        clock: Clock,
        *,
        user_agent: str,
        cache: FetchCache | None = None,
        sleeper: Sleeper | None = None,
        max_retries: int = 2,
        backoff_base_seconds: float = 0.5,
        max_redirects: int = 3,
        max_body_bytes: int = 2_000_000,
    ) -> None:
        self._client = client
        self._clock = clock
        self._user_agent = user_agent
        self._cache: FetchCache = cache if cache is not None else InMemoryFetchCache()
        self._sleeper = sleeper
        self._max_retries = max_retries
        self._backoff_base = backoff_base_seconds
        self._max_redirects = max_redirects
        self._max_body = max_body_bytes
        self._buckets: dict[str, TokenBucket] = {}
        # robots.txt fetches are rate-limited too, one bucket for all hosts.
        self._robots_bucket = TokenBucket(_ROBOTS_LIMIT_PER_MINUTE, clock, sleeper=sleeper)
        self.robots = RobotsPolicy(self._fetch_robots, user_agent)

    # ---- public ------------------------------------------------------------------

    async def fetch(self, source: SourceSpec, url: str | None = None) -> FetchResult:
        """GET `url` (default: the source's listing URL) under the source's rules."""
        if source.kind is SourceKind.FORWARDED_EMAIL or source.host is None:
            raise FetchRefusedError(url or source.id, "forwarded email is sent by the user")
        if not source.enabled:
            raise FetchRefusedError(url or source.id, f"source {source.id!r} is disabled")
        target = url if url is not None else source.url
        assert target is not None  # the registry guarantees a url for fetchable kinds
        return await self._fetch_within(source, target, redirects_left=self._max_redirects)

    # ---- the one place that sends a request ----------------------------------------

    async def _fetch_within(
        self, source: SourceSpec, url: str, *, redirects_left: int
    ) -> FetchResult:
        self._require_host(source, url)
        canonical = canonical_url(url)
        if not await self.robots.allows(canonical):
            raise FetchRefusedError(canonical, "robots.txt disallows it for our user agent")
        bucket = await self._bucket_for(source, canonical)
        cached = await self._cache.get(canonical)
        headers = {"User-Agent": self._user_agent, "Accept": "text/html, application/json;q=0.9"}
        if cached is not None:
            headers.update(cached.revalidation_headers)
        for attempt in range(self._max_retries + 1):
            await bucket.acquire()
            try:
                response = await self._get(canonical, headers)
            except httpx.HTTPError as exc:
                if attempt == self._max_retries:
                    raise FetchFailedError(canonical, f"transport: {exc!r}") from exc
                await self._backoff(attempt, None)
                continue
            status = response.status_code
            if status in _RETRY_STATUSES:
                if attempt == self._max_retries:
                    raise FetchFailedError(canonical, f"HTTP {status} after retries", status=status)
                await self._backoff(attempt, response.headers.get("Retry-After"))
                continue
            return await self._finish(source, canonical, response, cached, redirects_left)
        raise AssertionError("unreachable: the retry loop returns or raises")

    async def _get(self, url: str, headers: dict[str, str]) -> httpx.Response:
        # A Set-Cookie from the last response must never become a session on the next
        # request (I6: no auth flows); the jar is emptied before every GET.
        self._client.cookies.clear()
        return await self._client.get(url, headers=headers, follow_redirects=False)

    async def _finish(
        self,
        source: SourceSpec,
        canonical: str,
        response: httpx.Response,
        cached: CachedPage | None,
        redirects_left: int,
    ) -> FetchResult:
        status = response.status_code
        if status == 304 and cached is not None:
            return FetchResult(canonical, 200, cached.body, cached.content_type, from_cache=True)
        if status in {401, 407} or "www-authenticate" in response.headers:
            raise FetchRefusedError(canonical, f"HTTP {status} asks for credentials")
        if status == 403:
            raise FetchRefusedError(canonical, "HTTP 403: the site refuses automated access")
        if status in _REDIRECTS:
            location = response.headers.get("Location")
            if not location:
                raise FetchFailedError(canonical, f"HTTP {status} has no Location", status=status)
            if redirects_left == 0:
                raise FetchFailedError(canonical, "too many redirects", status=status)
            next_url = urljoin(canonical, location)
            return await self._fetch_within(source, next_url, redirects_left=redirects_left - 1)
        if status != 200:
            raise FetchFailedError(canonical, f"HTTP {status}", status=status)
        body = response.content
        if len(body) > self._max_body:
            raise FetchFailedError(canonical, f"body larger than {self._max_body} bytes")
        content_type = response.headers.get("Content-Type", "application/octet-stream")
        etag = response.headers.get("ETag")
        last_modified = response.headers.get("Last-Modified")
        if etag or last_modified:
            await self._cache.put(
                CachedPage(
                    url=canonical,
                    body=body,
                    content_type=content_type,
                    fetched_at=self._clock.now(),
                    etag=etag,
                    last_modified=last_modified,
                )
            )
        return FetchResult(canonical, status, body, content_type)

    # ---- rules -------------------------------------------------------------------

    @staticmethod
    def _require_host(source: SourceSpec, url: str) -> None:
        """Same hostname as the registered URL (any port: a site that redirects to its
        own :8443 is still that site; another host, however similar, is not)."""
        parts = urlsplit(url)
        host = (parts.hostname or "").lower()
        if parts.scheme not in {"http", "https"} or host != source.host:
            raise FetchRefusedError(url, f"not on the registered host {source.host!r}")
        if parts.username or parts.password:
            raise FetchRefusedError(url, "URL carries credentials")

    async def _bucket_for(self, source: SourceSpec, url: str) -> TokenBucket:
        bucket = self._buckets.get(source.id)
        if bucket is None:
            per_minute = float(source.rate_limit_per_minute)
            delay = await self.robots.crawl_delay(url)
            if delay is not None and delay > 0:
                per_minute = min(per_minute, 60.0 / delay)  # the slower of the two rules
            bucket = TokenBucket(per_minute, self._clock, sleeper=self._sleeper)
            self._buckets[source.id] = bucket
        return bucket

    async def _backoff(self, attempt: int, retry_after: str | None) -> None:
        seconds = self._backoff_base * (2**attempt)
        if retry_after is not None:
            # An HTTP-date Retry-After is not parsed; the exponential backoff stands.
            with contextlib.suppress(ValueError):
                seconds = max(seconds, min(float(retry_after), _MAX_RETRY_AFTER_SECONDS))
        sleeper: Sleeper = self._sleeper if self._sleeper is not None else asyncio.sleep
        await sleeper(seconds)

    async def _fetch_robots(self, url: str) -> tuple[int, str]:
        await self._robots_bucket.acquire()
        response = await self._get(url, {"User-Agent": self._user_agent, "Accept": "text/plain"})
        return response.status_code, response.text
