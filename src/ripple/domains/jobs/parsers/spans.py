"""Locate a model's quote in the source text (FR-2: every field links to its span).

The model is asked to quote verbatim, but PDF extraction and copy-paste break lines
where the model sees a space, and models tend to fix capitalisation. The search tries
exact, then whitespace-tolerant, then case-insensitive matching; the span always carries
the substring as it appears in the source, never the model's version of it. A quote
that is still not found returns None and the caller drops the field (ADR-0035).
"""

import re

from ripple.domains.jobs.vocabulary import TextSpan


def locate_span(text: str, quote: str) -> TextSpan | None:
    quote = quote.strip()
    if not quote:
        return None
    start = text.find(quote)
    if start >= 0:
        return TextSpan(start=start, end=start + len(quote), text=quote)
    tokens = quote.split()
    pattern = r"\s+".join(re.escape(token) for token in tokens)
    for flags in (0, re.IGNORECASE):
        match = re.search(pattern, text, flags)
        if match:
            return TextSpan(start=match.start(), end=match.end(), text=match.group(0))
    return None


def span_of_match(match: re.Match[str], group: int | str = 0) -> TextSpan:
    """A span for a regex match (used by the deterministic cross-check extractors)."""
    return TextSpan(start=match.start(group), end=match.end(group), text=match.group(group))
