"""POST /openings: a pasted JD or forwarded email becomes opening memories (FR-2)."""

from fastapi import APIRouter

from ripple.api.auth import CurrentServices, CurrentUser
from ripple.api.schemas import OpeningIn, OpeningOut, ParsedFieldOut
from ripple.core.ids import new_id

router = APIRouter(prefix="/openings", tags=["openings"])


@router.post("", response_model=OpeningOut, status_code=201)
async def post_opening(body: OpeningIn, user: CurrentUser, services: CurrentServices) -> OpeningOut:
    source_ref = body.source_ref or f"{body.source}:{new_id()}"
    parsed = await services.opening_parser.parse(body.text, source_ref=source_ref)
    recorded = await services.opening_recorder.record(user.id, parsed)
    return OpeningOut(
        opening_memory_id=recorded.opening_memory_id,
        memory_ids=list(recorded.memory_ids),
        event_id=recorded.event_id,
        source_ref=parsed.source_ref,
        summary=parsed.summary,
        fields=[
            ParsedFieldOut(
                attribute=f.attribute,
                value=f.value,
                span_start=f.span.start,
                span_end=f.span.end,
                span_text=f.span.text,
                confidence=f.confidence,
            )
            for f in parsed.fields
        ],
    )
