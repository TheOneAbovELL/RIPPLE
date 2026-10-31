"""Durable delivery log for digests and alerts (ADR-0095).

Revision: 0005
Revises: 0004
Date: 2026-10-24

Hand-written to match src/ripple/storage/delivery_tables.py; the slow test
tests/storage/test_hardening_delivery_log_postgres.py::test_migration_0005_matches_delivery_tables
asserts the two agree. WS-9 reserves 0007 and WS-10 reserves 0008 (production plan).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "delivery_log",
        sa.Column("user_id", sa.String(64), primary_key=True),
        sa.Column("kind", sa.String(16), primary_key=True),
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_delivery_log_user_kind_sent_at", "delivery_log", ["user_id", "kind", "sent_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_delivery_log_user_kind_sent_at", table_name="delivery_log")
    op.drop_table("delivery_log")
