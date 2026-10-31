"""LLMChangeDetector: classifies prose statements (ADR-0020, FR-5, I4).

Only reached when the deterministic structured path in core.change_detection did not
decide. The current date is passed in so "this month" becomes a concrete valid_to.
"""

from collections.abc import Sequence

from ripple.core.change_detection import ChangeClassification, ChangeKind
from ripple.core.clock import Clock
from ripple.core.errors import LLMOutputInvalidError
from ripple.core.models import Memory, StructuredFact
from ripple.llm.client import Message
from ripple.llm.evidence import memories_block
from ripple.llm.prompts import load_prompt
from ripple.llm.router import Router
from ripple.llm.schemas.change import ChangeVerdict

TASK = "change_detector"
PROMPT_VERSION = 1


class LLMChangeDetector:
    def __init__(
        self, router: Router, clock: Clock, *, prompt_version: int = PROMPT_VERSION
    ) -> None:
        self._router = router
        self._clock = clock
        self._system = load_prompt("change_detector", prompt_version)
        self.prompt_version = prompt_version

    async def classify(
        self, content: str, structured: StructuredFact | None, candidates: Sequence[Memory]
    ) -> ChangeClassification:
        user = "\n\n".join(
            [
                f"Current date-time: {self._clock.now().isoformat()}",
                f"STATEMENT:\n```text\n{content}\n```",
                memories_block("EXISTING memories", candidates),
            ]
        )
        completion = await self._router.complete(
            TASK,
            [Message(role="system", content=self._system), Message(role="user", content=user)],
            ChangeVerdict,
        )
        verdict = completion.output
        if (
            verdict.kind is ChangeKind.TEMPORARY
            and verdict.valid_to is not None
            and verdict.valid_to <= self._clock.now()
        ):
            raise LLMOutputInvalidError(TASK, completion.attempts, "valid_to is not in the future")
        known = {c.id for c in candidates}
        if verdict.kind is ChangeKind.UPDATE and verdict.updates_memory_id not in known:
            # A valid schema but an id we do not hold: treat as new rather than guess.
            return ChangeClassification(
                kind=ChangeKind.NEW,
                reason=f"{verdict.reason} (unknown update target; stored as new)",
            )
        return ChangeClassification(
            kind=verdict.kind,
            reason=verdict.reason,
            updates_memory_id=verdict.updates_memory_id,
            valid_to=verdict.valid_to,
        )
