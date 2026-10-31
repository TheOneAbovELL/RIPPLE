import asyncio

import httpx
import pytest

from ripple.domains.jobs.sources.cache import InMemoryFetchCache
from ripple.domains.jobs.sources.fetcher import FetchFailedError, FetchRefusedError, SourceFetcher
from tests.domains.jobs_sources.support import (
    ACME,
    USER_AGENT,
    Recorder,
    acme_routes,
    advancing_sleeper,
    career_page,
    client,
    fetcher,
    fixture,
    forwarded_email,
    html,
    robots,
)
from tests.fakes.clock import FakeClock


def _fetch(f: SourceFetcher, source=None, url=None):
    return asyncio.run(f.fetch(source or career_page(), url))


# ---- what a fetch looks like -----------------------------------------------------------


def test_fetcher_gets_the_listing_with_our_user_agent_after_robots_txt():
    recorder = acme_routes()
    f, _ = fetcher(recorder)
    result = _fetch(f)

    assert result.status == 200 and "Open positions" in result.text
    assert result.url == f"{ACME}/jobs"
    assert recorder.urls() == [f"{ACME}/robots.txt", f"{ACME}/jobs"]
    assert all(r.headers["User-Agent"] == USER_AGENT for r in recorder.requests)
    assert recorder.methods() == {"GET"}


def test_fetcher_canonicalises_the_url_it_requests():
    recorder = acme_routes()
    f, _ = fetcher(recorder)
    result = _fetch(f, url=f"{ACME}/jobs/42/?utm_source=mail#top")
    assert result.url == f"{ACME}/jobs/42"
    assert recorder.urls()[-1] == f"{ACME}/jobs/42"


# ---- refusals (I6, ADR-0008) ----------------------------------------------------------


def test_fetcher_refuses_a_url_on_another_host_without_sending_anything():
    recorder = acme_routes()
    f, _ = fetcher(recorder)
    with pytest.raises(FetchRefusedError, match="registered host"):
        _fetch(f, url="https://partner.example.org/jobs/7")
    assert recorder.requests == []


def test_fetcher_refuses_a_path_robots_txt_disallows_and_sends_no_get_for_it():
    recorder = acme_routes()
    f, _ = fetcher(recorder)
    with pytest.raises(FetchRefusedError, match=r"robots\.txt"):
        _fetch(f, url=f"{ACME}/private/salaries")
    assert recorder.urls() == [f"{ACME}/robots.txt"]


def test_fetcher_closes_a_host_whose_robots_txt_fails():
    recorder = acme_routes(**{f"{ACME}/robots.txt": robots(status=500)})
    f, _ = fetcher(recorder)
    with pytest.raises(FetchRefusedError, match=r"robots\.txt"):
        _fetch(f)


def test_fetcher_refuses_a_login_response_instead_of_retrying_or_following_it():
    for status, headers in ((401, {"WWW-Authenticate": "Basic"}), (403, {}), (407, {})):
        recorder = acme_routes(
            **{f"{ACME}/jobs": lambda r, s=status, h=headers: httpx.Response(s, headers=h)}
        )
        f, slept = fetcher(recorder)
        with pytest.raises(FetchRefusedError, match=str(status)):
            _fetch(f)
        assert recorder.urls().count(f"{ACME}/jobs") == 1  # not retried
        assert slept == []


def test_fetcher_refuses_a_redirect_to_another_host():
    recorder = acme_routes(
        **{
            f"{ACME}/jobs": lambda r: httpx.Response(
                302, headers={"Location": "https://login.example.net/sso?next=/jobs"}
            )
        }
    )
    f, _ = fetcher(recorder)
    with pytest.raises(FetchRefusedError, match="registered host"):
        _fetch(f)
    assert all(r.url.host == "careers.acme.example" for r in recorder.requests)


def test_fetcher_follows_a_same_host_redirect_and_reports_the_final_url():
    recorder = acme_routes(
        **{f"{ACME}/old": lambda r: httpx.Response(301, headers={"Location": "/jobs/42"})}
    )
    f, _ = fetcher(recorder)
    result = _fetch(f, url=f"{ACME}/old")
    assert result.url == f"{ACME}/jobs/42"
    assert "Software Engineer Intern" in result.text


def test_fetcher_gives_up_after_too_many_redirects():
    recorder = acme_routes(
        **{f"{ACME}/loop": lambda r: httpx.Response(302, headers={"Location": "/loop"})}
    )
    f, _ = fetcher(recorder)
    with pytest.raises(FetchFailedError, match="redirects"):
        _fetch(f, url=f"{ACME}/loop")


def test_fetcher_refuses_a_forwarded_email_source():
    f, _ = fetcher(acme_routes())
    with pytest.raises(FetchRefusedError, match="forwarded email"):
        _fetch(f, source=forwarded_email())


def test_fetcher_never_keeps_a_cookie_between_requests():
    recorder = acme_routes(
        **{f"{ACME}/jobs": html(fixture("careers.html"), **{"Set-Cookie": "session=abc"})}
    )
    f, _ = fetcher(recorder)
    _fetch(f)
    _fetch(f, url=f"{ACME}/jobs/42")
    assert all("cookie" not in r.headers for r in recorder.requests)


# ---- retries ---------------------------------------------------------------------------


def test_fetcher_retries_a_5xx_with_exponential_backoff_then_succeeds():
    attempts: list[int] = []

    def flaky(request: httpx.Request) -> httpx.Response:
        attempts.append(1)
        if len(attempts) < 3:
            return httpx.Response(503)
        return httpx.Response(200, text="<html>ok</html>", headers={"Content-Type": "text/html"})

    recorder = acme_routes(**{f"{ACME}/jobs": flaky})
    f, slept = fetcher(recorder, backoff_base_seconds=0.5)
    result = _fetch(f)

    assert result.status == 200
    assert len(attempts) == 3
    assert [s for s in slept if s < 1.0 or s == 1.0][:2] == [
        0.5,
        1.0,
    ]  # backoff, not the rate limit


def test_fetcher_raises_after_retries_are_exhausted():
    recorder = acme_routes(**{f"{ACME}/jobs": lambda r: httpx.Response(502)})
    f, _ = fetcher(recorder, max_retries=1)
    with pytest.raises(FetchFailedError, match="502"):
        _fetch(f)
    assert recorder.urls().count(f"{ACME}/jobs") == 2


def test_fetcher_honours_a_numeric_retry_after_on_429_up_to_a_cap():
    calls: list[int] = []

    def throttled(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) == 1:
            return httpx.Response(429, headers={"Retry-After": "7"})
        return httpx.Response(200, text="ok", headers={"Content-Type": "text/html"})

    recorder = acme_routes(**{f"{ACME}/jobs": throttled})
    f, slept = fetcher(recorder)
    _fetch(f)
    assert 7.0 in slept


def test_fetcher_retries_a_transport_error_and_reports_it_when_it_persists():
    def broken(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timed out", request=request)

    recorder = acme_routes(**{f"{ACME}/jobs": broken})
    f, _ = fetcher(recorder, max_retries=1)
    with pytest.raises(FetchFailedError, match="transport"):
        _fetch(f)
    assert recorder.urls().count(f"{ACME}/jobs") == 2


def test_fetcher_does_not_retry_a_404():
    recorder = acme_routes()
    f, _ = fetcher(recorder)
    with pytest.raises(FetchFailedError, match="404"):
        _fetch(f, url=f"{ACME}/jobs/999")
    assert recorder.urls().count(f"{ACME}/jobs/999") == 1


# ---- rate limit ----------------------------------------------------------------------------


def test_fetcher_spaces_requests_to_one_source_by_its_rate_limit():
    clock = FakeClock()
    recorder = acme_routes()
    f, slept = fetcher(recorder, clock)
    source = career_page(rate_limit_per_minute=6)  # one every 10 s
    _fetch(f, source)
    _fetch(f, source, url=f"{ACME}/jobs/42")
    assert any(s == pytest.approx(10.0) for s in slept)


def test_fetcher_slows_down_to_the_crawl_delay_when_robots_txt_asks_for_one():
    recorder = acme_routes()  # fixture robots.txt: Crawl-delay: 5
    f, slept = fetcher(recorder)
    source = career_page(rate_limit_per_minute=600)  # faster than the site allows
    _fetch(f, source)
    _fetch(f, source, url=f"{ACME}/jobs/42")
    assert any(s == pytest.approx(5.0) for s in slept)


def test_fetcher_keeps_separate_buckets_per_source():
    clock = FakeClock()
    recorder = Recorder(
        {
            "https://a.example/robots.txt": robots("User-agent: *\nAllow: /\n"),
            "https://b.example/robots.txt": robots("User-agent: *\nAllow: /\n"),
            "https://a.example/jobs": html("<ul><li class='job'>a</li></ul>"),
            "https://b.example/jobs": html("<ul><li class='job'>b</li></ul>"),
        }
    )
    f, slept = fetcher(recorder, clock)
    _fetch(f, career_page(id="site_a", url="https://a.example/jobs", rate_limit_per_minute=1))
    _fetch(f, career_page(id="site_b", url="https://b.example/jobs", rate_limit_per_minute=1))
    assert all(s < 60 for s in slept)  # each source's first request is immediate


# ---- caching -------------------------------------------------------------------------------


def test_fetcher_revalidates_with_if_none_match_and_serves_the_cached_body_on_304():
    seen_headers: list[dict[str, str]] = []

    def page(request: httpx.Request) -> httpx.Response:
        seen_headers.append(dict(request.headers))
        if request.headers.get("If-None-Match") == '"v1"':
            return httpx.Response(304)
        return httpx.Response(
            200,
            text=fixture("careers.html"),
            headers={
                "Content-Type": "text/html",
                "ETag": '"v1"',
                "Last-Modified": "Mon, 19 Oct 2026 09:00:00 GMT",
            },
        )

    cache = InMemoryFetchCache()
    recorder = acme_routes(**{f"{ACME}/jobs": page})
    clock = FakeClock()
    sleep, _ = advancing_sleeper(clock)
    f = SourceFetcher(client(recorder), clock, user_agent=USER_AGENT, cache=cache, sleeper=sleep)

    first = _fetch(f)
    second = _fetch(f)

    assert first.from_cache is False and second.from_cache is True
    assert second.text == first.text and second.status == 200
    assert "if-none-match" not in seen_headers[0]
    assert seen_headers[1]["if-none-match"] == '"v1"'
    assert seen_headers[1]["if-modified-since"] == "Mon, 19 Oct 2026 09:00:00 GMT"
    assert len(cache) == 1


def test_fetcher_does_not_cache_a_page_without_validators():
    cache = InMemoryFetchCache()
    recorder = acme_routes()
    f = SourceFetcher(client(recorder), FakeClock(), user_agent=USER_AGENT, cache=cache)
    _fetch(f)
    assert len(cache) == 0


def test_fetch_result_decodes_the_charset_from_the_content_type():
    recorder = acme_routes(
        **{
            f"{ACME}/jobs": lambda r: httpx.Response(
                200,
                content="Bengaluru, café".encode("latin-1", errors="replace"),
                headers={"Content-Type": "text/html; charset=latin-1"},
            )
        }
    )
    f, _ = fetcher(recorder)
    assert "café" in _fetch(f).text


def test_fetcher_refuses_a_body_over_the_size_limit():
    recorder = acme_routes(**{f"{ACME}/jobs": html("x" * 100)})
    f = SourceFetcher(client(recorder), FakeClock(), user_agent=USER_AGENT, max_body_bytes=50)
    with pytest.raises(FetchFailedError, match="larger"):
        _fetch(f)
