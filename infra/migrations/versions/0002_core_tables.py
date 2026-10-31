"""Core tables: memories, links, change_events, forget_events (docs/03, ADR-0016).

Revision: 0002
Revises: 0001
Date: 2026-10-19

Hand-written to match src/ripple/storage/tables.py; the slow test
test_migrations_match_table_metadata asserts the two agree.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "memories",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("domain", sa.String(32), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("structured", JSONB, nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("sensitivity", sa.String(8), nullable=False),
        sa.Column("source_ref", sa.Text, nullable=True),
        sa.Column("created_by", sa.String(64), nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("supersedes_id", sa.String(36), nullable=True),
    )
    op.create_index("ix_memories_user_status", "memories", ["user_id", "status"])
    op.create_index("ix_memories_valid_to", "memories", ["valid_to"])
    op.create_index("ix_memories_supersedes_id", "memories", ["supersedes_id"])

    op.create_table(
        "links",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("parent_id", sa.String(36), sa.ForeignKey("memories.id"), nullable=False),
        sa.Column("dependent_id", sa.String(36), sa.ForeignKey("memories.id"), nullable=False),
        sa.Column("link_type", sa.String(64), nullable=False),
        sa.Column("link_class", sa.String(16), nullable=False),
        sa.Column("strength", sa.Float, nullable=False),
        sa.Column("created_by", sa.String(8), nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("parent_id", "dependent_id", "link_type", name="uq_links_edge"),
    )
    op.create_index("ix_links_parent_id", "links", ["parent_id"])
    op.create_index("ix_links_dependent_id", "links", ["dependent_id"])

    op.create_table(
        "change_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("trigger_kind", sa.String(16), nullable=False),
        sa.Column("trigger_memory_id", sa.String(36), nullable=False),
        sa.Column("affected_ids", JSONB, nullable=False),
        sa.Column("decisions", JSONB, nullable=False),
        sa.Column("parked", JSONB, nullable=False),
        sa.Column("cost_usd", sa.Float, nullable=True),
        sa.Column("latency_ms", sa.Integer, nullable=False),
        sa.Column("trace_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_change_events_user_open", "change_events", ["user_id", "completed_at"])

    op.create_table(
        "forget_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("root_memory_id", sa.String(36), nullable=False),
        sa.Column("deleted_ids", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("forget_events")
    op.drop_index("ix_change_events_user_open", table_name="change_events")
    op.drop_table("change_events")
    op.drop_index("ix_links_dependent_id", table_name="links")
    op.drop_index("ix_links_parent_id", table_name="links")
    op.drop_table("links")
    op.drop_index("ix_memories_supersedes_id", table_name="memories")
    op.drop_index("ix_memories_valid_to", table_name="memories")
    op.drop_index("ix_memories_user_status", table_name="memories")
    op.drop_table("memories")
