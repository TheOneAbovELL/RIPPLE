"""tools.local_run: the offline parts (ADR-0132, ADR-0133). Postgres, npm and uvicorn
are exercised by running the command; these tests pin the seed, the site and the text."""

import asyncio
import os
import time
from pathlib import Path

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient
from tools.local_run import (
    SECURITY_HEADERS,
    AskTheStudent,
    DemoReport,
    ExportFiles,
    banner,
    build_dashboard,
    build_site,
    demo_openings,
    export_is_current,
    parsed_opening,
    seed_demo,
)

from ripple.core.models import DecisionAction, Status
from ripple.core.resolver import ResolutionContext
from ripple.domains.jobs.vocabulary import Kind, OpeningAttribute
from tests.builders import derived, fact
from tests.fakes.clock import FakeClock
from tests.fakes.store import InMemoryStore

# ---- the demo seed -----------------------------------------------------------------------


@pytest.fixture(scope="module")
def seeded() -> tuple[InMemoryStore, DemoReport]:
    store, clock = InMemoryStore(), FakeClock()
    report = asyncio.run(seed_demo(store, clock, "demo-user"))
    return store, report


def _live(store: InMemoryStore):
    return [
        m
        for m in asyncio.run(store.memories_for_user("demo-user"))
        if m.status is not Status.RETIRED
    ]


def _eligibility(store: InMemoryStore) -> dict[str, list]:
    """company -> the live eligibility beliefs about its opening."""
    memories = asyncio.run(store.memories_for_user("demo-user"))
    company_of = {
        m.structured.subject: str(m.structured.value)
        for m in memories
        if m.structured is not None and m.structured.attribute == OpeningAttribute.COMPANY
    }
    result: dict[str, list] = {}
    for m in memories:
        if (
            m.kind == Kind.DERIVED
            and m.structured is not None
            and m.structured.attribute == "eligible"
            and m.status is not Status.RETIRED
        ):
            result.setdefault(company_of[m.structured.subject], []).append(m)
    return result


def test_seed_demo_writes_the_profile_and_three_openings(seeded):
    store, report = seeded
    assert report.facts == 7
    assert len(report.openings) == 3
    live = _live(store)
    assert sum(1 for m in live if m.kind == Kind.OPENING) == 3
    assert any(
        m.structured and m.structured.attribute == "cgpa" and m.structured.value == 8.6
        for m in live
    )


def test_seed_demo_cgpa_change_makes_beta_eligible_through_the_ripple(seeded):
    store, report = seeded
    memories = {m.id: m for m in asyncio.run(store.memories_for_user("demo-user"))}
    cgpa_event = next(
        e
        for e in report.events
        if memories[e.trigger_memory_id].content.startswith("My CGPA is 8.6")
    )
    beta = next(
        d
        for d in cgpa_event.decisions
        if memories[d.memory_id].content.startswith("not eligible for Data Science Intern")
    )
    assert beta.action is DecisionAction.UPDATE
    assert beta.new_version_id is not None
    assert memories[beta.new_version_id].content.startswith("eligible for Data Science Intern")


def test_seed_demo_scale_correction_parks_questions_instead_of_guessing(seeded):
    store, report = seeded
    eligibility = _eligibility(store)
    # The two openings with a CGPA cutoff cannot be judged on a 4-point CGPA: asked.
    assert {m.status for m in eligibility["Acme Robotics"]} == {Status.PENDING_USER}
    assert {m.status for m in eligibility["Beta Analytics"]} == {Status.PENDING_USER}
    # Gamma states no cutoff, so the scale changes nothing there.
    assert {m.status for m in eligibility["Gamma Labs"]} == {Status.VALID}
    assert report.asked == 2


def test_seed_demo_every_state_change_has_a_change_event(seeded):
    # I2: each version, retirement, ask and parked doubt is accounted for by an event.
    store, _ = seeded
    memories = asyncio.run(store.memories_for_user("demo-user"))
    events = asyncio.run(store.change_events_for_user("demo-user"))
    assert events and all(e.completed_at is not None for e in events)
    decisions = [d for e in events for d in e.decisions]
    assert all(d.reason for d in decisions)
    triggers = {e.trigger_memory_id for e in events}
    new_versions = {d.new_version_id for d in decisions if d.new_version_id}
    asked = {d.memory_id for d in decisions if d.action is DecisionAction.ASK}
    retired = {d.memory_id for d in decisions if d.action is DecisionAction.RETIRE}
    parked = {m for e in events for ids in e.parked.values() for m in ids}
    superseded = {m.supersedes_id for m in memories if m.supersedes_id}
    for m in memories:
        if m.version > 1:
            assert m.id in triggers | new_versions, m.content
        if m.status is Status.PENDING_USER:
            assert m.id in asked, m.content
        if m.status is Status.SUSPECT:
            assert m.id in parked, m.content
        if m.status is Status.RETIRED:
            assert m.id in superseded | retired, m.content


def test_demo_openings_quote_the_exact_words_they_were_read_from():
    for opening in demo_openings(FakeClock().now()):
        parsed = parsed_opening(opening, f"paste:{opening.slug}")
        for field in parsed.fields:
            assert parsed.raw_text[field.span.start : field.span.end] == field.span.text


def test_ask_the_student_asks_with_the_belief_and_the_change_named():
    trigger = fact("student", "cgpa_scale", 4, content="CGPA is on a 4-point scale")
    belief = derived("eligible for SDE intern at Acme")
    resolution = asyncio.run(
        AskTheStudent().resolve(
            ResolutionContext(trigger=trigger, memory=belief, parents=[], wave=1)
        )
    )
    assert resolution.action is DecisionAction.ASK
    assert "CGPA is on a 4-point scale" in (resolution.question or "")
    assert "eligible for SDE intern at Acme" in (resolution.question or "")
    assert resolution.evidence_refs == (trigger.id,)


# ---- one origin --------------------------------------------------------------------------


@pytest.fixture
def export(tmp_path: Path) -> Path:
    (tmp_path / "index.html").write_text("login page", encoding="utf-8")
    (tmp_path / "home").mkdir()
    (tmp_path / "home" / "index.html").write_text("home page", encoding="utf-8")
    (tmp_path / "_next").mkdir()
    (tmp_path / "_next" / "app.js").write_text("js", encoding="utf-8")
    return tmp_path


def _site(export: Path) -> TestClient:
    api = FastAPI()

    @api.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return TestClient(build_site(api, export))


def test_site_serves_files_then_folder_index_then_the_root_index(export):
    client = _site(export)
    assert client.get("/_next/app.js").text == "js"
    assert client.get("/home/").text == "home page"
    assert client.get("/home").text == "home page"
    assert client.get("/memories/detail/?id=x").text == "login page"
    assert client.get("/").text == "login page"


def test_site_strips_the_api_prefix_like_caddy(export):
    response = _site(export).get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_site_sends_caddys_security_headers_on_static_and_api_responses(export):
    client = _site(export)
    for path in ("/", "/api/health"):
        headers = client.get(path).headers
        for name, value in SECURITY_HEADERS.items():
            assert headers[name] == value
    assert "Strict-Transport-Security" not in client.get("/").headers


def test_export_files_never_serves_outside_the_export(export, tmp_path: Path):
    (tmp_path.parent / "secret.txt").write_text("secret", encoding="utf-8")
    assert ExportFiles(export).resolve("/../secret.txt") == export.resolve() / "index.html"


# ---- the export build --------------------------------------------------------------------


def _web(tmp_path: Path) -> Path:
    web = tmp_path / "web"
    (web / "src").mkdir(parents=True)
    (web / "src" / "page.tsx").write_text("x", encoding="utf-8")
    (web / "openapi.json").write_text("{}", encoding="utf-8")
    return web


def test_export_is_current_only_when_index_is_newer_than_every_source(tmp_path: Path):
    web = _web(tmp_path)
    out = web / "out"
    sources = [web / "src" / "page.tsx", web / "openapi.json"]
    assert not export_is_current(out, sources)
    out.mkdir()
    (out / "index.html").write_text("built", encoding="utf-8")
    assert export_is_current(out, sources)
    later = time.time() + 60
    os.utime(web / "openapi.json", (later, later))
    assert not export_is_current(out, sources)


def test_build_dashboard_reuses_a_current_export_without_running_npm(tmp_path: Path):
    web = _web(tmp_path)
    (web / "out").mkdir()
    later = time.time() + 60
    (web / "out" / "index.html").write_text("built", encoding="utf-8")
    os.utime(web / "out" / "index.html", (later, later))
    calls: list[list[str]] = []
    assert build_dashboard(web, force=False, run=lambda cmd, **_: calls.append(cmd)) == web / "out"
    assert calls == []


def test_build_dashboard_installs_then_builds_when_forced(tmp_path: Path, monkeypatch):
    web = _web(tmp_path)
    monkeypatch.setattr("tools.local_run.shutil.which", lambda _: "npm")
    monkeypatch.setenv("NEXT_PUBLIC_RIPPLE_API_BASE", "http://elsewhere")
    calls: list[tuple[list[str], dict]] = []
    build_dashboard(web, force=True, run=lambda cmd, **kw: calls.append((cmd, kw["env"])))
    assert [cmd for cmd, _ in calls] == [["npm", "ci"], ["npm", "run", "build"]]
    # The export must call /api on its own origin, not a dev override.
    assert all("NEXT_PUBLIC_RIPPLE_API_BASE" not in env for _, env in calls)


# ---- the banner --------------------------------------------------------------------------


def test_banner_lists_what_needs_the_model_key_when_it_is_missing():
    text = banner("http://127.0.0.1:8765", "tok", {}, seeded=None)
    assert "Token:     tok" in text
    assert "ANTHROPIC_API_KEY is not set" in text
    assert "reading a resume PDF" in text
    assert "Works without it" in text
    assert "TELEGRAM_BOT_TOKEN is not set" in text


def test_banner_says_model_features_are_on_with_a_key_and_reports_the_seed():
    report = DemoReport(user_id="u", facts=7, openings=["a", "b", "c"])
    text = banner(
        "http://127.0.0.1:8765",
        "tok",
        {"ANTHROPIC_API_KEY": "k", "TELEGRAM_BOT_TOKEN": "t"},
        seeded=report,
    )
    assert "ANTHROPIC_API_KEY is set" in text
    assert "reading a resume PDF" not in text
    assert "Demo student seeded: 7 profile facts, 3 openings" in text
    assert "ripple.worker.telegram_poll" in text
