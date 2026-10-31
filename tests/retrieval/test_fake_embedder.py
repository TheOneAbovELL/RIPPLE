import asyncio
import math

import pytest

from ripple.retrieval.inmemory_search import cosine_similarity
from tests.fakes.embedder import DeterministicFakeEmbedder


def test_fake_embedder_is_deterministic_across_instances():
    first = asyncio.run(DeterministicFakeEmbedder(8).embed(["CGPA is 7.6"]))
    second = asyncio.run(DeterministicFakeEmbedder(8).embed(["CGPA is 7.6"]))
    assert first == second


def test_fake_embedder_returns_unit_vectors_of_the_requested_dimension():
    embedder = DeterministicFakeEmbedder(dimensions=12)
    [vector] = asyncio.run(embedder.embed(["likes Python"]))
    assert len(vector) == 12
    assert math.sqrt(sum(v * v for v in vector)) == pytest.approx(1.0)


def test_fake_embedder_shared_tokens_mean_higher_similarity():
    embedder = DeterministicFakeEmbedder(dimensions=32)
    a, b, c = asyncio.run(
        embedder.embed(["offer from Acme in Bangalore", "offer from Acme", "weather is sunny"])
    )
    assert cosine_similarity(a, b) > cosine_similarity(a, c)


def test_fake_embedder_empty_text_is_the_zero_vector_and_records_calls():
    embedder = DeterministicFakeEmbedder(dimensions=4)
    [vector] = asyncio.run(embedder.embed([""]))
    assert vector == [0.0] * 4
    assert embedder.calls == [[""]]


def test_fake_embedder_rejects_non_positive_dimensions():
    with pytest.raises(ValueError):
        DeterministicFakeEmbedder(0)
