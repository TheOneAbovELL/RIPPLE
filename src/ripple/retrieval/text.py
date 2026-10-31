"""Tokenisation shared by the in-memory backend and the fake embedder.

Deterministic and dependency-free on purpose: the same text always yields the same
tokens, so lexical scores and fake embeddings are reproducible across runs (NFR-5).
"""

import re

from ripple.core.models import Memory

# Words and numbers; a decimal such as "7.6" stays one token because CGPA cutoffs and
# versions are exactly the kind of literal a job-hunt query contains.
_TOKEN = re.compile(r"[a-z0-9]+(?:\.[0-9]+)?")


def tokenise(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


def searchable_text(memory: Memory) -> str:
    """Content plus the structured fact's parts, so a query on the value alone still hits."""
    parts = [memory.content]
    if memory.structured is not None:
        parts.extend(
            (
                memory.structured.subject,
                memory.structured.attribute,
                str(memory.structured.value),
            )
        )
    return " ".join(parts)
