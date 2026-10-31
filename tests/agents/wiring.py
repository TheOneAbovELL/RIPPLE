"""Wiring helpers shared by the agent tests.

Every agent is built from the same offline parts: FakeLLM behind a real Router,
InMemoryStore, FakeClock, a ScriptedEngine so the human-owned WaveEngine is not needed,
a ScriptedResolver, the RuleLinker (deterministic) and a detector that always says NEW
for prose. Tests override the parts they are about.
"""

import json
from collections.abc import Sequence
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver

from ripple.agents.checkpoints import memory_saver
from ripple.agents.conversation import ConversationAgent
from ripple.agents.tailor import TailorAgent
from ripple.core.change_detection import ChangeClassification, ChangeDetector, ChangeKind
from ripple.core.intake import Intake
from ripple.core.models import Link, Memory, StructuredFact
from ripple.core.resolver import Resolver
from ripple.core.ripple import RippleRunner
from ripple.domains.jobs.vocabulary import DOMAIN, jobs_registry
from ripple.linking.rules import RuleLinker
from ripple.llm.config import ModelSpec, RouterConfig
from ripple.llm.router import Router
from tests.fakes.clock import FakeClock
from tests.fakes.engine import ScriptedEngine
from tests.fakes.llm import FakeLLM
from tests.fakes.resolver import ScriptedResolver
from tests.fakes.retriever import ScriptedRetriever
from tests.fakes.store import InMemoryStore

TASKS = ("intent", "conversation", "tailor")


class ScriptedDetector:
    """Returns one classification for every prose statement."""

    def __init__(self, classification: ChangeClassification | None = None) -> None:
        self._classification = classification or ChangeClassification(
            kind=ChangeKind.NEW, reason="scripted: new"
        )

    async def classify(
        self, content: str, structured: StructuredFact | None, candidates: Sequence[Memory]
    ) -> ChangeClassification:
        return self._classification


def router(llm: FakeLLM, *, max_retries: int = 2) -> Router:
    config = RouterConfig(
        tasks={task: [ModelSpec(provider="fake", model="f")] for task in TASKS},
        max_retries=max_retries,
    )
    return Router(config, {"fake": llm})


def runner(
    store: InMemoryStore,
    clock: FakeClock,
    *,
    waves: Sequence[Sequence[str]] = (),
    resolver: Resolver | None = None,
) -> RippleRunner:
    class Factory(ScriptedEngine):
        def __init__(self, max_depth: int = 8) -> None:
            super().__init__(*waves, max_depth=max_depth)

    return RippleRunner(
        store,
        resolver or ScriptedResolver({}),
        clock,
        engine_factory=Factory,  # type: ignore[arg-type]
    )


def conversation_agent(
    store: InMemoryStore,
    clock: FakeClock,
    llm: FakeLLM,
    retriever: ScriptedRetriever | None = None,
    *,
    waves: Sequence[Sequence[str]] = (),
    resolver: Resolver | None = None,
    detector: ChangeDetector | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
    max_retries: int = 2,
) -> ConversationAgent:
    ripple_runner = runner(store, clock, waves=waves, resolver=resolver)
    intake = Intake(
        store,
        clock,
        jobs_registry(),
        RuleLinker(),
        detector or ScriptedDetector(),
        ripple_runner,
    )
    return ConversationAgent(
        store=store,
        clock=clock,
        router=router(llm, max_retries=max_retries),
        intake=intake,
        retriever=retriever or ScriptedRetriever(),
        runner=ripple_runner,
        checkpointer=checkpointer or memory_saver(),
        domain=DOMAIN,
    )


def tailor_agent(
    store: InMemoryStore,
    llm: FakeLLM,
    retriever: ScriptedRetriever | None = None,
    *,
    max_retries: int = 2,
) -> TailorAgent:
    return TailorAgent(
        store=store,
        router=router(llm, max_retries=max_retries),
        retriever=retriever or ScriptedRetriever(),
    )


async def seed(store: InMemoryStore, *memories: Memory, links: Sequence[Link] = ()) -> None:
    # Called on the class so a subclass that forbids transactions can still be seeded.
    async with InMemoryStore.transaction(store) as tx:
        for memory in memories:
            await tx.add_memory(memory)
        for edge in links:
            await tx.add_link(edge)


def intent(kind: str, **fields: Any) -> str:
    """Scripted IntentVerdict JSON."""
    return json.dumps({"intent": kind, "reason": "scripted", **fields})


def tell(statement: str, structured: dict[str, Any] | None = None) -> str:
    return intent("tell", statement=statement, structured=structured)


def claims(*items: tuple[str, list[str]]) -> str:
    """Scripted AnswerVerdict JSON: (text, evidence_ids) pairs."""
    return json.dumps({"claims": [{"text": t, "evidence_ids": ids} for t, ids in items]})


def highlights(*items: tuple[str, str, list[str]]) -> str:
    """Scripted TailorVerdict JSON: (memory_id, reason, opening_evidence_ids) triples."""
    return json.dumps(
        {
            "highlights": [
                {"memory_id": m, "reason": r, "opening_evidence_ids": ids} for m, r, ids in items
            ]
        }
    )
