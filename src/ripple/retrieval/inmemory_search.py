"""InMemorySearchBackend: BM25 over tokens plus cosine over stored vectors (ADR-0050).

The offline twin of ripple.storage.search. It ranks whatever it was asked to index,
status included; the retriever applies the I1 filter afterwards. Everything is
deterministic: ties are broken by memory id and no randomness enters the scores.
"""

import math
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from ripple.core.models import Memory
from ripple.retrieval.backend import SearchHit
from ripple.retrieval.text import searchable_text, tokenise

# Classic BM25 parameters (Robertson & Zaragoza, 2009): k1 saturates term frequency,
# b normalises for document length. Memories are short, so b matters little.
BM25_K1 = 1.5
BM25_B = 0.75


@dataclass(frozen=True)
class _Document:
    user_id: str
    term_counts: Counter[str]
    length: int


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b):
        raise ValueError(f"vector dimensions differ: {len(a)} != {len(b)}")
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class InMemorySearchBackend:
    def __init__(self) -> None:
        self._documents: dict[str, _Document] = {}
        self._embeddings: dict[str, tuple[float, ...]] = {}

    # ---- indexing ------------------------------------------------------------------

    async def index(self, memory: Memory, embedding: Sequence[float] | None) -> None:
        tokens = tokenise(searchable_text(memory))
        self._documents[memory.id] = _Document(memory.user_id, Counter(tokens), len(tokens))
        if embedding is None:
            self._embeddings.pop(memory.id, None)
        else:
            self._embeddings[memory.id] = tuple(embedding)

    def remove(self, memory_id: str) -> None:
        """Drop a forgotten memory; the Postgres backend gets this for free from the row."""
        self._documents.pop(memory_id, None)
        self._embeddings.pop(memory_id, None)

    def embedding_of(self, memory_id: str) -> tuple[float, ...] | None:
        """Test support: what index() stored for the memory."""
        return self._embeddings.get(memory_id)

    # ---- search --------------------------------------------------------------------

    async def lexical(self, user_id: str, query: str, k: int) -> list[SearchHit]:
        query_terms = tokenise(query)
        corpus = {
            memory_id: doc for memory_id, doc in self._documents.items() if doc.user_id == user_id
        }
        if not query_terms or not corpus or k <= 0:
            return []
        total = len(corpus)
        average_length = sum(doc.length for doc in corpus.values()) / total
        document_frequency = Counter(
            term for doc in corpus.values() for term in set(query_terms) if term in doc.term_counts
        )
        hits: list[SearchHit] = []
        for memory_id, doc in corpus.items():
            score = 0.0
            for term in query_terms:
                tf = doc.term_counts.get(term, 0)
                if tf == 0:
                    continue
                df = document_frequency[term]
                idf = math.log(1.0 + (total - df + 0.5) / (df + 0.5))
                length_norm = 1.0 - BM25_B + BM25_B * (doc.length / average_length)
                score += idf * (tf * (BM25_K1 + 1.0)) / (tf + BM25_K1 * length_norm)
            if score > 0.0:
                hits.append(SearchHit(memory_id, score))
        hits.sort(key=lambda hit: (-hit.score, hit.memory_id))
        return hits[:k]

    async def dense(self, user_id: str, vector: Sequence[float], k: int) -> list[SearchHit]:
        if k <= 0:
            return []
        hits = [
            SearchHit(memory_id, cosine_similarity(vector, embedding))
            for memory_id, embedding in self._embeddings.items()
            if self._documents[memory_id].user_id == user_id
        ]
        hits.sort(key=lambda hit: (-hit.score, hit.memory_id))
        return hits[:k]
