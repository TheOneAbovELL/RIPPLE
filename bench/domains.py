"""Which domain adapter a scenario is written in (ADR-0101).

A scenario names its domain in `meta.domain`; files without one are jobs scenarios,
so the smoke suite and RippleBench v0 read exactly as before. The runner takes the
Memory.domain value and the link-type registry from here, which is the write-flow job
docs/02 gives to the adapter's mapping.
"""

from collections.abc import Callable, Mapping
from typing import Any

from ripple.core.errors import ConfigurationError
from ripple.core.links import LinkTypeRegistry
from ripple.domains.finance.vocabulary import DOMAIN as FINANCE
from ripple.domains.finance.vocabulary import finance_registry
from ripple.domains.jobs.vocabulary import DOMAIN as JOBS
from ripple.domains.jobs.vocabulary import jobs_registry
from ripple.domains.news.vocabulary import DOMAIN as NEWS
from ripple.domains.news.vocabulary import news_registry

DEFAULT_DOMAIN = JOBS

REGISTRIES: Mapping[str, Callable[[], LinkTypeRegistry]] = {
    JOBS: jobs_registry,
    NEWS: news_registry,
    FINANCE: finance_registry,
}


def domain_of(meta: Mapping[str, Any]) -> str:
    domain = meta.get("domain", DEFAULT_DOMAIN)
    if not isinstance(domain, str) or domain not in REGISTRIES:
        raise ConfigurationError(
            f"scenario domain {domain!r} has no adapter; known: {', '.join(sorted(REGISTRIES))}"
        )
    return str(domain)


def registry_for(domain: str) -> LinkTypeRegistry:
    try:
        return REGISTRIES[domain]()
    except KeyError as exc:
        raise ConfigurationError(f"no link-type registry for domain {domain!r}") from exc
