"""Structured facts link by domain rule and unlock derivation without a model (ADR-0116)."""

from collections.abc import Sequence

import pytest

from ripple.core.intake import Intake
from ripple.core.linking import LinkProposal
from ripple.core.models import Memory, Status, StructuredFact
from ripple.core.resolver import ResolverChain
from ripple.core.ripple import RippleRunner
from ripple.domains.jobs.derive import ProfileDerivationObserver
from ripple.domains.jobs.linker import JobsStructureLinker
from ripple.domains.jobs.openings import record_opening
from ripple.domains.jobs.profile import profile_statement, record_profile_fact
from ripple.domains.jobs.rules import jobs_rules
from ripple.domains.jobs.vocabulary import (
    MULTI_VALUED_PROFILE_ATTRIBUTES,
    PERMANENT_PROFILE_FACTS,
    DerivedAttribute,
    JobsLinkType,
    Kind,
    ProfileAttribute,
    jobs_registry,
)
from ripple.linking.composite import StructuredFirstLinker
from ripple.linking.rules import RuleLinker
from tests.domains.jobs.helpers import USER, RefusingResolver, make_runner, parsed_acme, run
from tests.fakes.clock import FakeClock
from tests.fakes.store import InMemoryStore


class RefusingProseLinker:
    """Stands in for the LLM linker: any call fails the test (no key, no model)."""

    def __init__(self) -> None:
        self.calls = 0

    async def propose(self, memory: Memory, candidates: Sequence[Memory]) -> list[LinkProposal]:
        self.calls += 1
        raise AssertionError("a structured fact must not reach the prose linker")


class NoDetector:
    async def classify(self, content, structured, candidates):  # pragma: no cover
        raise AssertionError("a structured statement is classified deterministically")


def _beliefs(store: InMemoryStore, attribute: DerivedAttribute) -> list[Memory]:
    """The live beliefs of one kind (older versions are RETIRED by the ripple)."""
    return [
        m
        for m in run(store.memories_for_user(USER, [Status.VALID]))
        if m.structured is not None and m.structured.attribute == attribute
    ]


def test_structure_linker_links_a_new_skill_to_the_fit_of_openings_requiring_it():
    store, clock = InMemoryStore(), FakeClock()
    setup = make_runner(store, clock)
    run(record_profile_fact(store, clock, setup, USER, ProfileAttribute.CGPA, 8.1))
    run(record_profile_fact(store, clock, setup, USER, ProfileAttribute.SKILL, "SQL"))
    from ripple.domains.jobs.derive import derive_for_opening

    recorded = run(record_opening(store, clock, USER, parsed_acme(), setup))
    derived = run(derive_for_opening(store, clock, setup, recorded.anchor.id))
    assert derived.fit is not None
    pytorch = Memory(
        user_id=USER,
        domain="jobs",
        kind=Kind.FACT,
        content="Skill: PyTorch",
        structured=StructuredFact(subject="student", attribute="skill", value="PyTorch"),
        recorded_at=clock.now(),
        created_by="user",
    )

    proposals = run(JobsStructureLinker().propose(pytorch, run(store.memories_for_user(USER))))

    assert [(p.dependent_id, p.link_type) for p in proposals] == [
        (derived.fit.id, JobsLinkType.FIT_OF)
    ]
    assert proposals[0].confidence == 1.0


def test_structure_linker_proposes_nothing_for_prose_or_an_opening_field():
    clock = FakeClock()
    prose = Memory(
        user_id=USER,
        domain="jobs",
        kind=Kind.FACT,
        content="I like robotics",
        recorded_at=clock.now(),
        created_by="user",
    )
    assert run(JobsStructureLinker().propose(prose, [])) == []


def test_structured_first_linker_never_calls_the_prose_linker_for_a_structured_fact():
    prose = RefusingProseLinker()
    linker = StructuredFirstLinker([JobsStructureLinker(), RuleLinker()], prose)
    clock = FakeClock()
    fact = Memory(
        user_id=USER,
        domain="jobs",
        kind=Kind.FACT,
        content="CGPA is 8.1",
        structured=StructuredFact(subject="student", attribute="cgpa", value=8.1),
        recorded_at=clock.now(),
        created_by="user",
    )
    assert run(linker.propose(fact, [])) == [] and prose.calls == 0


def test_structured_first_linker_sends_prose_to_the_prose_linker():
    prose = RefusingProseLinker()
    linker = StructuredFirstLinker([RuleLinker()], prose)
    clock = FakeClock()
    note = Memory(
        user_id=USER,
        domain="jobs",
        kind=Kind.FACT,
        content="I prefer startups",
        recorded_at=clock.now(),
        created_by="user",
    )
    with pytest.raises(AssertionError, match="must not reach"):
        run(linker.propose(note, []))
    assert prose.calls == 1


def test_a_first_cgpa_statement_derives_eligibility_for_an_opening_saved_earlier():
    """The product path: save an opening, then tell Ripple your CGPA, with no model."""
    store, clock = InMemoryStore(), FakeClock()
    registry = jobs_registry()
    derivation = ProfileDerivationObserver(store, clock)
    # The real engine and the jobs rules, as production wires them; the LLM fallback
    # refuses, so every decision here is the rules' (ADR-0019, ADR-0116).
    runner = RippleRunner(
        store,
        ResolverChain(jobs_rules(), fallback=RefusingResolver()),
        clock,
        observers=[derivation],
    )
    derivation.attach(runner)
    intake = Intake(
        store,
        clock,
        registry,
        StructuredFirstLinker([JobsStructureLinker(), RuleLinker()], RefusingProseLinker()),
        NoDetector(),
        runner,
        multi_valued_attributes=MULTI_VALUED_PROFILE_ATTRIBUTES,
        permanent_facts=PERMANENT_PROFILE_FACTS,
    )
    run(record_profile_fact(store, clock, runner, USER, ProfileAttribute.BATCH, 2027))
    run(record_opening(store, clock, USER, parsed_acme(cutoff=7.8), runner))
    assert _beliefs(store, DerivedAttribute.ELIGIBLE) == []  # no CGPA yet: nothing to say

    run(intake.ingest(profile_statement(USER, ProfileAttribute.CGPA, 8.1)))

    [eligibility] = _beliefs(store, DerivedAttribute.ELIGIBLE)
    assert eligibility.content.startswith("eligible")
    [criteria] = _beliefs(store, DerivedAttribute.CRITERIA)
    assert "cgpa_cutoff <= 8.1" in criteria.content


def test_derivation_observer_refuses_to_run_unattached():
    from ripple.core.errors import ConfigurationError
    from tests.builders import change_event, fact

    store, clock = InMemoryStore(), FakeClock()
    cgpa = fact("student", "cgpa", 8.1, user_id=USER)

    async def seed():
        async with store.transaction() as tx:
            await tx.add_memory(cgpa)

    run(seed())
    with pytest.raises(ConfigurationError, match="attach"):
        run(ProfileDerivationObserver(store, clock).event_completed(change_event(cgpa)))


def test_derivation_observer_isolates_one_bad_opening_from_the_rest(monkeypatch, caplog):
    """An opening whose field cannot be read (a cutoff edited to prose, say) or that closed
    meanwhile is logged and skipped; every other opening is still derived."""
    import ripple.domains.jobs.derive as derive_module
    from ripple.core.errors import InvalidObjectError

    store, clock = InMemoryStore(), FakeClock()
    derivation = ProfileDerivationObserver(store, clock)
    runner = RippleRunner(
        store,
        ResolverChain(jobs_rules(), fallback=RefusingResolver()),
        clock,
        observers=[derivation],
    )
    derivation.attach(runner)
    first = run(record_opening(store, clock, USER, parsed_acme(), runner))
    second = run(
        record_opening(
            store,
            clock,
            USER,
            parsed_acme(source_ref="https://b.example/1", company="Beta"),
            runner,
        )
    )
    run(record_profile_fact(store, clock, runner, USER, ProfileAttribute.BATCH, 2027))
    real = derive_module.derive_for_opening
    reached: list[str] = []

    async def first_one_breaks(store_, clock_, runner_, anchor_id, **kwargs):
        reached.append(anchor_id)
        if len(reached) == 1:  # whichever the store lists first, so order cannot hide it
            raise InvalidObjectError("cgpa 'not specified' is not a number")
        return await real(store_, clock_, runner_, anchor_id, **kwargs)

    monkeypatch.setattr(derive_module, "derive_for_opening", first_one_breaks)
    run(record_profile_fact(store, clock, runner, USER, ProfileAttribute.CGPA, 8.1))

    assert sorted(reached) == sorted([first.anchor.id, second.anchor.id])  # store order
    assert len(_beliefs(store, DerivedAttribute.ELIGIBLE)) == 1  # the other one's, derived anyway
    assert "derivation skipped for one opening" in caplog.text
