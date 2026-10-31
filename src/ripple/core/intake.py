"""Intake: the write flow from a statement to a completed ripple (docs/02, flow 1 + 2).

    statement -> change detection -> write (new memory or new version) -> links -> ripple

Deterministic steps come first (structured update detection); the ChangeDetector and
Linker may be LLM-backed, but they are injected, so core never imports ripple.llm.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from ripple.core.change_detection import ChangeDetector, ChangeKind, detect_structured_update
from ripple.core.clock import Clock
from ripple.core.indexing import MemoryIndexer
from ripple.core.linking import Linker, proposals_to_links
from ripple.core.links import LinkTypeRegistry
from ripple.core.models import ChangeEvent, Memory, Sensitivity, Status, StructuredFact, TriggerKind
from ripple.core.ripple import RippleRunner
from ripple.core.store import Store
from ripple.core.writes import record_memory, update_memory

log = logging.getLogger("ripple.core.intake")


@dataclass(frozen=True)
class Statement:
    user_id: str
    domain: str
    kind: str
    content: str
    structured: StructuredFact | None = None
    source_ref: str | None = None
    created_by: str = "user"
    # Where the statement came from decides the trigger kind (docs/03): the inspector
    # is a user edit; a conversation message or an agent write is an ordinary ripple.
    origin: Literal["conversation", "inspector", "agent"] = "conversation"
    sensitivity: Sensitivity = Sensitivity.LOW
    confidence: float = 1.0


@dataclass(frozen=True)
class IntakeResult:
    memory: Memory
    change_kind: ChangeKind
    links_written: int
    # None when nothing was written (ChangeKind.UNCHANGED): no event, no ripple.
    event: ChangeEvent | None


class Intake:
    def __init__(
        self,
        store: Store,
        clock: Clock,
        registry: LinkTypeRegistry,
        linker: Linker,
        detector: ChangeDetector,
        runner: RippleRunner,
        *,
        min_link_confidence: float = 0.5,
        multi_valued_attributes: frozenset[str] = frozenset(),
        permanent_facts: frozenset[tuple[str, str]] = frozenset(),
        indexer: "MemoryIndexer | None" = None,
    ) -> None:
        self._store = store
        self._clock = clock
        self._registry = registry
        self._linker = linker
        self._detector = detector
        self._runner = runner
        self._min_link_confidence = min_link_confidence
        self._multi_valued = multi_valued_attributes
        self._permanent = permanent_facts
        self._indexer = indexer

    async def ingest(self, statement: Statement, *, trace_id: str | None = None) -> IntakeResult:
        candidates = await self._store.memories_for_user(
            statement.user_id, [Status.VALID, Status.SUSPECT, Status.PENDING_USER]
        )
        classification = detect_structured_update(
            statement.structured,
            candidates,
            multi_valued=self._multi_valued,
            permanent=self._permanent,
        )
        if classification is None:
            classification = await self._detector.classify(
                statement.content, statement.structured, candidates
            )
        log.info(
            "intake classified",
            extra={
                "kind": classification.kind.value,
                "user_id": statement.user_id,
                "trace_id": trace_id,
            },
        )
        kind = TriggerKind.USER_EDIT if statement.origin == "inspector" else TriggerKind.RIPPLE

        if classification.kind is ChangeKind.UNCHANGED:
            assert statement.structured is not None  # only the structured path says so
            existing = next(
                c
                for c in candidates
                if c.structured is not None
                and c.structured.subject == statement.structured.subject
                and c.structured.attribute == statement.structured.attribute
            )
            return IntakeResult(
                memory=existing, change_kind=ChangeKind.UNCHANGED, links_written=0, event=None
            )

        if classification.kind is ChangeKind.UPDATE:
            assert classification.updates_memory_id is not None
            memory, event = await update_memory(
                self._store,
                self._clock,
                classification.updates_memory_id,
                content=statement.content,
                structured=statement.structured,
                valid_to=classification.valid_to,
                created_by=statement.created_by,
                kind=kind,
                source_ref=statement.source_ref,
                trace_id=trace_id,
            )
            links_written = await self._link_new_version(memory, candidates)
        else:
            now = self._clock.now()
            memory = Memory(
                user_id=statement.user_id,
                domain=statement.domain,
                kind=statement.kind,
                content=statement.content,
                structured=statement.structured,
                valid_from=now,
                valid_to=classification.valid_to,
                recorded_at=now,
                confidence=statement.confidence,
                sensitivity=statement.sensitivity,
                source_ref=statement.source_ref,
                created_by=statement.created_by,
            )
            proposals = await self._linker.propose(memory, candidates)
            links = proposals_to_links(
                proposals, self._registry, now, min_confidence=self._min_link_confidence
            )
            event = await record_memory(
                self._store, self._clock, memory, links, kind=kind, trace_id=trace_id
            )
            links_written = len(links)

        if self._indexer is not None:
            await self._indexer.index(memory)
        event = await self._runner.run(event)
        return IntakeResult(
            memory=memory, change_kind=classification.kind, links_written=links_written, event=event
        )

    async def edit(
        self,
        memory_id: str,
        *,
        content: str,
        structured: StructuredFact | None = None,
        valid_to: datetime | None = None,
        created_by: str = "user",
        source_ref: str | None = None,
        trace_id: str | None = None,
    ) -> IntakeResult:
        """An inspector edit (FR-12): a user_edit version, re-linked, then rippled."""
        old = await self._store.latest_version(memory_id)
        candidates = await self._store.memories_for_user(
            old.user_id, [Status.VALID, Status.SUSPECT, Status.PENDING_USER]
        )
        memory, event = await update_memory(
            self._store,
            self._clock,
            memory_id,
            content=content,
            structured=structured if structured is not None else old.structured,
            valid_to=valid_to,
            created_by=created_by,
            kind=TriggerKind.USER_EDIT,
            source_ref=source_ref,
            trace_id=trace_id,
        )
        links_written = await self._link_new_version(memory, candidates)
        if self._indexer is not None:
            await self._indexer.index(memory)
        event = await self._runner.run(event)
        return IntakeResult(
            memory=memory, change_kind=ChangeKind.UPDATE, links_written=links_written, event=event
        )

    async def _link_new_version(self, memory: Memory, candidates: list[Memory]) -> int:
        """Links were copied by versioning; the Linker may add ones the old version lacked."""
        existing = {(e.parent_id, e.dependent_id) for e in await self._store.parents_of(memory.id)}
        existing |= {
            (e.parent_id, e.dependent_id) for e in await self._store.dependents_of(memory.id)
        }
        proposals = [
            p
            for p in await self._linker.propose(memory, candidates)
            if (p.parent_id, p.dependent_id) not in existing
        ]
        links = proposals_to_links(
            proposals, self._registry, self._clock.now(), min_confidence=self._min_link_confidence
        )
        if links:
            async with self._store.transaction() as tx:
                for link in links:
                    await tx.add_link(link)
        return len(links)
