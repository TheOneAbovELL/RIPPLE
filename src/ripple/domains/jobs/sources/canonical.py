"""Canonical URLs and (company, title) fingerprints for dedupe (ADR-0071).

The same opening reaches the Scout under several spellings: a tracking parameter, a
trailing slash, an upper-case host, a fragment. Two JDs that are the same role at the
same company reach it from two sources with no URL in common. Both reductions are
deterministic string functions, so a duplicate decision never needs a model.
"""

import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_TRACKING_PREFIXES = ("utm_",)
# `ref` is deliberately not here: career sites use it as the job reference id.
_TRACKING_PARAMS = frozenset(
    {"fbclid", "gclid", "dclid", "msclkid", "yclid", "igshid", "mc_cid", "mc_eid", "ref_src"}
)
_DEFAULT_PORTS = {"http": 80, "https": 443}
_COMPANY_SUFFIXES = frozenset(
    {"pvt", "private", "ltd", "limited", "inc", "llc", "llp", "corp", "corporation", "co"}
)
_NON_ALNUM = re.compile(r"[^0-9a-z]+")


def canonical_url(url: str) -> str:
    """Lower-case scheme and host, no credentials, no default port, no fragment, no
    tracking parameters, sorted query, no trailing slash; raises ValueError for a
    relative or non-http(s) URL."""
    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower()
    if scheme not in {"http", "https"} or not parts.hostname:
        raise ValueError(f"not an absolute http(s) URL: {url!r}")
    host = parts.hostname.lower()
    port = parts.port
    netloc = host if port is None or port == _DEFAULT_PORTS[scheme] else f"{host}:{port}"
    path = re.sub(r"/{2,}", "/", parts.path) or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")
    query = urlencode(
        sorted(
            (key, value)
            for key, value in parse_qsl(parts.query, keep_blank_values=True)
            if not _is_tracking(key)
        )
    )
    return urlunsplit((scheme, netloc, path, query, ""))


def _is_tracking(key: str) -> bool:
    lowered = key.lower()
    return lowered in _TRACKING_PARAMS or lowered.startswith(_TRACKING_PREFIXES)


def _normalise(text: str, *, drop: frozenset[str] = frozenset()) -> str:
    words = _NON_ALNUM.sub(" ", text.casefold().replace("&", " and ")).split()
    return " ".join(word for word in words if word not in drop)


def fingerprint(company: str, title: str) -> str:
    """`<company>|<title>` with case, punctuation, spacing and legal suffixes removed."""
    return f"{_normalise(company, drop=_COMPANY_SUFFIXES)}|{_normalise(title)}"


def short_digest(text: str) -> str:
    """Twelve hex characters of SHA-1: identifies a text (an API item without a URL,
    a criteria content) without storing it."""
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]
