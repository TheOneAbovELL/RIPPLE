"""Retrieval schema: embedding column, HNSW index, full-text GIN index (ADR-0050).

Revision: 0004
Revises: 0003
Date: 2026-10-19

Hand-written to match src/ripple/storage/search_schema.py, which extends the memories
table metadata with the same column and indexes so the autogenerate drift test can
compare them. The dimension is copied from ripple.retrieval.backend.EMBEDDING_DIMENSIONS
rather than imported: a migration must mean the same thing forever, and
tests/retrieval/test_migration_0004.py fails if the two numbers drift apart.

HNSW needs pgvector >= 0.5 (the compose image pgvector/pgvector:pg17 ships it). The
index is created on an empty column so it costs nothing until embeddings are written.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EMBEDDING_DIMENSIONS = 1024
FTS_CONFIG = "english"


def upgrade() -> None:
    op.execute(f"ALTER TABLE memories ADD COLUMN embedding vector({EMBEDDING_DIMENSIONS})")
    op.execute(
        "CREATE INDEX ix_memories_embedding_hnsw ON memories "
        "USING hnsw (embedding vector_cosine_ops)"
    )
    op.execute(
        "CREATE INDEX ix_memories_content_fts ON memories "
        f"USING gin (to_tsvector('{FTS_CONFIG}', content))"
    )


def downgrade() -> None:
    op.drop_index("ix_memories_content_fts", table_name="memories")
    op.drop_index("ix_memories_embedding_hnsw", table_name="memories")
    op.drop_column("memories", "embedding")
