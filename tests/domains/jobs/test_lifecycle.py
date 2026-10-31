"""An opening's life after it is recorded: the record-time wave, an inspector edit of the
anchor, closing it, and a skill learned after the fit belief exists (ADR-0030, ADR-0031).

Each test asks the dependency graph what the wave must be, then replays exactly that wave
through the scripted engine with the jobs rules and a fallback that fails when called.
"""

from ripple.core.engine import DependencyGraph
from ripple.core.models import DecisionAction, Status, TriggerKind
from ripple.core.writes import open_event, update_memory
from ripple.domains.jobs.derive import derive_criteria, derive_for_opening
from ripple.domains.jobs.openings import record_opening
from ripple.domains.jobs.profile import record_profile_fact
from ripple.domains.jobs.ranking import JobsRecommender
from ripple.domains.jobs.vocabulary import JobsLinkType, ProfileAttribute
from tests.domains.jobs.helpers import USER, make_runner, parsed_acme, rules_runner, run
from tests.fakes.clock import FakeClock
from tests.fakes.store import InMemoryStore


def _profile_and_opening():
    store, clock = InMemoryStore(), FakeClock()
    setup = make_runner(store, clock)
    run(record_profile_fact(store, clock, setup, USER, ProfileAttribute.CGPA, 7.9))
    run(record_profile_fact(store, clock, setup, USER, ProfileAttribute.BATCH, 2027))
    run(record_profile_fact(store, clock, setup, USER, ProfileAttribute.SKILL, "Python"))
    recorded = run(record_opening(store, clock, USER, parsed_acme(), setup))
    beliefs = run(derive_for_opening(store, clock, setup, recorded.anchor.id))
    return store, clock, setup, recorded, beliefs


def _wave(store: InMemoryStore, memory_id: str) -> list[str]:
    return list(DependencyGraph.from_links(run(store.links_for_user(USER))).dependents(memory_id))


def test_record_opening_wave_one_keeps_every_field_without_the_fallback():
    store, clock = InMemoryStore(), FakeClock()
    parsed = parsed_acme()
    # The wave is the anchor's dependents; field ids exist only after the write, so the
    # engine is scripted from a first dry recording of the same JD shape.
    probe_store = InMemoryStore()
    probe = run(record_opening(probe_store, clock, USER, parsed, make_runner(probe_store, clock)))
    assert len(_wave(probe_store, probe.anchor.id)) == len(parsed.fields)

    class WaveOfFields:
        """Engine stand-in: wave 1 = the trigger's dependents read from the live graph."""

        def __init__(self, max_depth: int = 8) -> None:
            self.max_depth, self.truncated, self._done = max_depth, False, False

        def first_wave(self, graph, seeds):
            from ripple.core.engine import Wave

            return Wave(number=1, memory_ids=tuple(graph.dependents(seeds[0])))

        def next_wave(self, graph, outcomes):
            return None

    from ripple.core.resolver import ResolverChain
    from ripple.core.ripple import RippleRunner
    from ripple.domains.jobs.rules import jobs_rules
    from tests.domains.jobs.helpers import RefusingResolver

    fallback = RefusingResolver()
    runner = RippleRunner(
        store,
        ResolverChain(jobs_rules(), fallback=fallback),  # type: ignore[arg-type]
        clock,
        engine_factory=WaveOfFields,  # type: ignore[arg-type]
    )
    recorded = run(record_opening(store, clock, USER, parsed, runner))
    assert fallback.contexts == []
    assert {d.memory_id for d in recorded.event.decisions} == {f.id for f in recorded.fields}
    assert {d.action for d in recorded.event.decisions} == {DecisionAction.KEEP}
    assert all(run(store.get_memory(f.id)).status is Status.VALID for f in recorded.fields)


def test_inspector_edit_of_the_anchor_keeps_fields_and_beliefs_attached():
    store, clock, _, recorded, beliefs = _profile_and_opening()
    assert recorded.anchor.structured is not None
    wave = _wave(store, recorded.anchor.id)
    runner, fallback = rules_runner(store, clock, runs=[[wave]])
    anchor_v2, event = run(
        update_memory(
            store,
            clock,
            recorded.anchor.id,
            content="SDE Intern (summer 2027) at Acme",
            # What the inspector edit does: structured carried over from the old version.
            structured=recorded.anchor.structured,
            valid_to=None,
            created_by="user",
            kind=TriggerKind.USER_EDIT,
        )
    )
    assert set(_wave(store, anchor_v2.id)) == set(wave)
    event = run(runner.run(event))
    assert fallback.contexts == []
    fields = {f.id for f in recorded.fields}
    assert {d.action for d in event.decisions if d.memory_id in fields} == {DecisionAction.KEEP}
    eligibility = run(store.latest_version(beliefs.eligibility.id))  # type: ignore[union-attr]
    assert eligibility.content.startswith("eligible for SDE Intern (summer 2027) at Acme: ")
    (rec,) = run(JobsRecommender(store).recommendations_for(USER, now=clock.now()))
    assert rec.opening_memory_id == anchor_v2.id
    assert (rec.company, rec.eligible, rec.deadline is not None) == ("Acme", True, True)
    assert rec.title == "Software Development Engineer Intern"


def test_closing_an_opening_retires_its_fields_and_beliefs_without_the_fallback():
    store, clock, _, recorded, beliefs = _profile_and_opening()
    wave = _wave(store, recorded.anchor.id)
    belief_ids = {b.id for b in (beliefs.eligibility, beliefs.fit, beliefs.reminder) if b}
    assert belief_ids <= set(wave)
    runner, fallback = rules_runner(store, clock, runs=[[wave]])

    async def close():
        # The same shape the sweep uses for expiry: retire the trigger, open its event.
        async with store.transaction() as tx:
            anchor = await tx.get_memory(recorded.anchor.id)
            await tx.replace_memory(anchor.model_copy(update={"status": Status.RETIRED}))
            return await open_event(tx, anchor, TriggerKind.EXPIRY, clock.now())

    event = run(runner.run(run(close())))
    assert fallback.contexts == []
    assert {d.action for d in event.decisions} == {DecisionAction.RETIRE}
    for memory_id in wave:
        assert run(store.get_memory(memory_id)).status is Status.RETIRED
    assert run(JobsRecommender(store).recommendations_for(USER, now=clock.now())) == []


def test_a_skill_learned_later_reaches_fit_and_criteria_through_rule_links():
    store, clock, setup, _, beliefs = _profile_and_opening()
    criteria = run(derive_criteria(store, clock, setup, USER))
    assert beliefs.fit is not None and criteria is not None
    assert beliefs.fit.structured is not None and beliefs.fit.structured.value == round(1 / 3, 4)
    runner, fallback = rules_runner(store, clock, runs=[[[beliefs.fit.id, criteria.id]]])
    sql, event = run(record_profile_fact(store, clock, runner, USER, ProfileAttribute.SKILL, "SQL"))
    assert event is not None and fallback.contexts == []
    # Links written with the skill; versioning then copies them onto the new versions.
    links = {(link.dependent_id, link.link_type) for link in run(store.dependents_of(sql.id))}
    assert {
        (beliefs.fit.id, JobsLinkType.FIT_OF),
        (criteria.id, JobsLinkType.CRITERIA_FROM),
    } <= links
    fit_v2 = run(store.latest_version(beliefs.fit.id))
    assert fit_v2.structured is not None and fit_v2.structured.value == round(2 / 3, 4)
    assert '- has SQL: JD says "Required: Python, PyTorch, SQL"; profile says "knows SQL"' in (
        fit_v2.content
    )
    assert run(store.latest_version(criteria.id)).content.endswith("skills python, sql")


def test_an_unrelated_skill_gets_no_fit_link():
    store, clock, setup, _, beliefs = _profile_and_opening()
    rust, _ = run(record_profile_fact(store, clock, setup, USER, ProfileAttribute.SKILL, "Rust"))
    assert beliefs.fit is not None
    assert [link.dependent_id for link in run(store.dependents_of(rust.id))] == []
