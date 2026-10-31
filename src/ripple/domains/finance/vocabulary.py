"""Finance-domain vocabulary (ADR-0100): kinds, attributes and link types.

The finance track holds a user's own investment theses and the assumptions under them
("margins stay above 20%", "the policy rate stays below 6%"). When an assumption
breaks, the thesis and everything built on it (an estimate, an alert) must be
re-examined; a journal entry that recorded a past decision is a snapshot and stays as
written. This is an unseen-domain test of the link finder (H4), not advice: the bench
data uses fictional companies only.

Core interprets none of these strings; the write flow maps each link type to a core
class through `finance_registry()`.
"""

from collections.abc import Mapping
from enum import StrEnum

from ripple.core.links import LinkTypeRegistry
from ripple.core.models import LinkClass

DOMAIN = "finance"
MACRO_SUBJECT = "macro"


class Kind(StrEnum):
    """Memory.kind values the finance adapter declares."""

    FACT = "fact"  # a reported company or macro fact
    DERIVED = "derived"  # an estimate or inference drawn from facts
    ASSUMPTION = "assumption"  # a premise the user's thesis relies on
    THESIS = "thesis"  # the user's own thesis about a company
    ALERT = "alert"  # a user-set reminder to look again under a condition
    JOURNAL = "journal"  # a dated record of a past decision; a historical record


class CompanyAttribute(StrEnum):
    """StructuredFact.attribute for subject company_subject(<ticker>)."""

    GUIDANCE = "guidance"  # the company's own revenue growth guidance, percent
    MARGIN = "margin"  # operating margin, percent
    LEADERSHIP = "leadership"  # who runs it
    TRADING_STATUS = "trading_status"  # trading | halted
    REGULATORY_STATUS = "regulatory_status"


class MacroAttribute(StrEnum):
    """StructuredFact.attribute for subject MACRO_SUBJECT."""

    POLICY_RATE = "policy_rate"  # percent
    INFLATION = "inflation"  # percent


def company_subject(ticker: str) -> str:
    return f"company:{ticker}"


def is_company_subject(subject: str) -> bool:
    return subject.startswith("company:")


class FinanceLinkType(StrEnum):
    # Stored parent -> dependent (docs/03): the dependent goes stale when the parent changes.
    PREMISE_OF = "premise_of"  # assumption or fact -> a thesis resting on it
    ESTIMATE_FROM = "estimate_from"  # fact -> an estimate computed from it
    ALERT_FOR = "alert_for"  # thesis or fact -> an alert watching it
    JOURNALED_WITH = "journaled_with"  # thesis -> a journal entry recording it as it was


FINANCE_LINK_TYPES: Mapping[str, LinkClass] = {
    FinanceLinkType.PREMISE_OF: LinkClass.DEPENDS_ON,
    FinanceLinkType.ESTIMATE_FROM: LinkClass.DEPENDS_ON,
    FinanceLinkType.ALERT_FOR: LinkClass.DEPENDS_ON,
    # A journal entry records why a decision was made on a date; a new thesis version
    # must not rewrite that record (the finance form of sent_with_resume).
    FinanceLinkType.JOURNALED_WITH: LinkClass.SNAPSHOT_OF,
}


def finance_registry() -> LinkTypeRegistry:
    """Generic link types plus the finance ones."""
    return LinkTypeRegistry(FINANCE_LINK_TYPES)
