from bench.linkpairs import PairMemory
from training.structure_rules import label_by_structure, opening_company

from ripple.core.models import StructuredFact


def _fact(attribute: str, value: str | float, content: str) -> PairMemory:
    return PairMemory(
        kind="fact",
        content=content,
        structured=StructuredFact(subject="student", attribute=attribute, value=value),
    )


def _opening(company: str, attribute: str, value: str | float, content: str) -> PairMemory:
    return PairMemory(
        kind="opening",
        content=content,
        structured=StructuredFact(
            subject=f"opening:{company}_opening", attribute=attribute, value=value
        ),
    )


CGPA = _fact("cgpa", 7.2, "CGPA is 7.2")
UMBRELLA = _opening("umbrella", "cgpa_cutoff", 7.4, "Umbrella SDE intern: CGPA cutoff 7.4")
HOOLI_DEADLINE = _opening(
    "hooli", "deadline", "2026-11-07T23:59:00+05:30", "Hooli SDE engineer: deadline 2026-11-07"
)
NOT_ELIGIBLE = PairMemory(kind="derived", content="not eligible for umbrella (7.2 < 7.4)")


def test_eligibility_rests_on_the_opening_whose_company_it_names():
    label = label_by_structure(UMBRELLA, NOT_ELIGIBLE, [UMBRELLA])
    assert label is not None
    assert (label.link_type, label.rule) == ("eligibility_of", "eligibility_from_cutoff")
    other = PairMemory(kind="derived", content="eligible for hooli")
    assert label_by_structure(UMBRELLA, other, [UMBRELLA]) is None


def test_eligibility_rests_on_cgpa_only_when_that_company_states_a_cutoff():
    label = label_by_structure(CGPA, NOT_ELIGIBLE, [CGPA, UMBRELLA, NOT_ELIGIBLE])
    assert label is not None and label.rule == "eligibility_from_cgpa"
    assert label_by_structure(CGPA, NOT_ELIGIBLE, [CGPA, NOT_ELIGIBLE]) is None
    hooli = PairMemory(kind="derived", content="eligible for hooli")
    assert label_by_structure(CGPA, hooli, [CGPA, HOOLI_DEADLINE, hooli]) is None


def test_reminder_matches_the_deadline_date_exactly():
    reminder = PairMemory(kind="derived", content="remind two days before 2026-11-07")
    label = label_by_structure(HOOLI_DEADLINE, reminder, [])
    assert label is not None and label.link_type == "reminder_for"
    stale = PairMemory(kind="derived", content="remind two days before 2026-12-19")
    assert label_by_structure(HOOLI_DEADLINE, stale, []) is None


def test_criteria_follow_the_cgpa_value():
    criteria = PairMemory(kind="criteria", content="search openings with cutoff <= 7.2")
    label = label_by_structure(CGPA, criteria, [])
    assert label is not None and label.link_type == "criteria_from"
    old = PairMemory(kind="criteria", content="search openings with cutoff <= 7.6")
    assert label_by_structure(CGPA, old, []) is None


def test_an_application_is_a_snapshot_of_the_resume_version_it_names():
    v1, v2 = _fact("resume", "v1", "resume v1"), _fact("resume", "v2", "resume v2")
    application = PairMemory(kind="application", content="applied to initech with resume v1")
    label = label_by_structure(v1, application, [])
    assert label is not None and label.link_type == "sent_with_resume"
    assert label_by_structure(v2, application, []) is None


def test_rules_never_fire_from_an_unstructured_parent_or_backwards():
    assert label_by_structure(NOT_ELIGIBLE, CGPA, [UMBRELLA]) is None
    prose = PairMemory(kind="derived", content="available for summer 2027")
    assert label_by_structure(prose, NOT_ELIGIBLE, [UMBRELLA]) is None


def test_opening_company_is_the_first_word_of_an_opening():
    assert opening_company(UMBRELLA) == "umbrella"
    assert opening_company(CGPA) is None
