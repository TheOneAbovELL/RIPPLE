"""Versioning: an update is a new row plus copied links (ADR-0014, ADR-0007).

Runs inside the caller's transaction so the new version, the old version's retirement
and every link copy commit together or not at all (NFR-4).
"""

from datetime import datetime

from ripple.core.ids import new_id
from ripple.core.links import policy_for
from ripple.core.models import Memory, Status, StructuredFact
from ripple.core.store import Transaction


async def write_new_version(
    tx: Transaction,
    old: Memory,
    *,
    content: str,
    structured: StructuredFact | None,
    valid_to: datetime | None,
    created_by: str,
    now: datetime,
    source_ref: str | None = None,
) -> Memory:
    """Create version n+1 of `old`, retire `old`, and copy its dependency links."""
    new = Memory(
        user_id=old.user_id,
        domain=old.domain,
        kind=old.kind,
        content=content,
        structured=structured,
        status=Status.VALID,
        valid_from=now,
        valid_to=valid_to,
        recorded_at=now,
        confidence=old.confidence,
        sensitivity=old.sensitivity,
        source_ref=source_ref if source_ref is not None else old.source_ref,
        created_by=created_by,
        version=old.version + 1,
        supersedes_id=old.id,
    )
    await tx.add_memory(new)
    await tx.replace_memory(old.model_copy(update={"status": Status.RETIRED}))

    # Incoming: the dependents of the old version now depend on the new one.
    # A dependent that is itself retired (superseded) is history and never ripples again.
    seen_dependents: set[tuple[str, str]] = set()
    for incoming in await tx.dependents_of(old.id):
        if policy_for(incoming.link_class).copied_on_update:
            dependent = await tx.get_memory(incoming.dependent_id)
            key = (dependent.id, incoming.link_type)
            if dependent.status is Status.RETIRED or key in seen_dependents:
                continue
            seen_dependents.add(key)
            await tx.add_link(
                incoming.model_copy(update={"id": new_id(), "parent_id": new.id, "created_at": now})
            )
    # Outgoing: the new version depends on the latest version of each parent, so a
    # later change to that parent still reaches it even if the Linker misses the edge.
    # A history link and its copy both resolve to the same latest parent: copy once.
    seen_parents: set[tuple[str, str]] = set()
    for outgoing in await tx.parents_of(old.id):
        if policy_for(outgoing.link_class).copied_on_update:
            parent = await tx.latest_version(outgoing.parent_id)
            if (parent.id, outgoing.link_type) in seen_parents:
                continue
            seen_parents.add((parent.id, outgoing.link_type))
            await tx.add_link(
                outgoing.model_copy(
                    update={
                        "id": new_id(),
                        "parent_id": parent.id,
                        "dependent_id": new.id,
                        "created_at": now,
                    }
                )
            )
    return new
