"""LLMResolver: the Resolver that asks a model (ADR-0003, ADR-0010, I4).

Reads prompt resolver.v<n>.md, sends trigger, belief and parents as evidence, and
validates the reply into ResolverVerdict through the Router before it becomes a core
Resolution. An invalid reply never reaches the runner: the Router retries, then raises.
"""

from ripple.core.resolver import Resolution, ResolutionContext
from ripple.llm.client import Message
from ripple.llm.evidence import memories_block, memory_block
from ripple.llm.prompts import load_prompt
from ripple.llm.router import Router
from ripple.llm.schemas.resolver import ResolverVerdict

TASK = "resolver"
PROMPT_VERSION = 1


class LLMResolver:
    def __init__(self, router: Router, *, prompt_version: int = PROMPT_VERSION) -> None:
        self._router = router
        self._system = load_prompt("resolver", prompt_version)
        self.prompt_version = prompt_version

    async def resolve(self, context: ResolutionContext) -> Resolution:
        user = "\n\n".join(
            [
                f"Wave {context.wave}.",
                memory_block("TRIGGER (the memory that changed)", context.trigger),
                memory_block("BELIEF (decide about this one)", context.memory),
                memories_block("PARENTS (current versions the belief depends on)", context.parents),
            ]
        )
        completion = await self._router.complete(
            TASK,
            [Message(role="system", content=self._system), Message(role="user", content=user)],
            ResolverVerdict,
        )
        verdict = completion.output
        shown = {context.trigger.id, context.memory.id, *(p.id for p in context.parents)}
        # Evidence must point at memories the model was shown, so I2 references resolve.
        evidence = tuple(ref for ref in verdict.evidence_refs if ref in shown)
        return Resolution(
            action=verdict.action,
            reason=verdict.reason,
            evidence_refs=evidence,
            new_content=verdict.new_content,
            question=verdict.question,
        )
