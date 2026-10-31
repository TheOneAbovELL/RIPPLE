"""LLMLinker: link finding by a model (ADR-0009, I4).

Proposals naming an id outside the candidate set or a link type outside the registry are
dropped, not retried: the schema was valid, the content was not usable, and a
deterministic filter is cheaper and more predictable than another model call.
"""

import logging
from collections.abc import Sequence

from ripple.core.linking import LinkProposal
from ripple.core.links import LinkTypeRegistry
from ripple.core.models import LinkCreator, Memory
from ripple.llm.client import Message
from ripple.llm.evidence import memories_block, memory_block
from ripple.llm.prompts import load_prompt
from ripple.llm.router import Router
from ripple.llm.schemas.links import LinkProposals

log = logging.getLogger("ripple.linking.llm")

TASK = "linker"
PROMPT_VERSION = 1


class LLMLinker:
    def __init__(
        self, router: Router, registry: LinkTypeRegistry, *, prompt_version: int = PROMPT_VERSION
    ) -> None:
        self._router = router
        self._registry = registry
        self._system = load_prompt("linker", prompt_version)
        self.prompt_version = prompt_version

    async def propose(self, memory: Memory, candidates: Sequence[Memory]) -> list[LinkProposal]:
        if not candidates:
            return []
        allowed = sorted(self._registry.known_types())
        user = "\n\n".join(
            [
                f"Allowed link types: {', '.join(allowed)}",
                memory_block("NEW memory", memory),
                memories_block("CANDIDATES", candidates),
            ]
        )
        completion = await self._router.complete(
            TASK,
            [Message(role="system", content=self._system), Message(role="user", content=user)],
            LinkProposals,
        )
        candidate_ids = {c.id for c in candidates}
        proposals: list[LinkProposal] = []
        for proposed in completion.output.proposals:
            if proposed.candidate_id not in candidate_ids or proposed.candidate_id == memory.id:
                log.info("linker dropped unknown candidate", extra={"memory_id": memory.id})
                continue
            if proposed.link_type not in allowed:
                log.info("linker dropped unknown link type", extra={"memory_id": memory.id})
                continue
            parent, dependent = (
                (proposed.candidate_id, memory.id)
                if proposed.candidate_is == "parent"
                else (memory.id, proposed.candidate_id)
            )
            proposals.append(
                LinkProposal(
                    parent_id=parent,
                    dependent_id=dependent,
                    link_type=proposed.link_type,
                    confidence=proposed.confidence,
                    reason=proposed.reason,
                    created_by=LinkCreator.LLM,
                )
            )
        return proposals
