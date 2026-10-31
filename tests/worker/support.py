"""Builders for worker tests: a JobContext over fakes, and a user graph with one expired
memory and one stranded open ripple, so a sweep has both kinds of work to do.
"""

import asyncio
from datetime import timedelta

import pytest

from ripple.core.models import TriggerKind
from ripple.core.ripple import RippleRunner
from ripple.core.sweep import NightlySweep
from ripple.core.writes import update_memory
from ripple.notify.delivery_log import InMemoryDeliveryLog
from ripple.notify.digest import DigestService
from ripple.worker.context import JobContext
from ripple.worker.lease import InMemoryLease
from tests.builders import derived, fact, link
from tests.fakes.clock import FakeClock
from tests.fakes.engine import ScriptedEngine
from tests.fakes.resolver import ExplodingResolver, ScriptedResolver
from tests.fakes.store import InMemoryStore
from tests.fakes.transport import RecordingTransport
from tests.notify.fakes import FakeRecommendationSource, FakeUserDirectory


class RecordingSweep:
    """Stands in for NightlySweep where a test only needs to know who was swept."""

    def __init__(self, *, fail_for: set[str] | None = None, events: int = 1) -> None:
        self.runs: list[str] = []
        self.fail_for = fail_for or set()
        self.events = events

    async def run(self, user_id: str) -> list:
        self.runs.append(user_id)
        if user_id in self.fail_for:
            raise ConnectionError("provider down")
        return [object()] * self.events


def context(
    *,
    clock: FakeClock | None = None,
    store: InMemoryStore | None = None,
    users: dict[str, str | None] | None = None,
    sweep=None,
    source: FakeRecommendationSource | None = None,
    transport: RecordingTransport | None = None,
    runner: RippleRunner | None = None,
    leases: InMemoryLease | None = None,
) -> JobContext:
    clock = clock or FakeClock()
    store = store or InMemoryStore()
    directory = FakeUserDirectory(users if users is not None else {"u1": "chat-1", "u2": "chat-2"})
    runner = runner or RippleRunner(store, ScriptedResolver({}), clock)
    return JobContext(
        store=store,
        runner=runner,
        clock=clock,
        users=directory,
        sweep=sweep if sweep is not None else NightlySweep(store, runner, clock),
        digest=DigestService(
            source or FakeRecommendationSource(),
            directory,
            transport if transport is not None else RecordingTransport(clock),
            clock,
            delivery_log=InMemoryDeliveryLog(),
        ),
        leases=leases or InMemoryLease(clock),
    )


def scripted_runner(store: InMemoryStore, resolver, clock: FakeClock, *waves) -> RippleRunner:
    class Factory(ScriptedEngine):
        def __init__(self, max_depth: int = 8) -> None:
            super().__init__(*waves, max_depth=max_depth)

    return RippleRunner(store, resolver, clock, engine_factory=Factory)  # type: ignore[arg-type]


def user_with_expiry_and_stranded_ripple(store: InMemoryStore, clock: FakeClock, user_id: str):
    """One temporary fact past its valid_to and one open ChangeEvent from a crashed ripple."""
    temporary = fact(
        "student",
        "availability",
        "busy with exams",
        user_id=user_id,
        valid_to=clock.now() - timedelta(hours=1),
    )
    cgpa = fact("student", "cgpa", 7.6, user_id=user_id)
    eligibility = derived("not eligible", user_id=user_id)

    async def write():
        async with store.transaction() as tx:
            for m in (temporary, cgpa, eligibility):
                await tx.add_memory(m)
            await tx.add_link(link(cgpa, eligibility))

    asyncio.run(write())
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
    exploding = ExplodingResolver(ScriptedResolver({}), explode_on_call=1)
    with pytest.raises(ConnectionError):
        asyncio.run(scripted_runner(store, exploding, clock, [eligibility.id]).run(event))
    clock.advance(timedelta(hours=2))  # past DEFAULT_STALE_AFTER so the sweep resumes it
    return temporary, eligibility, event
