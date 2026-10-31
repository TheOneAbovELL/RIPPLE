"""Wiring for the Scout agent tests (tests/agents/test_scout*.py), kept in the WS-9 test
tree: the fixture career site behind httpx.MockTransport, a FakeLLM behind the real Router
for the JD parser, InMemoryStore, FakeClock and a ScriptedEngine runner (the author's
WaveEngine is not needed)."""

import json

from ripple.agents.scout import ScoutAgent
from ripple.core.ripple import RippleRunner
from ripple.domains.jobs.derive import derive_criteria
from ripple.domains.jobs.sources.dedupe import InMemoryScoutLedger
from ripple.domains.jobs.sources.registry import SourceRegistry
from tests.builders import fact
from tests.domains.jobs.helpers import USER, make_runner, run
from tests.domains.jobs_parsers.support import router_for
from tests.domains.jobs_sources.support import Recorder, acme_routes, career_page, fetcher, registry
from tests.fakes.clock import FakeClock
from tests.fakes.llm import FakeLLM
from tests.fakes.store import InMemoryStore


def jd_reply(*fields: dict) -> str:
    return json.dumps({"fields": list(fields)})


# Replies quoting the fixture detail pages (tests/domains/jobs_sources/fixtures).
REPLY_42 = jd_reply(
    {
        "attribute": "title",
        "value": "Software Engineer Intern",
        "quote": "Software Engineer Intern",
    },
    {"attribute": "company", "value": "Acme Robotics", "quote": "Acme Robotics"},
    {"attribute": "role_type", "value": "internship", "quote": "Intern"},
    {"attribute": "location", "value": "Bengaluru, India", "quote": "Bengaluru, India"},
    {"attribute": "batch", "value": "2027", "quote": "B.Tech 2027 batch"},
    {"attribute": "cgpa_cutoff", "value": "7.5", "quote": "CGPA 7.5 and above"},
    {"attribute": "required_skill", "value": "Python", "quote": "Python"},
    {"attribute": "required_skill", "value": "ROS", "quote": "ROS"},
    {
        "attribute": "deadline",
        "value": "15 November 2026, 11:59 PM IST",
        "quote": "Apply by 15 November 2026, 11:59 PM IST",
    },
)
REPLY_43 = jd_reply(
    {"attribute": "title", "value": "Data Platform Engineer", "quote": "Data Platform Engineer"},
    {"attribute": "company", "value": "Acme Robotics", "quote": "Acme Robotics"},
    {"attribute": "role_type", "value": "full_time", "quote": "full time"},
    {"attribute": "batch", "value": "2026", "quote": "2026 batch"},
    {"attribute": "cgpa_cutoff", "value": "9.0", "quote": "CGPA 9.0 and above"},
    {"attribute": "required_skill", "value": "Spark", "quote": "Spark"},
    {"attribute": "deadline", "value": "30 November 2026", "quote": "30 November 2026"},
)
REPLY_NO_TITLE = jd_reply({"attribute": "location", "value": "Remote", "quote": "Remote"})


def profile(store: InMemoryStore, clock: FakeClock, runner: RippleRunner, user_id: str = USER):
    """CGPA 8.1, batch 2027, Python and SQL, then the derived criteria memory."""

    async def write():
        async with store.transaction() as tx:
            await tx.add_memory(fact("student", "cgpa", 8.1, user_id=user_id, at=clock.now()))
            await tx.add_memory(fact("student", "batch", 2027, user_id=user_id, at=clock.now()))
            await tx.add_memory(fact("student", "skill", "Python", user_id=user_id, at=clock.now()))
            await tx.add_memory(fact("student", "skill", "SQL", user_id=user_id, at=clock.now()))

    run(write())
    criteria = run(derive_criteria(store, clock, runner, user_id))
    assert criteria is not None
    return criteria


def scout(
    *,
    llm: FakeLLM,
    recorder: Recorder | None = None,
    sources: SourceRegistry | None = None,
    store: InMemoryStore | None = None,
    clock: FakeClock | None = None,
    runner: RippleRunner | None = None,
    ledger: InMemoryScoutLedger | None = None,
    max_candidates_per_source: int = 25,
) -> tuple[ScoutAgent, InMemoryStore, FakeClock, Recorder]:
    store = store or InMemoryStore()
    clock = clock or FakeClock()
    runner = runner or make_runner(store, clock)
    recorder = recorder or acme_routes()
    source_fetcher, _ = fetcher(recorder, clock)
    agent = ScoutAgent(
        store=store,
        clock=clock,
        runner=runner,
        router=router_for("jd_parser", llm),
        registry=sources or registry(career_page()),
        fetcher=source_fetcher,
        ledger=ledger,
        max_candidates_per_source=max_candidates_per_source,
    )
    return agent, store, clock, recorder
