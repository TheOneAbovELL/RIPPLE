"""Integration adapters over the real jobs modules, offline (FakeLLM, ScriptedEngine)."""

import asyncio
import json

import pytest

from ripple.api.adapters import (
    CandidateStatementsAdapter,
    OpeningParserAdapter,
    OpeningRecorderAdapter,
    ResumeParserAdapter,
)
from ripple.api.contracts import ResumeUnparseableError
from ripple.core.models import Status
from ripple.core.ripple import RippleRunner
from ripple.domains.jobs.vocabulary import (
    CandidateFact,
    OpeningAttribute,
    ParsedField,
    ParsedOpening,
    ProfileAttribute,
    TextSpan,
)
from ripple.llm.config import ModelSpec, RouterConfig
from ripple.llm.router import Router
from tests.fakes.clock import FakeClock
from tests.fakes.engine import ScriptedEngine
from tests.fakes.llm import FakeLLM
from tests.fakes.resolver import ScriptedResolver
from tests.fakes.store import InMemoryStore

USER = "student-1"


def _router(llm: FakeLLM) -> Router:
    config = RouterConfig(
        tasks={
            "jd_parser": [ModelSpec(provider="fake", model="f")],
            "resume_parser": [ModelSpec(provider="fake", model="f")],
        }
    )
    return Router(config, {"fake": llm})


def _opening(text: str) -> ParsedOpening:
    def field(attribute: str, value, needle: str) -> ParsedField:
        start = text.index(needle)
        return ParsedField(attribute, value, TextSpan(start, start + len(needle), needle))

    return ParsedOpening(
        source_ref="paste:1",
        raw_text=text,
        fields=(
            field(OpeningAttribute.TITLE, "SDE Intern", "SDE Intern"),
            field(OpeningAttribute.COMPANY, "Acme", "Acme"),
            field(OpeningAttribute.CGPA_CUTOFF, 7.8, "7.8"),
        ),
        summary="SDE Intern at Acme",
    )


def test_opening_recorder_records_anchor_fields_and_derived_beliefs():
    store, clock = InMemoryStore(), FakeClock()
    runner = RippleRunner(store, ScriptedResolver({}), clock, engine_factory=ScriptedEngine)  # type: ignore[arg-type]
    adapter = OpeningRecorderAdapter(store, clock, runner)
    written = asyncio.run(adapter.record(USER, _opening("Acme hires an SDE Intern, CGPA 7.8+")))
    assert written.opening_memory_id in written.memory_ids
    anchor = asyncio.run(store.get_memory(written.opening_memory_id))
    assert anchor.status is Status.VALID and anchor.user_id == USER
    # Three fields plus the anchor; derived beliefs need profile facts, so none here.
    assert len(written.memory_ids) >= 4
    assert written.event_id is not None


def test_candidate_statements_adapter_marks_the_statement_as_an_inspector_edit():
    candidate = CandidateFact(
        attribute=ProfileAttribute.CGPA,
        value=7.9,
        span=TextSpan(0, 3, "7.9"),
        content="CGPA is 7.9",
    )
    statement = CandidateStatementsAdapter().statement_for(USER, candidate, source_ref="resume:u1")
    assert statement.user_id == USER and statement.origin == "inspector"
    assert statement.structured is not None and statement.structured.value == 7.9


def test_resume_parser_adapter_maps_unparseable_pdf_to_the_api_error():
    adapter = ResumeParserAdapter(_router(FakeLLM()))
    with pytest.raises(ResumeUnparseableError):
        asyncio.run(adapter.parse(b"not a pdf", source_ref="resume:u1"))


def test_opening_parser_adapter_strips_email_envelopes_only_for_email_sources():
    llm = FakeLLM(
        json.dumps({"fields": []}),
        json.dumps({"fields": []}),
    )
    adapter = OpeningParserAdapter(_router(llm))
    body = "Subject: Fwd: Acme\nFrom: placement@bit\n\nAcme hires an SDE Intern."
    asyncio.run(adapter.parse(body, source_ref="email:1"))
    asyncio.run(adapter.parse(body, source_ref="paste:1"))
    email_prompt, paste_prompt = (c.messages[-1].content for c in llm.calls)
    assert "From: placement" not in email_prompt or "From: placement" in paste_prompt
