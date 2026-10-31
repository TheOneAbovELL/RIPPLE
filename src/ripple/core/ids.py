"""Identifiers for memories, links and events.

Plain uuid4 strings: ordering comes from recorded_at, so no ULID/UUIDv7 dependency
(docs/plans/phase-0.md, task 0.5).
"""

from uuid import uuid4


def new_id() -> str:
    return str(uuid4())
