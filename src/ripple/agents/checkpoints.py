"""Checkpoint savers for the agent graphs (ADR-0023).

Tests use the in-memory saver. Production opens a Postgres saver on the same database
as the memory store, in LangGraph's own tables, created by its `setup()` here rather
than by Alembic. The connection string is a psycopg DSN, not a SQLAlchemy URL.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver


def memory_saver() -> BaseCheckpointSaver:
    """Per-process saver for tests and local runs; state is lost on exit."""
    return InMemorySaver()


@asynccontextmanager
async def postgres_saver(dsn: str) -> AsyncIterator[BaseCheckpointSaver]:
    """Durable saver for the service; call once at start-up and keep it open.

    Not exercised by the offline suite (NFR-1); covered by the slow tests once a
    database is available (docs/plans/parallel-execution/ws-4.md, open problems).
    """
    async with AsyncPostgresSaver.from_conn_string(dsn) as saver:
        await saver.setup()
        yield saver
