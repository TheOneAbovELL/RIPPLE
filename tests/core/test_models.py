from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from ripple.core.models import DecisionAction, Memory, Status
from tests.builders import decision, derived, fact, link, memory
from tests.fakes.clock import DEFAULT_START

NAIVE = datetime(2026, 11, 1)


def test_memory_defaults_to_valid_version_one():
    m = memory()
    assert m.status is Status.VALID
    assert m.version == 1
    assert m.supersedes_id is None


def test_memory_rejects_naive_recorded_at():
    with pytest.raises(ValidationError, match="timezone-aware"):
        memory(at=NAIVE)


def test_memory_rejects_valid_to_before_valid_from():
    with pytest.raises(ValidationError, match="valid_to must be after"):
        memory(valid_from=DEFAULT_START, valid_to=DEFAULT_START - timedelta(days=1))


def test_memory_version_two_requires_supersedes_id():
    with pytest.raises(ValidationError, match="supersedes_id"):
        memory(version=2)


def test_memory_version_one_forbids_supersedes_id():
    with pytest.raises(ValidationError, match="supersedes_id"):
        memory(version=1, supersedes_id="other")


def test_memory_cannot_supersede_itself():
    with pytest.raises(ValidationError, match="supersede itself"):
        memory(id="m1", version=2, supersedes_id="m1")


def test_memory_is_immutable():
    m = memory()
    with pytest.raises(ValidationError):
        m.status = Status.RETIRED  # type: ignore[misc]


def test_memory_temporary_fact_expires_after_valid_to():
    m = memory(valid_to=DEFAULT_START + timedelta(days=30))
    assert m.is_temporary
    assert not m.expired_at(DEFAULT_START + timedelta(days=29))
    assert m.expired_at(DEFAULT_START + timedelta(days=30))


def test_memory_without_valid_to_never_expires():
    assert not memory().expired_at(datetime(2099, 1, 1, tzinfo=UTC))


def test_fact_builder_sets_structured_fields():
    m = fact("student", "cgpa", 7.6)
    assert m.structured is not None
    assert (m.structured.subject, m.structured.attribute, m.structured.value) == (
        "student",
        "cgpa",
        7.6,
    )


def test_link_rejects_self_dependency():
    m = memory()
    with pytest.raises(ValidationError, match="depend on itself"):
        link(m, m)


def test_link_connects_parent_to_dependent():
    cgpa = fact("student", "cgpa", 7.6)
    eligibility = derived("not eligible for Acme")
    edge = link(cgpa, eligibility, link_type="eligibility_of")
    assert (edge.parent_id, edge.dependent_id) == (cgpa.id, eligibility.id)


def test_decision_update_requires_new_version_id():
    with pytest.raises(ValidationError, match="new_version_id"):
        decision(memory(), DecisionAction.UPDATE)


def test_decision_keep_forbids_new_version_id():
    with pytest.raises(ValidationError, match="new_version_id"):
        decision(memory(), DecisionAction.KEEP, new_version_id="v2")


def test_memory_round_trips_through_json():
    m = fact("student", "cgpa", 7.9, valid_to=DEFAULT_START + timedelta(days=1))
    assert Memory.model_validate_json(m.model_dump_json()) == m
