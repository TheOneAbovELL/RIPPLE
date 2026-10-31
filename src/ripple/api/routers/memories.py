"""The memory inspector (FR-12): list, explain, edit, forget.

I1 at the boundary: listing goes through `visible_for_retrieval`, so RETIRED rows
never appear and SUSPECT / PENDING_USER rows carry `flagged`. A single RETIRED memory
is reachable only with `history=true`, which is the inspector's explicit "show me the
past" view.
"""

from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, status

from ripple.api.auth import CurrentServices, CurrentUser, not_found, owned_memory
from ripple.api.inspector import mentions, why
from ripple.api.logging import current_trace_id
from ripple.api.schemas import (
    EditIn,
    ForgetOut,
    HistoryOut,
    IntakeOut,
    MemoriesOut,
    MemoryDetailOut,
    MemoryOut,
)
from ripple.api.uploads import source_for
from ripple.core.change_detection import ChangeKind
from ripple.core.forget import forget
from ripple.core.models import Status, TriggerKind
from ripple.core.visibility import FLAGGED, visible_for_retrieval
from ripple.core.writes import update_memory

router = APIRouter(prefix="/memories", tags=["memories"])

VisibleStatus = Literal["VALID", "SUSPECT", "PENDING_USER"]


@router.get("", response_model=MemoriesOut)
async def list_memories(
    user: CurrentUser,
    services: CurrentServices,
    kind: Annotated[str | None, Query(max_length=32)] = None,
    status_filter: Annotated[VisibleStatus | None, Query(alias="status")] = None,
    flagged: Annotated[
        bool, Query(description="Include SUSPECT and PENDING_USER (flagged).")
    ] = True,
) -> MemoriesOut:
    statuses = [Status(status_filter)] if status_filter else None
    memories = await services.store.memories_for_user(user.id, statuses)
    visible = visible_for_retrieval(memories, include_flagged=flagged)
    return MemoriesOut(
        memories=[
            MemoryOut(memory=v.memory, flagged=v.flagged)
            for v in visible
            if kind is None or v.memory.kind == kind
        ]
    )


@router.get("/{memory_id}", response_model=MemoryDetailOut)
async def get_memory(
    memory_id: str,
    user: CurrentUser,
    services: CurrentServices,
    history: Annotated[bool, Query(description="Include the version chain and events.")] = False,
) -> MemoryDetailOut:
    memory = await owned_memory(services.store, user, memory_id)
    if memory.status is Status.RETIRED and not history:
        raise not_found()
    parents = await why(services.store, memory)
    history_out = None
    if history:
        versions = await services.store.version_chain(memory.id)
        events = await services.store.change_events_for_user(user.id)
        chain_ids = {v.id for v in versions}
        history_out = HistoryOut(
            versions=versions, events=[e for e in events if mentions(e, chain_ids)]
        )
    return MemoryDetailOut(
        memory=memory,
        flagged=memory.status in FLAGGED,
        why=parents,
        history=history_out,
        source=await source_for(services.upload_store, memory),
    )


@router.post("/{memory_id}/edit", response_model=IntakeOut)
async def edit_memory(
    memory_id: str, body: EditIn, user: CurrentUser, services: CurrentServices
) -> IntakeOut:
    """A new version created_by user that ripples as a user_edit (FR-12, ADR-0042).

    The inspector names the memory, so there is nothing to detect: the write goes
    straight to versioning rather than through change detection.
    """
    memory = await owned_memory(services.store, user, memory_id)
    if memory.status is Status.RETIRED:
        raise not_found()
    if memory.status is Status.PENDING_USER:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="memory has an open question; answer it with POST /questions/{id}/answer",
        )
    valid_to = body.valid_to if "valid_to" in body.model_fields_set else memory.valid_to
    now = services.clock.now()
    if valid_to is not None and valid_to <= now:
        # The new version starts now, so an end at or before now is not a belief; the
        # carried-over case is a temporary fact past its end before the sweep ran.
        if "valid_to" in body.model_fields_set:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="valid_to must be later than now",
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="this belief has already expired; send a new valid_to or null to keep it",
        )
    new_version, event = await update_memory(
        services.store,
        services.clock,
        memory.id,
        content=body.content,
        structured=body.structured if body.structured is not None else memory.structured,
        valid_to=valid_to,
        created_by="user",
        kind=TriggerKind.USER_EDIT,
        source_ref=f"inspector:{user.id}",
        trace_id=current_trace_id(),
    )
    event = await services.runner.run(event)
    return IntakeOut(
        memory=new_version, change_kind=ChangeKind.UPDATE, links_written=0, event=event
    )


@router.post("/{memory_id}/forget", response_model=ForgetOut)
async def forget_memory(memory_id: str, user: CurrentUser, services: CurrentServices) -> ForgetOut:
    """Hard deletion of the whole version chain and its depends_on subtree (I7)."""
    await owned_memory(services.store, user, memory_id)
    return ForgetOut(event=await forget(services.store, services.clock, memory_id))
