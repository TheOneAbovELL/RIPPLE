"""derive_for_opening / derive_criteria: derived beliefs, their links and their content."""

from datetime import UTC, datetime, timedelta, timezone

import pytest

from ripple.core.errors import InvalidObjectError
from ripple.core.forget import forget
from ripple.core.models import LinkClass, Status
from ripple.domains.jobs.derive import derive_criteria, derive_for_opening
from ripple.domains.jobs.openings import record_opening
from ripple.domains.jobs.profile import record_profile_fact
from ripple.domains.jobs.vocabulary import (
    DerivedAttribute,
    JobsLinkType,
    Kind,
    OpeningAttribute,
    ParsedOpening,
    ProfileAttribute,
    opening_subject,
)
from tests.domains.jobs.helpers import DEADLINE, USER, make_runner, parsed_acme, run
from tests.fakes.clock import FakeClock
from tests.fakes.store import InMemoryStore


def _setup(
    *,
    cgpa: float | None = 7.9,
    batch: int | None = 2027,
    skills: tuple[str, ...] = ("Python", "PyTorch"),
    parsed: ParsedOpening | None = None,
):
    store, clock = InMemoryStore(), FakeClock()
    runner = make_runner(store, clock)
    profile: dict[str, object] = {}
    if cgpa is not None:
        profile["cgpa"], _ = run(
            record_profile_fact(store, clock, runner, USER, ProfileAttribute.CGPA, cgpa)
        )
    if batch is not None:
        profile["batch"], _ = run(
            record_profile_fact(store, clock, runner, USER, ProfileAttribute.BATCH, batch)
        )
    profile["skills"] = [
        run(record_profile_fact(store, clock, runner, USER, ProfileAttribute.SKILL, s))[0]
        for s in skills
    ]
    recorded = run(record_opening(store, clock, USER, parsed or parsed_acme(), runner))
    return store, clock, runner, profile, recorded


def _parent_ids(store: InMemoryStore, memory_id: str) -> set[str]:
    return {link.parent_id for link in run(store.parents_of(memory_id))}


def test_derive_eligibility_links_profile_and_opening_facts_and_cites_their_values():
    store, clock, runner, profile, recorded = _setup()
    beliefs = run(derive_for_opening(store, clock, runner, recorded.anchor.id))
    eligibility = beliefs.eligibility
    assert eligibility is not None and eligibility.structured is not None
    assert eligibility.kind == Kind.DERIVED and eligibility.created_by == "curator"
    assert eligibility.structured.subject == opening_subject(recorded.anchor.id)
    assert eligibility.structured.attribute == DerivedAttribute.ELIGIBLE
    assert eligibility.structured.value is True
    assert eligibility.content == (
        "eligible for Software Development Engineer Intern at Acme: "
        "CGPA 7.9 >= cutoff 7.8; batch 2027 matches required batch 2027"
    )
    cutoff = recorded.field(OpeningAttribute.CGPA_CUTOFF)
    batch = recorded.field(OpeningAttribute.BATCH)
    assert cutoff is not None and batch is not None
    assert _parent_ids(store, eligibility.id) == {
        recorded.anchor.id,
        profile["cgpa"].id,  # type: ignore[attr-defined]
        profile["batch"].id,  # type: ignore[attr-defined]
        cutoff.id,
        batch.id,
    }
    links = run(store.parents_of(eligibility.id))
    assert {link.link_type for link in links} == {JobsLinkType.ELIGIBILITY_OF}
    assert {link.link_class for link in links} == {LinkClass.DEPENDS_ON}


def test_derive_eligibility_is_false_when_cgpa_is_below_the_cutoff():
    store, clock, runner, _, recorded = _setup(cgpa=7.6)
    beliefs = run(derive_for_opening(store, clock, runner, recorded.anchor.id))
    assert beliefs.eligibility is not None and beliefs.eligibility.structured is not None
    assert beliefs.eligibility.structured.value is False
    assert beliefs.eligibility.content.startswith("not eligible for")
    assert "CGPA 7.6 < cutoff 7.8" in beliefs.eligibility.content


def test_derive_eligibility_is_skipped_when_the_profile_lacks_the_cgpa():
    store, clock, runner, _, recorded = _setup(cgpa=None)
    beliefs = run(derive_for_opening(store, clock, runner, recorded.anchor.id))
    assert beliefs.eligibility is None
    assert not [
        m for m in store.all_memories() if m.kind == Kind.DERIVED and "eligible" in m.content
    ]


def test_derive_eligibility_without_constraints_is_eligible_and_depends_on_the_anchor_only():
    store, clock, runner, _, recorded = _setup(parsed=parsed_acme(cutoff=None, batch=None))
    beliefs = run(derive_for_opening(store, clock, runner, recorded.anchor.id))
    assert beliefs.eligibility is not None
    assert "no CGPA cutoff or batch restriction stated" in beliefs.eligibility.content
    assert _parent_ids(store, beliefs.eligibility.id) == {recorded.anchor.id}


def test_derive_fit_scores_the_overlap_and_cites_the_jd_span_text():
    store, clock, runner, profile, recorded = _setup()
    beliefs = run(derive_for_opening(store, clock, runner, recorded.anchor.id))
    fit = beliefs.fit
    assert fit is not None and fit.structured is not None
    assert fit.structured.attribute == DerivedAttribute.FIT_SCORE
    assert fit.structured.value == round(2 / 3, 4)
    lines = fit.content.splitlines()
    assert (
        lines[0]
        == "fit 0.67 for Software Development Engineer Intern at Acme: 2 of 3 required skills"
    )
    assert (
        lines[1]
        == '- has Python: JD says "Required: Python, PyTorch, SQL"; profile says "knows Python"'
    )
    assert lines[3] == '- missing SQL: JD says "Required: Python, PyTorch, SQL"'
    required = recorded.all_fields(OpeningAttribute.REQUIRED_SKILL)
    skills = profile["skills"]
    assert isinstance(skills, list)
    assert _parent_ids(store, fit.id) == {
        recorded.anchor.id,
        *(r.id for r in required),
        *(s.id for s in skills),
    }
    assert {link.link_type for link in run(store.parents_of(fit.id))} == {JobsLinkType.FIT_OF}


def test_derive_fit_matches_skills_case_insensitively():
    store, clock, runner, _, recorded = _setup(skills=("python", "PYTORCH", "sql"))
    beliefs = run(derive_for_opening(store, clock, runner, recorded.anchor.id))
    assert beliefs.fit is not None and beliefs.fit.structured is not None
    assert beliefs.fit.structured.value == 1.0


def test_derive_reminder_is_48_hours_before_the_deadline_and_links_the_deadline_fact():
    store, clock, runner, _, recorded = _setup()
    beliefs = run(derive_for_opening(store, clock, runner, recorded.anchor.id))
    reminder = beliefs.reminder
    assert reminder is not None and reminder.structured is not None
    assert reminder.structured.attribute == DerivedAttribute.REMIND_AT
    assert datetime.fromisoformat(str(reminder.structured.value)) == DEADLINE - timedelta(hours=48)
    assert reminder.content.startswith("remind at 2026-11-03T09:00:00+00:00 about ")
    deadline = recorded.field(OpeningAttribute.DEADLINE)
    assert deadline is not None
    assert _parent_ids(store, reminder.id) == {recorded.anchor.id, deadline.id}
    assert {link.link_type for link in run(store.parents_of(reminder.id))} == {
        JobsLinkType.REMINDER_FOR
    }


def test_derive_skips_reminder_without_deadline_and_fit_without_required_skills():
    store, clock, runner, _, recorded = _setup(parsed=parsed_acme(deadline=None, skills=()))
    beliefs = run(derive_for_opening(store, clock, runner, recorded.anchor.id))
    assert beliefs.reminder is None and beliefs.fit is None
    assert beliefs.eligibility is not None


def test_derive_twice_returns_the_existing_beliefs_and_writes_nothing_new():
    store, clock, runner, _, recorded = _setup()
    first = run(derive_for_opening(store, clock, runner, recorded.anchor.id))
    before = len(store.all_memories()), len(store.change_events())
    second = run(derive_for_opening(store, clock, runner, recorded.anchor.id))
    assert (second.eligibility, second.fit, second.reminder) == (
        first.eligibility,
        first.fit,
        first.reminder,
    )
    assert (len(store.all_memories()), len(store.change_events())) == before


def test_derive_each_belief_opens_its_own_completed_change_event():
    store, clock, runner, _, recorded = _setup()
    events_before = len(store.change_events())
    beliefs = run(derive_for_opening(store, clock, runner, recorded.anchor.id))
    events = store.change_events()
    assert len(events) == events_before + 3
    belief_ids = {
        beliefs.eligibility.id,  # type: ignore[union-attr]
        beliefs.fit.id,  # type: ignore[union-attr]
        beliefs.reminder.id,  # type: ignore[union-attr]
    }
    own = [e for e in events if e.trigger_memory_id in belief_ids]
    assert {e.trigger_memory_id for e in own} == belief_ids
    assert all(e.completed_at is not None for e in own)


def test_derive_forget_anchor_cascades_to_the_derived_beliefs():
    store, clock, runner, profile, recorded = _setup()
    beliefs = run(derive_for_opening(store, clock, runner, recorded.anchor.id))
    event = run(forget(store, clock, recorded.anchor.id))
    for belief in (beliefs.eligibility, beliefs.fit, beliefs.reminder):
        assert belief is not None and belief.id in event.deleted_ids
    remaining = {m.id for m in store.all_memories()}
    assert profile["cgpa"].id in remaining  # type: ignore[attr-defined]


def test_derive_criteria_from_profile_facts_links_criteria_from():
    store, clock, runner, profile, _ = _setup()
    criteria = run(derive_criteria(store, clock, runner, USER))
    assert criteria is not None and criteria.structured is not None
    assert criteria.kind == Kind.CRITERIA
    assert (
        criteria.content
        == "search openings with cgpa_cutoff <= 7.9; batch 2027; skills python, pytorch"
    )
    assert criteria.structured.attribute == DerivedAttribute.CRITERIA
    skills = profile["skills"]
    assert isinstance(skills, list)
    assert _parent_ids(store, criteria.id) == {
        profile["cgpa"].id,  # type: ignore[attr-defined]
        profile["batch"].id,  # type: ignore[attr-defined]
        *(s.id for s in skills),
    }
    assert {link.link_type for link in run(store.parents_of(criteria.id))} == {
        JobsLinkType.CRITERIA_FROM
    }


def test_derive_criteria_is_none_for_an_empty_profile():
    store, clock = InMemoryStore(), FakeClock()
    assert run(derive_criteria(store, clock, make_runner(store, clock), USER)) is None
    assert store.all_memories() == []


def test_derive_ignores_suspect_profile_facts_when_deciding_what_it_can_compute():
    store, clock, runner, profile, recorded = _setup()
    cgpa = profile["cgpa"]

    async def flag():
        async with store.transaction() as tx:
            await tx.replace_memory(cgpa.model_copy(update={"status": Status.SUSPECT}))  # type: ignore[attr-defined]

    run(flag())
    beliefs = run(derive_for_opening(store, clock, runner, recorded.anchor.id))
    assert beliefs.eligibility is None  # the cutoff cannot be judged against a flagged CGPA
    assert beliefs.fit is not None


def test_derive_reminder_uses_the_deadline_timezone_as_given():
    ist = datetime(2026, 11, 5, 23, 59, tzinfo=UTC).astimezone(
        timezone(timedelta(hours=5, minutes=30))
    )
    store, clock, runner, _, recorded = _setup(parsed=parsed_acme(deadline=ist.isoformat()))
    beliefs = run(derive_for_opening(store, clock, runner, recorded.anchor.id))
    assert beliefs.reminder is not None and beliefs.reminder.structured is not None
    assert datetime.fromisoformat(str(beliefs.reminder.structured.value)) == ist - timedelta(
        hours=48
    )


def test_derive_returns_a_suspect_belief_instead_of_writing_a_second_one():
    store, clock, runner, _, recorded = _setup()
    first = run(derive_for_opening(store, clock, runner, recorded.anchor.id))
    assert first.eligibility is not None

    async def flag():
        async with store.transaction() as tx:
            await tx.replace_memory(first.eligibility.model_copy(update={"status": Status.SUSPECT}))  # type: ignore[union-attr]

    run(flag())
    before = len(store.all_memories())
    again = run(derive_for_opening(store, clock, runner, recorded.anchor.id))
    assert again.eligibility is not None and again.eligibility.id == first.eligibility.id
    assert len(store.all_memories()) == before


def test_derive_refuses_a_closed_opening():
    store, clock, runner, _, recorded = _setup()

    async def close():
        async with store.transaction() as tx:
            await tx.replace_memory(recorded.anchor.model_copy(update={"status": Status.RETIRED}))

    run(close())
    with pytest.raises(InvalidObjectError):
        run(derive_for_opening(store, clock, runner, recorded.anchor.id))
