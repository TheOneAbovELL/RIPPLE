"""The resume_uploads table (ADR-0097), registered on the shared Base.metadata.

The text layer of every uploaded resume is kept so that a confirmed fact's
`source_ref` of the form `resume:<upload id>#<start>-<end>` resolves to the exact
characters the parser read (FR-12: the inspector shows the quoted line). The PDF bytes
are not kept: the text is what the spans index into, and the file itself is the user's.
user_id cascades on delete so a user row can never outlive its uploads by accident;
DELETE /me still removes them explicitly first (ADR-0044).
"""

import sqlalchemy as sa

from ripple.storage.base import Base

metadata = Base.metadata

resume_uploads = sa.Table(
    "resume_uploads",
    metadata,
    sa.Column("id", sa.String(36), primary_key=True),
    sa.Column(
        "user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    ),
    sa.Column("filename", sa.String(255), nullable=False),
    sa.Column("sha256", sa.String(64), nullable=False),
    sa.Column("text", sa.Text, nullable=False),
    sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
    sa.Index("ix_resume_uploads_user_id", "user_id"),
)
