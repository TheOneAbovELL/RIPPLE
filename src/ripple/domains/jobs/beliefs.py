"""Pure computations behind every derived jobs belief (ADR-0031).

Derivation (`derive.py`) and the rule resolvers (`rules.py`) call the same functions,
so "has this belief changed?" is a string comparison of two outputs of the same pure
function. Every number or name in a belief's content is read from a parent memory the
belief links to (I5): these functions receive views over memories and nothing else.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import timedelta

from ripple.core.models import Memory, StructuredFact
from ripple.domains.jobs.schemas import OpeningView, ProfileView
from ripple.domains.jobs.vocabulary import PROFILE_SUBJECT, DerivedAttribute, JobsLinkType, Kind

REMINDER_LEAD = timedelta(hours=48)
REASON_PREFIX = "- "


@dataclass(frozen=True)
class Belief:
    """What a derived memory must say, and which memories it was read from."""

    kind: str
    content: str
    structured: StructuredFact
    link_type: str
    parents: tuple[Memory, ...]

    @property
    def evidence_refs(self) -> tuple[str, ...]:
        return tuple(p.id for p in self.parents)


def _num(value: float) -> str:
    """7.9 -> '7.9', 8.0 -> '8': the way a student writes a CGPA."""
    return f"{value:g}"


def _unique(memories: Iterable[Memory | None]) -> tuple[Memory, ...]:
    seen: set[str] = set()
    ordered: list[Memory] = []
    for memory in memories:
        if memory is not None and memory.id not in seen:
            seen.add(memory.id)
            ordered.append(memory)
    return tuple(ordered)


def compute_eligibility(profile: ProfileView, opening: OpeningView) -> Belief | None:
    """Eligibility from the CGPA cutoff and the batch, when the profile can answer.

    None when the opening states a constraint the profile has no fact for: nothing is
    derived, and a rule facing that case leaves the decision to the LLM.
    """
    checks: list[tuple[bool, str]] = []
    parents: list[Memory | None] = [opening.anchor]
    cutoff = opening.cgpa_cutoff_value
    if cutoff is not None:
        cgpa = profile.cgpa_value
        # A 4-point CGPA against a 10-point cutoff would be a guess (ADR-0034); no
        # belief is derived, and the rule leaves the decision to the chain's fallback.
        if cgpa is None or not profile.cgpa_on_cutoff_scale:
            return None
        passed = cgpa >= cutoff
        checks.append(
            (passed, f"CGPA {_num(cgpa)} {'>=' if passed else '<'} cutoff {_num(cutoff)}")
        )
        # The scale fact, when one exists, is read too: changing it must ripple here.
        parents += [profile.cgpa, profile.cgpa_scale, opening.cgpa_cutoff]
    required_batch = opening.batch_value
    if required_batch is not None:
        batch = profile.batch_value
        if batch is None:
            return None
        passed = batch == required_batch
        relation = "matches" if passed else "is not"
        checks.append((passed, f"batch {batch} {relation} required batch {required_batch}"))
        parents += [profile.batch, opening.batch]
    eligible = all(passed for passed, _ in checks)
    reasons = (
        "; ".join(text for _, text in checks)
        if checks
        else "no CGPA cutoff or batch restriction stated"
    )
    verdict = "eligible" if eligible else "not eligible"
    return Belief(
        kind=Kind.DERIVED,
        content=f"{verdict} for {opening.label}: {reasons}",
        structured=StructuredFact(
            subject=opening.subject, attribute=DerivedAttribute.ELIGIBLE, value=eligible
        ),
        link_type=JobsLinkType.ELIGIBILITY_OF,
        parents=_unique(parents),
    )


def compute_fit(profile: ProfileView, opening: OpeningView) -> Belief | None:
    """Skill overlap, one reason line per required skill quoting the JD span.

    None when the JD lists no required skills: there is no overlap to compute.
    """
    required = opening.required_skill_values
    if not required:
        return None
    known = profile.skill_values
    reasons: list[str] = []
    matched: list[Memory] = []
    for key, requirement in required.items():
        stated = str(requirement.structured.value) if requirement.structured else key
        if key in known:
            matched.append(known[key])
            reasons.append(
                f'{REASON_PREFIX}has {stated}: JD says "{requirement.content}"; '
                f'profile says "{known[key].content}"'
            )
        else:
            reasons.append(f'{REASON_PREFIX}missing {stated}: JD says "{requirement.content}"')
    score = len(matched) / len(required)
    header = (
        f"fit {score:.2f} for {opening.label}: {len(matched)} of {len(required)} required skills"
    )
    return Belief(
        kind=Kind.DERIVED,
        content="\n".join([header, *reasons]),
        structured=StructuredFact(
            subject=opening.subject, attribute=DerivedAttribute.FIT_SCORE, value=round(score, 4)
        ),
        link_type=JobsLinkType.FIT_OF,
        parents=_unique([opening.anchor, *required.values(), *matched]),
    )


def compute_reminder(opening: OpeningView) -> Belief | None:
    """A reminder 48 hours before the deadline; None when the JD states no deadline."""
    deadline = opening.deadline_value
    if deadline is None:
        return None
    remind_at = deadline - REMINDER_LEAD
    lead_hours = int(REMINDER_LEAD.total_seconds() // 3600)
    return Belief(
        kind=Kind.DERIVED,
        content=(
            f"remind at {remind_at.isoformat()} about {opening.label}: "
            f"deadline {deadline.isoformat()} ({lead_hours} hours before)"
        ),
        structured=StructuredFact(
            subject=opening.subject,
            attribute=DerivedAttribute.REMIND_AT,
            value=remind_at.isoformat(),
        ),
        link_type=JobsLinkType.REMINDER_FOR,
        parents=_unique([opening.anchor, opening.deadline]),
    )


def compute_criteria(profile: ProfileView) -> Belief | None:
    """Search criteria the Scout filters with; None when the profile is empty."""
    clauses: list[str] = []
    parents: list[Memory | None] = []
    cgpa = profile.cgpa_value
    if cgpa is not None:
        # A parent even off the cutoff scale: correcting the scale later must find the
        # CGPA among the criteria's parents to bring the clause back (ADR-0034).
        parents.append(profile.cgpa)
        if profile.cgpa_on_cutoff_scale:
            clauses.append(f"cgpa_cutoff <= {_num(cgpa)}")
    if profile.cgpa_scale is not None:
        # Off the cutoff scale the Scout must not gate on CGPA (ADR-0034); either way a
        # scale change re-derives the criteria.
        parents.append(profile.cgpa_scale)
    batch = profile.batch_value
    if batch is not None:
        clauses.append(f"batch {batch}")
        parents.append(profile.batch)
    skills = profile.skill_values
    if skills:
        clauses.append("skills " + ", ".join(sorted(skills)))
        parents.extend(skills[key] for key in sorted(skills))
    if not clauses:
        return None
    content = "search openings with " + "; ".join(clauses)
    return Belief(
        kind=Kind.CRITERIA,
        content=content,
        structured=StructuredFact(
            subject=PROFILE_SUBJECT, attribute=DerivedAttribute.CRITERIA, value=content
        ),
        link_type=JobsLinkType.CRITERIA_FROM,
        parents=_unique(parents),
    )


def fit_reasons(content: str) -> tuple[str, ...]:
    """The reason lines of a fit belief's content, as `Recommendation.fit_reasons`."""
    return tuple(
        line.removeprefix(REASON_PREFIX)
        for line in content.splitlines()
        if line.startswith(REASON_PREFIX)
    )
