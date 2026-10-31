"""The delivery log table (ADR-0095), registered on the shared Base.metadata so Alembic
autogenerate and the drift test see it.

One row per (user, kind, key) that was sent: a digest day (`kind="digest"`, key = ISO
day) or an alert (`kind` = the AlertKind value, key = the opening memory id). The
primary key is the idempotency key: two workers racing to record the same delivery
collide on it instead of both believing they were first. Memory ids are plain strings,
not foreign keys, for the same reason as the event tables: an alert's audit outlives a
forgotten opening.
"""

import sqlalchemy as sa

from ripple.storage.base import Base

metadata = Base.metadata

DIGEST_KIND = "digest"

delivery_log = sa.Table(
    "delivery_log",
    metadata,
    sa.Column("user_id", sa.String(64), primary_key=True),
    sa.Column("kind", sa.String(16), primary_key=True),
    sa.Column("key", sa.String(64), primary_key=True),
    sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
    sa.Index("ix_delivery_log_user_kind_sent_at", "user_id", "kind", "sent_at"),
)
