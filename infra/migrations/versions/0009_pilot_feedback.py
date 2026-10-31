"""Pilot feedback: saved, applied, dismissed, question usefulness (ADR-0105).

Revision: 0009
Revises: 0006
Date: 2026-10-31

Ids 0007 and 0008 are reserved for the Scout and Telegram ledgers (IDEAS 11), so this
revision follows 0006 directly. They are planned with down_revision "0006" too: when
either lands, re-point this revision to the newest of them before any database runs
0009, or the chain has two heads (tests/storage/test_feedback_migration.py fails then).
Hand-written to match
src/ripple/storage/feedback_tables.py; the slow test
tests/storage/test_feedback_postgres.py::test_migration_0009_matches_feedback_tables
asserts the two agree.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pilot_feedback",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_memory_id",
            sa.String(36),
            sa.ForeignKey("memories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("note", sa.String(280), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "user_id", "target_memory_id", "kind", name="uq_pilot_feedback_user_target_kind"
        ),
    )
    op.create_index("ix_pilot_feedback_created_at", "pilot_feedback", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_pilot_feedback_created_at", table_name="pilot_feedback")
    op.drop_table("pilot_feedback")
