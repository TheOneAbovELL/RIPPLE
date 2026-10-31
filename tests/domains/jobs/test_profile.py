"""Profile fact builders: typed values, one memory per skill, resume candidates."""

from datetime import timedelta

import pytest

from ripple.core.errors import InvalidObjectError
from ripple.core.models import Sensitivity, Status, TriggerKind
from ripple.domains.jobs.profile import (
    profile_fact,
    profile_memory,
    profile_statement,
    record_profile_fact,
    statement_from_candidate,
)
from ripple.domains.jobs.schemas import ProfileView
from ripple.domains.jobs.vocabulary import (
    DOMAIN,
    PROFILE_SUBJECT,
    CandidateFact,
    Kind,
    ProfileAttribute,
    TextSpan,
)
from tests.domains.jobs.helpers import USER, make_runner, run
from tests.fakes.clock import FakeClock
from tests.fakes.store import InMemoryStore


def test_profile_fact_types_cgpa_as_float_and_batch_as_int():
    cgpa = profile_fact(ProfileAttribute.CGPA, 8)
    batch = profile_fact(ProfileAttribute.BATCH, 2027)
    assert cgpa.value == 8.0 and isinstance(cgpa.value, float)
    assert batch.value == 2027 and isinstance(batch.value, int)
    assert cgpa.subject == batch.subject == PROFILE_SUBJECT


@pytest.mark.parametrize(
    ("attribute", "value"),
    [
        (ProfileAttribute.CGPA, "7.6"),
        (ProfileAttribute.CGPA, 10.5),
        (ProfileAttribute.CGPA, True),
        (ProfileAttribute.BATCH, 2027.0),
        (ProfileAttribute.BATCH, "2027"),
        (ProfileAttribute.SKILL, ""),
        (ProfileAttribute.SKILL, 3),
        (ProfileAttribute.LOOKING, "yes"),
    ],
)
def test_profile_fact_rejects_a_value_of_the_wrong_type(attribute, value):
    with pytest.raises(InvalidObjectError):
        profile_fact(attribute, value)


def test_profile_statement_fills_content_sensitivity_and_domain():
    statement = profile_statement(USER, ProfileAttribute.CGPA, 7.6)
    assert statement.content == "CGPA is 7.6"
    assert statement.domain == DOMAIN and statement.kind == Kind.FACT
    assert statement.sensitivity is Sensitivity.MEDIUM
    assert statement.structured is not None and statement.structured.value == 7.6
    skill = profile_statement(USER, ProfileAttribute.SKILL, " PyTorch ", content="I know PyTorch")
    assert skill.content == "I know PyTorch"
    assert skill.structured is not None and skill.structured.value == "PyTorch"
    assert skill.sensitivity is Sensitivity.LOW


def test_profile_memory_uses_the_given_time_for_validity_and_recording():
    clock = FakeClock()
    memory = profile_memory(USER, ProfileAttribute.BATCH, 2027, clock.now())
    assert memory.valid_from == memory.recorded_at == clock.now()
    assert memory.content == "graduating batch is 2027"


def test_record_profile_fact_writes_one_memory_per_skill_and_ripples_each():
    store, clock = InMemoryStore(), FakeClock()
    runner = make_runner(store, clock)
    for skill in ("Python", "PyTorch"):
        memory, event = run(
            record_profile_fact(store, clock, runner, USER, ProfileAttribute.SKILL, skill)
        )
        assert event is not None and event.trigger_memory_id == memory.id
        assert event.trigger_kind is TriggerKind.RIPPLE
        assert event.completed_at is not None
    profile = ProfileView.from_memories(run(store.memories_for_user(USER)))
    assert sorted(profile.skill_values) == ["python", "pytorch"]
    assert len(store.change_events()) == 2


def test_profile_view_takes_the_latest_recorded_single_valued_fact():
    clock = FakeClock()
    old = profile_memory(USER, ProfileAttribute.CGPA, 7.6, clock.now())
    clock.advance(timedelta(days=1))
    new = profile_memory(USER, ProfileAttribute.CGPA, 7.9, clock.now())
    profile = ProfileView.from_memories([old, new])
    assert profile.cgpa is new and profile.cgpa_value == 7.9


def test_statement_from_candidate_carries_the_resume_span_and_content():
    candidate = CandidateFact(
        attribute=ProfileAttribute.CGPA,
        value=8.1,
        span=TextSpan(start=120, end=129, text="CGPA 8.10"),
        confidence=0.9,
        content="CGPA 8.10 (as printed on the resume)",
    )
    statement = statement_from_candidate(USER, candidate, resume_ref="resume:r1")
    assert statement.source_ref == "resume:r1#120-129"
    assert statement.content == "CGPA 8.10 (as printed on the resume)"
    assert statement.confidence == 0.9
    assert statement.structured is not None and statement.structured.value == 8.1


def test_record_profile_fact_versions_a_single_valued_fact_instead_of_adding_a_second():
    store, clock = InMemoryStore(), FakeClock()
    runner = make_runner(store, clock)
    old, _ = run(record_profile_fact(store, clock, runner, USER, ProfileAttribute.CGPA, 7.6))
    new, event = run(record_profile_fact(store, clock, runner, USER, ProfileAttribute.CGPA, 7.9))
    assert event is not None and event.trigger_memory_id == new.id
    assert (new.version, new.supersedes_id) == (2, old.id)
    assert run(store.get_memory(old.id)).status is Status.RETIRED
    live = [m for m in store.all_memories() if m.status is Status.VALID]
    assert [m.content for m in live] == ["CGPA is 7.9"]


def test_record_profile_fact_writes_nothing_for_a_value_already_held():
    store, clock = InMemoryStore(), FakeClock()
    runner = make_runner(store, clock)
    cgpa, _ = run(record_profile_fact(store, clock, runner, USER, ProfileAttribute.CGPA, 7.6))
    skill, _ = run(record_profile_fact(store, clock, runner, USER, ProfileAttribute.SKILL, "SQL"))
    assert run(record_profile_fact(store, clock, runner, USER, ProfileAttribute.CGPA, 7.6)) == (
        cgpa,
        None,
    )
    assert run(record_profile_fact(store, clock, runner, USER, ProfileAttribute.SKILL, "sql ")) == (
        skill,
        None,
    )
    assert len(store.all_memories()) == 2 and len(store.change_events()) == 2


def test_statement_from_candidate_rejects_an_unknown_attribute():
    candidate = CandidateFact(attribute="salary", value="12 LPA", span=TextSpan(0, 6, "12 LPA"))
    with pytest.raises(InvalidObjectError):
        statement_from_candidate(USER, candidate, resume_ref="resume:r1")


def test_profile_fact_accepts_only_a_4_or_10_point_cgpa_scale():
    assert profile_fact(ProfileAttribute.CGPA_SCALE, 10).value == 10
    with pytest.raises(InvalidObjectError):
        profile_fact(ProfileAttribute.CGPA_SCALE, 5)
