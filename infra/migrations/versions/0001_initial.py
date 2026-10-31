"""Initial migration: enable pgvector, no tables yet.

Revision: 0001
Revises:
Date: 2026-10-19

Tables for Memory, Link, ChangeEvent, Decision and ForgetEvent arrive in Phase 1
(docs/03-data-model.md). This revision only proves the pipeline and creates the
extension every later revision relies on (ADR-0004).
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS vector")
