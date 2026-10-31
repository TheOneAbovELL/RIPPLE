"""The pilot_feedback table (ADR-0105), registered on the shared Base.metadata.

One row per (user, target memory, kind): what a student said about a recommendation
(saved, applied, dismissed) or about a question the resolver asked (useful or not).
The unique key makes a double-tapped button one statement, not two. user_id cascades
on delete like resume_uploads, so a user row never outlives its feedback; DELETE /me
still removes the rows explicitly first (ADR-0044). target_memory_id cascades from
memories too: forgetting a memory (I7, the only hard deletion) removes what the student
said about it, in the forget's own transaction, so a note never outlives what it is
about whichever path called forget. A new version of an opening keeps the old version's
row, because versions are not deleted.
"""

import sqlalchemy as sa

from ripple.storage.base import Base

metadata = Base.metadata

NOTE_MAX_CHARS = 280

pilot_feedback = sa.Table(
    "pilot_feedback",
    metadata,
    sa.Column("id", sa.String(36), primary_key=True),
    sa.Column(
        "user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    ),
    sa.Column(
        "target_memory_id",
        sa.String(36),
        sa.ForeignKey("memories.id", ondelete="CASCADE"),
        nullable=False,
    ),
    sa.Column("kind", sa.String(32), nullable=False),
    sa.Column("note", sa.String(NOTE_MAX_CHARS), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.UniqueConstraint(
        "user_id", "target_memory_id", "kind", name="uq_pilot_feedback_user_target_kind"
    ),
    sa.Index("ix_pilot_feedback_created_at", "created_at"),
)
