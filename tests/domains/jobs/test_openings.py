"""record_opening: anchor + one fact per field, atomic, forget cascades (ADR-0030)."""

from datetime import UTC, datetime

import pytest

from ripple.core.errors import InvalidObjectError
from ripple.core.forget import forget
from ripple.core.models import LinkClass, Status, TriggerKind
from ripple.domains.jobs.openings import (
    OpeningAlreadyRecordedError,
    opening_memories,
    record_opening,
)
from ripple.domains.jobs.schemas import OpeningView
from ripple.domains.jobs.vocabulary import (
    Kind,
    OpeningAttribute,
    ParsedField,
    ParsedOpening,
    TextSpan,
    opening_subject,
)
from tests.domains.jobs.helpers import ACME_JD, USER, field, make_runner, parsed_acme, run, span
from tests.fakes.clock import FakeClock
from tests.fakes.store import InMemoryStore


def _record(parsed: ParsedOpening | None = None):
    store, clock = InMemoryStore(), FakeClock()
    runner = make_runner(store, clock)
    recorded = run(record_opening(store, clock, USER, parsed or parsed_acme(), runner))
    return store, clock, recorded


def test_record_opening_writes_anchor_and_one_fact_per_field_with_opening_subject():
    store, _, recorded = _record()
    assert recorded.anchor.kind == Kind.OPENING
    assert recorded.anchor.content == "Software Development Engineer Intern at Acme"
    assert recorded.anchor.source_ref == "https://acme.example/jobs/42"
    assert len(recorded.fields) == len(parsed_acme().fields)
    subject = opening_subject(recorded.anchor.id)
    assert all(f.kind == Kind.FACT and f.structured is not None for f in recorded.fields)
    assert {f.structured.subject for f in recorded.fields if f.structured} == {subject}
    assert len(recorded.all_fields(OpeningAttribute.REQUIRED_SKILL)) == 3
    # The anchor carries the same subject, so it is listed with its fields.
    assert len(run(opening_memories(store, recorded.anchor.id))) == len(recorded.fields) + 1


def test_record_opening_fact_content_is_the_span_text_and_source_ref_carries_offsets():
    _, _, recorded = _record()
    cutoff = recorded.field(OpeningAttribute.CGPA_CUTOFF)
    assert cutoff is not None and cutoff.structured is not None
    assert cutoff.content == "Minimum CGPA: 7.8"
    assert cutoff.structured.value == 7.8
    s = span("Minimum CGPA: 7.8")
    assert cutoff.source_ref == f"https://acme.example/jobs/42#{s.start}-{s.end}"
    assert ACME_JD[s.start : s.end] == cutoff.content


def test_record_opening_links_each_field_to_the_anchor_as_depends_on_fact():
    store, _, recorded = _record()
    links = run(store.dependents_of(recorded.anchor.id))
    assert {link.dependent_id for link in links} == {f.id for f in recorded.fields}
    assert {link.link_type for link in links} == {"depends_on_fact"}
    assert {link.link_class for link in links} == {LinkClass.DEPENDS_ON}


def test_record_opening_forget_anchor_cascades_to_every_field():
    store, clock, recorded = _record()
    event = run(forget(store, clock, recorded.anchor.id))
    assert set(event.deleted_ids) == {recorded.anchor.id, *(f.id for f in recorded.fields)}
    assert store.all_memories() == []
    assert store.all_links() == []


def test_record_opening_opens_one_change_event_with_the_anchor_as_trigger_and_completes():
    store, _, recorded = _record()
    events = store.change_events()
    assert len(events) == 1
    assert events[0].trigger_memory_id == recorded.anchor.id
    assert events[0].trigger_kind is TriggerKind.RIPPLE
    assert recorded.event.completed_at is not None
    assert all(m.status is Status.VALID for m in store.all_memories())


def test_record_opening_sets_valid_from_and_recorded_at_from_the_clock():
    at = datetime(2026, 10, 20, 8, 0, tzinfo=UTC)
    store, clock = InMemoryStore(), FakeClock(at)
    recorded = run(record_opening(store, clock, USER, parsed_acme(), make_runner(store, clock)))
    assert recorded.anchor.recorded_at == at and recorded.anchor.valid_from == at
    assert all(f.recorded_at == at for f in recorded.fields)


@pytest.mark.parametrize(
    "bad",
    [
        field(OpeningAttribute.DEADLINE, "next friday", "Apply by 2026-11-05T09:00:00+00:00"),
        field(
            OpeningAttribute.DEADLINE, "2026-11-05T09:00:00", "Apply by 2026-11-05T09:00:00+00:00"
        ),
        field(OpeningAttribute.CGPA_CUTOFF, "7.8", "Minimum CGPA: 7.8"),
        field(OpeningAttribute.CGPA_CUTOFF, 11.0, "Minimum CGPA: 7.8"),
        field(OpeningAttribute.BATCH, "2027", "Eligible batch: 2027"),
        ParsedField(attribute="salary", value="12 LPA", span=span("Acme")),
        field(OpeningAttribute.COMPANY, "   ", "Acme"),
        field(OpeningAttribute.BATCH, 2028, "Eligible batch: 2027"),
        ParsedField(
            attribute=OpeningAttribute.LOCATION,
            value="Pune",
            span=TextSpan(start=0, end=4, text="Pune"),
        ),
        ParsedField(attribute=OpeningAttribute.LOCATION, value="Pune", span=TextSpan(0, 0, "")),
    ],
    ids=[
        "prose deadline",
        "naive deadline",
        "string cutoff",
        "cutoff > 10",
        "string batch",
        "unknown attribute",
        "empty value",
        "second batch",
        "span not in source",
        "empty span",
    ],
)
def test_record_opening_rejects_a_malformed_field_and_writes_nothing(bad: ParsedField):
    store, clock = InMemoryStore(), FakeClock()
    base = parsed_acme()
    parsed = ParsedOpening(
        source_ref=base.source_ref,
        raw_text=base.raw_text,
        fields=(*base.fields, bad),
        summary=base.summary,
    )
    with pytest.raises(InvalidObjectError):
        run(record_opening(store, clock, USER, parsed, make_runner(store, clock)))
    assert store.all_memories() == []
    assert store.change_events() == []


def test_record_opening_rejects_an_empty_summary():
    store, clock = InMemoryStore(), FakeClock()
    base = parsed_acme()
    parsed = ParsedOpening(
        source_ref=base.source_ref, raw_text=base.raw_text, fields=base.fields, summary=" "
    )
    with pytest.raises(InvalidObjectError):
        run(record_opening(store, clock, USER, parsed, make_runner(store, clock)))


def test_opening_view_reads_typed_values_from_the_field_facts():
    store, _, recorded = _record()
    view = OpeningView.from_memories(recorded.anchor, run(store.memories_for_user(USER)))
    assert view.title_value == "Software Development Engineer Intern"
    assert view.company_value == "Acme"
    assert view.cgpa_cutoff_value == 7.8
    assert view.batch_value == 2027
    assert view.deadline_value == datetime(2026, 11, 5, 9, 0, tzinfo=UTC)
    assert set(view.required_skill_values) == {"python", "pytorch", "sql"}
    assert view.label == recorded.anchor.content


def test_opening_view_ignores_retired_fields():
    store, _, recorded = _record()
    cutoff = recorded.field(OpeningAttribute.CGPA_CUTOFF)
    assert cutoff is not None

    async def retire():
        async with store.transaction() as tx:
            await tx.replace_memory(cutoff.model_copy(update={"status": Status.RETIRED}))

    run(retire())
    view = OpeningView.from_memories(recorded.anchor, run(store.memories_for_user(USER)))
    assert view.cgpa_cutoff is None


def test_record_opening_rejects_the_same_source_twice():
    store, clock, recorded = _record()
    with pytest.raises(OpeningAlreadyRecordedError) as raised:
        run(record_opening(store, clock, USER, parsed_acme(), make_runner(store, clock)))
    assert raised.value.anchor_id == recorded.anchor.id
    assert len([m for m in store.all_memories() if m.kind == Kind.OPENING]) == 1


def test_record_opening_accepts_the_same_source_again_once_the_first_is_retired():
    store, clock, recorded = _record()

    async def close():
        async with store.transaction() as tx:
            await tx.replace_memory(recorded.anchor.model_copy(update={"status": Status.RETIRED}))

    run(close())
    again = run(record_opening(store, clock, USER, parsed_acme(), make_runner(store, clock)))
    assert again.anchor.id != recorded.anchor.id


def test_record_opening_anchor_carries_a_stable_opening_key():
    _, _, recorded = _record()
    assert recorded.anchor.structured is not None
    assert recorded.anchor.structured.subject == opening_subject(recorded.anchor.id)
    assert recorded.anchor.structured.value == "https://acme.example/jobs/42"
