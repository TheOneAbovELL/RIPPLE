"""Checkpoint factories (ADR-0023): the in-memory saver works offline; the Postgres one
is only constructed, never connected (NFR-1)."""

import inspect

from langgraph.checkpoint.base import BaseCheckpointSaver

from ripple.agents.checkpoints import memory_saver, postgres_saver


def test_memory_saver_is_a_fresh_checkpointer_each_time():
    a, b = memory_saver(), memory_saver()
    assert isinstance(a, BaseCheckpointSaver) and isinstance(b, BaseCheckpointSaver)
    assert a is not b


def test_postgres_saver_is_an_async_context_manager_that_does_not_connect_on_creation():
    assert inspect.isasyncgenfunction(postgres_saver.__wrapped__)  # type: ignore[attr-defined]
    manager = postgres_saver("postgresql://ripple:change-me@localhost:5432/ripple")
    assert hasattr(manager, "__aenter__") and hasattr(manager, "__aexit__")
