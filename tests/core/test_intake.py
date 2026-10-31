"""Intake end to end with scripted linker, detector and engine."""

import asyncio
from collections.abc import Sequence
from datetime import timedelta

from ripple.core.change_detection import ChangeClassification, ChangeKind
from ripple.core.intake import Intake, Statement
from ripple.core.linking import LinkProposal
from ripple.core.links import LinkTypeRegistry
from ripple.core.models import LinkCreator, Memory, Status, StructuredFact, TriggerKind
from ripple.core.ripple import RippleRunner
from tests.builders import USER, derived, fact, link
from tests.fakes.clock import DEFAULT_START, FakeClock
from tests.fakes.engine import ScriptedEngine
from tests.fakes.resolver import ScriptedResolver, update
from tests.fakes.store import InMemoryStore


class ScriptedLinker:
    def __init__(self, *proposals: LinkProposal) -> None:
        self._proposals = list(proposals)
        self.seen: list[Memory] = []

    async def propose(self, memory: Memory, candidates: Sequence[Memory]) -> list[LinkProposal]:
        self.seen.append(memory)
        return [
            LinkProposal(
                parent_id=p.parent_id if p.parent_id != "NEW" else memory.id,
                dependent_id=p.dependent_id if p.dependent_id != "NEW" else memory.id,
                link_type=p.link_type,
                confidence=p.confidence,
                reason=p.reason,
                created_by=p.created_by,
            )
            for p in self._proposals
        ]


class ScriptedDetector:
    def __init__(self, classification: ChangeClassification) -> None:
        self._classification = classification
        self.calls = 0

    async def classify(self, content, structured, candidates):
        self.calls += 1
        return self._classification


def _intake(store, clock, linker, detector, *waves, resolver=None):
    class Factory(ScriptedEngine):
        def __init__(self, max_depth: int = 8) -> None:
            super().__init__(*waves, max_depth=max_depth)

    runner = RippleRunner(store, resolver or ScriptedResolver({}), clock, engine_factory=Factory)  # type: ignore[arg-type]
    return Intake(store, clock, LinkTypeRegistry(), linker, detector, runner)


def _proposal(parent, dependent, confidence=0.9):
    return LinkProposal(
        parent_id=parent,
        dependent_id=dependent,
        link_type="depends_on_fact",
        confidence=confidence,
        reason="scripted",
        created_by=LinkCreator.LLM,
    )


def test_intake_new_statement_writes_memory_links_and_completes_event():
    store, clock = InMemoryStore(), FakeClock()
    cgpa = fact("student", "cgpa", 7.6)
    asyncio.run(_seed(store, cgpa))
    detector = ScriptedDetector(ChangeClassification(kind=ChangeKind.NEW, reason="new"))
    linker = ScriptedLinker(_proposal(cgpa.id, "NEW"), _proposal(cgpa.id, "NEW", confidence=0.1))
    intake = _intake(store, clock, linker, detector)

    result = asyncio.run(intake.ingest(Statement(USER, "jobs", "derived", "not eligible for Acme")))

    assert result.change_kind is ChangeKind.NEW
    assert result.links_written == 1  # the 0.1-confidence duplicate was dropped
    assert result.event is not None
    assert result.event.completed_at is not None
    assert result.event.trigger_kind is TriggerKind.RIPPLE
    assert [edge.parent_id for edge in asyncio.run(store.parents_of(result.memory.id))] == [cgpa.id]
    assert result.memory.valid_from == DEFAULT_START


def test_intake_structured_update_skips_the_detector_and_ripples():
    store, clock = InMemoryStore(), FakeClock()
    cgpa = fact("student", "cgpa", 7.6)
    eligibility = derived("not eligible")
    asyncio.run(_seed(store, cgpa, eligibility, links=[link(cgpa, eligibility)]))
    detector = ScriptedDetector(ChangeClassification(kind=ChangeKind.NEW, reason="unused"))
    resolver = ScriptedResolver({eligibility.id: update("eligible")})
    intake = _intake(store, clock, ScriptedLinker(), detector, [eligibility.id], resolver=resolver)

    statement = Statement(
        USER,
        "jobs",
        "fact",
        "CGPA is 7.9",
        structured=StructuredFact(subject="student", attribute="cgpa", value=7.9),
    )
    result = asyncio.run(intake.ingest(statement))

    assert detector.calls == 0
    assert result.change_kind is ChangeKind.UPDATE
    assert (result.memory.version, result.memory.supersedes_id) == (2, cgpa.id)
    assert asyncio.run(store.latest_version(eligibility.id)).content == "eligible"


def test_intake_temporary_statement_sets_valid_to():
    store, clock = InMemoryStore(), FakeClock()
    until = DEFAULT_START + timedelta(days=30)
    detector = ScriptedDetector(
        ChangeClassification(kind=ChangeKind.TEMPORARY, reason="exams", valid_to=until)
    )
    intake = _intake(store, clock, ScriptedLinker(), detector)
    result = asyncio.run(
        intake.ingest(Statement(USER, "jobs", "fact", "busy with exams this month"))
    )
    assert result.memory.valid_to == until and result.memory.is_temporary
    assert asyncio.run(store.memories_expiring_at(USER, until)) == [result.memory]


def test_intake_agent_written_statement_uses_ripple_trigger_kind():
    store, clock = InMemoryStore(), FakeClock()
    detector = ScriptedDetector(ChangeClassification(kind=ChangeKind.NEW, reason="new"))
    intake = _intake(store, clock, ScriptedLinker(), detector)
    result = asyncio.run(
        intake.ingest(
            Statement(
                USER, "jobs", "opening", "Acme SDE intern", created_by="scout", origin="agent"
            )
        )
    )
    assert result.event is not None and result.event.trigger_kind is TriggerKind.RIPPLE


def test_intake_inspector_edit_uses_user_edit_trigger_kind():
    store, clock = InMemoryStore(), FakeClock()
    detector = ScriptedDetector(ChangeClassification(kind=ChangeKind.NEW, reason="new"))
    intake = _intake(store, clock, ScriptedLinker(), detector)
    result = asyncio.run(
        intake.ingest(Statement(USER, "jobs", "fact", "edited in inspector", origin="inspector"))
    )
    assert result.event is not None and result.event.trigger_kind is TriggerKind.USER_EDIT


def test_intake_same_value_statement_writes_nothing():
    store, clock = InMemoryStore(), FakeClock()
    cgpa = fact("student", "cgpa", 7.6)
    asyncio.run(_seed(store, cgpa))
    detector = ScriptedDetector(ChangeClassification(kind=ChangeKind.NEW, reason="unused"))
    intake = _intake(store, clock, ScriptedLinker(), detector)
    statement = Statement(
        USER,
        "jobs",
        "fact",
        "CGPA is 7.6",
        structured=StructuredFact(subject="student", attribute="cgpa", value=7.6),
    )
    result = asyncio.run(intake.ingest(statement))
    assert result.change_kind is ChangeKind.UNCHANGED and result.event is None
    assert result.memory.id == cgpa.id
    assert len(asyncio.run(store.memories_for_user(USER))) == 1
    assert store.change_events() == []


def test_intake_update_adds_links_the_linker_finds_beyond_the_copies():
    store, clock = InMemoryStore(), FakeClock()
    cgpa = fact("student", "cgpa", 7.6)
    eligibility = derived("not eligible")
    newer_fit = derived("fit mentions cgpa")
    asyncio.run(_seed(store, cgpa, eligibility, newer_fit, links=[link(cgpa, eligibility)]))
    detector = ScriptedDetector(ChangeClassification(kind=ChangeKind.NEW, reason="unused"))
    linker = ScriptedLinker(_proposal("NEW", eligibility.id), _proposal("NEW", newer_fit.id))
    intake = _intake(store, clock, linker, detector, [eligibility.id, newer_fit.id])
    statement = Statement(
        USER,
        "jobs",
        "fact",
        "CGPA is 7.9",
        structured=StructuredFact(subject="student", attribute="cgpa", value=7.9),
    )
    result = asyncio.run(intake.ingest(statement))
    assert result.links_written == 1  # eligibility was already copied; newer_fit is new
    dependents = {edge.dependent_id for edge in asyncio.run(store.dependents_of(result.memory.id))}
    assert dependents == {eligibility.id, newer_fit.id}


async def _seed(store: InMemoryStore, *memories: Memory, links=()):
    async with store.transaction() as tx:
        for m in memories:
            await tx.add_memory(m)
        for edge in links:
            await tx.add_link(edge)
    assert all(m.status is Status.VALID for m in memories)
