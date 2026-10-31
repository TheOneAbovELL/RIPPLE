import asyncio
from datetime import timedelta

import httpx
import pytest

from ripple.agents.scout import (
    SCOUT_LEASE_TTL,
    EnqueueingScoutTrigger,
    ImmediateScoutTrigger,
    ScoutCriteria,
    ScoutReport,
    criteria_for,
    event_changed_criteria,
    scout_lease_key,
)
from ripple.core.models import Status
from ripple.domains.jobs.openings import record_opening
from ripple.domains.jobs.ranking import JobsRecommender
from ripple.domains.jobs.sources.dedupe import InMemoryScoutLedger
from ripple.domains.jobs.vocabulary import Kind
from ripple.notify.delivery_log import InMemoryDeliveryLog
from ripple.notify.digest import DigestService
from ripple.worker.jobs import JobFailedForUsersError, scout_run
from ripple.worker.lease import InMemoryLease
from tests.domains.jobs.helpers import USER, make_runner, parsed_acme, run
from tests.domains.jobs_sources.scout_support import (
    REPLY_42,
    REPLY_43,
    REPLY_NO_TITLE,
    profile,
    scout,
)
from tests.domains.jobs_sources.support import (
    ACME,
    acme_routes,
    career_page,
    fixture,
    json_page,
    public_api,
    registry,
    robots,
)
from tests.fakes.clock import FakeClock
from tests.fakes.llm import FakeLLM
from tests.fakes.store import InMemoryStore
from tests.fakes.transport import RecordingTransport
from tests.notify.fakes import FakeUserDirectory
from tests.worker.support import context

# ---- end to end -----------------------------------------------------------------------


def test_scout_records_a_fixture_career_page_as_openings_and_recommendations():
    store, clock = InMemoryStore(), FakeClock()
    runner = make_runner(store, clock)
    profile(store, clock, runner)
    agent, _, _, recorder = scout(
        llm=FakeLLM(REPLY_42, REPLY_43), store=store, clock=clock, runner=runner
    )

    report = run(agent.run_for_user(USER))

    acme = report.per_source["acme"]
    counts = (acme.candidates, acme.new, acme.filtered, acme.duplicates, acme.refused)
    assert counts == (3, 1, 1, 0, 1)
    assert report.new == 1 and len(report.recorded_anchor_ids) == 1
    # The off-site link is refused by policy (ADR-0008), which is not an error.
    assert acme.errors == 0 and report.errors == []
    anchor = run(store.get_memory(report.recorded_anchor_ids[0]))
    assert (
        anchor.kind == Kind.OPENING
        and anchor.content == "Software Engineer Intern at Acme Robotics"
    )
    assert anchor.source_ref == f"scout:acme:{ACME}/jobs/42"
    assert anchor.created_by == "scout"
    ranked = run(JobsRecommender(store).recommendations_for(USER, now=clock.now()))
    assert [(r.title, r.company, r.eligible) for r in ranked] == [
        ("Software Engineer Intern", "Acme Robotics", True)
    ]
    assert ranked[0].fit_score > 0  # Python matches
    # The fetches: robots once, the listing, the two same-host detail pages; nothing else.
    assert recorder.urls() == [
        f"{ACME}/robots.txt",
        f"{ACME}/jobs",
        f"{ACME}/jobs/42",
        f"{ACME}/jobs/43",
    ]


def test_scout_openings_reach_the_daily_digest():
    store, clock = InMemoryStore(), FakeClock()
    runner = make_runner(store, clock)
    profile(store, clock, runner)
    agent, _, _, _ = scout(llm=FakeLLM(REPLY_42, REPLY_43), store=store, clock=clock, runner=runner)
    run(agent.run_for_user(USER))
    transport = RecordingTransport(clock)
    digest = DigestService(
        JobsRecommender(store),
        FakeUserDirectory({USER: "chat-1"}),
        transport,
        clock,
        delivery_log=InMemoryDeliveryLog(),
    )

    receipt = run(digest.send_daily(USER))

    assert receipt is not None
    assert "Software Engineer Intern" in transport.texts_for("chat-1")[0]


def test_scout_second_run_counts_duplicates_and_filtered_without_a_model_call():
    store, clock = InMemoryStore(), FakeClock()
    runner = make_runner(store, clock)
    profile(store, clock, runner)
    ledger = InMemoryScoutLedger()
    llm = FakeLLM(REPLY_42, REPLY_43)  # exactly two replies: a third call would fail the test
    agent, _, _, recorder = scout(llm=llm, store=store, clock=clock, runner=runner, ledger=ledger)
    run(agent.run_for_user(USER))
    clock.advance(timedelta(days=1))

    report = run(agent.run_for_user(USER))

    acme = report.per_source["acme"]
    counts = (acme.candidates, acme.new, acme.duplicates, acme.filtered, acme.refused)
    assert counts == (3, 0, 1, 1, 1)
    assert len(llm.calls) == 2
    assert len([m for m in run(store.memories_for_user(USER)) if m.kind == Kind.OPENING]) == 1
    # Known and filtered candidates are not even fetched again.
    assert recorder.urls().count(f"{ACME}/jobs/42") == 1


def test_scout_reparses_a_filtered_opening_once_the_criteria_change():
    store, clock = InMemoryStore(), FakeClock()
    runner = make_runner(store, clock)
    profile(store, clock, runner)  # CGPA 8.1: job 43 (cutoff 9.0) is filtered
    llm = FakeLLM(REPLY_42, REPLY_43, REPLY_43)
    agent, _, _, _ = scout(llm=llm, store=store, clock=clock, runner=runner)
    run(agent.run_for_user(USER))

    async def raise_cgpa():
        # A new criteria memory, as the ripple would write after a CGPA rise.
        criteria = [m for m in await store.memories_for_user(USER) if m.kind == Kind.CRITERIA][-1]
        async with store.transaction() as tx:
            await tx.replace_memory(criteria.model_copy(update={"status": Status.RETIRED}))
            await tx.add_memory(
                criteria.model_copy(
                    update={
                        "id": "criteria-v2",
                        "content": "search openings with cgpa_cutoff <= 9.2; batch 2026",
                        "recorded_at": clock.now() + timedelta(seconds=1),
                    }
                )
            )

    run(raise_cgpa())
    report = run(agent.run_for_user(USER))

    assert report.per_source["acme"].new == 1  # job 43 now admitted
    assert len(llm.calls) == 3


def test_scout_without_a_criteria_memory_records_everything_parseable():
    agent, _, _, _ = scout(llm=FakeLLM(REPLY_42, REPLY_43))
    report = run(agent.run_for_user(USER))
    assert report.criteria_content is None
    assert report.per_source["acme"].new == 2
    assert report.filtered == 0


def test_scout_skips_a_parse_without_a_title_and_never_parses_that_url_again():
    llm = FakeLLM(REPLY_NO_TITLE, REPLY_43)
    agent, _, _, _ = scout(llm=llm)
    report = run(agent.run_for_user(USER))
    assert (report.per_source["acme"].filtered, report.per_source["acme"].new) == (1, 1)
    run(agent.run_for_user(USER))
    assert len(llm.calls) == 2


def test_scout_treats_a_same_role_from_another_url_as_a_duplicate_by_fingerprint():
    store, clock = InMemoryStore(), FakeClock()
    runner = make_runner(store, clock)
    # The user pasted the Acme JD earlier with a different source_ref.
    pasted = parsed_acme(source_ref="paste:1")
    run(record_opening(store, clock, USER, pasted, runner))
    same_role = (
        '{"fields": [{"attribute": "title", "value": "Software Development Engineer Intern", '
        '"quote": "Software Engineer Intern"}, {"attribute": "company", "value": "Acme", '
        '"quote": "Acme Robotics"}]}'
    )
    agent, _, _, _ = scout(
        llm=FakeLLM(same_role, REPLY_43), store=store, clock=clock, runner=runner
    )

    report = run(agent.run_for_user(USER))

    assert report.per_source["acme"].duplicates == 1
    assert len([m for m in run(store.memories_for_user(USER)) if m.kind == Kind.OPENING]) == 2


def test_scout_caps_the_candidates_parsed_per_source():
    llm = FakeLLM(REPLY_42)
    agent, _, _, recorder = scout(llm=llm, max_candidates_per_source=1)
    report = run(agent.run_for_user(USER))
    assert report.per_source["acme"].candidates == 1
    assert recorder.urls().count(f"{ACME}/jobs/43") == 0


def test_scout_counts_a_failing_source_and_continues_with_the_next():
    recorder = acme_routes(
        **{
            "https://api.globex.example/robots.txt": robots("User-agent: *\nAllow: /\n"),
            "https://api.globex.example/v1/jobs": lambda r: httpx.Response(500),
        }
    )
    sources = registry(public_api(), career_page())
    agent, _, _, _ = scout(llm=FakeLLM(REPLY_42, REPLY_43), recorder=recorder, sources=sources)

    report = run(agent.run_for_user(USER))

    assert report.per_source["globex_api"].errors == 1
    assert report.per_source["acme"].new == 2
    assert report.errors[0].source_id == "globex_api" and "500" in report.errors[0].message


def test_scout_reads_a_public_api_source_and_identifies_items_without_a_url_by_their_text():
    recorder = acme_routes(
        **{
            "https://api.globex.example/robots.txt": robots("User-agent: *\nAllow: /\n"),
            "https://api.globex.example/v1/jobs": json_page(fixture("api.json")),
        }
    )
    reply_101 = (
        '{"fields": [{"attribute": "title", "value": "Backend Developer Intern", '
        '"quote": "Backend Developer Intern"}, {"attribute": "company", "value": "Globex Corp", '
        '"quote": "Globex Corp"}]}'
    )
    reply_103 = (
        '{"fields": [{"attribute": "title", "value": "Research Intern", '
        '"quote": "Research Intern"}, '
        '{"attribute": "company", "value": "Initech", "quote": "Initech"}]}'
    )
    agent, store, _, _ = scout(
        llm=FakeLLM(reply_101, reply_103), recorder=recorder, sources=registry(public_api())
    )

    report = run(agent.run_for_user(USER))

    assert report.per_source["globex_api"].new == 2
    refs = sorted(
        m.source_ref or "" for m in run(store.memories_for_user(USER)) if m.kind == Kind.OPENING
    )
    assert refs[0] == "scout:globex_api:https://api.globex.example/postings/101"
    assert refs[1].startswith("scout:globex_api:https://api.globex.example/v1/jobs#item-")


def test_scout_uses_only_the_jd_text_from_the_detail_selector_in_the_parser_call():
    llm = FakeLLM(REPLY_42, REPLY_43)
    agent, _, _, _ = scout(llm=llm)
    run(agent.run_for_user(USER))
    user_message = llm.calls[0].messages[-1].content
    assert "CGPA 7.5 and above" in user_message
    assert "Recruiter login" not in user_message and "Share this job" not in user_message


def test_scout_does_not_fetch_a_disabled_source():
    agent, _, _, recorder = scout(llm=FakeLLM(), sources=registry(career_page(enabled=False)))
    report = run(agent.run_for_user(USER))
    assert report.per_source == {} and recorder.requests == []


# ---- criteria -------------------------------------------------------------------------


def test_scout_criteria_parses_the_content_the_jobs_adapter_writes():
    criteria = ScoutCriteria.from_content(
        "search openings with cgpa_cutoff <= 8.1; batch 2027; skills python, sql"
    )
    # Skills are a graded fit (ADR-0031), not a gate, so they are not parsed.
    assert (criteria.cgpa, criteria.batch) == (8.1, 2027)


def test_scout_criteria_admits_by_cutoff_and_batch_and_passes_a_silent_jd():
    criteria = ScoutCriteria(cgpa=8.1, batch=2027)
    assert criteria.admits(parsed_acme(cutoff=7.8, batch=2027)) is True
    assert criteria.admits(parsed_acme(cutoff=8.1, batch=2027)) is True  # equal counts
    assert criteria.admits(parsed_acme(cutoff=8.5, batch=2027)) is False
    assert criteria.admits(parsed_acme(cutoff=7.8, batch=2026)) is False
    assert criteria.admits(parsed_acme(cutoff=None, batch=None)) is True
    assert ScoutCriteria().admits(parsed_acme(cutoff=9.9, batch=2020)) is True


def test_scout_criteria_fingerprint_changes_with_the_content():
    a = ScoutCriteria.from_content("search openings with cgpa_cutoff <= 8.1")
    b = ScoutCriteria.from_content("search openings with cgpa_cutoff <= 8.5")
    assert a.fingerprint != b.fingerprint and len(a.fingerprint) == 12


def test_criteria_for_returns_the_valid_criteria_memory_and_ignores_a_questioned_one():
    store, clock = InMemoryStore(), FakeClock()
    runner = make_runner(store, clock)
    criteria = profile(store, clock, runner)
    found = run(criteria_for(store, USER))
    assert found is not None and found.cgpa == 8.1 and found.batch == 2027

    async def question():
        async with store.transaction() as tx:
            await tx.replace_memory(criteria.model_copy(update={"status": Status.PENDING_USER}))

    run(question())
    assert run(criteria_for(store, USER)) is None


# ---- triggers -------------------------------------------------------------------------


def test_event_changed_criteria_is_true_for_a_criteria_derivation_and_false_for_an_opening():
    store, clock = InMemoryStore(), FakeClock()
    runner = make_runner(store, clock)
    profile(store, clock, runner)
    events = run(store.change_events_for_user(USER))
    assert run(event_changed_criteria(store, events[-1])) is True
    recorded = run(record_opening(store, clock, USER, parsed_acme(), runner))
    assert run(event_changed_criteria(store, recorded.event)) is False


def test_immediate_trigger_runs_the_scout_for_the_user():
    agent, _, _, _ = scout(llm=FakeLLM(REPLY_42, REPLY_43))
    trigger = ImmediateScoutTrigger(agent)
    run(trigger.on_criteria_changed(USER))
    assert len(trigger.reports) == 1 and trigger.reports[0].new == 2


def test_enqueueing_trigger_hands_the_user_id_to_the_queue():
    queued: list[str] = []

    async def enqueue(user_id: str) -> None:
        queued.append(user_id)

    run(EnqueueingScoutTrigger(enqueue).on_criteria_changed(USER))
    assert queued == [USER]


# ---- the job --------------------------------------------------------------------------


def test_scout_run_scouts_every_active_user_with_an_injected_agent():
    store, clock = InMemoryStore(), FakeClock()
    runner = make_runner(store, clock)
    agent, _, _, _ = scout(
        llm=FakeLLM(REPLY_42, REPLY_43, REPLY_42, REPLY_43), store=store, clock=clock, runner=runner
    )
    ctx = context(store=store, clock=clock, runner=runner, users={"u1": "c1", "u2": None})

    report = asyncio.run(scout_run(ctx, scout=agent))

    assert {u: r.new for u, r in report.by_user.items()} == {"u1": 2, "u2": 2}
    assert report.skipped_leased == [] and report.failed == []


def test_scout_run_skips_a_user_whose_lease_is_held():
    clock = FakeClock()
    leases = InMemoryLease(clock)
    assert asyncio.run(leases.acquire(scout_lease_key("u1"), SCOUT_LEASE_TTL))
    agent, _, _, _ = scout(llm=FakeLLM(REPLY_42, REPLY_43), clock=clock)
    ctx = context(clock=clock, leases=leases, users={"u1": "c1", "u2": "c2"})

    report = asyncio.run(scout_run(ctx, scout=agent))

    assert report.skipped_leased == ["u1"] and list(report.by_user) == ["u2"]
    assert asyncio.run(leases.acquire(scout_lease_key("u2"), SCOUT_LEASE_TTL))  # released


def test_scout_run_isolates_a_failing_user_and_raises_at_the_end():
    class Exploding:
        async def run_for_user(
            self, user_id: str, *, cache: object = None, trace_id: str | None = None
        ) -> ScoutReport:
            if user_id == "u1":
                raise ConnectionError("store down")
            return ScoutReport(user_id=user_id, started_at=FakeClock().now())

    ctx = context(users={"u1": "c1", "u2": "c2"})
    with pytest.raises(JobFailedForUsersError) as info:
        asyncio.run(scout_run(ctx, scout=Exploding()))  # type: ignore[arg-type]
    assert info.value.failed_user_ids == ["u1"]
    assert isinstance(info.value.__cause__, ExceptionGroup)


def test_scout_run_with_the_default_registry_fetches_nothing(monkeypatch):
    from pathlib import Path

    repo = Path(__file__).resolve().parents[2]
    monkeypatch.setenv("RIPPLE_SOURCES_CONFIG", str(repo / "config" / "sources.yaml"))
    monkeypatch.setenv("RIPPLE_LLM_CONFIG", str(repo / "config" / "llm.default.toml"))
    report = asyncio.run(scout_run(context(users={"u1": "c1"})))
    assert report.by_user["u1"].per_source == {}  # the example source is disabled
    assert report.by_user["u1"].new == 0
