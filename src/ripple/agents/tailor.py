"""Tailor agent (ADR-0046, FR-11): which real projects and skills to highlight for an opening.

    gather --> suggest

Read-only by construction: the graph never opens a store transaction. `gather` loads
the opening, its field memories and the candidate set (every recorded project or skill
fact, plus what retrieval adds); `suggest` asks the Router to pick from the candidates
by id and drops any highlight naming an id it was not shown (I5). The jobs vocabulary
is imported here on purpose: FR-11 is a jobs feature.
"""

import logging
from dataclasses import dataclass
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from ripple.agents.capabilities import Capability
from ripple.agents.evidence import flagged_memories_block
from ripple.core.errors import RippleError
from ripple.core.models import Memory, Status
from ripple.core.retrieval_contract import Retriever
from ripple.core.store import MemoryNotFoundError, Store
from ripple.core.visibility import FLAGGED
from ripple.domains.jobs.vocabulary import (
    PROFILE_SUBJECT,
    Kind,
    OpeningAttribute,
    ProfileAttribute,
    opening_subject,
)
from ripple.llm.client import Message
from ripple.llm.prompts import load_prompt
from ripple.llm.router import Router
from ripple.llm.schemas.tailor import TailorVerdict

log = logging.getLogger("ripple.agents.tailor")

TASK = "tailor"
PROMPT_VERSION = 1
LIVE = (Status.VALID, Status.SUSPECT, Status.PENDING_USER)
HIGHLIGHTABLE = frozenset({ProfileAttribute.PROJECT, ProfileAttribute.SKILL})
QUERY_ATTRIBUTES = (
    OpeningAttribute.TITLE,
    OpeningAttribute.COMPANY,
    OpeningAttribute.ROLE_TYPE,
    OpeningAttribute.REQUIRED_SKILL,
)

CAPABILITIES = frozenset(
    {Capability.LLM_COMPLETE, Capability.MEMORY_READ, Capability.MEMORY_RETRIEVE}
)

NO_CANDIDATES = "No projects or skills are recorded yet, so there is nothing real to highlight."


class OpeningUnavailableError(RippleError):
    """The opening does not exist for this user, is not an opening, or is retired."""

    def __init__(self, opening_memory_id: str, why: str) -> None:
        self.opening_memory_id = opening_memory_id
        super().__init__(f"opening {opening_memory_id!r}: {why}")


@dataclass(frozen=True)
class Suggestion:
    memory_id: str
    content: str
    reason: str
    # The opening and its field memories the reason rests on.
    evidence_ids: tuple[str, ...]
    flagged: bool


@dataclass(frozen=True)
class TailorSuggestions:
    opening_memory_id: str
    suggestions: tuple[Suggestion, ...]
    # Highlights the model gave for ids it was not shown (I5), or gave twice.
    dropped: int = 0
    note: str | None = None


NOT_PROFILE_KINDS = frozenset({Kind.OPENING, Kind.APPLICATION, Kind.CRITERIA})


def _about_the_student(memory: Memory) -> bool:
    """A retrieval hit is a candidate only if it describes the student: another
    opening's required skill is a real memory, but not the student's project."""
    if memory.kind in NOT_PROFILE_KINDS:
        return False
    return memory.structured is None or memory.structured.subject == PROFILE_SUBJECT


class TailorState(TypedDict):
    user_id: str
    opening_memory_id: str
    trace_id: str | None
    opening: Memory | None
    fields: list[Memory]
    candidates: list[Memory]
    suggestions: TailorSuggestions | None


class TailorAgent:
    def __init__(
        self,
        *,
        store: Store,
        router: Router,
        retriever: Retriever,
        k: int = 10,
        prompt_version: int = PROMPT_VERSION,
    ) -> None:
        self._store = store
        self._router = router
        self._retriever = retriever
        self._k = k
        self.prompt_version = prompt_version
        self._prompt = load_prompt("tailor", prompt_version)
        self.graph = self._build()

    @property
    def capabilities(self) -> frozenset[Capability]:
        return CAPABILITIES

    async def suggest(
        self, user_id: str, opening_memory_id: str, *, trace_id: str | None = None
    ) -> TailorSuggestions:
        state = await self.graph.ainvoke(
            {
                "user_id": user_id,
                "opening_memory_id": opening_memory_id,
                "trace_id": trace_id,
                "opening": None,
                "fields": [],
                "candidates": [],
                "suggestions": None,
            }
        )
        suggestions = state["suggestions"]
        assert suggestions is not None
        return suggestions

    # ---- graph ---------------------------------------------------------------

    def _build(self) -> Any:
        builder = StateGraph(TailorState)
        builder.add_node("gather", self._gather)
        builder.add_node("suggest", self._suggest)
        builder.add_edge(START, "gather")
        builder.add_edge("gather", "suggest")
        builder.add_edge("suggest", END)
        return builder.compile()

    async def _gather(self, state: TailorState) -> dict[str, Any]:
        user_id, opening_id = state["user_id"], state["opening_memory_id"]
        try:
            opening = await self._store.get_memory(opening_id)
        except MemoryNotFoundError as exc:
            raise OpeningUnavailableError(opening_id, "not found") from exc
        if opening.user_id != user_id:
            raise OpeningUnavailableError(opening_id, "belongs to another user")
        if opening.kind != Kind.OPENING:
            raise OpeningUnavailableError(opening_id, f"kind is {opening.kind!r}")
        if opening.status is Status.RETIRED:
            raise OpeningUnavailableError(opening_id, "retired")

        live = await self._store.memories_for_user(user_id, LIVE)
        subject = opening_subject(opening_id)
        fields = [m for m in live if m.structured is not None and m.structured.subject == subject]
        # Every recorded project or skill is a candidate whatever retrieval recalls.
        candidates = {
            m.id: m
            for m in live
            if m.structured is not None
            and m.structured.subject == PROFILE_SUBJECT
            and m.structured.attribute in HIGHLIGHTABLE
        }
        # Title, company, role, skills: a fixed order so the query is reproducible.
        values: dict[str, list[str]] = {}
        for f in fields:
            if f.structured is not None:
                values.setdefault(f.structured.attribute, []).append(str(f.structured.value))
        query = " ".join(v for a in QUERY_ATTRIBUTES for v in values.get(a, [])) or opening.content
        for h in await self._retriever.search(
            user_id, query, k=self._k, include_flagged=True, expand_graph=True
        ):
            if _about_the_student(h.memory):
                candidates.setdefault(h.memory.id, h.memory)
        return {"opening": opening, "fields": fields, "candidates": list(candidates.values())}

    async def _suggest(self, state: TailorState) -> dict[str, Any]:
        opening = state["opening"]
        assert opening is not None
        candidates = state["candidates"]
        if not candidates:
            return {
                "suggestions": TailorSuggestions(opening.id, (), note=NO_CANDIDATES),
            }
        user = "\n\n".join(
            [
                flagged_memories_block(
                    "OPENING (the memory and its fields)",
                    [(m, m.status in FLAGGED) for m in (opening, *state["fields"])],
                ),
                flagged_memories_block(
                    "CANDIDATES (the student's real projects and skills)",
                    [(m, m.status in FLAGGED) for m in candidates],
                ),
            ]
        )
        completion = await self._router.complete(
            TASK,
            [Message(role="system", content=self._prompt), Message(role="user", content=user)],
            TailorVerdict,
            trace_id=state["trace_id"],
        )
        by_id = {m.id: m for m in candidates}
        opening_ids = {opening.id, *(f.id for f in state["fields"])}
        kept: list[Suggestion] = []
        dropped = 0
        for highlight in completion.output.highlights:
            memory = by_id.get(highlight.memory_id)
            if memory is None or any(s.memory_id == memory.id for s in kept):
                dropped += 1
                continue
            kept.append(
                Suggestion(
                    memory_id=memory.id,
                    content=memory.content,
                    reason=highlight.reason,
                    evidence_ids=tuple(
                        i for i in dict.fromkeys(highlight.opening_evidence_ids) if i in opening_ids
                    ),
                    flagged=memory.status in FLAGGED,
                )
            )
        if dropped:
            log.info(
                "dropped highlights for unknown or repeated memories",
                extra={
                    "user_id": state["user_id"],
                    "dropped": dropped,
                    "trace_id": state["trace_id"],
                },
            )
        return {"suggestions": TailorSuggestions(opening.id, tuple(kept), dropped=dropped)}
