"""DeterministicFakeEmbedder: hash-based vectors, no model, no network (ADR-0026).

Each token contributes a fixed pseudo-random direction derived from its sha256, so two
texts sharing tokens have similar vectors and unrelated texts do not. That is enough
for tests to exercise ranking, fusion and dimension checks; it says nothing about
semantic quality, which only the real Embedder comparison in Phase 3 can measure.
"""

import hashlib
import math
from collections.abc import Sequence

from ripple.retrieval.text import tokenise


class DeterministicFakeEmbedder:
    def __init__(self, dimensions: int = 8) -> None:
        if dimensions < 1:
            raise ValueError("dimensions must be positive")
        self._dimensions = dimensions
        self.calls: list[list[str]] = []  # what was embedded, for assertions

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self._dimensions
        for token in tokenise(text):
            for i, value in enumerate(self._direction(token)):
                vector[i] += value
        norm = math.sqrt(sum(v * v for v in vector))
        return [v / norm for v in vector] if norm else vector

    def _direction(self, token: str) -> list[float]:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        # Stretch the digest over the requested dimensions, mapping bytes to [-1, 1].
        values: list[float] = []
        counter = 0
        while len(values) < self._dimensions:
            block = digest if counter == 0 else hashlib.sha256(digest + bytes([counter])).digest()
            values.extend(byte / 127.5 - 1.0 for byte in block)
            counter += 1
        return values[: self._dimensions]
