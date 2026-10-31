"""ScriptedRetriever: returns the hits a test constructs, through the C2 contract.

It honours what the contract promises (I1): hits pass `visible_for_retrieval`, so a
RETIRED memory never comes back and a flagged one only when the caller opted in. Every
call is recorded so a test can assert the query and options an agent used.
"""

from dataclasses import dataclass

from ripple.core.models import Memory, Status
from ripple.core.retrieval_contract import RetrievalPath, RetrievedMemory
from ripple.core.visibility import visible_for_retrieval


@dataclass(frozen=True)
class SearchCall:
    user_id: str
    query: str
    k: int
    include_flagged: bool
    expand_graph: bool


def hit(
    memory: Memory,
    *,
    score: float = 1.0,
    via: RetrievalPath = RetrievalPath.LEXICAL,
    evidence: tuple[str, ...] | None = None,
) -> RetrievedMemory:
    """A RetrievedMemory as the real retriever would build it: flag from status,
    evidence defaulting to the memory's own source_ref."""
    if evidence is None:
        evidence = (memory.source_ref,) if memory.source_ref else ()
    return RetrievedMemory(
        memory=memory,
        score=score,
        flagged=memory.status is not Status.VALID,
        via=via,
        evidence=evidence,
    )


class ScriptedRetriever:
    def __init__(self, *hits: RetrievedMemory) -> None:
        self._hits = list(hits)
        self.calls: list[SearchCall] = []

    def script(self, *hits: RetrievedMemory) -> None:
        self._hits = list(hits)

    async def search(
        self,
        user_id: str,
        query: str,
        *,
        k: int = 10,
        include_flagged: bool = False,
        expand_graph: bool = True,
    ) -> list[RetrievedMemory]:
        self.calls.append(SearchCall(user_id, query, k, include_flagged, expand_graph))
        visible = {
            v.memory.id: v
            for v in visible_for_retrieval(
                (h.memory for h in self._hits if h.memory.user_id == user_id),
                include_flagged=include_flagged,
            )
        }
        results = [
            RetrievedMemory(
                memory=h.memory,
                score=h.score,
                flagged=visible[h.memory.id].flagged,
                via=h.via,
                evidence=h.evidence,
            )
            for h in self._hits
            if h.memory.id in visible
        ]
        return results[:k]
