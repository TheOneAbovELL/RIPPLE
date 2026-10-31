"""Persisted resume text so span references resolve (ADR-0097).

Revision: 0006
Revises: 0005
Date: 2026-10-24

Hand-written to match src/ripple/storage/uploads_tables.py; the slow test
tests/storage/test_hardening_uploads_postgres.py::test_migration_0006_matches_uploads_tables
asserts the two agree.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "resume_uploads",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_resume_uploads_user_id", "resume_uploads", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_resume_uploads_user_id", table_name="resume_uploads")
    op.drop_table("resume_uploads")
