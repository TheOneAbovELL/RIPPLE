"""The allowed-sources registry: config/sources.yaml validated into Pydantic (ADR-0070).

ADR-0008 says the Scout uses only sources whose terms permit automated access, plus
what the user forwards. The registry is where that permission is written down: a
source without a terms note does not load, `robots_respected` can only be true, and a
career page stays `enabled: false` until the author has confirmed permission with the
site. Nothing else in the Scout can name a URL.
"""

import os
from collections.abc import Mapping
from enum import StrEnum
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from ripple.core.errors import ConfigurationError
from ripple.domains.jobs.sources.selectors import parse_selector

ENV_SOURCES_CONFIG = "RIPPLE_SOURCES_CONFIG"
DEFAULT_SOURCES_CONFIG = "config/sources.yaml"
_ID_PATTERN = r"^[a-z0-9][a-z0-9_-]{1,63}$"


class SourceRegistryError(ConfigurationError):
    """The registry file is missing, malformed or names a source we may not fetch."""


class SourceKind(StrEnum):
    PUBLIC_API = "public_api"  # a JSON endpoint the publisher documents for automated use
    CAREER_PAGE = "career_page"  # an HTML listing fetched with the site's permission
    FORWARDED_EMAIL = "forwarded_email"  # the user forwards it; nothing is fetched


class ExtractionHint(BaseModel):
    """How to find candidate JD texts in what a source returns (ADR-0070, point 4).

    HTML: `css_selector` picks the listing items; with `follow_links` each item's link
    is fetched and `detail_selector` (or the whole page) gives the JD text. JSON:
    `json_items` is a dotted path to the array, `json_text` / `json_url` /
    `json_title` dotted paths inside each item.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    css_selector: str | None = None
    detail_selector: str | None = None
    follow_links: bool = False
    json_items: str | None = None
    json_text: str | None = None
    json_url: str | None = None
    json_title: str | None = None

    @model_validator(mode="after")
    def _check_selectors(self) -> "ExtractionHint":
        # A bad selector fails here, once, not on every candidate every night.
        for name in ("css_selector", "detail_selector"):
            value = getattr(self, name)
            if value is not None:
                try:
                    parse_selector(value)
                except ValueError as exc:
                    raise ValueError(f"{name}: {exc}") from exc
        return self

    @property
    def is_empty(self) -> bool:
        return self.css_selector is None and self.json_items is None


class SourceSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=_ID_PATTERN)
    kind: SourceKind
    url: str | None = None
    # Where the permission comes from: the API terms page, the mail granting access,
    # or "the user forwards it". Free text, but it must say something (ADR-0008).
    terms_note: str = Field(min_length=1)
    # The only accepted value. Writing `false` is a request we refuse, not a setting.
    robots_respected: Literal[True]
    rate_limit_per_minute: int = Field(ge=1, le=600)
    parser: ExtractionHint = ExtractionHint()
    enabled: bool = True

    @model_validator(mode="after")
    def _check(self) -> "SourceSpec":
        if not self.terms_note.strip():
            raise ValueError("terms_note must say where the permission comes from")
        if self.kind is SourceKind.FORWARDED_EMAIL:
            if self.url is not None:
                raise ValueError("a forwarded_email source has no url; the user sends the text")
            if not self.parser.is_empty:
                raise ValueError("a forwarded_email source has no parser hint")
            return self
        if self.url is None:
            raise ValueError(f"a {self.kind.value} source needs a url")
        parts = urlsplit(self.url)
        if parts.scheme not in {"http", "https"} or not parts.hostname:
            raise ValueError("url must be an absolute http(s) URL")
        if parts.username or parts.password:
            raise ValueError("url must not carry credentials (I6)")
        if self.kind is SourceKind.CAREER_PAGE and self.parser.is_empty:
            raise ValueError("a career_page source needs parser.css_selector or parser.json_items")
        if self.kind is SourceKind.PUBLIC_API and (
            self.parser.json_items is None or self.parser.json_text is None
        ):
            raise ValueError("a public_api source needs parser.json_items and parser.json_text")
        return self

    @property
    def host(self) -> str | None:
        """The one host this source may be fetched from; None for forwarded email."""
        if self.url is None:
            return None
        hostname = urlsplit(self.url).hostname
        return hostname.lower() if hostname else None

    @property
    def fetchable(self) -> bool:
        return self.enabled and self.kind is not SourceKind.FORWARDED_EMAIL


class SourceRegistry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    # Identifies the Scout to the sites it fetches; a site owner must be able to tell
    # who is asking (robots.txt rules are matched against it too).
    user_agent: str = Field(min_length=1)
    sources: list[SourceSpec] = []

    @model_validator(mode="after")
    def _check(self) -> "SourceRegistry":
        seen: set[str] = set()
        for source in self.sources:
            if source.id in seen:
                raise ValueError(f"source id {source.id!r} appears twice")
            seen.add(source.id)
        return self

    def get(self, source_id: str) -> SourceSpec:
        for source in self.sources:
            if source.id == source_id:
                return source
        raise KeyError(source_id)

    def fetchable(self) -> list[SourceSpec]:
        """Sources the Scout may fetch this run: enabled and not forwarded email."""
        return [s for s in self.sources if s.fetchable]


def parse_registry(text: str) -> SourceRegistry:
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise SourceRegistryError(f"sources registry is not valid YAML: {exc}") from exc
    if not isinstance(raw, dict):
        raise SourceRegistryError("sources registry must be a mapping with user_agent and sources")
    try:
        return SourceRegistry.model_validate(raw)
    except ValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        )
        raise SourceRegistryError(f"sources registry refused: {problems}") from exc


def load_registry(path: Path) -> SourceRegistry:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SourceRegistryError(f"sources registry {path} cannot be read: {exc}") from exc
    return parse_registry(text)


def registry_from_env(env: Mapping[str, str] | None = None) -> SourceRegistry:
    env = os.environ if env is None else env
    return load_registry(Path(env.get(ENV_SOURCES_CONFIG, DEFAULT_SOURCES_CONFIG)))
