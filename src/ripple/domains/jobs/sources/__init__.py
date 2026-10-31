"""Allowed sources for the Scout (FR-8, ADR-0008, ADR-0070, ADR-0071).

A source is fetched only when the registry lists it with a terms note, robots.txt is
honoured per host, every request is a rate-limited GET, and nothing here follows a
login or posts a form (I6). Extraction turns a listing or an API reply into candidate
JD texts; the parsers (WS-2) and the adapter (WS-1) do the rest.
"""

from ripple.domains.jobs.sources.cache import CachedPage, FetchCache, InMemoryFetchCache
from ripple.domains.jobs.sources.canonical import canonical_url, fingerprint
from ripple.domains.jobs.sources.dedupe import (
    InMemoryScoutLedger,
    OpeningDeduplicator,
    ScoutLedger,
)
from ripple.domains.jobs.sources.extract import Candidate, extract_candidates, page_text
from ripple.domains.jobs.sources.fetcher import (
    FetchFailedError,
    FetchRefusedError,
    FetchResult,
    SourceFetcher,
)
from ripple.domains.jobs.sources.registry import (
    DEFAULT_SOURCES_CONFIG,
    ENV_SOURCES_CONFIG,
    ExtractionHint,
    SourceKind,
    SourceRegistry,
    SourceRegistryError,
    SourceSpec,
    load_registry,
    parse_registry,
    registry_from_env,
)

__all__ = [
    "DEFAULT_SOURCES_CONFIG",
    "ENV_SOURCES_CONFIG",
    "CachedPage",
    "Candidate",
    "ExtractionHint",
    "FetchCache",
    "FetchFailedError",
    "FetchRefusedError",
    "FetchResult",
    "InMemoryFetchCache",
    "InMemoryScoutLedger",
    "OpeningDeduplicator",
    "ScoutLedger",
    "SourceFetcher",
    "SourceKind",
    "SourceRegistry",
    "SourceRegistryError",
    "SourceSpec",
    "canonical_url",
    "extract_candidates",
    "fingerprint",
    "load_registry",
    "page_text",
    "parse_registry",
    "registry_from_env",
]
