"""Jobs rule resolvers (ADR-0031, implementing ripple.core.resolver.RuleResolver).

Each rule owns one belief kind, recomputes it from the parents in the
ResolutionContext with the same pure function that derived it, and answers:
- None: not its kind, a parent it needs is missing, or any parent is SUSPECT or
  PENDING_USER (in doubt: computing around it would be confidently wrong, so the LLM
  decides). A RETIRED parent is a removed fact: an opening constraint that is gone no
  longer applies; a profile fact that is gone leaves nothing to compute with;
- retire: the opening anchor among the parents is RETIRED (the opening closed);
- keep: the recomputation equals what is stored;
- update: new content and structured value, evidence = the parents read.
No rule reads the store, the clock or a model.

CGPA scale (ADR-0034): JD cutoffs are ten-point values only (the
parsers and `schemas.parse_cgpa` accept nothing else). A student whose cgpa_scale
fact says 4 cannot be compared with them without a conversion nobody agrees on, so
`compute_eligibility` returns None, EligibilityRule declines and the chain falls back
to the LLM, which can ask.
"""

from collections.abc import Callable, Sequence

from ripple.core.models import DecisionAction, Memory, Status
from ripple.core.resolver import Resolution, ResolutionContext, RuleResolver
from ripple.core.visibility import FLAGGED
from ripple.domains.jobs.beliefs import (
    Belief,
    compute_criteria,
    compute_eligibility,
    compute_fit,
    compute_reminder,
)
from ripple.domains.jobs.schemas import (
    TEN_POINT_SCALE,
    OpeningView,
    ProfileView,
    anchor_of,
    opening_key,
    opening_subject_of,
)
from ripple.domains.jobs.vocabulary import DerivedAttribute, Kind

# The scale every stored cgpa_cutoff is on. Mirrors parsers.numbers.CGPA_SCALE_MAX
# (pinned by a test) without importing the parsers, which pull in the LLM client.
JD_CGPA_SCALE = TEN_POINT_SCALE
# A profile with no live cgpa_scale fact is on the ten-point scale (data model).
DEFAULT_CGPA_SCALE = TEN_POINT_SCALE


def _owns(memory: Memory, kind: str, attribute: DerivedAttribute) -> bool:
    return (
        memory.kind == kind
        and memory.structured is not None
        and memory.structured.attribute == attribute
    )


def _retire_closed(anchor: Memory) -> Resolution:
    return Resolution(
        action=DecisionAction.RETIRE,
        reason=f"the opening it belongs to is retired: {anchor.content}",
        evidence_refs=(anchor.id,),
    )


def _compare(memory: Memory, belief: Belief) -> Resolution:
    if belief.content == memory.content and belief.structured == memory.structured:
        return Resolution(
            action=DecisionAction.KEEP,
            reason="recomputed from current parents; unchanged",
            evidence_refs=belief.evidence_refs,
        )
    return Resolution(
        action=DecisionAction.UPDATE,
        reason="recomputed from current parents; changed",
        evidence_refs=belief.evidence_refs,
        new_content=belief.content,
        new_structured=belief.structured,
    )


# Signature shared by the per-opening computations.
_Compute = Callable[[ProfileView, OpeningView], Belief | None]


def _in_doubt(parents: Sequence[Memory], opening: str | None = None) -> bool:
    """A parent whose value may be wrong: PENDING_USER, or SUSPECT for any reason other
    than being a field of this (VALID) opening. A field is SUSPECT only while its own
    anchor ripples, and OpeningFieldRule keeps it in that same wave, so its value stands.
    """
    return any(
        p.status is Status.PENDING_USER
        or (p.status in FLAGGED and (opening is None or opening_subject_of(p) != opening))
        for p in parents
    )


def _opening_belief(
    context: ResolutionContext,
    kind: str,
    attribute: DerivedAttribute,
    compute: _Compute,
) -> Resolution | None:
    memory = context.memory
    if not _owns(memory, kind, attribute):
        return None
    anchor = anchor_of(context.parents)
    if anchor is None or opening_key(anchor) != opening_subject_of(memory):
        return None
    if anchor.status is Status.RETIRED:
        return _retire_closed(anchor)
    if anchor.status is not Status.VALID or _in_doubt(context.parents, opening_key(anchor)):
        return None
    profile = ProfileView.from_memories(context.parents)
    # Same-opening fields may be SUSPECT mid-wave (see _in_doubt); read them anyway.
    opening = OpeningView.from_memories(anchor, context.parents, include_flagged=True)
    belief = compute(profile, opening)
    return None if belief is None else _compare(memory, belief)


class EligibilityRule:
    """cgpa vs cgpa_cutoff and batch vs batch, from the current parent values. Declines
    when the student's CGPA is not on the cutoff's scale: `compute_eligibility` returns
    None there, the same function derivation uses (ADR-0034)."""

    def resolve(self, context: ResolutionContext) -> Resolution | None:
        return _opening_belief(
            context, Kind.DERIVED, DerivedAttribute.ELIGIBLE, compute_eligibility
        )


class FitRule:
    """Skill overlap between the profile's skill facts and the JD's required skills."""

    def resolve(self, context: ResolutionContext) -> Resolution | None:
        return _opening_belief(context, Kind.DERIVED, DerivedAttribute.FIT_SCORE, compute_fit)


class ReminderRule:
    """Deadline minus 48 hours, from the current deadline fact."""

    def resolve(self, context: ResolutionContext) -> Resolution | None:
        return _opening_belief(
            context,
            Kind.DERIVED,
            DerivedAttribute.REMIND_AT,
            lambda _profile, opening: compute_reminder(opening),
        )


class CriteriaRule:
    """Search criteria from the current profile facts."""

    def resolve(self, context: ResolutionContext) -> Resolution | None:
        if not _owns(context.memory, Kind.CRITERIA, DerivedAttribute.CRITERIA):
            return None
        if _in_doubt(context.parents):
            return None
        belief = compute_criteria(ProfileView.from_memories(context.parents))
        return None if belief is None else _compare(context.memory, belief)


class OpeningFieldRule:
    """A field fact follows its anchor: kept while the opening is open, retired with it."""

    def resolve(self, context: ResolutionContext) -> Resolution | None:
        memory = context.memory
        if memory.kind != Kind.FACT:
            return None
        subject = opening_subject_of(memory)
        if subject is None:
            return None
        anchor = next(
            (p for p in context.parents if p.kind == Kind.OPENING and opening_key(p) == subject),
            None,
        )
        if anchor is None:
            return None
        if anchor.status is Status.RETIRED:
            return _retire_closed(anchor)
        if anchor.status is Status.VALID:
            return Resolution(
                action=DecisionAction.KEEP,
                reason=f"field of an opening that is still open: {anchor.content}",
                evidence_refs=(anchor.id,),
            )
        return None


def jobs_rules() -> Sequence[RuleResolver]:
    """The rule stage of the jobs ResolverChain, in a fixed order (ADR-0031)."""
    return (OpeningFieldRule(), EligibilityRule(), FitRule(), ReminderRule(), CriteriaRule())
