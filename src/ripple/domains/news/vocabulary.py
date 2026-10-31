"""News-domain vocabulary (ADR-0100): kinds, attributes and link types.

A news memory is a claim about a developing story ("the toll is 12", "officials blame
the contractor") or a belief built on claims: a summary, an analysis, a briefing for
the reader. Stories develop and get corrected, and every summary that repeated the
old claim goes stale with it; that is the cascade the news track measures. Something
the reader already shared is a record of what was said at the time, so it is a
snapshot and a correction never rewrites it.

Core interprets none of these strings; the write flow maps each link type to a core
class through `news_registry()` (docs/02, "How core stays domain-agnostic").
"""

from collections.abc import Mapping
from enum import StrEnum

from ripple.core.links import LinkTypeRegistry
from ripple.core.models import LinkClass

DOMAIN = "news"
READER_SUBJECT = "reader"


class Kind(StrEnum):
    """Memory.kind values the news adapter declares."""

    FACT = "fact"  # a reader fact (interests, region) or a generic statement
    DERIVED = "derived"  # an analysis or an inference drawn from claims
    CLAIM = "claim"  # one reported claim about a story, with its source
    SUMMARY = "summary"  # the agent's running summary of a story
    BRIEFING = "briefing"  # what the reader is told: a digest built from summaries
    SHARED = "shared"  # something the reader already passed on; a historical record


class StoryAttribute(StrEnum):
    """StructuredFact.attribute for subject story_subject(<story id>)."""

    HEADLINE = "headline"
    STATUS = "status"  # developing | confirmed | corrected | retracted
    FIGURE = "figure"  # the reported number (toll, turnout, amount)
    ATTRIBUTION = "attribution"  # who or what the reports hold responsible
    OUTCOME = "outcome"  # how the story resolved (verdict, result, decision)
    CLOSURE = "closure"  # a temporary restriction tied to the story (closure, curfew)
    SOURCE_URL = "source_url"


class ReaderAttribute(StrEnum):
    """StructuredFact.attribute for subject READER_SUBJECT."""

    INTEREST = "interest"
    REGION = "region"


def story_subject(story_id: str) -> str:
    return f"story:{story_id}"


def is_story_subject(subject: str) -> bool:
    return subject.startswith("story:")


class NewsLinkType(StrEnum):
    # Stored parent -> dependent (docs/03): the dependent goes stale when the parent changes.
    SUMMARISES = "summarises"  # claim -> a summary that repeats it
    INFERRED_FROM = "inferred_from"  # claim or summary -> an analysis reasoned from it
    BRIEFING_FROM = "briefing_from"  # summary -> a briefing built on it
    SHARED_FROM = "shared_from"  # claim or summary -> a note the reader shared from it


NEWS_LINK_TYPES: Mapping[str, LinkClass] = {
    NewsLinkType.SUMMARISES: LinkClass.DEPENDS_ON,
    NewsLinkType.INFERRED_FROM: LinkClass.DEPENDS_ON,
    NewsLinkType.BRIEFING_FROM: LinkClass.DEPENDS_ON,
    # A shared note records what the reader said on a date; a later correction to the
    # summary must not rewrite it (the news form of sent_with_resume).
    NewsLinkType.SHARED_FROM: LinkClass.SNAPSHOT_OF,
}


def news_registry() -> LinkTypeRegistry:
    """Generic link types plus the news ones."""
    return LinkTypeRegistry(NEWS_LINK_TYPES)
