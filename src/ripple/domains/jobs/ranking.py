"""JobsRecommender: ranked openings read from memory, never recomputed (ADR-0032).

Order: eligible, then deadline within 48 hours, then fit score, then earliest deadline;
variety within each tier so one company cannot fill the list. Everything passes through
`visible_for_retrieval` (I1): RETIRED never appears, SUSPECT and PENDING_USER appear
flagged.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from ripple.core.store import Store
from ripple.core.visibility import VisibleMemory, visible_for_retrieval
from ripple.domains.jobs.beliefs import fit_reasons
from ripple.domains.jobs.schemas import OpeningView, opening_key, opening_subject_of
from ripple.domains.jobs.vocabulary import DerivedAttribute, Kind, Recommendation

URGENT_WITHIN = timedelta(hours=48)


@dataclass(frozen=True)
class _Ranked:
    recommendation: Recommendation
    urgent: bool
    # Variety bucket: the company, or the opening itself when no company was parsed, so
    # unnamed openings are not spread against each other as if they were one employer.
    company_key: str

    def sort_key(self) -> tuple[bool, bool, float, float]:
        deadline = self.recommendation.deadline
        return (
            not self.recommendation.eligible,
            not self.urgent,
            -self.recommendation.fit_score,
            deadline.timestamp() if deadline is not None else float("inf"),
        )

    @property
    def tier(self) -> tuple[bool, bool]:
        return (self.recommendation.eligible, self.urgent)


def _belief(
    memories: Sequence[VisibleMemory], subject: str, attribute: str
) -> VisibleMemory | None:
    return next(
        (
            v
            for v in memories
            if v.memory.kind in (Kind.DERIVED, Kind.CRITERIA)
            and v.memory.structured is not None
            and v.memory.structured.subject == subject
            and v.memory.structured.attribute == attribute
        ),
        None,
    )


def _value(belief: VisibleMemory | None) -> str | int | float | bool | None:
    if belief is None or belief.memory.structured is None:
        return None
    return belief.memory.structured.value


def _spread_by_company(ranked: list[_Ranked]) -> list[_Ranked]:
    """Within each tier, take the company seen least so far; ties keep the sort order."""
    ordered = sorted(ranked, key=_Ranked.sort_key)
    position = {id(r): i for i, r in enumerate(ordered)}
    seen: dict[str, int] = {}
    spread: list[_Ranked] = []
    start = 0
    while start < len(ordered):
        end = start
        while end < len(ordered) and ordered[end].tier == ordered[start].tier:
            end += 1
        tier = ordered[start:end]
        while tier:
            chosen = min(tier, key=lambda r: (seen.get(r.company_key, 0), position[id(r)]))
            tier.remove(chosen)
            seen[chosen.company_key] = seen.get(chosen.company_key, 0) + 1
            spread.append(chosen)
        start = end
    return spread


class JobsRecommender:
    """Implements `ripple.domains.jobs.vocabulary.RecommendationSource` over a Store."""

    def __init__(self, store: Store) -> None:
        self._store = store

    async def recommendations_for(
        self, user_id: str, *, now: datetime, limit: int = 10
    ) -> Sequence[Recommendation]:
        visible = visible_for_retrieval(
            await self._store.memories_for_user(user_id), include_flagged=True
        )
        by_subject: dict[str, list[VisibleMemory]] = {}
        for item in visible:
            subject = opening_subject_of(item.memory)
            if subject is not None and item.memory.kind != Kind.OPENING:
                by_subject.setdefault(subject, []).append(item)
        ranked: list[_Ranked] = []
        for anchor in visible:
            if anchor.memory.kind != Kind.OPENING:
                continue
            own = by_subject.get(opening_key(anchor.memory), [])
            if (r := self._rank_one(anchor, own, now)) is not None:
                ranked.append(r)
        return [r.recommendation for r in _spread_by_company(ranked)[:limit]]

    def _rank_one(
        self, anchor: VisibleMemory, own: Sequence[VisibleMemory], now: datetime
    ) -> _Ranked | None:
        subject = opening_key(anchor.memory)
        # Flagged fields are shown, not dropped (I1): a deadline in doubt still orders.
        opening = OpeningView.from_memories(
            anchor.memory, [v.memory for v in own], include_flagged=True
        )
        deadline = opening.deadline_value
        if deadline is not None and deadline <= now:
            return None  # closed; listing it would be the stale recommendation we measure
        eligibility = _belief(own, subject, DerivedAttribute.ELIGIBLE)
        fit = _belief(own, subject, DerivedAttribute.FIT_SCORE)
        eligible = _value(eligibility) is True
        score = float(_value(fit) or 0.0)
        # Only what this recommendation is built from can flag it (the reminder cannot).
        used = {m.id for m in (opening.title, opening.company, opening.deadline) if m} | {
            b.memory.id for b in (eligibility, fit) if b is not None
        }
        recommendation = Recommendation(
            opening_memory_id=anchor.memory.id,
            title=opening.title_value,
            company=opening.company_value,
            eligible=eligible,
            fit_score=score,
            fit_reasons=fit_reasons(fit.memory.content) if fit else (),
            deadline=deadline,
            flagged=anchor.flagged or any(v.flagged for v in own if v.memory.id in used),
        )
        return _Ranked(
            recommendation=recommendation,
            urgent=deadline is not None and deadline - now <= URGENT_WITHIN,
            company_key=opening.company_value or subject,
        )
