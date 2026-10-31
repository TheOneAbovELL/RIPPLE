"""Evidence formatting shared by the LLM-backed components.

Evidence (memory texts, user statements) goes in the user message only, inside fenced
blocks the prompts tell the model to treat as data (prompts.md, docs/02 Security).
"""

import json
from collections.abc import Iterable

from ripple.core.models import Memory


def memory_block(label: str, memory: Memory) -> str:
    payload = {
        "id": memory.id,
        "kind": memory.kind,
        "status": memory.status.value,
        "content": memory.content,
        "structured": memory.structured.model_dump() if memory.structured else None,
        "valid_to": memory.valid_to.isoformat() if memory.valid_to else None,
    }
    return f"{label}:\n```json\n{json.dumps(payload, ensure_ascii=False)}\n```"


def memories_block(label: str, memories: Iterable[Memory]) -> str:
    rows = [
        {
            "id": m.id,
            "kind": m.kind,
            "status": m.status.value,
            "content": m.content,
            "structured": m.structured.model_dump() if m.structured else None,
        }
        for m in memories
    ]
    return f"{label}:\n```json\n{json.dumps(rows, ensure_ascii=False)}\n```"
