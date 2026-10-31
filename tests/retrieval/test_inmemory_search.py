import asyncio

import pytest

from ripple.retrieval.inmemory_search import InMemorySearchBackend, cosine_similarity
from ripple.retrieval.text import searchable_text, tokenise
from tests.builders import USER, fact, memory


def _indexed(*memories, embeddings=None):
    backend = InMemorySearchBackend()

    async def fill():
        for i, m in enumerate(memories):
            await backend.index(m, embeddings[i] if embeddings else None)

    asyncio.run(fill())
    return backend


def test_tokenise_lowercases_and_keeps_decimals_whole():
    assert tokenise("CGPA is 7.6, Acme-Corp!") == ["cgpa", "is", "7.6", "acme", "corp"]


def test_searchable_text_includes_structured_parts():
    text = searchable_text(fact("student", "cgpa", 7.6, content="my grade"))
    assert tokenise(text) == ["my", "grade", "student", "cgpa", "7.6"]


def test_lexical_ranks_the_memory_with_more_matching_terms_first():
    python = memory(content="likes Python and Django")
    rust = memory(content="likes Rust")
    backend = _indexed(python, rust)
    hits = asyncio.run(backend.lexical(USER, "python django", 10))
    assert [h.memory_id for h in hits] == [python.id]


def test_lexical_rarer_term_outweighs_common_term():
    a = memory(content="offer from Acme")
    b = memory(content="offer from Globex")
    c = memory(content="offer from Initech")
    backend = _indexed(a, b, c)
    hits = asyncio.run(backend.lexical(USER, "offer Globex", 10))
    assert hits[0].memory_id == b.id
    assert hits[0].score > hits[1].score


def test_lexical_matches_structured_value_not_in_content():
    cgpa = fact("student", "cgpa", 7.6, content="my grade")
    other = memory(content="unrelated")
    backend = _indexed(cgpa, other)
    assert [h.memory_id for h in asyncio.run(backend.lexical(USER, "7.6", 10))] == [cgpa.id]


def test_lexical_scopes_to_the_user():
    mine = memory(content="likes Python")
    theirs = memory(content="likes Python", user_id="student-2")
    backend = _indexed(mine, theirs)
    assert [h.memory_id for h in asyncio.run(backend.lexical(USER, "python", 10))] == [mine.id]
    assert [h.memory_id for h in asyncio.run(backend.lexical("student-2", "python", 10))] == [
        theirs.id
    ]


def test_lexical_breaks_ties_by_memory_id():
    twins = sorted((memory(content="likes Python") for _ in range(3)), key=lambda m: m.id)
    backend = _indexed(*reversed(twins))
    hits = asyncio.run(backend.lexical(USER, "python", 10))
    assert [h.memory_id for h in hits] == [m.id for m in twins]


def test_lexical_empty_query_returns_nothing():
    backend = _indexed(memory(content="likes Python"))
    assert asyncio.run(backend.lexical(USER, "", 10)) == []
    assert asyncio.run(backend.lexical(USER, "   ", 10)) == []


def test_lexical_no_matching_term_returns_nothing():
    backend = _indexed(memory(content="likes Python"))
    assert asyncio.run(backend.lexical(USER, "haskell", 10)) == []


def test_lexical_respects_k():
    memories = [memory(content=f"python note {i}") for i in range(5)]
    backend = _indexed(*memories)
    assert len(asyncio.run(backend.lexical(USER, "python", 2))) == 2
    assert asyncio.run(backend.lexical(USER, "python", 0)) == []


def test_reindexing_a_memory_replaces_its_terms():
    m = memory(content="likes Python")
    backend = _indexed(m)
    asyncio.run(backend.index(m.model_copy(update={"content": "likes Rust"}), None))
    assert asyncio.run(backend.lexical(USER, "python", 10)) == []
    assert [h.memory_id for h in asyncio.run(backend.lexical(USER, "rust", 10))] == [m.id]


def test_remove_drops_a_memory_from_both_indexes():
    m = memory(content="likes Python")
    backend = _indexed(m, embeddings=[[1.0, 0.0]])
    backend.remove(m.id)
    assert asyncio.run(backend.lexical(USER, "python", 10)) == []
    assert asyncio.run(backend.dense(USER, [1.0, 0.0], 10)) == []


def test_dense_orders_by_cosine_similarity():
    close, far, opposite = memory(content="a"), memory(content="b"), memory(content="c")
    backend = _indexed(close, far, opposite, embeddings=[[1.0, 0.1], [0.0, 1.0], [-1.0, 0.0]])
    hits = asyncio.run(backend.dense(USER, [1.0, 0.0], 10))
    assert [h.memory_id for h in hits] == [close.id, far.id, opposite.id]
    assert hits[0].score == pytest.approx(cosine_similarity([1.0, 0.1], [1.0, 0.0]))


def test_dense_skips_memories_without_an_embedding_and_other_users():
    with_vector = memory(content="a")
    without = memory(content="b")
    theirs = memory(content="c", user_id="student-2")
    backend = _indexed(with_vector, without, theirs, embeddings=[[1.0, 0.0], None, [1.0, 0.0]])
    hits = asyncio.run(backend.dense(USER, [1.0, 0.0], 10))
    assert [h.memory_id for h in hits] == [with_vector.id]


def test_dense_respects_k():
    memories = [memory(content=str(i)) for i in range(4)]
    backend = _indexed(*memories, embeddings=[[1.0, 0.0]] * 4)
    assert len(asyncio.run(backend.dense(USER, [1.0, 0.0], 2))) == 2


def test_cosine_similarity_rejects_dimension_mismatch():
    with pytest.raises(ValueError):
        cosine_similarity([1.0], [1.0, 0.0])


def test_cosine_similarity_of_a_zero_vector_is_zero():
    assert cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0
