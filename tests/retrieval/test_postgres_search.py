"""PostgresSearchBackend against a real database (slow). Needs TEST_DATABASE_URL or
DATABASE_URL pointing at a disposable Postgres with pgvector >= 0.5; CI provides one.

Mirrors the fixture pattern of tests/storage/test_postgres_store.py; the schema is the
one migration 0004 creates, so `alembic upgrade head` must include it.
"""

import asyncio
import os
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from ripple.core.errors import ConfigurationError
from ripple.core.models import Status
from ripple.core.retrieval_contract import RetrievalPath
from ripple.core.store import MemoryNotFoundError
from ripple.retrieval.hybrid import HybridRetriever
from ripple.retrieval.indexing import index_memory
from ripple.retrieval.postgres_search import PostgresSearchBackend
from ripple.storage.engine import database_url, engine_from_url
from ripple.storage.postgres import PostgresStore
from ripple.storage.search_schema import EMBEDDING_DIMENSIONS
from tests.builders import USER, derived, fact, link, memory
from tests.fakes.embedder import DeterministicFakeEmbedder

pytestmark = pytest.mark.slow

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def migrated():
    url = os.environ.get("TEST_DATABASE_URL") or database_url()
    if url is None:
        pytest.skip("TEST_DATABASE_URL/DATABASE_URL not set")
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv("DATABASE_URL", url)
    command.upgrade(Config(str(REPO_ROOT / "alembic.ini")), "head")
    yield url
    monkeypatch.undo()


@pytest.fixture
def engine(migrated: str):
    engine = engine_from_url(migrated)

    async def truncate():
        async with engine.begin() as conn:
            for table in ("links", "change_events", "forget_events", "memories"):
                await conn.execute(sa.text(f"TRUNCATE TABLE {table} CASCADE"))

    asyncio.run(truncate())
    yield engine
    asyncio.run(engine.dispose())


@pytest.fixture
def store(engine):
    return PostgresStore(engine)


@pytest.fixture
def backend(engine):
    return PostgresSearchBackend(engine)


@pytest.fixture
def embedder():
    return DeterministicFakeEmbedder(dimensions=EMBEDDING_DIMENSIONS)


def _write(store, memories, links=()):
    async def go():
        async with store.transaction() as tx:
            for m in memories:
                await tx.add_memory(m)
            for edge in links:
                await tx.add_link(edge)

    asyncio.run(go())


def test_postgres_lexical_ranks_matching_memories_of_the_user(store, backend):
    python = memory(content="likes Python and Django")
    rust = memory(content="likes Rust")
    theirs = memory(content="likes Python", user_id="student-2")
    _write(store, [python, rust, theirs])
    hits = asyncio.run(backend.lexical(USER, "python django", 10))
    assert [h.memory_id for h in hits] == [python.id]
    assert hits[0].score > 0


def test_postgres_lexical_empty_query_or_no_match_returns_nothing(store, backend):
    _write(store, [memory(content="likes Python")])
    assert asyncio.run(backend.lexical(USER, "", 10)) == []
    assert asyncio.run(backend.lexical(USER, "haskell", 10)) == []


def test_postgres_lexical_breaks_ties_by_id(store, backend):
    twins = sorted((memory(content="likes Python") for _ in range(3)), key=lambda m: m.id)
    _write(store, twins)
    assert [h.memory_id for h in asyncio.run(backend.lexical(USER, "python", 10))] == [
        m.id for m in twins
    ]


def test_postgres_lexical_respects_k(store, backend):
    _write(store, [memory(content="likes Python") for _ in range(3)])
    assert len(asyncio.run(backend.lexical(USER, "python", 2))) == 2


def test_postgres_index_writes_the_embedding_and_dense_ranks_by_cosine(store, backend, embedder):
    offer = memory(content="offer from Acme in Bangalore")
    talk = memory(content="Acme campus talk")
    weather = memory(content="weather is sunny")
    _write(store, [offer, talk, weather])
    for m in (offer, talk, weather):
        asyncio.run(index_memory(backend, embedder, m))
    stored = asyncio.run(backend.embedding_of(offer.id))
    assert stored is not None and len(stored) == EMBEDDING_DIMENSIONS
    [probe] = asyncio.run(embedder.embed(["offer from Acme"]))
    hits = asyncio.run(backend.dense(USER, probe, 10))
    assert [h.memory_id for h in hits][:2] == [offer.id, talk.id]
    assert hits[0].score > hits[1].score > hits[2].score


def test_postgres_dense_skips_rows_without_an_embedding(store, backend, embedder):
    with_vector, without = memory(content="a"), memory(content="b")
    _write(store, [with_vector, without])
    asyncio.run(index_memory(backend, embedder, with_vector))
    [probe] = asyncio.run(embedder.embed(["a"]))
    assert [h.memory_id for h in asyncio.run(backend.dense(USER, probe, 10))] == [with_vector.id]


def test_postgres_index_rejects_a_vector_of_the_wrong_dimension(store, backend):
    m = memory(content="a")
    _write(store, [m])
    with pytest.raises(ConfigurationError, match="dimensions"):
        asyncio.run(backend.index(m, [0.0] * 3))


def test_postgres_index_rejects_an_unknown_memory(store, backend):
    with pytest.raises(MemoryNotFoundError):
        asyncio.run(backend.index(memory(content="ghost"), [0.0] * EMBEDDING_DIMENSIONS))


def _seed_graph(store, backend, embedder):
    cgpa = fact("student", "cgpa", 7.6, content="cgpa is 7.6")
    old = fact("student", "cgpa", 7.1, content="cgpa was 7.1", status=Status.RETIRED)
    suspect = derived("cgpa under review", status=Status.SUSPECT)
    eligibility = derived("eligible for Globex")
    _write(store, [cgpa, old, suspect, eligibility], [link(cgpa, eligibility)])
    for m in (cgpa, old, suspect, eligibility):
        asyncio.run(index_memory(backend, embedder, m))
    return cgpa, suspect, eligibility


def test_postgres_lexical_retriever_expands_graph_from_the_only_visible_hit(
    store, backend, embedder
):
    # Lexical only: cgpa is the one VALID "cgpa" match, so eligibility must come via GRAPH.
    cgpa, _suspect, eligibility = _seed_graph(store, backend, embedder)
    plain = asyncio.run(HybridRetriever(store, backend).search(USER, "cgpa"))
    assert [(r.memory.id, r.via) for r in plain] == [
        (cgpa.id, RetrievalPath.LEXICAL),
        (eligibility.id, RetrievalPath.GRAPH),
    ]


def test_postgres_hybrid_retriever_end_to_end_respects_I1(store, backend, embedder):  # noqa: N802
    # With the dense path every embedded row is a candidate, so only I1 is asserted here.
    cgpa, suspect, eligibility = _seed_graph(store, backend, embedder)
    retriever = HybridRetriever(store, backend, embedder)
    plain = asyncio.run(retriever.search(USER, "cgpa"))
    assert {r.memory.id for r in plain} == {cgpa.id, eligibility.id}
    flagged = asyncio.run(retriever.search(USER, "cgpa", include_flagged=True))
    assert {r.memory.id: r.flagged for r in flagged} == {
        cgpa.id: False,
        suspect.id: True,
        eligibility.id: False,
    }
