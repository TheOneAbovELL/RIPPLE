"""GET /events: the user's recent ChangeEvents, for the dashboard's "Recent ripples".

Every event carries the ids it touched; `memories` labels exactly those ids so a client
can show the trace without downloading the whole export (ADR-0118 amends ADR-0131
point 6). This is an audit view, like the inspector's `history=true`: a version an
event retired is named with status RETIRED so it is shown as the past, never as a live
belief (I1 governs retrieval, and nothing here is offered as current).

Forgetting deletes memories, not the ChangeEvents that mention them (I7, ADR-0044), so a
decision's reason can still quote a forgotten value. Here, a decision about, producing,
or resting on a forgotten memory (or in an event a forgotten memory triggered) has its
reason and question replaced by a fixed text before it leaves the API.
"""

from typing import Annotated

from fastapi import APIRouter, Query

from ripple.api.auth import CurrentServices, CurrentUser
from ripple.api.schemas import EventMemoryOut, EventsOut
from ripple.core.models import ChangeEvent, Decision
from ripple.core.store import MemoryNotFoundError

router = APIRouter(prefix="/events", tags=["me"])

FORGOTTEN_TEXT = "forgotten at the user's request"


def _named_ids(event: ChangeEvent) -> set[str]:
    ids = {event.trigger_memory_id, *event.affected_ids}
    for decision in event.decisions:
        ids.add(decision.memory_id)
        if decision.new_version_id is not None:
            ids.add(decision.new_version_id)
    for asked, parked in event.parked.items():
        ids.update([asked, *parked])
    return ids


@router.get("", response_model=EventsOut)
async def list_events(
    user: CurrentUser,
    services: CurrentServices,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    rippled_only: Annotated[
        bool, Query(description="Only events that decided on at least one belief.")
    ] = True,
) -> EventsOut:
    every = await services.store.change_events_for_user(user.id)
    # "Rippled": it reached another belief, decided or not yet (a ripple a model outage
    # stopped has affected ids and no decisions, and is exactly what to show).
    shown = [e for e in every if not rippled_only or e.decisions or e.affected_ids]
    shown.sort(key=lambda e: e.created_at, reverse=True)
    shown = shown[:limit]
    labels: dict[str, EventMemoryOut] = {}
    for memory_id in sorted(set().union(*(_named_ids(e) for e in shown))):
        try:
            memory = await services.store.get_memory(memory_id)
        except MemoryNotFoundError:
            continue  # forgotten since (I7): the event keeps the id, the content is gone
        if memory.user_id == user.id:
            labels[memory_id] = EventMemoryOut(content=memory.content, status=memory.status)
    forgotten = {
        memory_id
        for forget in await services.store.forget_events_for_user(user.id)
        for memory_id in forget.deleted_ids
    }
    if forgotten:
        shown = [_redacted(event, forgotten) for event in shown]
    return EventsOut(events=shown, memories=labels, total=len(every))


def _redacted(event: ChangeEvent, forgotten: set[str]) -> ChangeEvent:
    trigger_forgotten = event.trigger_memory_id in forgotten
    decisions: list[Decision] = []
    for decision in event.decisions:
        named = {decision.memory_id, decision.new_version_id, *decision.evidence_refs}
        if trigger_forgotten or named & forgotten:
            decision = decision.model_copy(
                update={
                    "reason": FORGOTTEN_TEXT,
                    "question": FORGOTTEN_TEXT if decision.question is not None else None,
                }
            )
        decisions.append(decision)
    return event.model_copy(update={"decisions": decisions})
