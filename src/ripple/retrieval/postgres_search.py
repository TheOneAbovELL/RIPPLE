"""PostgresSearchBackend: full-text search and pgvector cosine over memories (ADR-0050).

Lives in ripple.retrieval, not ripple.storage, because docs/02 has retrieval depending on
storage and never the reverse: this module imports the tables and the schema extension
from storage and the SearchHit type from its own package.

The memories table is the index: a row that forget deleted cannot be found, and a new
version is searchable as soon as it is committed. Lexical ranking is ts_rank_cd over
`to_tsvector('english', content)`, the expression migration 0004 indexes with GIN;
dense ranking is pgvector's cosine distance on the `embedding` column, HNSW-indexed.
Status is deliberately not filtered here: the retriever applies the I1 rule.
"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from ripple.core.errors import ConfigurationError
from ripple.core.models import Memory
from ripple.core.store import MemoryNotFoundError
from ripple.retrieval.backend import SearchHit
from ripple.storage import search_schema
from ripple.storage import tables as t
from ripple.storage.search_schema import EMBEDDING_DIMENSIONS


class PostgresSearchBackend:
    def __init__(self, engine: AsyncEngine, *, dimensions: int = EMBEDDING_DIMENSIONS) -> None:
        self._engine = engine
        self._dimensions = dimensions

    async def lexical(self, user_id: str, query: str, k: int) -> list[SearchHit]:
        if not query.strip() or k <= 0:
            return []
        tsquery = sa.func.plainto_tsquery(sa.literal_column(f"'{search_schema.FTS_CONFIG}'"), query)
        document = search_schema.content_tsvector()
        rank = sa.func.ts_rank_cd(document, tsquery).label("score")
        statement = (
            sa.select(t.memories.c.id, rank)
            .where(t.memories.c.user_id == user_id)
            .where(document.op("@@")(tsquery))
            .order_by(sa.desc("score"), t.memories.c.id)
            .limit(k)
        )
        return await self._hits(statement)

    async def dense(self, user_id: str, vector: Sequence[float], k: int) -> list[SearchHit]:
        if k <= 0:
            return []
        self._check_dimensions(vector)
        embedding = t.memories.c[search_schema.EMBEDDING_COLUMN]
        probe = sa.cast(sa.literal(search_schema.vector_literal(vector)), search_schema.Vector())
        # Without return_type the operator inherits the vector type and `1 - distance`
        # would try to bind the 1 as a vector.
        distance = embedding.op("<=>", return_type=sa.Float)(probe)
        statement = (
            sa.select(t.memories.c.id, (1 - distance).label("score"))
            .where(t.memories.c.user_id == user_id)
            .where(embedding.is_not(None))
            .order_by(distance, t.memories.c.id)
            .limit(k)
        )
        return await self._hits(statement)

    async def index(self, memory: Memory, embedding: Sequence[float] | None) -> None:
        """Store the vector on the committed row; the lexical index needs no extra write."""
        if embedding is None:
            return
        self._check_dimensions(embedding)
        async with self._engine.begin() as conn:
            result = await conn.execute(
                sa.update(t.memories)
                .where(t.memories.c.id == memory.id)
                .values({search_schema.EMBEDDING_COLUMN: list(embedding)})
            )
            if result.rowcount == 0:
                raise MemoryNotFoundError(memory.id)

    async def embedding_of(self, memory_id: str) -> list[float] | None:
        """Read the stored vector back; test support, the only way to inspect the column."""
        async with self._engine.connect() as conn:
            row = (
                await conn.execute(
                    sa.select(t.memories.c[search_schema.EMBEDDING_COLUMN]).where(
                        t.memories.c.id == memory_id
                    )
                )
            ).first()
        if row is None:
            raise MemoryNotFoundError(memory_id)
        return row[0]

    def _check_dimensions(self, vector: Sequence[float]) -> None:
        if len(vector) != self._dimensions:
            raise ConfigurationError(
                f"vector has {len(vector)} dimensions; the column holds {self._dimensions}"
            )

    async def _hits(self, statement: sa.Select[Any, Any]) -> list[SearchHit]:
        async with self._engine.connect() as conn:
            rows = await conn.execute(statement)
        return [SearchHit(memory_id=memory_id, score=float(score)) for memory_id, score in rows]
