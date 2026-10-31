"""Finance adapter vocabulary (ADR-0100): link types map onto the two core classes."""

import ast
import asyncio
import sys
from pathlib import Path

import pytest

import ripple.domains.finance
from ripple.core.links import (
    GENERIC_LINK_TYPES,
    LinkTypeRegistry,
    UnknownLinkTypeError,
    policy_for,
)
from ripple.core.models import LinkClass, Status, TriggerKind
from ripple.core.writes import update_memory
from ripple.domains.finance.vocabulary import (
    DOMAIN,
    FINANCE_LINK_TYPES,
    MACRO_SUBJECT,
    CompanyAttribute,
    FinanceLinkType,
    company_subject,
    finance_registry,
    is_company_subject,
)
from ripple.domains.jobs.vocabulary import JOBS_LINK_TYPES
from ripple.domains.news.vocabulary import NEWS_LINK_TYPES
from tests.builders import derived, fact, link
from tests.fakes.clock import FakeClock
from tests.fakes.store import InMemoryStore


def test_registry_knows_the_generic_and_every_finance_type():
    registry = finance_registry()
    assert registry.known_types() == set(GENERIC_LINK_TYPES) | set(FinanceLinkType)
    for link_type, link_class in FINANCE_LINK_TYPES.items():
        assert registry.class_of(link_type) is link_class


def test_only_journaled_with_is_a_snapshot_and_it_never_propagates():
    snapshots = {t for t, c in FINANCE_LINK_TYPES.items() if c is LinkClass.SNAPSHOT_OF}
    assert snapshots == {FinanceLinkType.JOURNALED_WITH}
    policy = policy_for(finance_registry().class_of(FinanceLinkType.JOURNALED_WITH))
    assert not policy.propagates and not policy.copied_on_update


@pytest.mark.parametrize("foreign", ["eligibility_of", "sent_with_resume", "summarises"])
def test_another_domains_link_type_is_refused(foreign):
    with pytest.raises(UnknownLinkTypeError):
        finance_registry().class_of(foreign)


def test_finance_types_combine_with_jobs_and_news_without_a_conflicting_mapping():
    combined = LinkTypeRegistry(JOBS_LINK_TYPES)
    for mapping in (NEWS_LINK_TYPES, FINANCE_LINK_TYPES):
        for link_type, link_class in mapping.items():
            combined.register(link_type, link_class)
    assert set(FinanceLinkType) <= combined.known_types()


def test_company_subject_round_trip():
    assert company_subject("ZNTH") == "company:ZNTH"
    assert is_company_subject(company_subject("ZNTH")) and not is_company_subject(MACRO_SUBJECT)


def test_a_thesis_update_carries_alerts_to_the_new_version_but_not_journal_entries():
    # docs/03 copy rule applied to the finance types: depends_on links move to the new
    # version, the snapshot_of link stays on the version the journal recorded.
    store, clock, registry = InMemoryStore(), FakeClock(), finance_registry()
    margin = fact(company_subject("ZNTH"), CompanyAttribute.MARGIN, 22, domain=DOMAIN)
    thesis = derived("ZNTH compounds while margins hold above 20%", kind="thesis", domain=DOMAIN)
    alert = derived("look again if ZNTH margin drops below 20%", kind="alert", domain=DOMAIN)
    journal = derived("2026-10-01: added ZNTH on the margin thesis", kind="journal", domain=DOMAIN)

    def typed(parent, dependent, link_type):
        return link(parent, dependent, link_type=link_type, link_class=registry.class_of(link_type))

    links = [
        typed(margin, thesis, FinanceLinkType.PREMISE_OF),
        typed(thesis, alert, FinanceLinkType.ALERT_FOR),
        typed(thesis, journal, FinanceLinkType.JOURNALED_WITH),
    ]

    async def scenario():
        async with store.transaction() as tx:
            for memory in (margin, thesis, alert, journal):
                await tx.add_memory(memory)
            for item in links:
                await tx.add_link(item)
        new, _ = await update_memory(
            store,
            clock,
            thesis.id,
            content="ZNTH thesis on hold: margins fell to 17%",
            structured=None,
            valid_to=None,
            created_by="curator",
            kind=TriggerKind.RIPPLE,
        )
        return (
            new,
            await store.dependents_of(new.id),
            await store.parents_of(new.id),
            await store.get_memory(thesis.id),
        )

    new, dependents, parents, old = asyncio.run(scenario())
    assert {(d.dependent_id, d.link_type) for d in dependents} == {
        (alert.id, FinanceLinkType.ALERT_FOR)
    }
    assert {(p.parent_id, p.link_type) for p in parents} == {
        (margin.id, FinanceLinkType.PREMISE_OF)
    }
    assert old.status is Status.RETIRED and new.version == 2


def test_the_adapter_imports_only_the_standard_library_and_core():
    package = Path(ripple.domains.finance.__file__).parent
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
