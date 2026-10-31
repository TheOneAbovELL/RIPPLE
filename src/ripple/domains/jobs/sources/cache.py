"""Conditional-request cache for fetched pages (ADR-0070, point 3).

A page fetched once with an ETag or Last-Modified header is asked for again with
If-None-Match / If-Modified-Since; a 304 costs the site almost nothing and costs us no
re-extraction. The protocol is small on purpose: the in-memory implementation serves
one worker process; a shared Redis implementation (keys `scout:cache:<url>`, TTL a few
days) is the follow-up named in docs/plans/parallel-execution/ws-9.md and needs no
Postgres table.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class CachedPage:
    url: str  # canonical
    body: bytes
    content_type: str
    fetched_at: datetime
    etag: str | None = None
    last_modified: str | None = None

    @property
    def revalidation_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self.etag:
            headers["If-None-Match"] = self.etag
        if self.last_modified:
            headers["If-Modified-Since"] = self.last_modified
        return headers


class FetchCache(Protocol):
    async def get(self, url: str) -> CachedPage | None: ...

    async def put(self, page: CachedPage) -> None: ...


class InMemoryFetchCache:
    def __init__(self) -> None:
        self._pages: dict[str, CachedPage] = {}

    async def get(self, url: str) -> CachedPage | None:
        return self._pages.get(url)

    async def put(self, page: CachedPage) -> None:
        self._pages[page.url] = page

    def __len__(self) -> int:
        return len(self._pages)
