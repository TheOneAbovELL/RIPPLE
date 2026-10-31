"""Resolver protocols (ADR-0003: the LLM decides action; ADR-0019: rules first).

The runner hands each SUSPECT memory to a Resolver with its trigger, its current
parents and the wave number. The resolver answers keep / update / retire / ask with a
reason and evidence references (I2). The LLM-backed resolver lives in ripple.llm;
core only defines the contract and the rule-first chain.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from ripple.core.errors import InvalidObjectError
from ripple.core.models import DecisionAction, Memory, StructuredFact


@dataclass(frozen=True)
class ResolutionContext:
    trigger: Memory
    memory: Memory
    parents: Sequence[Memory]
    wave: int


@dataclass(frozen=True)
class Resolution:
    action: DecisionAction
    reason: str
    evidence_refs: tuple[str, ...] = ()
    # For update only: the replacement content the new version carries.
    new_content: str | None = None
    new_structured: StructuredFact | None = None
    new_valid_to: datetime | None = None
    # For ask only: the question the user will see.
    question: str | None = None

    def __post_init__(self) -> None:
        if self.action is DecisionAction.UPDATE and not self.new_content:
            raise InvalidObjectError("an update resolution needs new_content")
        if self.action is not DecisionAction.UPDATE and self.new_content:
            raise InvalidObjectError("only an update resolution carries new_content")
        if self.action is DecisionAction.ASK and not self.question:
            raise InvalidObjectError("an ask resolution needs a question")
        if not self.reason:
            raise InvalidObjectError("a resolution needs a reason (I2)")


class Resolver(Protocol):
    async def resolve(self, context: ResolutionContext) -> Resolution: ...


class RuleResolver(Protocol):
    """A pure, deterministic first stage. Returns None when no rule applies."""

    def resolve(self, context: ResolutionContext) -> Resolution | None: ...


class ResolverChain:
    """Rules first, then the fallback (normally the LLM resolver)."""

    def __init__(self, rules: Sequence[RuleResolver], fallback: Resolver) -> None:
        self._rules = tuple(rules)
        self._fallback = fallback

    async def resolve(self, context: ResolutionContext) -> Resolution:
        for rule in self._rules:
            resolution = rule.resolve(context)
            if resolution is not None:
                return resolution
        return await self._fallback.resolve(context)
