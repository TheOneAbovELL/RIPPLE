import asyncio
import logging
from io import BytesIO

import pytest
from pypdf import PdfReader, PdfWriter

from ripple.core.change_detection import ChangeClassification, ChangeKind
from ripple.core.errors import LLMOutputInvalidError, RippleError
from ripple.core.intake import Intake
from ripple.core.links import LinkTypeRegistry
from ripple.core.models import Sensitivity, Status, StructuredFact
from ripple.core.ripple import RippleRunner
from ripple.domains.jobs.parsers import (
    UnparseableResumeError,
    candidate_to_statement,
    extract_text,
    parse_resume,
)
from ripple.domains.jobs.vocabulary import DOMAIN, PROFILE_SUBJECT, CandidateFact
from tests.domains.jobs_parsers.support import (
    RESUME_TEXT,
    build_pdf,
    candidate,
    pdf_with_lines,
    resume_reply,
    router_for,
)
from tests.fakes.clock import FakeClock
from tests.fakes.engine import ScriptedEngine
from tests.fakes.llm import FakeLLM
from tests.fakes.resolver import ScriptedResolver
from tests.fakes.store import InMemoryStore

FULL_REPLY = resume_reply(
    {"attribute": "cgpa", "value": "8.1", "quote": "CGPA: 8.1 / 10"},
    {"attribute": "batch", "value": "2023-2027", "quote": "2023-2027"},
    {
        "attribute": "branch",
        "value": "Computer Science and Engineering",
        "quote": "B.Tech Computer Science and Engineering",
    },
    {"attribute": "skill", "value": "Python", "quote": "Skills: Python, Go, PostgreSQL"},
    {"attribute": "skill", "value": "Go", "quote": "Skills: Python, Go, PostgreSQL"},
    {"attribute": "skill", "value": "PostgreSQL", "quote": "Skills: Python, Go, PostgreSQL"},
    {"attribute": "project", "value": "Ripple", "quote": "Projects: Ripple"},
    {
        "attribute": "preference",
        "value": "backend roles in Bengaluru",
        "quote": "Open to backend roles in Bengaluru",
    },
)


def _parse(llm: FakeLLM, text: str = RESUME_TEXT, **kwargs) -> list[CandidateFact]:
    return asyncio.run(parse_resume(router_for("resume_parser", llm, **kwargs), text))


# ---- extract_text -------------------------------------------------------------------


def test_extract_text_reads_the_text_layer_of_a_pdf():
    text = extract_text(pdf_with_lines("Omjee R Giri", "CGPA: 8.1 / 10", "Skills: Python, Go"))
    assert text.splitlines() == ["Omjee R Giri", "CGPA: 8.1 / 10", "Skills: Python, Go"]


def test_extract_text_joins_pages_with_a_blank_line():
    text = extract_text(pdf_with_lines("Same page text", pages=2))
    assert text == "Same page text\n\nSame page text"


def test_extract_text_raises_when_pdf_has_no_text_layer():
    with pytest.raises(UnparseableResumeError, match="no text layer"):
        extract_text(build_pdf(b""))


def test_extract_text_raises_when_bytes_are_not_a_pdf():
    with pytest.raises(UnparseableResumeError, match="not a readable PDF"):
        extract_text(b"\x89PNG\r\n\x1a\n not a pdf")


def test_extract_text_raises_when_pdf_is_password_protected():
    writer = PdfWriter(clone_from=PdfReader(BytesIO(pdf_with_lines("secret resume"))))
    writer.encrypt("hunter2", algorithm="RC4-128")
    locked = BytesIO()
    writer.write(locked)
    with pytest.raises(UnparseableResumeError, match="password"):
        extract_text(locked.getvalue())


def test_unparseable_resume_error_is_a_ripple_error():
    assert issubclass(UnparseableResumeError, RippleError)


# ---- parse_resume -------------------------------------------------------------------


def test_parse_resume_returns_candidates_with_spans_into_the_text():
    candidates = _parse(FakeLLM(FULL_REPLY))
    assert candidates, "expected candidates"
    for found in candidates:
        assert RESUME_TEXT[found.span.start : found.span.end] == found.span.text
        assert found.content


def test_parse_resume_parses_cgpa_to_float_and_batch_to_int():
    by_attribute = {c.attribute: c for c in _parse(FakeLLM(FULL_REPLY))}
    assert by_attribute["cgpa"].value == 8.1 and isinstance(by_attribute["cgpa"].value, float)
    assert by_attribute["batch"].value == 2027 and isinstance(by_attribute["batch"].value, int)
    # Wording comes from the shared profile template, not from this module or the model.
    assert by_attribute["cgpa"].content == "CGPA is 8.1"
    assert by_attribute["batch"].content == "graduating batch is 2027"


def test_parse_resume_reads_a_short_year_range_as_the_graduation_year():
    text = "B.Tech CSE, 2023-27\nCGPA 8.1"
    llm = FakeLLM(resume_reply({"attribute": "batch", "value": "2023-27", "quote": "2023-27"}))
    [batch] = _parse(llm, text)
    assert batch.value == 2027


def test_parse_resume_emits_one_candidate_per_skill():
    skills = [c for c in _parse(FakeLLM(FULL_REPLY)) if c.attribute == "skill"]
    assert [s.value for s in skills] == ["Python", "Go", "PostgreSQL"]
    assert [s.content for s in skills] == ["knows Python", "knows Go", "knows PostgreSQL"]


def test_parse_resume_splits_a_skill_list_the_model_failed_to_split():
    llm = FakeLLM(
        resume_reply(
            {
                "attribute": "skill",
                "value": "Python, Go and PostgreSQL",
                "quote": "Python, Go, PostgreSQL",
            }
        )
    )
    assert [c.value for c in _parse(llm)] == ["Python", "Go", "PostgreSQL"]


def test_parse_resume_keeps_a_slash_inside_a_single_skill_name():
    text = "Skills: CI/CD, TCP/IP"
    llm = FakeLLM(resume_reply({"attribute": "skill", "value": "CI/CD", "quote": "CI/CD"}))
    assert [c.value for c in _parse(llm, text)] == ["CI/CD"]


def test_parse_resume_passes_model_confidence_through():
    llm = FakeLLM(
        resume_reply({"attribute": "skill", "value": "Go", "quote": "Go", "confidence": 0.4})
    )
    [go] = _parse(llm)
    assert go.confidence == 0.4


def test_parse_resume_keeps_one_candidate_per_attribute_and_value():
    llm = FakeLLM(
        resume_reply(
            {"attribute": "skill", "value": "Go", "quote": "Go"},
            {"attribute": "skill", "value": "Go", "quote": "Python, Go"},
        )
    )
    assert [c.value for c in _parse(llm)] == ["Go"]


def test_parse_resume_drops_candidate_whose_quote_is_not_in_text_and_logs(caplog):
    llm = FakeLLM(
        resume_reply(
            {"attribute": "cgpa", "value": 9.0, "quote": "CGPA: 9.0"},
            {"attribute": "skill", "value": "Go", "quote": "Go"},
        )
    )
    with caplog.at_level(logging.INFO, logger="ripple.domains.jobs.parsers.resume"):
        candidates = _parse(llm)
    assert [c.attribute for c in candidates] == ["skill"]
    assert any("quote not in text" in record.message for record in caplog.records)
    assert len(llm.calls) == 1


def test_parse_resume_drops_cgpa_that_is_not_a_number_on_a_ten_point_scale():
    llm = FakeLLM(
        resume_reply(
            {"attribute": "cgpa", "value": "excellent", "quote": "CGPA: 8.1 / 10"},
            {"attribute": "cgpa", "value": 81, "quote": "CGPA: 8.1 / 10"},
        )
    )
    assert _parse(llm) == []


def test_parse_resume_rejects_attributes_a_resume_cannot_state():
    # accepted_offer and looking are decisions made in conversation, never read off a
    # document; the schema refuses them so they are retried, then rejected (I4, I5).
    llm = FakeLLM(
        resume_reply({"attribute": "accepted_offer", "value": "Acme", "quote": "Omjee"}),
        resume_reply({"attribute": "looking", "value": "no", "quote": "Omjee"}),
    )
    with pytest.raises(LLMOutputInvalidError):
        _parse(llm, max_retries=1)


def test_parse_resume_retries_invalid_schema_then_accepts():
    llm = FakeLLM(
        '{"candidates": [{"attribute": "cgpa", "value": 8.1}]}',  # missing quote
        resume_reply({"attribute": "cgpa", "value": 8.1, "quote": "CGPA: 8.1 / 10"}),
    )
    [cgpa] = _parse(llm)
    assert cgpa.value == 8.1
    assert len(llm.calls) == 2
    assert "quote" in llm.calls[1].messages[-1].content


def test_parse_resume_rejects_after_retry_budget():
    with pytest.raises(LLMOutputInvalidError):
        _parse(FakeLLM("nope", "nope"), max_retries=1)


def test_parse_resume_sends_resume_text_in_user_message_only():
    llm = FakeLLM(resume_reply())
    _parse(llm)
    [system, user] = llm.calls[0].messages
    assert system.role == "system" and "Omjee" not in system.content
    assert "```text\n" + RESUME_TEXT in user.content


# ---- candidate_to_statement ---------------------------------------------------------


def test_candidate_to_statement_builds_a_profile_fact_statement():
    statement = candidate_to_statement(candidate(confidence=0.7), "student-1", "resume:upload-9")
    assert statement.user_id == "student-1"
    assert statement.domain == DOMAIN and statement.kind == "fact"
    assert statement.content == "CGPA is 8.1"
    assert statement.structured == StructuredFact(
        subject=PROFILE_SUBJECT, attribute="cgpa", value=8.1
    )
    assert statement.source_ref == "resume:upload-9#60-74"
    assert statement.created_by == "user"
    assert statement.confidence == 1.0  # confirmed by the user, not guessed by the model
    assert statement.sensitivity is Sensitivity.MEDIUM  # the profile builder's choice for CGPA


def test_candidate_to_statement_passes_origin_through():
    statement = candidate_to_statement(
        candidate("skill", "Go", text="Go", content="knows Go"), "u", "resume:1", origin="inspector"
    )
    assert statement.origin == "inspector"


def test_candidate_to_statement_result_is_ingested_as_a_valid_profile_memory():
    store, clock = InMemoryStore(), FakeClock()

    class NoLinks:
        async def propose(self, memory, candidates):
            return []

    class AlwaysNew:
        async def classify(self, content, structured, candidates):
            return ChangeClassification(kind=ChangeKind.NEW, reason="first fact")

    runner = RippleRunner(store, ScriptedResolver({}), clock, engine_factory=ScriptedEngine)  # type: ignore[arg-type]
    intake = Intake(store, clock, LinkTypeRegistry(), NoLinks(), AlwaysNew(), runner)
    statement = candidate_to_statement(candidate(), "student-1", "resume:upload-9")

    result = asyncio.run(intake.ingest(statement))
    assert result.change_kind is ChangeKind.NEW
    assert result.memory.status is Status.VALID
    assert result.memory.structured == StructuredFact(
        subject=PROFILE_SUBJECT, attribute="cgpa", value=8.1
    )
    assert result.memory.source_ref == "resume:upload-9#60-74"
