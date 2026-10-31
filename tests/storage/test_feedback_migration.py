"""Migration 0009 offline checks: one head, and 0009 follows 0006 (ADR-0105).

0007 and 0008 are reserved (IDEAS 11) and planned with down_revision "0006" as well
(docs/plans/parallel-execution/ws-9.md). The day one of them lands, this test fails
with two heads: re-point 0009 to the newest of them before any database runs 0009.
"""

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

REPO_ROOT = Path(__file__).resolve().parents[2]


def scripts() -> ScriptDirectory:
    return ScriptDirectory.from_config(Config(str(REPO_ROOT / "alembic.ini")))


def test_migration_chain_has_a_single_head():
    assert len(scripts().get_heads()) == 1


def test_migration_0009_creates_pilot_feedback_after_0006():
    revision = scripts().get_revision("0009")
    assert revision is not None
    assert revision.down_revision == "0006"
