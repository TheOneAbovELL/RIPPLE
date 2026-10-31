"""Silver link labels derived from structure over the jobs vocabulary (proposal 0002,
ADR-0090).

A rule fires only when the parent is a structured fact and the dependent's text names
the same value or entity in the surface form the jobs track writes it in. Rules cover
the link types that structure determines (eligibility_of, reminder_for, criteria_from,
sent_with_resume); depends_on_fact and fit_of are the "hidden" links a rule cannot see
and stay with scenario or LLM labels. A rule is exact on the v0 surface forms and says
nothing outside them: it returns None rather than guess.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass

from bench.linkpairs import PairMemory

from ripple.domains.jobs.vocabulary import (
    PROFILE_SUBJECT,
    JobsLinkType,
    Kind,
    OpeningAttribute,
    ProfileAttribute,
)

_ELIGIBILITY = re.compile(r"^(?:not )?eligible for ([a-z][a-z0-9]*)\b")
_REMINDER = re.compile(r"^remind .* before (\d{4}-\d{2}-\d{2})$")
_CRITERIA_CUTOFF = re.compile(r"cutoff <= (\d+(?:\.\d+)?)\b")
_SENT_WITH = re.compile(r"\bwith resume (\S+)$")
_COMPANY = re.compile(r"^([A-Za-z][A-Za-z0-9]*)\b")


@dataclass(frozen=True)
class RuleLabel:
    link_type: str
    rule: str  # the rule's name, kept in LabelledPair.note for stratified analysis


def opening_company(memory: PairMemory) -> str | None:
    """The company an opening names: its first word ("Vandelay SDE intern: ...")."""
    if memory.kind != Kind.OPENING:
        return None
    match = _COMPANY.match(memory.content)
    return match.group(1).lower() if match else None


def _is_profile(memory: PairMemory, attribute: ProfileAttribute) -> bool:
    s = memory.structured
    return (
        memory.kind == Kind.FACT
        and s is not None
        and s.subject == PROFILE_SUBJECT
        and s.attribute == attribute
    )


def _is_opening_with(memory: PairMemory, attribute: OpeningAttribute) -> bool:
    s = memory.structured
    return memory.kind == Kind.OPENING and s is not None and s.attribute == attribute


def _eligibility_company(memory: PairMemory) -> str | None:
    if memory.kind != Kind.DERIVED:
        return None
    match = _ELIGIBILITY.match(memory.content)
    return match.group(1) if match else None


def _same_number(text: str, value: object) -> bool:
    try:
        return float(text) == float(str(value))
    except ValueError:
        return False


def label_by_structure(
    parent: PairMemory, dependent: PairMemory, context: Iterable[PairMemory]
) -> RuleLabel | None:
    """The link a structure rule derives from `parent` to `dependent`, or None.

    `context` is every memory that coexists with the pair (one scenario snapshot or a
    persona's seeded pool): eligibility rests on a CGPA only for a company whose
    opening states a CGPA cutoff there.
    """
    company = _eligibility_company(dependent)
    if company is not None:
        if (
            _is_opening_with(parent, OpeningAttribute.CGPA_CUTOFF)
            and opening_company(parent) == company
        ):
            return RuleLabel(JobsLinkType.ELIGIBILITY_OF, "eligibility_from_cutoff")
        if _is_profile(parent, ProfileAttribute.CGPA) and any(
            _is_opening_with(other, OpeningAttribute.CGPA_CUTOFF)
            and opening_company(other) == company
            for other in context
        ):
            return RuleLabel(JobsLinkType.ELIGIBILITY_OF, "eligibility_from_cgpa")
    fact = parent.structured
    if fact is None:
        return None
    if _is_opening_with(parent, OpeningAttribute.DEADLINE) and dependent.kind == Kind.DERIVED:
        match = _REMINDER.match(dependent.content)
        if match and str(fact.value)[:10] == match.group(1):
            return RuleLabel(JobsLinkType.REMINDER_FOR, "reminder_from_deadline")
    if _is_profile(parent, ProfileAttribute.CGPA) and dependent.kind == Kind.CRITERIA:
        match = _CRITERIA_CUTOFF.search(dependent.content)
        if match and _same_number(match.group(1), fact.value):
            return RuleLabel(JobsLinkType.CRITERIA_FROM, "criteria_from_cgpa")
    if _is_profile(parent, ProfileAttribute.RESUME) and dependent.kind == Kind.APPLICATION:
        match = _SENT_WITH.search(dependent.content)
        if match and match.group(1) == str(fact.value):
            return RuleLabel(JobsLinkType.SENT_WITH_RESUME, "application_sent_with_resume")
    return None
