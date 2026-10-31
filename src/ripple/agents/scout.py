"""The Scout: fetch allowed sources, parse, dedupe, record openings (FR-8, ADR-0072).

    criteria memory -> registry sources -> fetch (I6) -> extract candidates
        -> dedupe by URL (before any model call) -> parse_jd (WS-2)
        -> dedupe by (company, title) -> criteria filter
        -> record_opening + derive_for_opening (WS-1) -> ScoutReport

No LangGraph here: the loop has no branching a model decides, so a plain class is the
honest shape (the Conversation and Tailor agents need the graph; this one does not).
The only model call is the JD parser, and every field it returns carries a span into
the page's own text (I5). Nothing is submitted anywhere (I6): the fetcher only GETs
registered hosts, and the agent writes only to the user's memory. Pages and parses are
shared across the users of one run through `ScoutRunCache`, so a listing is fetched and
a JD parsed once a night, not once per user.
"""

import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Protocol

from ripple.agents.capabilities import Capability
from ripple.core.clock import Clock
from ripple.core.errors import (
    ConfigurationError,
    InvalidObjectError,
    LLMUnavailableError,
    RippleError,
)
from ripple.core.models import ChangeEvent, DecisionAction, Memory, Status
from ripple.core.ripple import RippleRunner
from ripple.core.store import Store
from ripple.domains.jobs.derive import derive_for_opening
from ripple.domains.jobs.openings import OpeningAlreadyRecordedError, record_opening
from ripple.domains.jobs.parsers import parse_jd
from ripple.domains.jobs.sources.cache import FetchCache
from ripple.domains.jobs.sources.canonical import canonical_url, short_digest
from ripple.domains.jobs.sources.dedupe import (
    HeldOpenings,
    InMemoryScoutLedger,
    OpeningDeduplicator,
    ScoutLedger,
    scout_source_ref,
)
from ripple.domains.jobs.sources.extract import Candidate, extract_candidates, page_text
from ripple.domains.jobs.sources.fetcher import FetchRefusedError, FetchResult, SourceFetcher
from ripple.domains.jobs.sources.ratelimit import Sleeper
from ripple.domains.jobs.sources.registry import SourceRegistry, SourceSpec
from ripple.domains.jobs.sources.report import (
    SCOUT_LEASE_TTL,
    ScoutError,
    ScoutReport,
    ScoutRunReport,
    SourceCount,
    scout_lease_key,
)
from ripple.domains.jobs.sources.wiring import DEFAULT_TIMEOUT_SECONDS, open_fetcher
from ripple.domains.jobs.vocabulary import Kind, OpeningAttribute, ParsedOpening
from ripple.llm.router import Router

log = logging.getLogger("ripple.agents.scout")

DEFAULT_MAX_CANDIDATES_PER_SOURCE = 25  # bounds model calls per source per run
DEFAULT_MAX_TEXT_CHARS = 20_000  # a JD longer than this is cut before the parser

__all__ = [
    "SCOUT_LEASE_TTL",
    "EnqueueingScoutTrigger",
    "ImmediateScoutTrigger",
    "ScoutAgent",
    "ScoutCriteria",
    "ScoutError",
    "ScoutReport",
    "ScoutRunCache",
    "ScoutRunReport",
    "ScoutTrigger",
    "SourceCount",
    "criteria_for",
    "event_changed_criteria",
    "open_scout",
    "process_ledger",
    "scout_lease_key",
]


# ---- criteria --------------------------------------------------------------------


@dataclass(frozen=True)
class ScoutCriteria:
    """The filter read from the user's criteria memory (ADR-0031 writes its content as
    "search openings with cgpa_cutoff <= 8.1; batch 2027; skills python, ros").

    Only the cutoff and the batch filter; skills are a graded fit (ADR-0031), not a
    gate, so they are neither parsed nor part of the fingerprint: a new skill must not
    re-judge every filtered JD.
    """

    cgpa: float | None = None
    batch: int | None = None

    @classmethod
    def from_content(cls, content: str) -> "ScoutCriteria":
        cgpa: float | None = None
        batch: int | None = None
        _, _, clauses = content.partition("search openings with ")
        for clause in clauses.split(";"):
            words = clause.strip().split()
            try:
                if len(words) == 3 and words[0] == "cgpa_cutoff" and words[1] == "<=":
                    cgpa = float(words[2])
                elif len(words) == 2 and words[0] == "batch":
                    batch = int(words[1])
            except ValueError:
                log.warning("criteria clause not understood", extra={"clause": clause.strip()})
        return cls(cgpa=cgpa, batch=batch)

    @property
    def fingerprint(self) -> str:
        """Identifies this filter, so a JD filtered out under it is re-judged when it
        changes (a CGPA rise must let an opening back in)."""
        return short_digest(f"cgpa_cutoff <= {self.cgpa}; batch {self.batch}")

    def admits(self, parsed: ParsedOpening) -> bool:
        """False when the JD states a cutoff above the CGPA or batches that exclude the
        student's. A JD that states neither passes: eligibility is decided later from
        the facts (ADR-0031); the filter only saves writing openings the student cannot
        apply to."""
        cutoff = parsed.get(OpeningAttribute.CGPA_CUTOFF)
        if cutoff is not None and self.cgpa is not None and float(cutoff.value) > self.cgpa:
            return False
        batches = parsed.all(OpeningAttribute.BATCH)
        if batches and self.batch is not None:
            return any(int(b.value) == self.batch for b in batches)
        return True


async def criteria_for(store: Store, user_id: str) -> ScoutCriteria | None:
    """The user's latest VALID criteria memory as a filter; None without one.

    A SUSPECT or PENDING_USER criteria is in doubt and is not used to filter (I1 in
    spirit: the Scout does not act on a belief the ripple has questioned)."""
    memories = await store.memories_for_user(user_id, [Status.VALID])
    criteria = [m for m in memories if m.kind == Kind.CRITERIA]  # oldest first
    if not criteria:
        return None
    return ScoutCriteria.from_content(criteria[-1].content)


# ---- per-run state -----------------------------------------------------------------


@dataclass
class ScoutRunCache:
    """Pages and parses shared by every user of one run (ADR-0072, point 4).

    A listing is the same for everyone and a parse is user-independent; without this
    the site sees one fetch per user and the model one call per user per JD.
    """

    pages: dict[str, FetchResult] = field(default_factory=dict)
    parsed: dict[str, ParsedOpening] = field(default_factory=dict)  # by source_ref


@dataclass
class _UserRun:
    """Everything one `run_for_user` call carries through its sources and candidates."""

    user_id: str
    criteria: ScoutCriteria | None
    report: ScoutReport
    held: HeldOpenings
    cache: ScoutRunCache
    trace_id: str | None


def _is_fatal(exc: RippleError) -> bool:
    """A failure that would repeat for every candidate and user: stop the run instead
    of paying for it twenty-five times per source (review S6)."""
    return isinstance(exc, LLMUnavailableError | ConfigurationError)


# ---- the agent -------------------------------------------------------------------


class ScoutAgent:
    def __init__(
        self,
        *,
        store: Store,
        clock: Clock,
        runner: RippleRunner,
        router: Router,
        registry: SourceRegistry,
        fetcher: SourceFetcher,
        ledger: ScoutLedger | None = None,
        max_candidates_per_source: int = DEFAULT_MAX_CANDIDATES_PER_SOURCE,
        max_text_chars: int = DEFAULT_MAX_TEXT_CHARS,
    ) -> None:
        self._store = store
        self._clock = clock
        self._runner = runner
        self._router = router
        self._registry = registry
        self._fetcher = fetcher
        self._ledger: ScoutLedger = ledger if ledger is not None else InMemoryScoutLedger()
        self._dedupe = OpeningDeduplicator(store, self._ledger)
        self._max_candidates = max_candidates_per_source
        self._max_text_chars = max_text_chars

    @property
    def capabilities(self) -> frozenset[Capability]:
        """What the Scout's loop reaches (I6); checked against the closed enum in tests."""
        return frozenset(
            {
                Capability.SOURCES_READ,
                Capability.LLM_COMPLETE,
                Capability.MEMORY_READ,
                Capability.MEMORY_WRITE_OPENING,
                Capability.MEMORY_WRITE_DERIVED,
            }
        )

    async def run_for_user(
        self,
        user_id: str,
        *,
        cache: ScoutRunCache | None = None,
        trace_id: str | None = None,
    ) -> ScoutReport:
        """Scout every fetchable source for one user.

        A source's or a candidate's own failure is counted and the run goes on. What
        propagates: a failure outside any source (the store, the criteria read) and a
        fatal one (provider unavailable, configuration), so the job isolates the user
        and the operator sees it. Pass the same `cache` for every user of one run.
        """
        report = ScoutReport(user_id=user_id, started_at=self._clock.now())
        criteria = await criteria_for(self._store, user_id)
        if criteria is None:
            log.info("scout: no criteria memory; no filter applied", extra={"user_id": user_id})
        else:
            report.criteria_content = f"cgpa_cutoff <= {criteria.cgpa}; batch {criteria.batch}"
        run = _UserRun(
            user_id=user_id,
            criteria=criteria,
            report=report,
            held=await self._dedupe.held(user_id),
            cache=cache if cache is not None else ScoutRunCache(),
            trace_id=trace_id,
        )
        for source in self._registry.fetchable():
            count = report.per_source.setdefault(source.id, SourceCount())
            try:
                await self._scout_source(run, source, count)
            except RippleError as exc:
                if _is_fatal(exc):
                    raise
                count.errors += 1
                report.errors.append(ScoutError(source.id, source.url, str(exc)))
                log.warning(
                    "scout: source failed",
                    extra={"user_id": user_id, "source_id": source.id, "error": str(exc)},
                )
        report.finished_at = self._clock.now()
        log.info(
            "scout: run done",
            extra={
                "user_id": user_id,
                "candidates": report.candidates,
                "new": report.new,
                "duplicates": report.duplicates,
                "filtered": report.filtered,
                "refused": report.refused,
                "errors": len(report.errors),
                "trace_id": trace_id,
            },
        )
        return report

    async def _fetch(self, run: _UserRun, source: SourceSpec, url: str | None) -> FetchResult:
        key = f"{source.id}:{url if url is not None else source.url}"
        page = run.cache.pages.get(key)
        if page is None:
            page = await self._fetcher.fetch(source, url)
            run.cache.pages[key] = page
        return page

    async def _scout_source(self, run: _UserRun, source: SourceSpec, count: SourceCount) -> None:
        listing = await self._fetch(run, source, None)
        try:
            candidates = extract_candidates(
                listing.text, listing.content_type, listing.url, source.parser
            )
        except ValueError as exc:  # invalid JSON from an API: the source's fault, not ours
            raise InvalidObjectError(f"source {source.id!r}: {exc}") from exc
        if len(candidates) > self._max_candidates:
            log.info(
                "scout: candidate cap applied",
                extra={"source_id": source.id, "seen": len(candidates)},
            )
        for candidate in candidates[: self._max_candidates]:
            count.candidates += 1
            url = _candidate_url(candidate, listing)
            try:
                await self._handle_candidate(run, source, candidate, url, count)
            except OpeningAlreadyRecordedError:
                count.duplicates += 1
                await self._dedupe.remember(run.user_id, url, self._clock.now(), held=run.held)
            except FetchRefusedError as exc:
                # Policy, not failure: off-host, robots or a login (ADR-0008). Marked so
                # the next run does not send the request again.
                count.refused += 1
                await self._ledger.mark(run.user_id, _refused_key(url), self._clock.now())
                log.info(
                    "scout: candidate refused",
                    extra={"user_id": run.user_id, "source_id": source.id, "reason": exc.reason},
                )
            except RippleError as exc:
                if _is_fatal(exc):
                    raise
                count.errors += 1
                run.report.errors.append(ScoutError(source.id, url, str(exc)))
                log.warning(
                    "scout: candidate failed",
                    extra={"user_id": run.user_id, "source_id": source.id, "error": str(exc)},
                )

    async def _handle_candidate(
        self,
        run: _UserRun,
        source: SourceSpec,
        candidate: Candidate,
        url: str,
        count: SourceCount,
    ) -> None:
        user_id, now = run.user_id, self._clock.now()
        # Cheapest checks first: a known URL costs no fetch and no model call (ADR-0071).
        if await self._dedupe.known_url(user_id, url, run.held):
            count.duplicates += 1
            return
        if await self._ledger.seen(user_id, _not_a_jd_key(url)):
            count.filtered += 1
            return
        if await self._ledger.seen(user_id, _refused_key(url)):
            count.refused += 1
            return
        filtered_key = _filtered_key(url, run.criteria)
        if filtered_key is not None and await self._ledger.seen(user_id, filtered_key):
            count.filtered += 1
            return
        parsed = await self._parse(run, source, candidate, url)
        title = parsed.get(OpeningAttribute.TITLE)
        company = parsed.get(OpeningAttribute.COMPANY)
        if title is None:
            # Not a JD (a navigation block, an empty card): nothing worth a memory.
            count.filtered += 1
            await self._ledger.mark(user_id, _not_a_jd_key(url), now)
            return
        if company is not None and await self._dedupe.known_fingerprint(
            user_id, str(company.value), str(title.value), run.held
        ):
            count.duplicates += 1
            await self._dedupe.remember(user_id, url, now, held=run.held)
            return
        if run.criteria is not None and not run.criteria.admits(parsed):
            count.filtered += 1
            if filtered_key is not None:
                await self._ledger.mark(user_id, filtered_key, now)
            return
        recorded = await record_opening(
            self._store, self._clock, user_id, parsed, self._runner, trace_id=run.trace_id
        )
        # Bookkeeping right after the commit: a derivation failure below must not turn a
        # recorded opening into a "duplicate" that never gets its beliefs (review S4).
        await self._dedupe.remember(
            user_id,
            url,
            now,
            company=str(company.value) if company is not None else None,
            title=str(title.value),
            held=run.held,
        )
        run.report.recorded_anchor_ids.append(recorded.anchor.id)
        count.new += 1
        try:
            await derive_for_opening(
                self._store, self._clock, self._runner, recorded.anchor.id, trace_id=run.trace_id
            )
        except RippleError as exc:
            if _is_fatal(exc):
                raise
            count.errors += 1
            run.report.errors.append(
                ScoutError(source.id, url, f"recorded without derived beliefs: {exc}")
            )
            log.warning(
                "scout: derivation failed after recording",
                extra={"user_id": user_id, "memory_id": recorded.anchor.id, "error": str(exc)},
            )

    async def _parse(
        self, run: _UserRun, source: SourceSpec, candidate: Candidate, url: str
    ) -> ParsedOpening:
        source_ref = scout_source_ref(source.id, url)
        parsed = run.cache.parsed.get(source_ref)
        if parsed is not None:
            return parsed
        text = candidate.text
        if source.parser.follow_links and candidate.url is not None:
            detail = await self._fetch(run, source, candidate.url)
            text = page_text(detail.text, source.parser.detail_selector)
        text = text[: self._max_text_chars]
        parsed = await parse_jd(self._router, text, source_ref, trace_id=run.trace_id)
        run.cache.parsed[source_ref] = parsed
        return parsed


def _candidate_url(candidate: Candidate, listing: FetchResult) -> str:
    """The canonical URL that identifies the candidate; a candidate without one (an API
    item with no link) is identified by the listing URL plus a digest of its text."""
    if candidate.url is not None:
        try:
            return canonical_url(candidate.url)
        except ValueError:
            pass  # a mailto: or javascript: href; fall back to the listing
    return f"{listing.url}#item-{short_digest(candidate.text)}"


def _filtered_key(url: str, criteria: ScoutCriteria | None) -> str | None:
    return None if criteria is None else f"filtered:{criteria.fingerprint}:{url}"


def _not_a_jd_key(url: str) -> str:
    return f"not_jd:{url}"


def _refused_key(url: str) -> str:
    return f"refused:{url}"


# ---- triggers (FR-8: on criteria change) --------------------------------------------


class ScoutTrigger(Protocol):
    """Hooked where a criteria memory changes (docs/learning/scout.md, section 3)."""

    async def on_criteria_changed(self, user_id: str) -> None: ...


class ImmediateScoutTrigger:
    """Runs the Scout in the caller's process; development and tests."""

    def __init__(self, agent: ScoutAgent) -> None:
        self._agent = agent
        self.reports: list[ScoutReport] = []

    async def on_criteria_changed(self, user_id: str) -> None:
        self.reports.append(await self._agent.run_for_user(user_id))


class EnqueueingScoutTrigger:
    """Hands the user id to a queue; a worker job runs the Scout for that user.

    The production shape: a criteria change must not make an API request wait on
    fetches. The job itself (`scout_user_job`, one lease, one `run_for_user`) is
    registered by the worker (docs/plans/parallel-execution/ws-9.md, coordinator action 2).
    """

    def __init__(self, enqueue: Callable[[str], Awaitable[None]]) -> None:
        self._enqueue = enqueue

    async def on_criteria_changed(self, user_id: str) -> None:
        await self._enqueue(user_id)


async def event_changed_criteria(store: Store, event: ChangeEvent) -> bool:
    """True when a completed ChangeEvent created, updated or restored a criteria memory.

    The trigger of a criteria derivation is the criteria memory itself; a profile
    change reaches criteria through an UPDATE decision on it (ADR-0031, CriteriaRule).
    """
    trigger = await store.get_memory(event.trigger_memory_id)
    if trigger.kind == Kind.CRITERIA:
        return True
    for decision in event.decisions:
        if decision.action not in (DecisionAction.UPDATE, DecisionAction.RETIRE):
            continue
        memory: Memory = await store.get_memory(decision.memory_id)
        if memory.kind == Kind.CRITERIA:
            return True
    return False


class CriteriaChangeObserver:
    """A RippleRunner EventObserver: scout again when an event changed the criteria.

    FR-8's second trigger. Registered on the runners that write profile changes (the
    API's and the worker's); production pairs it with EnqueueingScoutTrigger so the
    write that changed the criteria never waits on fetches (ADR-0079).
    """

    def __init__(self, store: Store, trigger: ScoutTrigger) -> None:
        self._store = store
        self._trigger = trigger

    async def event_completed(self, event: ChangeEvent) -> None:
        if await event_changed_criteria(self._store, event):
            await self._trigger.on_criteria_changed(event.user_id)


# ---- wiring ------------------------------------------------------------------------

_process_ledger = InMemoryScoutLedger()


def process_ledger() -> InMemoryScoutLedger:
    """One ledger per worker process until the Postgres table (migration 0007) exists.

    The store check in OpeningDeduplicator covers restarts for everything recorded;
    only the filtered, not-a-JD and refused marks are lost with the process.
    """
    return _process_ledger


@asynccontextmanager
async def open_scout(
    *,
    store: Store,
    clock: Clock,
    runner: RippleRunner,
    router: Router,
    registry: SourceRegistry,
    ledger: ScoutLedger | None = None,
    cache: FetchCache | None = None,
    sleeper: Sleeper | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> AsyncIterator[ScoutAgent]:
    """A ScoutAgent over a real HTTP client that is closed when the block ends."""
    async with open_fetcher(
        clock,
        user_agent=registry.user_agent,
        cache=cache,
        sleeper=sleeper,
        timeout_seconds=timeout_seconds,
    ) as fetcher:
        yield ScoutAgent(
            store=store,
            clock=clock,
            runner=runner,
            router=router,
            registry=registry,
            fetcher=fetcher,
            ledger=ledger if ledger is not None else process_ledger(),
        )
