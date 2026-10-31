"""StructuredFirstLinker: deterministic linkers for structured facts, a model for prose.

A structured fact's dependents are found by rules (the domain's structure linker and
the mention rules of RuleLinker), exactly and without a model call. A prose memory has
no structure to reason from, so it goes to the prose linker (the LLM linker in
production) as well as the mention rules. Proposals are merged; `proposals_to_links`
drops duplicates (ADR-0116).
"""

from collections.abc import Sequence

from ripple.core.linking import Linker, LinkProposal
from ripple.core.models import Memory


class StructuredFirstLinker:
    def __init__(self, deterministic: Sequence[Linker], prose: Linker) -> None:
        self._deterministic = tuple(deterministic)
        self._prose = prose

    async def propose(self, memory: Memory, candidates: Sequence[Memory]) -> list[LinkProposal]:
        proposals: list[LinkProposal] = []
        for linker in self._deterministic:
            proposals += await linker.propose(memory, candidates)
        if memory.structured is None:
            proposals += await self._prose.propose(memory, candidates)
        return proposals
