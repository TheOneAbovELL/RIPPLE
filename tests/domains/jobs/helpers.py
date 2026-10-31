"""Builders and wiring shared by the jobs adapter tests (offline: fakes only)."""

import asyncio
from collections import deque
from collections.abc import Awaitable, Sequence
from datetime import UTC, datetime
from typing import NoReturn

from ripple.core.clock import Clock
from ripple.core.resolver import ResolutionContext, Resolver, ResolverChain
from ripple.core.ripple import EventObserver, RippleRunner
from ripple.core.store import Store
from ripple.domains.jobs.rules import jobs_rules
from ripple.domains.jobs.vocabulary import OpeningAttribute, ParsedField, ParsedOpening, TextSpan
from tests.fakes.engine import ScriptedEngine
from tests.fakes.resolver import ScriptedResolver

USER = "student-1"
DEADLINE = datetime(2026, 11, 5, 9, 0, tzinfo=UTC)
ACME_JD = (
    "Acme is hiring a Software Development Engineer Intern. "
    "Minimum CGPA: 7.8. Eligible batch: 2027. "
    "Required: Python, PyTorch, SQL. "
    "Location: Bengaluru. Apply by 2026-11-05T09:00:00+00:00."
)


def run[T](coro: Awaitable[T]) -> T:
    return asyncio.run(coro)  # type: ignore[arg-type]


def span(text: str, source: str = ACME_JD) -> TextSpan:
    start = source.index(text)
    return TextSpan(start=start, end=start + len(text), text=text)


def field(attribute: str, value: str | int | float | bool, text: str) -> ParsedField:
    return ParsedField(attribute=attribute, value=value, span=span(text))


def parsed_acme(
    *,
    cutoff: float | None = 7.8,
    batch: int | None = 2027,
    skills: Sequence[str] = ("Python", "PyTorch", "SQL"),
    deadline: str | None = DEADLINE.isoformat(),
    company: str | None = "Acme",
    source_ref: str = "https://acme.example/jobs/42",
) -> ParsedOpening:
    fields: list[ParsedField] = [
        field(
            OpeningAttribute.TITLE,
            "Software Development Engineer Intern",
            "Software Development Engineer Intern",
        ),
        field(OpeningAttribute.ROLE_TYPE, "internship", "Intern"),
    ]
    if company is not None:
        fields.append(field(OpeningAttribute.COMPANY, company, "Acme"))
    if cutoff is not None:
        fields.append(field(OpeningAttribute.CGPA_CUTOFF, cutoff, "Minimum CGPA: 7.8"))
    if batch is not None:
        fields.append(field(OpeningAttribute.BATCH, batch, "Eligible batch: 2027"))
    fields += [
        field(OpeningAttribute.REQUIRED_SKILL, skill, "Required: Python, PyTorch, SQL")
        for skill in skills
    ]
    if deadline is not None:
        fields.append(
            field(OpeningAttribute.DEADLINE, deadline, "Apply by 2026-11-05T09:00:00+00:00")
        )
    fields.append(field(OpeningAttribute.LOCATION, "Bengaluru", "Location: Bengaluru"))
    return ParsedOpening(
        source_ref=source_ref,
        raw_text=ACME_JD,
        fields=tuple(fields),
        summary=f"Software Development Engineer Intern at {company or 'an unnamed employer'}",
    )


class RefusingResolver:
    """A fallback that fails the test: the rules must have decided (ADR-0031)."""

    def __init__(self) -> None:
        self.contexts: list[ResolutionContext] = []

    async def resolve(self, context: ResolutionContext) -> NoReturn:
        self.contexts.append(context)
        raise AssertionError(f"LLM fallback called for {context.memory.content!r}")


def make_runner(
    store: Store,
    clock: Clock,
    *,
    resolver: Resolver | None = None,
    runs: Sequence[Sequence[Sequence[str]]] = (),
    observers: Sequence[EventObserver] = (),
) -> RippleRunner:
    """A runner whose engine replays `runs[i]` (a list of waves) on its i-th run and
    emits nothing afterwards, so setup writes ripple into empty waves."""
    queue: deque[Sequence[Sequence[str]]] = deque(runs)

    class Factory(ScriptedEngine):
        def __init__(self, max_depth: int = 8) -> None:
            waves = queue.popleft() if queue else ()
            super().__init__(*waves, max_depth=max_depth)

    return RippleRunner(
        store,
        resolver or ScriptedResolver({}),
        clock,
        engine_factory=Factory,  # type: ignore[arg-type]
        observers=observers,
    )


def rules_runner(store: Store, clock: Clock, runs: Sequence[Sequence[Sequence[str]]]):
    """Runner wired with the jobs rules and a fallback that fails the test."""
    fallback = RefusingResolver()
    chain = ResolverChain(jobs_rules(), fallback=fallback)  # type: ignore[arg-type]
    return make_runner(store, clock, resolver=chain, runs=runs), fallback
