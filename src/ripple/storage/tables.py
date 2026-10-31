"""SQL tables for the core models (docs/03-data-model.md, ADR-0016).

Core tables only. The embedding column for retrieval arrives in Phase 3 with its own
migration. Memory references inside events are plain strings, not foreign keys: an
event must survive the forget of the memories it names (I7 deletes rows; the audit
trail stays).
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from ripple.storage.base import Base

metadata = Base.metadata

memories = sa.Table(
    "memories",
    metadata,
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
    sa.Index("ix_memories_user_status", "user_id", "status"),
    sa.Index("ix_memories_valid_to", "valid_to"),
    sa.Index("ix_memories_supersedes_id", "supersedes_id"),
)

links = sa.Table(
    "links",
    metadata,
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
    sa.Index("ix_links_parent_id", "parent_id"),
    sa.Index("ix_links_dependent_id", "dependent_id"),
)

change_events = sa.Table(
    "change_events",
    metadata,
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
    sa.Index("ix_change_events_user_open", "user_id", "completed_at"),
)

forget_events = sa.Table(
    "forget_events",
    metadata,
    sa.Column("id", sa.String(36), primary_key=True),
    sa.Column("user_id", sa.String(64), nullable=False),
    sa.Column("root_memory_id", sa.String(36), nullable=False),
    sa.Column("deleted_ids", JSONB, nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
)
