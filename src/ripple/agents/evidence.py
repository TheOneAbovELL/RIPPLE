"""Evidence blocks the agents put in the user message (prompts.md: evidence is data).

Extends ripple.llm.evidence with what retrieval adds: the flag (I1) and the source
references the agent may cite.
"""

import json
from collections.abc import Iterable

from ripple.core.models import Memory
from ripple.core.retrieval_contract import RetrievedMemory


def retrieved_block(label: str, hits: Iterable[RetrievedMemory]) -> str:
    rows = [
        {
            "id": h.memory.id,
            "kind": h.memory.kind,
            "status": h.memory.status.value,
            "flagged": h.flagged,
            "content": h.memory.content,
            "structured": h.memory.structured.model_dump() if h.memory.structured else None,
            "source_refs": list(h.evidence),
        }
        for h in hits
    ]
    return f"{label}:\n```json\n{json.dumps(rows, ensure_ascii=False)}\n```"


def flagged_memories_block(label: str, memories: Iterable[tuple[Memory, bool]]) -> str:
    rows = [
        {
            "id": m.id,
            "kind": m.kind,
            "status": m.status.value,
            "flagged": flagged,
            "content": m.content,
            "structured": m.structured.model_dump() if m.structured else None,
        }
        for m, flagged in memories
    ]
    return f"{label}:\n```json\n{json.dumps(rows, ensure_ascii=False)}\n```"


def text_block(label: str, text: str) -> str:
    return f"{label}:\n```text\n{text}\n```"
