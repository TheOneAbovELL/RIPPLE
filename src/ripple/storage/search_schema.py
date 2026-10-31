"""Schema additions for retrieval on the memories table (migration 0004, ADR-0050).

tables.py is coordinator-owned and knows only the core columns, so this module extends
the shared metadata in place: a pgvector `embedding` column, an HNSW index on it and a
GIN index over `to_tsvector('english', content)`. Importing it is what lets Alembic's
autogenerate comparison (tests/storage/test_postgres_store.py) see the same schema the
migration creates; ripple.retrieval.postgres_search imports it, so any process that
searches has it. Alembic's env.py does not yet (see the WS-5 handover).

No pgvector Python package is installed (no new dependency without an ADR), so `Vector`
is a minimal SQLAlchemy type: it renders the DDL, teaches reflection the `vector` name,
and binds values as the text literal pgvector parses ("[0.1,0.2,...]").
"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import base as pg_base
from sqlalchemy.types import UserDefinedType

from ripple.storage import tables as t

# Dimension of the pgvector column added by migration 0004 (ADR-0050). 1024 is BGE-M3's
# output size, the leading candidate in ADR-0026; the migration hard-codes the same
# number and tests/retrieval/test_migration_0004.py keeps the two equal. An Embedder
# with another size needs a new migration, not a new constant.
EMBEDDING_DIMENSIONS = 1024
EMBEDDING_COLUMN = "embedding"
EMBEDDING_INDEX = "ix_memories_embedding_hnsw"
CONTENT_FTS_INDEX = "ix_memories_content_fts"
FTS_CONFIG = "english"


class Vector(UserDefinedType[list[float]]):
    cache_ok = True

    def __init__(self, dimensions: int | str | None = None) -> None:
        # Reflection passes the dimension parsed from "vector(1024)" as a string.
        self.dimensions = int(dimensions) if dimensions is not None else None

    def get_col_spec(self, **kw: Any) -> str:
        return "vector" if self.dimensions is None else f"vector({self.dimensions})"

    def bind_processor(self, dialect: sa.Dialect) -> Any:
        def process(value: Sequence[float] | str | None) -> str | None:
            if value is None or isinstance(value, str):
                return value
            return vector_literal(value)

        return process

    def result_processor(self, dialect: sa.Dialect, coltype: Any) -> Any:
        def process(value: str | None) -> list[float] | None:
            if value is None:
                return None
            return [float(part) for part in value.strip("[]").split(",") if part]

        return process


def vector_literal(vector: Sequence[float]) -> str:
    return "[" + ",".join(repr(float(v)) for v in vector) + "]"


def content_tsvector() -> sa.ColumnElement[Any]:
    """The indexed expression; every lexical query must use exactly this to hit the index."""
    return sa.func.to_tsvector(sa.literal_column(f"'{FTS_CONFIG}'"), t.memories.c.content)


def _extend_metadata() -> None:
    if EMBEDDING_COLUMN in t.memories.c:
        return  # idempotent across repeated imports and reloads
    # Let reflection map a `vector` column back to this type, as pgvector's package does.
    pg_base.ischema_names["vector"] = Vector
    t.memories.append_column(
        sa.Column(EMBEDDING_COLUMN, Vector(EMBEDDING_DIMENSIONS), nullable=True)
    )
    sa.Index(
        EMBEDDING_INDEX,
        t.memories.c[EMBEDDING_COLUMN],
        postgresql_using="hnsw",
        postgresql_ops={EMBEDDING_COLUMN: "vector_cosine_ops"},
    )
    # A purely functional index does not infer its table from the column inside the
    # function call (checked on SQLAlchemy 2.1.5), so the table is named explicitly.
    sa.Index(CONTENT_FTS_INDEX, content_tsvector(), postgresql_using="gin", _table=t.memories)


_extend_metadata()
