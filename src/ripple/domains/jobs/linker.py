"""JobsStructureLinker: the jobs adapter's exact links for structured profile facts.

A profile fact (cgpa, its scale, batch, a skill) reaches the jobs beliefs by rules
that are part of the domain, not a matter of judgement: `profile.rule_targets` names
them. Proposing them here lets Intake link a structured statement without a model call
(ADR-0116, proposal 0002's "silver labels from structure"); prose still goes to the
LLM linker. Confidence is 1.0 because the rule is the definition of the dependency.
"""

from collections.abc import Sequence

from ripple.core.linking import LinkProposal
from ripple.core.models import LinkCreator, Memory
from ripple.domains.jobs.profile import rule_targets

STRUCTURE_CONFIDENCE = 1.0


class JobsStructureLinker:
    async def propose(self, memory: Memory, candidates: Sequence[Memory]) -> list[LinkProposal]:
        own = [c for c in candidates if c.user_id == memory.user_id and c.id != memory.id]
        return [
            LinkProposal(
                parent_id=memory.id,
                dependent_id=belief.id,
                link_type=link_type,
                confidence=STRUCTURE_CONFIDENCE,
                reason=f"domain rule: {memory.structured.attribute if memory.structured else '?'}"
                f" feeds {link_type}",
                created_by=LinkCreator.RULE,
            )
            for belief, link_type in rule_targets(memory, own)
        ]
