"""detect_structured_update's permanent path (ADR-0116, tightened by the 2026-10-31 review)."""

import pytest

from ripple.core.change_detection import ChangeKind, detect_structured_update
from ripple.core.models import Status, StructuredFact
from tests.builders import fact

PERMANENT = frozenset({("student", "cgpa"), ("student", "skill")})


def _cgpa(value: float) -> StructuredFact:
    return StructuredFact(subject="student", attribute="cgpa", value=value)


def test_permanent_fact_with_no_earlier_value_is_new_without_a_detector():
    result = detect_structured_update(_cgpa(8.1), [], permanent=PERMANENT)
    assert result is not None and result.kind is ChangeKind.NEW


def test_attribute_that_can_lapse_still_goes_to_the_detector():
    exams = StructuredFact(subject="student", attribute="availability", value="exams")
    assert detect_structured_update(exams, [], permanent=PERMANENT) is None


def test_permanence_is_keyed_on_subject_and_attribute_not_the_attribute_alone():
    # A field of an opening can share an attribute name with a profile fact.
    opening_field = StructuredFact(subject="opening:o1", attribute="cgpa", value=7.0)
    assert detect_structured_update(opening_field, [], permanent=PERMANENT) is None


@pytest.mark.parametrize("status", [Status.SUSPECT, Status.PENDING_USER])
def test_permanent_fact_whose_earlier_value_is_in_doubt_goes_to_the_detector(status: Status):
    """A second live CGPA would make every view pick one arbitrarily: when the earlier
    value is parked or mid-ripple, the deterministic shortcut steps aside."""
    earlier = fact("student", "cgpa", 7.6, status=status)
    assert detect_structured_update(_cgpa(8.1), [earlier], permanent=PERMANENT) is None


def test_permanent_multi_valued_fact_in_doubt_with_the_same_value_goes_to_the_detector():
    earlier = fact("student", "skill", "SQL", status=Status.PENDING_USER)
    sql = StructuredFact(subject="student", attribute="skill", value="SQL")
    result = detect_structured_update(
        sql, [earlier], multi_valued=frozenset({"skill"}), permanent=PERMANENT
    )
    assert result is None


def test_permanent_multi_valued_fact_with_a_new_value_is_new_beside_a_doubtful_sibling():
    earlier = fact("student", "skill", "SQL", status=Status.SUSPECT)
    docker = StructuredFact(subject="student", attribute="skill", value="Docker")
    result = detect_structured_update(
        docker, [earlier], multi_valued=frozenset({"skill"}), permanent=PERMANENT
    )
    assert result is not None and result.kind is ChangeKind.NEW
