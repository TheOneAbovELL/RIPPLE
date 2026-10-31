"""GET /graph: the user's visible memories and their links in one call (ADR-0087).

Replaces one detail request per node on the dashboard's map page. Read-only.
"""

from fastapi import APIRouter

from ripple.api.auth import CurrentServices, CurrentUser
from ripple.api.schemas import GraphOut, MemoryOut
from ripple.core.visibility import visible_for_retrieval

router = APIRouter(prefix="/graph", tags=["memories"])


@router.get("", response_model=GraphOut)
async def get_graph(user: CurrentUser, services: CurrentServices) -> GraphOut:
    memories = await services.store.memories_for_user(user.id)
    visible = visible_for_retrieval(memories, include_flagged=True)
    ids = {v.memory.id for v in visible}
    links = [
        link
        for link in await services.store.links_for_user(user.id)
        if link.parent_id in ids and link.dependent_id in ids
    ]
    return GraphOut(
        nodes=[MemoryOut(memory=v.memory, flagged=v.flagged) for v in visible], links=links
    )
