"""Migration 0004 copies constants instead of importing them; keep the copies honest."""

import importlib.util
from pathlib import Path

from ripple.storage import search_schema, tables
from ripple.storage.search_schema import EMBEDDING_DIMENSIONS

MIGRATION = (
    Path(__file__).resolve().parents[2] / "infra" / "migrations" / "versions" / "0004_embeddings.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location("migration_0004", MIGRATION)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_0004_dimension_matches_the_backend_constant():
    migration = _load_migration()
    assert migration.EMBEDDING_DIMENSIONS == EMBEDDING_DIMENSIONS == 1024
    assert migration.FTS_CONFIG == search_schema.FTS_CONFIG


def test_migration_0004_chains_after_0003_users():
    migration = _load_migration()
    assert (migration.revision, migration.down_revision) == ("0004", "0003")


def test_search_schema_adds_a_nullable_vector_column_of_the_migration_dimension():
    column = tables.memories.c[search_schema.EMBEDDING_COLUMN]
    assert column.nullable is True
    assert isinstance(column.type, search_schema.Vector)
    assert column.type.get_col_spec() == f"vector({EMBEDDING_DIMENSIONS})"


def test_search_schema_attaches_both_indexes_to_the_memories_table():
    # The functional index needs the private `_table=` kwarg; a SQLAlchemy upgrade that
    # drops it must fail here rather than silently lose the index from metadata.
    by_name = {str(index.name): index for index in tables.memories.indexes}
    assert {search_schema.EMBEDDING_INDEX, search_schema.CONTENT_FTS_INDEX} <= set(by_name)
    assert by_name[search_schema.CONTENT_FTS_INDEX].table is tables.memories


def test_vector_type_parses_the_pgvector_text_literal():
    parse = search_schema.Vector(3).result_processor(None, None)  # type: ignore[arg-type]
    assert parse("[1,0.5,-2]") == [1.0, 0.5, -2.0]
    assert parse(None) is None


def test_vector_type_binds_sequences_as_the_pgvector_text_literal():
    assert search_schema.vector_literal([1.0, 0.5, -2]) == "[1.0,0.5,-2.0]"
    bind = search_schema.Vector(3).bind_processor(None)  # type: ignore[arg-type]
    assert bind([1, 2, 3]) == "[1.0,2.0,3.0]"
    assert bind("[1,2,3]") == "[1,2,3]"
    assert bind(None) is None
