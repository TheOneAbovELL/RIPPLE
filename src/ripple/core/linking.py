"""Linker protocol (ADR-0009): find typed dependency links for a new memory.

A linker sees the new memory and a set of candidate memories and proposes edges in
either direction: an existing fact the new belief depends on, or an existing belief
that depends on the new fact (the "hidden link" case: a fit score for a JD that asks
for PyTorch depends on the new "skills: pytorch" fact). Core defines the contract and
the conversion to Link rows; implementations live in ripple.linking.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from ripple.core.errors import InvalidObjectError
from ripple.core.links import LinkTypeRegistry
from ripple.core.models import Link, LinkCreator, Memory


@dataclass(frozen=True)
class LinkProposal:
    parent_id: str
    dependent_id: str
    link_type: str
    confidence: float
    reason: str
    created_by: LinkCreator

    def __post_init__(self) -> None:
        if self.parent_id == self.dependent_id:
            raise InvalidObjectError("a memory cannot depend on itself")
        if not 0.0 <= self.confidence <= 1.0:
            raise InvalidObjectError("confidence must be in [0, 1]")


class Linker(Protocol):
    async def propose(self, memory: Memory, candidates: Sequence[Memory]) -> list[LinkProposal]:
        """Edges involving `memory`; every other endpoint must be one of `candidates`."""
        ...


def proposals_to_links(
    proposals: Sequence[LinkProposal],
    registry: LinkTypeRegistry,
    now: datetime,
    *,
    min_confidence: float = 0.0,
) -> list[Link]:
    """Stamp link_class from the registry and drop duplicates and weak proposals."""
    links: list[Link] = []
    seen: set[tuple[str, str, str]] = set()
    for proposal in proposals:
        key = (proposal.parent_id, proposal.dependent_id, proposal.link_type)
        if key in seen or proposal.confidence < min_confidence:
            continue
        seen.add(key)
        links.append(
            Link(
                parent_id=proposal.parent_id,
                dependent_id=proposal.dependent_id,
                link_type=proposal.link_type,
                link_class=registry.class_of(proposal.link_type),
                created_by=proposal.created_by,
                confidence=proposal.confidence,
                created_at=now,
            )
        )
    return links
