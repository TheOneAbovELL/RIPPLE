"""Dedupe against what the user already holds and what the Scout already saw (ADR-0071).

Two questions before a candidate costs a model call or a memory write: is this URL
already an opening of this user (any status: a closed opening re-found at its URL is
still the same opening), and is this (company, title) a live opening already held?
The store answers for everything recorded; the ledger remembers what the Scout looked
at and chose not to record (a filtered JD under the current criteria, a forgotten
opening) so it is not re-parsed every night. The ledger is in memory for now; the
Postgres table is the follow-up with migration id 0007 reserved
(docs/plans/parallel-execution/ws-9.md).
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from ripple.core.models import Memory, Status
from ripple.core.store import Store
from ripple.domains.jobs.schemas import opening_key
from ripple.domains.jobs.sources.canonical import canonical_url, fingerprint
from ripple.domains.jobs.vocabulary import Kind, OpeningAttribute

SOURCE_REF_PREFIX = "scout"


def scout_source_ref(source_id: str, canonical: str) -> str:
    """`scout:<source id>:<canonical url>`: the anchor's source_ref (ADR-0071)."""
    return f"{SOURCE_REF_PREFIX}:{source_id}:{canonical}"


def canonical_of_source_ref(source_ref: str | None) -> str | None:
    """The canonical URL inside a Scout source_ref, or None for any other provenance."""
    if source_ref is None:
        return None
    prefix, _, rest = source_ref.partition(":")
    if prefix != SOURCE_REF_PREFIX:
        return None
    _, _, canonical = rest.partition(":")
    return canonical or None


def url_key(canonical: str) -> str:
    return f"url:{canonical}"


def fingerprint_key(print_: str) -> str:
    return f"fp:{print_}"


class ScoutLedger(Protocol):
    """What the Scout has already looked at for a user, keyed by a short string."""

    async def seen(self, user_id: str, key: str) -> bool: ...

    async def mark(self, user_id: str, key: str, at: datetime) -> None: ...


class InMemoryScoutLedger:
    def __init__(self) -> None:
        self.entries: dict[tuple[str, str], datetime] = {}

    async def seen(self, user_id: str, key: str) -> bool:
        return (user_id, key) in self.entries

    async def mark(self, user_id: str, key: str, at: datetime) -> None:
        self.entries[(user_id, key)] = at


@dataclass
class HeldOpenings:
    """What the user's memory already holds, read once per run and extended as the
    run records, so a candidate check never rescans the store."""

    urls: set[str] = field(default_factory=set)
    fingerprints: set[str] = field(default_factory=set)


class OpeningDeduplicator:
    def __init__(self, store: Store, ledger: ScoutLedger) -> None:
        self._store = store
        self._ledger = ledger

    async def held(self, user_id: str) -> HeldOpenings:
        memories = await self._store.memories_for_user(user_id)
        return HeldOpenings(urls=_held_urls(memories), fingerprints=_held_fingerprints(memories))

    async def known_url(
        self, user_id: str, canonical: str, held: HeldOpenings | None = None
    ) -> bool:
        if await self._ledger.seen(user_id, url_key(canonical)):
            return True
        held = held if held is not None else await self.held(user_id)
        return canonical in held.urls

    async def known_fingerprint(
        self, user_id: str, company: str, title: str, held: HeldOpenings | None = None
    ) -> bool:
        print_ = fingerprint(company, title)
        if await self._ledger.seen(user_id, fingerprint_key(print_)):
            return True
        held = held if held is not None else await self.held(user_id)
        return print_ in held.fingerprints

    async def remember(
        self,
        user_id: str,
        canonical: str,
        at: datetime,
        *,
        company: str | None = None,
        title: str | None = None,
        held: HeldOpenings | None = None,
    ) -> None:
        await self._ledger.mark(user_id, url_key(canonical), at)
        if held is not None:
            held.urls.add(canonical)
        if company and title:
            print_ = fingerprint(company, title)
            await self._ledger.mark(user_id, fingerprint_key(print_), at)
            if held is not None:
                held.fingerprints.add(print_)


def _held_urls(memories: list[Memory]) -> set[str]:
    """Canonical URLs of every opening the user holds, from Scout refs and source_url fields."""
    urls: set[str] = set()
    for memory in memories:
        if memory.kind == Kind.OPENING:
            canonical = canonical_of_source_ref(memory.source_ref)
            if canonical:
                urls.add(canonical)
        elif (
            memory.structured is not None
            and memory.structured.attribute == OpeningAttribute.SOURCE_URL
            and isinstance(memory.structured.value, str)
        ):
            try:
                urls.add(canonical_url(memory.structured.value))
            except ValueError:
                continue  # a JD quoted something that is not a URL; nothing to match
    return urls


def _held_fingerprints(memories: list[Memory]) -> set[str]:
    """(company, title) of every live opening. RETIRED anchors are left out on purpose:
    a closed role reposted next season under a new URL is a new opening (ADR-0071)."""
    anchors = [m for m in memories if m.kind == Kind.OPENING and m.status is not Status.RETIRED]
    titles: dict[str, str] = {}
    companies: dict[str, str] = {}
    for memory in memories:
        if memory.structured is None or memory.kind != Kind.FACT:
            continue
        if memory.structured.attribute == OpeningAttribute.TITLE:
            titles[memory.structured.subject] = str(memory.structured.value)
        elif memory.structured.attribute == OpeningAttribute.COMPANY:
            companies[memory.structured.subject] = str(memory.structured.value)
    prints: set[str] = set()
    for anchor in anchors:
        subject = opening_key(anchor)
        if subject in titles and subject in companies:
            prints.add(fingerprint(companies[subject], titles[subject]))
    return prints
