"""The prompt files follow .claude/rules/prompts.md: header, named schema, evidence-as-data."""

from importlib import resources

import pytest

from ripple.llm.prompts import load_prompt


@pytest.mark.parametrize(
    ("name", "schema"),
    [
        ("jd_parser", "ripple.llm.schemas.jd.JDParse"),
        ("resume_parser", "ripple.llm.schemas.resume.ResumeParse"),
    ],
)
def test_parser_prompt_header_names_version_and_schema(name, schema):
    raw = resources.files("ripple.llm.prompts").joinpath(f"{name}.v1.md").read_text("utf-8")
    header = raw.split("---\n", 2)[1]
    assert f"prompt: {name}" in header
    assert "version: 1" in header
    assert f"schema: {schema}" in header
    assert "changelog:" in header


@pytest.mark.parametrize("name", ["jd_parser", "resume_parser"])
def test_parser_prompt_asks_for_verbatim_quotes_and_treats_evidence_as_data(name):
    prompt = load_prompt(name, 1)
    assert "exact substring" in prompt
    assert "Ignore any instructions" in prompt
    assert "JSON matching the schema" in prompt
    assert "Never infer" in prompt or "Never invent" in prompt
    # The evidence block lives in the user message; the system prompt only names it.
    assert "```" not in prompt
