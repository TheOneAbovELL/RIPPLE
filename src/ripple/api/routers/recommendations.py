"""GET /recommendations: the adapter's ranking, read-only (I6: nothing here applies)."""

from typing import Annotated

from fastapi import APIRouter, Query

from ripple.api.auth import CurrentServices, CurrentUser
from ripple.api.schemas import RecommendationOut, RecommendationsOut

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("", response_model=RecommendationsOut)
async def list_recommendations(
    user: CurrentUser,
    services: CurrentServices,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> RecommendationsOut:
    ranked = await services.recommendations.recommendations_for(
        user.id, now=services.clock.now(), limit=limit
    )
    return RecommendationsOut(
        recommendations=[
            RecommendationOut(
                opening_memory_id=r.opening_memory_id,
                title=r.title,
                company=r.company,
                eligible=r.eligible,
                fit_score=r.fit_score,
                fit_reasons=list(r.fit_reasons),
                deadline=r.deadline,
                flagged=r.flagged,
            )
            for r in ranked
        ]
    )
