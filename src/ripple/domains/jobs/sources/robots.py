"""robots.txt per host, fetched once per run (ADR-0070, point 2; ADR-0008).

The parser is the standard library's; only the fetch is ours, so the policy never
opens a connection the fetcher did not rate-limit. Unknown is treated as closed: a
host whose robots.txt cannot be read (anything but 200 or 4xx: 5xx, a redirect, a
timeout) is not fetched this run. A 4xx (no robots.txt) allows everything, which is
what the protocol says.
"""

import logging
from collections.abc import Awaitable, Callable
from urllib.parse import urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

log = logging.getLogger("ripple.domains.jobs.sources.robots")

# (status, text); a transport failure is raised by the callable and treated as closed.
RobotsFetcher = Callable[[str], Awaitable[tuple[int, str]]]


class RobotsPolicy:
    def __init__(self, fetch: RobotsFetcher, user_agent: str) -> None:
        self._fetch = fetch
        self._user_agent = user_agent
        # None: the host is closed for this run (robots.txt unreadable).
        self._parsers: dict[str, RobotFileParser | None] = {}

    @staticmethod
    def origin_of(url: str) -> str:
        parts = urlsplit(url)
        return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), "", "", ""))

    async def _parser_for(self, url: str) -> RobotFileParser | None:
        origin = self.origin_of(url)
        if origin in self._parsers:
            return self._parsers[origin]
        robots_url = f"{origin}/robots.txt"
        parser = RobotFileParser()
        try:
            status, text = await self._fetch(robots_url)
        except Exception as exc:  # any transport problem: closed for this run
            log.warning(
                "robots.txt unreachable; host closed for this run",
                extra={"origin": origin, "error": repr(exc)},
            )
            self._parsers[origin] = None
            return None
        if status == 200:
            parser.parse(text.splitlines())
        elif 400 <= status < 500:
            parser.parse([])  # no rules at all: the standard library then allows everything
        else:
            log.warning(
                "robots.txt returned %s; host closed for this run", status, extra={"origin": origin}
            )
            self._parsers[origin] = None
            return None
        self._parsers[origin] = parser
        return parser

    async def allows(self, url: str) -> bool:
        parser = await self._parser_for(url)
        return parser is not None and parser.can_fetch(self._user_agent, url)

    async def crawl_delay(self, url: str) -> float | None:
        """Crawl-delay for our agent, in seconds, when the host states one."""
        parser = await self._parser_for(url)
        if parser is None:
            return None
        delay = parser.crawl_delay(self._user_agent)
        return float(delay) if delay is not None else None
