"""I5: the agent never invents profile facts, experience or numbers. For the parsers
this means no field or candidate leaves without a span found in the text, and the
deterministic cross-check never produces a number the JD does not state.
I4: output that never matches the schema is rejected, never partially applied."""

import asyncio

import pytest

from ripple.core.errors import LLMOutputInvalidError
from ripple.domains.jobs.parsers import parse_jd, parse_resume
from ripple.domains.jobs.vocabulary import OpeningAttribute
from tests.domains.jobs_parsers.support import (
    JD_TEXT,
    RESUME_TEXT,
    jd_reply,
    resume_reply,
    router_for,
)
from tests.fakes.llm import FakeLLM


def test_invariant_I5_parsers_never_emit_fields_without_a_span():
    # Every item here is plausible and well-formed, but none of the quotes is in the text.
    jd_llm = FakeLLM(
        jd_reply(
            {"attribute": "cgpa_cutoff", "value": 8.0, "quote": "CGPA 8.0 or above"},
            {"attribute": "deadline", "value": "1 December 2026", "quote": "by 1 December 2026"},
            {"attribute": "location", "value": "Remote", "quote": "Remote"},
            {"attribute": "required_skill", "value": "Rust", "quote": "Rust"},
        )
    )
    jd = asyncio.run(parse_jd(router_for("jd_parser", jd_llm), JD_TEXT, "paste:1"))
    # Only the regex cross-check contributes, and it quotes the text it matched.
    assert all(JD_TEXT[f.span.start : f.span.end] == f.span.text for f in jd.fields)
    assert {f.attribute for f in jd.fields} <= {"cgpa_cutoff", "deadline"}
    assert jd.get("location") is None and jd.all("required_skill") == ()

    resume_llm = FakeLLM(
        resume_reply(
            {"attribute": "cgpa", "value": 9.5, "quote": "CGPA: 9.5"},
            {"attribute": "skill", "value": "Rust", "quote": "Rust"},
            {"attribute": "project", "value": "Compiler", "quote": "Built a compiler"},
        )
    )
    candidates = asyncio.run(parse_resume(router_for("resume_parser", resume_llm), RESUME_TEXT))
    assert candidates == []


@pytest.mark.parametrize(
    "text",
    [
        "CGPA: No bar. Stipend: 8 LPA",
        "CGPA/Percentage: 75% or above",
        "Marks are on a 10 CGPA scale; no cutoff announced",
        "Final year students only. Stipend 25,000 per month.",
    ],
)
def test_invariant_I5_regex_cross_check_never_adds_a_number_the_jd_does_not_state(text):
    opening = asyncio.run(parse_jd(router_for("jd_parser", FakeLLM(jd_reply())), text, "p"))
    assert opening.get(OpeningAttribute.CGPA_CUTOFF) is None
    assert opening.get(OpeningAttribute.DEADLINE) is None


def test_invariant_I4_parsers_reject_output_that_never_matches_the_schema():
    jd_llm = FakeLLM("not json", '{"fields": [{"attribute": "salary"}]}', "[]")
    with pytest.raises(LLMOutputInvalidError):
        asyncio.run(parse_jd(router_for("jd_parser", jd_llm), JD_TEXT, "paste:1"))
    resume_llm = FakeLLM("not json", '{"candidates": "none"}', "{}}")
    with pytest.raises(LLMOutputInvalidError):
        asyncio.run(parse_resume(router_for("resume_parser", resume_llm), RESUME_TEXT))
    assert len(jd_llm.calls) == 3 and len(resume_llm.calls) == 3
