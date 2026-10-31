"""/feedback: the student's own reactions, for the pilot report (ADR-0105, docs/04).

POST records one statement about a recommended opening (saved, applied, dismissed) or
about a question the resolver asked (useful, not useful); GET lists the caller's own
rows. Nothing here acts on anything: "applied" stores that the student says they
applied (I6). The response carries ids and kinds only, never memory content, so a
RETIRED target is never returned through this route (I1). The rules live in
`ripple.pilot.feedback.record_feedback`, shared with the Telegram buttons. The store
is `Services.feedback_store` (checkpoint C4).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field

from ripple.api.auth import CurrentServices, CurrentUser, not_found
from ripple.api.services import services_of
from ripple.pilot.feedback import (
    FeedbackKindMismatchError,
    FeedbackTargetNotFoundError,
    record_feedback,
)
from ripple.storage.feedback import (
    Feedback,
    FeedbackKind,
    FeedbackRecordRaceError,
    FeedbackStore,
)
from ripple.storage.feedback_tables import NOTE_MAX_CHARS

router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_memory_id: str = Field(min_length=1, max_length=64)
    kind: FeedbackKind
    note: str | None = Field(default=None, max_length=NOTE_MAX_CHARS)


class FeedbackListOut(BaseModel):
    feedback: list[Feedback]


def feedback_store_of(request: Request) -> FeedbackStore:
    return services_of(request).feedback_store


CurrentFeedbackStore = Annotated[FeedbackStore, Depends(feedback_store_of)]


@router.post(
    "",
    response_model=Feedback,
    status_code=status.HTTP_201_CREATED,
    responses={200: {"model": Feedback, "description": "Already recorded; the first row."}},
)
async def post_feedback(
    body: FeedbackIn,
    response: Response,
    user: CurrentUser,
    services: CurrentServices,
    feedback_store: CurrentFeedbackStore,
) -> Feedback:
    try:
        stored, created = await record_feedback(
            services.store,
            feedback_store,
            services.clock,
            user_id=user.id,
            target_memory_id=body.target_memory_id,
            kind=body.kind,
            note=body.note,
        )
    except FeedbackTargetNotFoundError as exc:
        # 404 for an unknown or another user's memory, as everywhere else (ADR-0040).
        raise not_found() from exc
    except FeedbackKindMismatchError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    except FeedbackRecordRaceError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="the target changed; retry"
        ) from exc
    if not created:
        response.status_code = status.HTTP_200_OK
    return stored


@router.get("", response_model=FeedbackListOut)
async def list_feedback(
    user: CurrentUser,
    feedback_store: CurrentFeedbackStore,
    target_memory_id: Annotated[str | None, Query(min_length=1, max_length=64)] = None,
) -> FeedbackListOut:
    rows = await feedback_store.feedback_for_user(user.id)
    if target_memory_id is not None:
        rows = [f for f in rows if f.target_memory_id == target_memory_id]
    return FeedbackListOut(feedback=rows)
