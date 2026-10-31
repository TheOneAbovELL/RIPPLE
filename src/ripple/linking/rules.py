"""RuleLinker: the baseline link finder (ADR-0009).

Deterministic and cheap, with known low recall on hidden links. Two rules:
1. A new memory whose text mentions a structured fact's attribute or value depends on
   that fact (depends_on_fact).
2. A new structured fact is a parent of every existing memory whose text mentions its
   attribute or value, except other facts about the same subject and attribute, which
   are versions, not dependents.
Tokens are compared case-insensitively on word boundaries.
"""

import re
from collections.abc import Sequence

from ripple.core.linking import LinkProposal
from ripple.core.models import LinkCreator, Memory, StructuredFact

RULE_CONFIDENCE = 0.6
LINK_TYPE = "depends_on_fact"


def _mentions(text: str, structured: StructuredFact) -> bool:
    haystack = text.lower()
    needles = [structured.attribute.lower(), str(structured.value).lower()]
    return any(
        re.search(rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])", haystack)
        for needle in needles
        if len(needle) >= 2
    )


def _same_fact(a: StructuredFact, b: StructuredFact) -> bool:
    return a.subject == b.subject and a.attribute == b.attribute


class RuleLinker:
    async def propose(self, memory: Memory, candidates: Sequence[Memory]) -> list[LinkProposal]:
        proposals: list[LinkProposal] = []
        for candidate in candidates:
            if candidate.id == memory.id or candidate.user_id != memory.user_id:
                continue
            # Rule 1: the new memory depends on a fact it mentions.
            if (
                candidate.structured is not None
                and _mentions(memory.content, candidate.structured)
                and (
                    memory.structured is None
                    or not _same_fact(memory.structured, candidate.structured)
                )
            ):
                proposals.append(
                    LinkProposal(
                        parent_id=candidate.id,
                        dependent_id=memory.id,
                        link_type=LINK_TYPE,
                        confidence=RULE_CONFIDENCE,
                        reason=f"mentions {candidate.structured.attribute}",
                        created_by=LinkCreator.RULE,
                    )
                )
            # Rule 2: an existing memory that mentions the new fact depends on it.
            if (
                memory.structured is not None
                and _mentions(candidate.content, memory.structured)
                and (
                    candidate.structured is None
                    or not _same_fact(candidate.structured, memory.structured)
                )
            ):
                proposals.append(
                    LinkProposal(
                        parent_id=memory.id,
                        dependent_id=candidate.id,
                        link_type=LINK_TYPE,
                        confidence=RULE_CONFIDENCE,
                        reason=f"mentions {memory.structured.attribute}",
                        created_by=LinkCreator.RULE,
                    )
                )
        return proposals
