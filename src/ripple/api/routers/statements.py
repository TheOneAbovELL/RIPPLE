"""POST /statements: the write flow (docs/02 flow 1) from the conversation or inspector."""

from fastapi import APIRouter

from ripple.api.auth import CurrentServices, CurrentUser
from ripple.api.logging import current_trace_id
from ripple.api.schemas import IntakeOut, StatementIn
from ripple.core.intake import Statement

router = APIRouter(prefix="/statements", tags=["statements"])


@router.post("", response_model=IntakeOut, status_code=201)
async def post_statement(
    body: StatementIn, user: CurrentUser, services: CurrentServices
) -> IntakeOut:
    statement = Statement(
        user_id=user.id,
        domain=services.domain,
        kind=body.kind,
        content=body.content,
        structured=body.structured,
        source_ref=body.source_ref,
        created_by="user",
        origin=body.origin,
        sensitivity=body.sensitivity,
    )
    result = await services.intake.ingest(statement, trace_id=current_trace_id())
    return IntakeOut(
        memory=result.memory,
        change_kind=result.change_kind,
        links_written=result.links_written,
        event=result.event,
    )
