"""POST /openings: pasted or forwarded JDs through the injected parser and recorder."""

import asyncio

from ripple.domains.jobs.vocabulary import OpeningAttribute, ParsedField
from tests.api.fakes import ScriptedOpeningParser, span, unparseable_opening
from tests.api.harness import Harness, body

JD = "Acme Corp is hiring Software Interns. CGPA 7.5 or above. Apply by 2026-11-30."


def test_opening_is_parsed_and_recorded_for_the_token_holder():
    fields = (
        ParsedField(OpeningAttribute.COMPANY, "Acme Corp", span("Acme Corp")),
        ParsedField(OpeningAttribute.CGPA_CUTOFF, 7.5, span("CGPA 7.5", 38), confidence=0.8),
    )
    h = Harness.build(opening_parser=ScriptedOpeningParser(fields))

    async def run():
        user, headers = await h.user()
        async with h.client() as c:
            pasted = await c.post("/openings", json={"text": JD}, headers=headers)
            emailed = await c.post(
                "/openings",
                json={"text": JD, "source": "email", "source_ref": "email:msg-9"},
                headers=headers,
            )
        return user, pasted, emailed

    user, pasted, emailed = asyncio.run(run())
    assert pasted.status_code == 201, pasted.text
    out = body(pasted)
    assert out["opening_memory_id"] == "opening-1"
    assert out["memory_ids"] == ["opening-1", "req-1"]
    assert out["event_id"] == "event-1"
    assert out["source_ref"].startswith("paste:")
    assert out["summary"] == "Intern at Acme"
    assert [
        (f["attribute"], f["value"], f["span_start"], f["span_end"]) for f in out["fields"]
    ] == [
        ("company", "Acme Corp", 0, 9),
        ("cgpa_cutoff", 7.5, 38, 46),
    ]
    assert body(emailed)["source_ref"] == "email:msg-9"
    assert [u for u, _ in h.opening_recorder.recorded] == [user.id, user.id]
    assert h.opening_parser.calls[1][1] == "email:msg-9"


def test_empty_text_is_422_and_parser_errors_are_422():
    h = Harness.build(opening_parser=ScriptedOpeningParser(error=unparseable_opening()))

    async def run():
        _, headers = await h.user()
        async with h.client() as c:
            empty = await c.post("/openings", json={"text": ""}, headers=headers)
            bad = await c.post("/openings", json={"text": "hello"}, headers=headers)
        return empty, bad

    empty, bad = asyncio.run(run())
    assert empty.status_code == 422
    assert bad.status_code == 422
    assert body(bad)["error"] == "OpeningUnparseableError"
    assert h.opening_recorder.recorded == []


def test_an_opening_already_held_is_409_with_its_anchor_not_a_500():
    from ripple.domains.jobs.openings import OpeningAlreadyRecordedError

    async def already_held(user_id, opening):
        raise OpeningAlreadyRecordedError("paste:abc", "opening-7")

    h = Harness.build(
        opening_parser=ScriptedOpeningParser(
            (ParsedField(OpeningAttribute.COMPANY, "Acme Corp", span("Acme Corp")),)
        )
    )
    h.opening_recorder.record = already_held  # type: ignore[method-assign]

    async def run():
        _, headers = await h.user()
        async with h.client() as c:
            return await c.post("/openings", json={"text": JD}, headers=headers)

    duplicate = asyncio.run(run())
    assert duplicate.status_code == 409, duplicate.text
    assert body(duplicate)["error"] == "OpeningAlreadyRecordedError"
    assert "opening-7" in body(duplicate)["detail"]
