"""Identity and confirmation flow: users, api_tokens, telegram_link_codes,
resume_candidates (ADR-0040, ADR-0043).

Revision: 0003
Revises: 0002
Date: 2026-10-19

Hand-written to match src/ripple/storage/users_tables.py; the slow test
tests/storage/test_users_postgres.py::test_migration_0003_matches_users_tables asserts
the two agree.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("display_name", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("telegram_chat_id", sa.BigInteger, nullable=True),
    )
    op.create_index("ix_users_telegram_chat_id", "users", ["telegram_chat_id"])

    op.create_table(
        "api_tokens",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("label", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("token_hash", name="uq_api_tokens_token_hash"),
    )
    op.create_index("ix_api_tokens_user_id", "api_tokens", ["user_id"])

    op.create_table(
        "telegram_link_codes",
        sa.Column("code", sa.String(16), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_telegram_link_codes_user_id", "telegram_link_codes", ["user_id"])

    op.create_table(
        "resume_candidates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("upload_id", sa.String(36), nullable=False),
        sa.Column("attribute", sa.String(64), nullable=False),
        sa.Column("value", JSONB, nullable=False),
        sa.Column("span_start", sa.Integer, nullable=False),
        sa.Column("span_end", sa.Integer, nullable=False),
        sa.Column("span_text", sa.Text, nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("memory_id", sa.String(36), nullable=True),
    )
    op.create_index("ix_resume_candidates_user_status", "resume_candidates", ["user_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_resume_candidates_user_status", table_name="resume_candidates")
    op.drop_table("resume_candidates")
    op.drop_index("ix_telegram_link_codes_user_id", table_name="telegram_link_codes")
    op.drop_table("telegram_link_codes")
    op.drop_index("ix_api_tokens_user_id", table_name="api_tokens")
    op.drop_table("api_tokens")
    op.drop_index("ix_users_telegram_chat_id", table_name="users")
    op.drop_table("users")
