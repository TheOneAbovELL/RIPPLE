"""What retrieval may show (I1). Every retrieval path filters through here.

VALID memories are returned plainly. SUSPECT and PENDING_USER memories are returned
only when the caller asks for flagged results, and always carry the flag. RETIRED
memories are never returned.
"""

from collections.abc import Iterable
from dataclasses import dataclass

from ripple.core.models import Memory, Status

FLAGGED = frozenset({Status.SUSPECT, Status.PENDING_USER})


@dataclass(frozen=True)
class VisibleMemory:
    memory: Memory
    flagged: bool


def visible_for_retrieval(
    memories: Iterable[Memory], *, include_flagged: bool = False
) -> list[VisibleMemory]:
    visible: list[VisibleMemory] = []
    for memory in memories:
        if memory.status is Status.VALID:
            visible.append(VisibleMemory(memory, flagged=False))
        elif memory.status in FLAGGED and include_flagged:
            visible.append(VisibleMemory(memory, flagged=True))
        # RETIRED, and flagged-without-opt-in, never reach the caller.
    return visible
