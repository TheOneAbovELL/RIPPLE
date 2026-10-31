"""Validity-aware hybrid retrieval, graph expansion, evidence (ADR-0026, ADR-0050).

Implements the C2 contract in ripple.core.retrieval_contract. The in-memory backend
imports core only; ripple.retrieval.postgres_search imports ripple.storage (the allowed
direction, docs/02) and is injected where a database exists.
"""

from ripple.retrieval.backend import SearchBackend, SearchHit
from ripple.retrieval.hybrid import HybridRetriever
from ripple.retrieval.indexing import index_memory
from ripple.retrieval.inmemory_search import InMemorySearchBackend

__all__ = [
    "HybridRetriever",
    "InMemorySearchBackend",
    "SearchBackend",
    "SearchHit",
    "index_memory",
]
