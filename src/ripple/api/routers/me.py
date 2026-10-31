"""/me: who am I, Telegram linking, export and delete (FR-15, NFR-3, ADR-0044).

DELETE /me forgets every memory through the forget API (I7: no other deletion path),
removes the candidates and uploads, then the user with their tokens and codes. ForgetEvents stay:
they hold ids and timestamps, no content, and are the audit that the deletion happened.
"""

from fastapi import APIRouter, Response, status

from ripple.api.auth import CurrentServices, CurrentUser
from ripple.api.schemas import ExportOut, LinkCodeOut, MeOut
from ripple.core.forget import forget
from ripple.core.store import MemoryNotFoundError
from ripple.storage.users import TelegramLinkCode, new_link_code

router = APIRouter(prefix="/me", tags=["me"])


@router.get("", response_model=MeOut)
async def get_me(user: CurrentUser) -> MeOut:
    return MeOut(
        id=user.id,
        display_name=user.display_name,
        created_at=user.created_at,
        telegram_linked=user.telegram_chat_id is not None,
    )


@router.post("/telegram/link", response_model=LinkCodeOut, status_code=201)
async def create_telegram_link_code(user: CurrentUser, services: CurrentServices) -> LinkCodeOut:
    """A one-time code to send to the bot; the worker consumes it (ADR-0025)."""
    now = services.clock.now()
    code = TelegramLinkCode(
        code=new_link_code(),
        user_id=user.id,
        created_at=now,
        expires_at=now + services.link_code_ttl,
    )
    await services.user_store.add_link_code(code)
    return LinkCodeOut(code=code.code, expires_at=code.expires_at)


@router.get("/export", response_model=ExportOut)
async def export_me(user: CurrentUser, services: CurrentServices) -> ExportOut:
    store = services.store
    return ExportOut(
        exported_at=services.clock.now(),
        user=user,
        memories=await store.memories_for_user(user.id),
        links=await store.links_for_user(user.id),
        change_events=await services.store.change_events_for_user(user.id),
        forget_events=await services.store.forget_events_for_user(user.id),
        resume_candidates=await services.candidate_store.candidates_for_user(user.id),
        resume_uploads=await services.upload_store.uploads_for_user(user.id),
        feedback=await services.feedback_store.feedback_for_user(user.id),
    )


@router.delete("", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_me(user: CurrentUser, services: CurrentServices) -> Response:
    # Forget cascades, so one call may remove several; re-list until nothing is left.
    remaining = await services.store.memories_for_user(user.id)
    while remaining:
        for memory in remaining:
            try:
                await forget(services.store, services.clock, memory.id)
            except MemoryNotFoundError:
                continue  # deleted by an earlier cascade in this loop
        remaining = await services.store.memories_for_user(user.id)
    # ChangeEvents may quote content in their reasons; FR-15 erases them. ForgetEvents
    # stay as the deletion audit (ADR-0044): ids only, no content.
    async with services.store.transaction() as tx:
        await tx.delete_change_events_for_user(user.id)
    await services.candidate_store.delete_for_user(user.id)
    await services.upload_store.delete_for_user(user.id)  # the resume text is user data too
    await services.feedback_store.delete_for_user(user.id)  # pilot statements (ADR-0105)
    if services.delivery_log is not None:
        await services.delivery_log.delete_for_user(user.id)
    await services.user_store.delete_user(user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
