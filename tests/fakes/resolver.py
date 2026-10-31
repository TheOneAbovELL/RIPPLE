"""ScriptedResolver: answers per memory id, and records every context it saw."""

from collections.abc import Mapping

from ripple.core.models import DecisionAction
from ripple.core.resolver import Resolution, ResolutionContext


def keep(reason: str = "still holds") -> Resolution:
    return Resolution(action=DecisionAction.KEEP, reason=reason)


def retire(reason: str = "no longer holds") -> Resolution:
    return Resolution(action=DecisionAction.RETIRE, reason=reason)


def update(new_content: str, reason: str = "changed with its parent") -> Resolution:
    return Resolution(action=DecisionAction.UPDATE, reason=reason, new_content=new_content)


def ask(question: str = "Does this still hold?", reason: str = "unsure") -> Resolution:
    return Resolution(action=DecisionAction.ASK, reason=reason, question=question)


class ScriptedResolver:
    def __init__(self, answers: Mapping[str, Resolution], default: Resolution | None = None):
        self._answers = dict(answers)
        self._default = default or keep()
        self.contexts: list[ResolutionContext] = []

    async def resolve(self, context: ResolutionContext) -> Resolution:
        self.contexts.append(context)
        return self._answers.get(context.memory.id, self._default)


class ExplodingResolver:
    """Raises on the nth call, to test crash recovery between commits."""

    def __init__(self, inner: ScriptedResolver, explode_on_call: int) -> None:
        self._inner = inner
        self._explode_on = explode_on_call
        self.calls = 0

    async def resolve(self, context: ResolutionContext) -> Resolution:
        self.calls += 1
        if self.calls == self._explode_on:
            raise ConnectionError("provider down")
        return await self._inner.resolve(context)
