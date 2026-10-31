"""Named invariant tests for the Scout (CLAUDE.md): I5 and I6."""

import httpx

from ripple.agents.capabilities import Capability
from ripple.core.models import Memory, StructuredFact
from ripple.domains.jobs.sources.extract import page_text
from ripple.domains.jobs.vocabulary import Kind, OpeningAttribute
from tests.domains.jobs.helpers import USER, run
from tests.domains.jobs_sources.scout_support import REPLY_42, REPLY_43, scout
from tests.domains.jobs_sources.support import ACME, acme_routes, career_page, fixture, registry
from tests.fakes.llm import FakeLLM


def test_invariant_I5_scout_records_only_parsed_fields_with_spans_into_the_page_text():
    llm = FakeLLM(REPLY_42, REPLY_43)
    agent, store, _, _ = scout(llm=llm)
    report = run(agent.run_for_user(USER))
    assert report.new == 2
    page_texts = {
        f"scout:acme:{ACME}/jobs/42": page_text(fixture("job-42.html"), "article.job-description"),
        f"scout:acme:{ACME}/jobs/43": page_text(fixture("job-43.html"), "article.job-description"),
    }
    memories = run(store.memories_for_user(USER))
    anchors = [m for m in memories if m.kind == Kind.OPENING]
    fields: list[tuple[Memory, StructuredFact]] = [
        (m, m.structured) for m in memories if m.kind == Kind.FACT and m.structured is not None
    ]
    assert len(anchors) == 2 and fields
    for field, structured in fields:
        assert field.source_ref is not None
        source, _, span = field.source_ref.rpartition("#")
        start, end = (int(part) for part in span.split("-"))
        text = page_texts[source]
        # The memory's content is the page's own words at the span it cites.
        assert field.content == text[start:end].strip()
        # Typed values come from those words: a title or company is the span itself.
        if structured.attribute in {OpeningAttribute.TITLE, OpeningAttribute.COMPANY}:
            assert structured.value == field.content
    for anchor in anchors:
        by_attribute = {
            s.attribute: s.value for _, s in fields if s.subject == f"opening:{anchor.id}"
        }
        title, company = (
            by_attribute[OpeningAttribute.TITLE],
            by_attribute[OpeningAttribute.COMPANY],
        )
        assert anchor.content == f"{title} at {company}"
    # The parser saw nothing but the page text inside the fence of the user message.
    for call in llm.calls:
        jd = call.messages[-1].content
        assert any(text in jd for text in page_texts.values())


def test_invariant_I6_scout_only_gets_allowed_sources():
    """Every request is a GET to the registered host; a form on the page, an off-site
    link, a login page and a robots-disallowed path never produce a request."""
    recorder = acme_routes(
        **{
            f"{ACME}/jobs/43": lambda r: httpx.Response(
                401, headers={"WWW-Authenticate": "Basic realm=recruiters"}
            )
        }
    )
    agent, _, _, _ = scout(
        llm=FakeLLM(REPLY_42), recorder=recorder, sources=registry(career_page())
    )

    report = run(agent.run_for_user(USER))

    assert report.per_source["acme"].new == 1
    acme = report.per_source["acme"]
    assert (acme.refused, acme.errors) == (2, 0)  # the login page and the off-site link
    assert recorder.methods() == {"GET"}
    assert {r.url.host for r in recorder.requests} == {"careers.acme.example"}
    assert recorder.urls().count(f"{ACME}/jobs/43") == 1  # the 401 was not retried
    assert f"{ACME}/apply" not in recorder.urls()  # the apply form is never submitted
    for request in recorder.requests:
        assert "authorization" not in request.headers and "cookie" not in request.headers
        assert request.content == b""
    assert all("partner.example.org" not in url for url in recorder.urls())


def test_invariant_I6_scout_declares_only_closed_capabilities_and_writes_only_openings():
    agent, _, _, _ = scout(llm=FakeLLM())
    assert agent.capabilities <= set(Capability)
    writes = {c for c in agent.capabilities if "write" in c.value}
    # Openings and the beliefs derived from them; never a profile fact or an answer.
    assert writes == {Capability.MEMORY_WRITE_OPENING, Capability.MEMORY_WRITE_DERIVED}
    assert Capability.MEMORY_ANSWER_QUESTION not in agent.capabilities
    assert Capability.MEMORY_WRITE_VIA_INTAKE not in agent.capabilities
