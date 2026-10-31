"""Identity and confirmation-flow tables (ADR-0040, ADR-0043), registered on the shared
Base.metadata so Alembic autogenerate and the drift test see them.

Owned by the API workstream (docs/plans/parallel-execution.md, WS-3). Memory ids on
resume_candidates are plain strings, not foreign keys, for the same reason as the event
tables: a forget deletes the memory and the candidate row is its own audit of what the
user confirmed. Tokens are stored hashed (sha256 of a secrets.token_urlsafe value);
the raw token is shown once by the admin CLI and never persisted.
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from ripple.storage.base import Base

metadata = Base.metadata

users = sa.Table(
    "users",
    metadata,
    sa.Column("id", sa.String(36), primary_key=True),
    sa.Column("display_name", sa.String(128), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("telegram_chat_id", sa.BigInteger, nullable=True),
    sa.Index("ix_users_telegram_chat_id", "telegram_chat_id"),
)

api_tokens = sa.Table(
    "api_tokens",
    metadata,
    sa.Column("id", sa.String(36), primary_key=True),
    sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
    sa.Column("token_hash", sa.String(64), nullable=False),
    sa.Column("label", sa.String(64), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.UniqueConstraint("token_hash", name="uq_api_tokens_token_hash"),
    sa.Index("ix_api_tokens_user_id", "user_id"),
)

telegram_link_codes = sa.Table(
    "telegram_link_codes",
    metadata,
    sa.Column("code", sa.String(16), primary_key=True),
    sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
    sa.Index("ix_telegram_link_codes_user_id", "user_id"),
)

resume_candidates = sa.Table(
    "resume_candidates",
    metadata,
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
    sa.Index("ix_resume_candidates_user_status", "user_id", "status"),
)
