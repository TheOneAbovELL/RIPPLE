"""News adapter vocabulary (ADR-0100): link types map onto the two core classes."""

import ast
import asyncio
import sys
from pathlib import Path

import pytest

import ripple.domains.news
from ripple.core.links import (
    GENERIC_LINK_TYPES,
    LinkTypeRegistry,
    UnknownLinkTypeError,
    policy_for,
)
from ripple.core.models import LinkClass, Status, TriggerKind
from ripple.core.writes import update_memory
from ripple.domains.jobs.vocabulary import JOBS_LINK_TYPES
from ripple.domains.news.vocabulary import (
    DOMAIN,
    NEWS_LINK_TYPES,
    NewsLinkType,
    StoryAttribute,
    is_story_subject,
    news_registry,
    story_subject,
)
from tests.builders import derived, fact, link
from tests.fakes.clock import FakeClock
from tests.fakes.store import InMemoryStore


def test_registry_knows_the_generic_and_every_news_type():
    registry = news_registry()
    assert registry.known_types() == set(GENERIC_LINK_TYPES) | set(NewsLinkType)
    for link_type, link_class in NEWS_LINK_TYPES.items():
        assert registry.class_of(link_type) is link_class


def test_only_shared_from_is_a_snapshot_and_it_never_propagates():
    snapshots = {t for t, c in NEWS_LINK_TYPES.items() if c is LinkClass.SNAPSHOT_OF}
    assert snapshots == {NewsLinkType.SHARED_FROM}
    policy = policy_for(news_registry().class_of(NewsLinkType.SHARED_FROM))
    assert not policy.propagates and not policy.copied_on_update


@pytest.mark.parametrize("foreign", ["eligibility_of", "sent_with_resume", "premise_of"])
def test_another_domains_link_type_is_refused(foreign):
    with pytest.raises(UnknownLinkTypeError):
        news_registry().class_of(foreign)


def test_news_and_jobs_types_combine_without_a_conflicting_mapping():
    combined = LinkTypeRegistry(JOBS_LINK_TYPES)
    for link_type, link_class in NEWS_LINK_TYPES.items():
        combined.register(link_type, link_class)
    assert set(NewsLinkType) <= combined.known_types()


def test_story_subject_round_trip():
    assert story_subject("bridge") == "story:bridge"
    assert is_story_subject(story_subject("bridge")) and not is_story_subject("reader")


def test_a_correction_carries_summaries_to_the_new_claim_but_not_shared_notes():
    # docs/03 copy rule applied to the news types: depends_on links move to the new
    # version, the snapshot_of link stays on the version that was shared.
    store, clock, registry = InMemoryStore(), FakeClock(), news_registry()
    subject = story_subject("bridge")
    claim = fact(subject, StoryAttribute.FIGURE, 12, content="toll is 12", domain=DOMAIN)
    summary = derived("12 died in the bridge collapse", kind="summary", domain=DOMAIN)
    shared = derived("told the group: 12 died", kind="shared", domain=DOMAIN)
    links = [
        link(
            claim,
            summary,
            link_type=NewsLinkType.SUMMARISES,
            link_class=registry.class_of(NewsLinkType.SUMMARISES),
        ),
        link(
            summary,
            shared,
            link_type=NewsLinkType.SHARED_FROM,
            link_class=registry.class_of(NewsLinkType.SHARED_FROM),
        ),
        link(
            claim,
            shared,
            link_type=NewsLinkType.SHARED_FROM,
            link_class=registry.class_of(NewsLinkType.SHARED_FROM),
        ),
    ]

    async def scenario():
        async with store.transaction() as tx:
            for memory in (claim, summary, shared):
                await tx.add_memory(memory)
            for item in links:
                await tx.add_link(item)
        new, _ = await update_memory(
            store,
            clock,
            claim.id,
            content="toll is 9",
            structured=None,
            valid_to=None,
            created_by="user",
            kind=TriggerKind.USER_EDIT,
        )
        return new, await store.dependents_of(new.id), await store.get_memory(claim.id)

    new, dependents, old = asyncio.run(scenario())
    assert {(d.dependent_id, d.link_type) for d in dependents} == {
        (summary.id, NewsLinkType.SUMMARISES)
    }
    assert old.status is Status.RETIRED and new.version == 2


def test_the_adapter_imports_only_the_standard_library_and_core():
    package = Path(ripple.domains.news.__file__).parent
    for path in package.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            elif isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            else:
                continue
            for name in names:
                top = name.split(".", 1)[0]
                allowed = name.startswith("ripple.core") or top in sys.stdlib_module_names
                assert allowed, f"{path.name} imports {name}"
