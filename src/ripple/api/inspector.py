"""What the inspector shows about one memory: why it is held and which events touched it.

Shared by the HTTP inspector (ripple.api.routers.memories) and the MCP `explain` tool
(ripple.mcp_server.tools), so ADR-0042's rule for "why" is stated once.
"""

from ripple.api.schemas import ParentOut
from ripple.core.links import policy_for
from ripple.core.models import ChangeEvent, Memory
from ripple.core.store import StoreReader


async def why(store: StoreReader, memory: Memory) -> list[ParentOut]:
    """The parents this belief rests on. A history depends_on link (parent superseded)
    is skipped, docs/03 "Versioning"; snapshot_of links are shown always."""
    parents: list[ParentOut] = []
    seen: set[tuple[str, str]] = set()
    for link in await store.parents_of(memory.id):
        parent = await store.get_memory(link.parent_id)
        if parent.user_id != memory.user_id:
            continue  # core does not forbid cross-user links; the inspector never shows one
        if policy_for(link.link_class).propagates:
            latest = await store.latest_version(parent.id)
            if latest.id != parent.id:
                continue
        key = (parent.id, link.link_type)
        if key in seen:
            continue
        seen.add(key)
        parents.append(
            ParentOut(
                link_id=link.id,
                link_type=link.link_type,
                link_class=link.link_class,
                created_by=link.created_by,
                confidence=link.confidence,
                parent=parent,
            )
        )
    return parents


def mentions(event: ChangeEvent, memory_ids: set[str]) -> bool:
    """True when the event was triggered by, decided on, or parked any of the ids."""
    if event.trigger_memory_id in memory_ids or memory_ids & set(event.affected_ids):
        return True
    for decision in event.decisions:
        if decision.memory_id in memory_ids or decision.new_version_id in memory_ids:
            return True
    for asked, parked in event.parked.items():
        if asked in memory_ids or memory_ids & set(parked):
            return True
    return False
