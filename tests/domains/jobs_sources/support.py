"""Builders for the sources tests: registry specs, an httpx client over MockTransport
that records every request, fixture pages, and a sleeper that advances the FakeClock.
Not a conftest, so importing from it is an ordinary import."""

from collections.abc import Callable
from datetime import timedelta
from pathlib import Path

import httpx

from ripple.domains.jobs.sources.fetcher import SourceFetcher
from ripple.domains.jobs.sources.ratelimit import Sleeper
from ripple.domains.jobs.sources.registry import (
    ExtractionHint,
    SourceKind,
    SourceRegistry,
    SourceSpec,
)
from tests.fakes.clock import FakeClock

FIXTURES = Path(__file__).parent / "fixtures"
USER_AGENT = "RippleScout/0.1 (test)"
ACME = "https://careers.acme.example"
ROBOTS_TXT = (FIXTURES / "robots.txt").read_text(encoding="utf-8")


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def career_page(
    *,
    id: str = "acme",
    url: str = f"{ACME}/jobs",
    selector: str = "li.job",
    follow_links: bool = True,
    detail_selector: str | None = "article.job-description",
    rate_limit_per_minute: int = 60,
    enabled: bool = True,
    terms_note: str = "Mail from Acme HR dated 2026-10-01 permitting hourly fetches",
) -> SourceSpec:
    return SourceSpec(
        id=id,
        kind=SourceKind.CAREER_PAGE,
        url=url,
        terms_note=terms_note,
        robots_respected=True,
        rate_limit_per_minute=rate_limit_per_minute,
        enabled=enabled,
        parser=ExtractionHint(
            css_selector=selector, follow_links=follow_links, detail_selector=detail_selector
        ),
    )


def public_api(
    *,
    id: str = "globex_api",
    url: str = "https://api.globex.example/v1/jobs",
    rate_limit_per_minute: int = 60,
) -> SourceSpec:
    return SourceSpec(
        id=id,
        kind=SourceKind.PUBLIC_API,
        url=url,
        terms_note="Public API, terms at https://api.globex.example/terms (read 2026-10-20)",
        robots_respected=True,
        rate_limit_per_minute=rate_limit_per_minute,
        parser=ExtractionHint(
            json_items="data.jobs",
            json_text="description",
            json_url="url",
            json_title="title",
        ),
    )


def forwarded_email() -> SourceSpec:
    return SourceSpec(
        id="forwarded_email",
        kind=SourceKind.FORWARDED_EMAIL,
        terms_note="the student forwards it",
        robots_respected=True,
        rate_limit_per_minute=1,
    )


def registry(*sources: SourceSpec) -> SourceRegistry:
    return SourceRegistry(user_agent=USER_AGENT, sources=list(sources))


class Recorder:
    """A MockTransport handler: routes by URL (without query) and records every request."""

    def __init__(self, routes: dict[str, Callable[[httpx.Request], httpx.Response]]) -> None:
        self.routes = routes
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        key = f"{request.url.scheme}://{request.url.host}{request.url.path}"
        route = self.routes.get(key)
        if route is None:
            return httpx.Response(404, text="not found")
        return route(request)

    def urls(self) -> list[str]:
        return [str(r.url) for r in self.requests]

    def methods(self) -> set[str]:
        return {r.method for r in self.requests}


def html(text: str, **headers: str) -> Callable[[httpx.Request], httpx.Response]:
    def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, text=text, headers={"Content-Type": "text/html; charset=utf-8", **headers}
        )

    return respond


def json_page(text: str, **headers: str) -> Callable[[httpx.Request], httpx.Response]:
    def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, text=text, headers={"Content-Type": "application/json", **headers}
        )

    return respond


def robots(text: str = ROBOTS_TXT, status: int = 200) -> Callable[[httpx.Request], httpx.Response]:
    def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, text=text, headers={"Content-Type": "text/plain"})

    return respond


def acme_routes(**extra: Callable[[httpx.Request], httpx.Response]) -> Recorder:
    """The fixture career site: robots, the listing and two detail pages."""
    return Recorder(
        {
            f"{ACME}/robots.txt": robots(),
            f"{ACME}/jobs": html(fixture("careers.html")),
            f"{ACME}/jobs/42": html(fixture("job-42.html")),
            f"{ACME}/jobs/43": html(fixture("job-43.html")),
            **extra,
        }
    )


def client(recorder: Recorder) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(recorder), follow_redirects=False)


def advancing_sleeper(clock: FakeClock) -> tuple[Sleeper, list[float]]:
    """A sleeper that moves the FakeClock instead of waiting, and the seconds it was asked."""
    slept: list[float] = []

    async def sleep(seconds: float) -> None:
        slept.append(seconds)
        clock.advance(timedelta(seconds=seconds))

    return sleep, slept


def fetcher(
    recorder: Recorder,
    clock: FakeClock | None = None,
    *,
    max_retries: int = 2,
    backoff_base_seconds: float = 0.5,
) -> tuple[SourceFetcher, list[float]]:
    clock = clock or FakeClock()
    sleep, slept = advancing_sleeper(clock)
    fetcher = SourceFetcher(
        client(recorder),
        clock,
        user_agent=USER_AGENT,
        sleeper=sleep,
        max_retries=max_retries,
        backoff_base_seconds=backoff_base_seconds,
    )
    return fetcher, slept
