"""The ask-user queue (FR-7): what the resolver parked, and the three answers."""

from fastapi import APIRouter, HTTPException, status

from ripple.api.auth import CurrentServices, CurrentUser, not_found, owned_memory
from ripple.api.schemas import AnswerIn, AnswerOut, QuestionOut, QuestionsOut
from ripple.core.answers import (
    answer_no_longer_holds,
    answer_with_correction,
    confirm_still_holds,
    pending_questions,
)
from ripple.core.models import Status

router = APIRouter(prefix="/questions", tags=["questions"])


@router.get("", response_model=QuestionsOut)
async def list_questions(user: CurrentUser, services: CurrentServices) -> QuestionsOut:
    return QuestionsOut(
        questions=[
            QuestionOut(
                memory=q.memory,
                question=q.question,
                reason=q.reason,
                asked_at=q.asked_at,
                event_id=q.event_id,
            )
            for q in await pending_questions(services.store, user.id)
        ]
    )


@router.post("/{memory_id}/answer", response_model=AnswerOut)
async def answer_question(
    memory_id: str, body: AnswerIn, user: CurrentUser, services: CurrentServices
) -> AnswerOut:
    memory = await owned_memory(services.store, user, memory_id)
    if memory.status is Status.RETIRED:
        raise not_found()
    match body.answer:
        case "still_holds":
            event = await confirm_still_holds(services.store, services.clock, memory.id)
        case "no_longer_holds":
            event = await answer_no_longer_holds(
                services.store, services.clock, services.runner, memory.id
            )
        case "correction":
            if body.content is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="a correction needs content",
                )
            event = await answer_with_correction(
                services.store,
                services.clock,
                services.runner,
                memory.id,
                content=body.content,
                structured=body.structured,
                valid_to=body.valid_to,
            )
    latest = await services.store.latest_version(memory.id)
    return AnswerOut(
        memory_id=latest.id,
        status=latest.status,
        memory=None if latest.status is Status.RETIRED else latest,
        event=event,
    )
