"""Named invariant tests (CLAUDE.md). One test per invariant that core can enforce.

I4 (LLM output validated before use) lives with the LLM resolver in tests/llm,
I5/I6 belong to the agents (Phase 2/3), I8 to the eval auditor.
"""

import ast
import asyncio
from pathlib import Path

import ripple.core.engine
import ripple.core.ripple
from ripple.core.forget import forget
from ripple.core.models import Status, TriggerKind
from ripple.core.ripple import RippleRunner
from ripple.core.sweep import NightlySweep
from ripple.core.visibility import visible_for_retrieval
from ripple.core.writes import update_memory
from tests.builders import USER, derived, fact, link, memory, snapshot_link
from tests.fakes.clock import FakeClock
from tests.fakes.engine import ScriptedEngine
from tests.fakes.resolver import ScriptedResolver, ask, retire, update
from tests.fakes.store import InMemoryStore


def test_invariant_I1_retrieval_never_returns_retired_and_flags_suspect():
    memories = [
        memory(content="valid"),
        memory(content="suspect", status=Status.SUSPECT),
        memory(content="pending", status=Status.PENDING_USER),
        memory(content="retired", status=Status.RETIRED),
    ]
    plain = visible_for_retrieval(memories)
    assert [v.memory.content for v in plain] == ["valid"]
    flagged = visible_for_retrieval(memories, include_flagged=True)
    assert [(v.memory.content, v.flagged) for v in flagged] == [
        ("valid", False),
        ("suspect", True),
        ("pending", True),
    ]


def test_invariant_I2_every_state_change_is_covered_by_a_change_event():
    """Drive update, retire, ask, expiry and a crash-free run; then audit the store."""
    store, clock = InMemoryStore(), FakeClock()
    cgpa = fact("student", "cgpa", 7.6)
    eligibility = derived("not eligible")
    fit = derived("weak fit")
    reminder = derived("remind on Friday")
    below_reminder = derived("prepare for Friday")
    temp = memory(content="busy", valid_to=clock.now())
    availability = derived("unavailable")

    async def write():
        async with store.transaction() as tx:
            for m in (cgpa, eligibility, fit, reminder, below_reminder, temp, availability):
                await tx.add_memory(m)
            await tx.add_link(link(cgpa, eligibility))
            await tx.add_link(link(cgpa, fit))
            await tx.add_link(link(cgpa, reminder))
            await tx.add_link(link(reminder, below_reminder))
            await tx.add_link(link(temp, availability))

    asyncio.run(write())

    class Factory(ScriptedEngine):
        def __init__(self, max_depth: int = 8) -> None:
            super().__init__(
                [eligibility.id, fit.id, reminder.id], max_depth=max_depth
            ) if not Factory.used else super().__init__([availability.id], max_depth=max_depth)
            Factory.used = True

        used = False

    resolver = ScriptedResolver(
        {eligibility.id: update("eligible"), fit.id: retire(), reminder.id: ask()},
        default=update("available"),
    )
    runner = RippleRunner(store, resolver, clock, engine_factory=Factory)  # type: ignore[arg-type]
    _, event = asyncio.run(
        update_memory(
            store,
            clock,
            cgpa.id,
            content="CGPA is 7.9",
            structured=None,
            valid_to=None,
            created_by="user",
            kind=TriggerKind.USER_EDIT,
        )
    )
    asyncio.run(runner.run(event))
    asyncio.run(NightlySweep(store, runner, clock).expire(USER))

    events = store.change_events()
    covered: set[str] = set()
    for e in events:
        assert e.completed_at is not None
        covered.add(e.trigger_memory_id)
        covered.update(e.affected_ids)
        for parked_ids in e.parked.values():
            covered.update(parked_ids)
        # The retirement of a superseded version is recorded by the event whose trigger
        # supersedes it (ADR-0015, docs/03 ChangeEvent).
        trigger = asyncio.run(store.get_memory(e.trigger_memory_id))
        if trigger.supersedes_id:
            covered.add(trigger.supersedes_id)
        for d in e.decisions:
            assert d.reason, "every decision carries a reason"
            covered.add(d.memory_id)
            if d.new_version_id:
                covered.add(d.new_version_id)
    for m in store.all_memories():
        changed = m.status is not Status.VALID or m.version > 1
        if changed:
            assert m.id in covered, f"{m.content!r} changed state without a ChangeEvent"
    # The trigger versions are covered through their events, retired originals through
    # the update that superseded them.
    retired_originals = [m for m in store.all_memories() if m.status is Status.RETIRED]
    assert retired_originals, "the scenario did retire something"


def test_invariant_I3_engine_never_calls_an_llm():
    for module in (ripple.core.engine, ripple.core.ripple):
        assert module.__file__ is not None
        source = Path(module.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported = {
            name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import | ast.ImportFrom)
            for name in (
                [alias.name for alias in node.names]
                if isinstance(node, ast.Import)
                else [node.module or ""]
            )
        }
        assert not any(name.startswith("ripple.llm") for name in imported), module.__name__
    # The traversal object is constructed from a depth limit alone: no client, no store.
    import inspect

    params = inspect.signature(ripple.core.engine.WaveEngine).parameters
    assert set(params) <= {"max_depth", "truncated"}


def test_invariant_I7_hard_deletion_only_via_forget_with_cascade():
    store, clock = InMemoryStore(), FakeClock()
    cgpa = fact("student", "cgpa", 7.6)
    eligibility = derived("not eligible")
    resume = fact("student", "resume", "v1")
    application = derived("applied with v1", kind="application")

    async def write():
        async with store.transaction() as tx:
            for m in (cgpa, eligibility, resume, application):
                await tx.add_memory(m)
            await tx.add_link(link(cgpa, eligibility))
            await tx.add_link(snapshot_link(resume, application))

    asyncio.run(write())
    # Retire never deletes: the row is still there with its history.
    asyncio.run(
        update_memory(
            store,
            clock,
            cgpa.id,
            content="CGPA is 7.9",
            structured=None,
            valid_to=None,
            created_by="user",
            kind=TriggerKind.USER_EDIT,
        )
    )
    assert asyncio.run(store.get_memory(cgpa.id)).status is Status.RETIRED
    # Forget deletes the chain and cascades along depends_on, never along snapshot_of.
    forget_event = asyncio.run(forget(store, clock, cgpa.id))
    assert eligibility.id in forget_event.deleted_ids
    assert application.id not in forget_event.deleted_ids
    assert len(store.forget_events()) == 1
