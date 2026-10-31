"""The forget API: the only path to hard deletion (I7, ADR-0007, ADR-0013).

Forget applies to a whole version chain and cascades along depends_on links; a
snapshot_of link is removed and its dependent kept. Everything commits in one
transaction with a ForgetEvent naming every deleted id, so an audit can show what left
the store without keeping the content.
"""

from ripple.core.clock import Clock
from ripple.core.indexing import MemoryIndexer
from ripple.core.links import ForgetBehaviour, policy_for
from ripple.core.models import ForgetEvent
from ripple.core.store import Store, Transaction


async def forget(
    store: Store, clock: Clock, root_memory_id: str, *, indexer: MemoryIndexer | None = None
) -> ForgetEvent:
    event = await _forget(store, clock, root_memory_id)
    if indexer is not None:
        for memory_id in event.deleted_ids:
            await indexer.remove(memory_id)
    return event


async def _forget(store: Store, clock: Clock, root_memory_id: str) -> ForgetEvent:
    async with store.transaction() as tx:
        root = await tx.get_memory(root_memory_id)
        doomed = await _cascade(tx, root_memory_id)
        link_ids: set[str] = set()
        for memory_id in doomed:
            for link in await tx.dependents_of(memory_id):
                link_ids.add(link.id)
            for link in await tx.parents_of(memory_id):
                link_ids.add(link.id)
        await tx.delete_links(link_ids)
        await tx.delete_memories(doomed)
        event = ForgetEvent(
            user_id=root.user_id,
            root_memory_id=root_memory_id,
            deleted_ids=sorted(doomed),
            created_at=clock.now(),
        )
        await tx.add_forget_event(event)
        return event


async def _cascade(tx: Transaction, root_memory_id: str) -> set[str]:
    """Every memory id to delete: the root's chain, then dependents' chains, recursively."""
    doomed: set[str] = set()
    frontier = [root_memory_id]
    while frontier:
        memory_id = frontier.pop()
        for version in await tx.version_chain(memory_id):
            if version.id in doomed:
                continue
            doomed.add(version.id)
            for link in await tx.dependents_of(version.id):
                # REMOVE_LINK: the link itself is deleted by the caller; the dependent stays.
                cascades = policy_for(link.link_class).on_forget is ForgetBehaviour.CASCADE_DELETE
                if cascades and link.dependent_id not in doomed:
                    frontier.append(link.dependent_id)
    return doomed
