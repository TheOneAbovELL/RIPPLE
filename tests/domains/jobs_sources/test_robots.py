import asyncio

from ripple.domains.jobs.sources.robots import RobotsPolicy
from tests.domains.jobs_sources.support import ROBOTS_TXT, USER_AGENT


class ScriptedRobots:
    def __init__(self, status: int = 200, text: str = ROBOTS_TXT, error: Exception | None = None):
        self.status, self.text, self.error = status, text, error
        self.calls: list[str] = []

    async def __call__(self, url: str) -> tuple[int, str]:
        self.calls.append(url)
        if self.error is not None:
            raise self.error
        return self.status, self.text


def test_robots_policy_refuses_a_disallowed_path_and_allows_the_rest():
    policy = RobotsPolicy(ScriptedRobots(), USER_AGENT)
    assert asyncio.run(policy.allows("https://careers.acme.example/private/salaries")) is False
    assert asyncio.run(policy.allows("https://careers.acme.example/login")) is False
    assert asyncio.run(policy.allows("https://careers.acme.example/jobs/42")) is True


def test_robots_policy_fetches_robots_txt_once_per_host_per_run():
    fetch = ScriptedRobots()
    policy = RobotsPolicy(fetch, USER_AGENT)
    for path in ("/jobs", "/jobs/42", "/jobs/43"):
        asyncio.run(policy.allows(f"https://careers.acme.example{path}"))
    asyncio.run(policy.allows("https://api.globex.example/v1/jobs"))

    assert fetch.calls == [
        "https://careers.acme.example/robots.txt",
        "https://api.globex.example/robots.txt",
    ]


def test_robots_policy_allows_everything_when_robots_txt_is_missing():
    policy = RobotsPolicy(ScriptedRobots(status=404, text="not found"), USER_AGENT)
    assert asyncio.run(policy.allows("https://careers.acme.example/private/x")) is True


def test_robots_policy_closes_the_host_when_robots_txt_cannot_be_read():
    for fetch in (ScriptedRobots(status=503), ScriptedRobots(error=ConnectionError("down"))):
        policy = RobotsPolicy(fetch, USER_AGENT)
        assert asyncio.run(policy.allows("https://careers.acme.example/jobs")) is False
        assert len(fetch.calls) == 1  # the answer is cached for the run, not retried per URL
        asyncio.run(policy.allows("https://careers.acme.example/jobs/42"))
        assert len(fetch.calls) == 1


def test_robots_policy_reads_the_crawl_delay_for_our_agent():
    policy = RobotsPolicy(ScriptedRobots(), USER_AGENT)
    assert asyncio.run(policy.crawl_delay("https://careers.acme.example/jobs")) == 5.0
    policy = RobotsPolicy(ScriptedRobots(text="User-agent: *\nDisallow: /x\n"), USER_AGENT)
    assert asyncio.run(policy.crawl_delay("https://careers.acme.example/jobs")) is None


def test_robots_policy_applies_rules_for_a_named_agent():
    policy = RobotsPolicy(ScriptedRobots(), "BadBot/1.0")
    assert asyncio.run(policy.allows("https://careers.acme.example/jobs")) is False
