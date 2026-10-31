"""Scenario format and runner: replay a YAML timeline against a memory strategy.

Moved here from tests/scenarios/runner.py (which re-exports everything) so that the
bench owns the format RippleBench is generated in (ADR-0021, ADR-0061).

File format (tests/scenarios/*.yaml and bench/data/<track>/*.yaml), validated into the
models below:

    name: cgpa_change
    meta: {persona: p0_asha, template: cgpa_rise, family: changed}   # optional
    # meta.domain (default jobs) picks the adapter: Memory.domain and the link-type
    # registry (bench/domains.py, ADR-0101); news_v1 and finance_v1 set it.
    memories:            # alias -> memory; alias is used everywhere else
      cgpa: {kind: fact, content: "CGPA is 7.6",
             structured: {subject: student, attribute: cgpa, value: 7.6}}
      eligibility: {kind: derived, content: "not eligible for Acme (cutoff 7.8)"}
    links:               # [parent alias, dependent alias, link_type]
      - [cgpa, eligibility, eligibility_of]
    resolutions:         # what the (scripted) resolver answers, by alias; default keep
      eligibility: {action: update, new_content: "eligible for Acme"}
      # or a list, each entry optionally scoped to the alias that triggered the ripple:
      # eligibility:
      #   - {trigger: cgpa, action: update, new_content: "eligible for Acme"}
    events:              # in order; each carries expectations checked after it
      - update: cgpa
        content: "CGPA is 7.9"
        structured: {subject: student, attribute: cgpa, value: 7.9}
        expect:
          cgpa: {status: RETIRED}
          cgpa@latest: {status: VALID, version: 2}
          eligibility@latest: {status: VALID, content: "eligible for Acme", version: 2}

Event kinds: update, new, advance_days (then the sweep runs), answer
(still_holds | no_longer_holds | correction), forget. Expectations address a memory by
alias (its original row) or alias@latest (its newest version); `deleted: true` asserts
the row is gone. The resolver answers by alias, following version chains, so a scripted
answer applies to whichever version is being resolved; an entry with `trigger` applies
only when the ripple was started by that alias, which is how a generated scenario
encodes "re-derive this belief when *that* parent changes" without flattering a
baseline that re-checks everything.

The root row of every alias gets the alias as its id. Ids are opaque to core, and
stable ids make traces readable and baseline wave order deterministic.
"""

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from tests.fakes.clock import FakeClock
from tests.fakes.store import InMemoryStore

from bench.domains import domain_of, registry_for
from bench.metrics import ScenarioMetrics, scenario_metrics
from bench.probe import retrieval_probe
from bench.replay import (
    ActionLayer,
    EventSnapshot,
    GoldState,
    ReplayTrace,
    StubActionLayer,
    snapshot_after_event,
)
from bench.strategies import MemoryStrategy, as_runner, build_strategy
from ripple.core.answers import (
    NotPendingError,
    answer_no_longer_holds,
    answer_with_correction,
    confirm_still_holds,
)
from ripple.core.clock import Clock
from ripple.core.engine import WaveEngine
from ripple.core.errors import ConfigurationError
from ripple.core.forget import forget
from ripple.core.links import LinkTypeRegistry, UnknownLinkTypeError
from ripple.core.models import (
    DecisionAction,
    Link,
    LinkCreator,
    Memory,
    Status,
    StructuredFact,
    TriggerKind,
)
from ripple.core.resolver import Resolution, ResolutionContext
from ripple.core.store import MemoryNotFoundError, Store
from ripple.core.sweep import NightlySweep
from ripple.core.writes import record_memory, update_memory

USER = "scenario-user"


# ---- file schema ------------------------------------------------------------------


class MemorySpec(BaseModel):
    kind: str = "fact"
    content: str
    structured: StructuredFact | None = None
    valid_to_days: int | None = None  # relative to the scenario start


class ResolutionSpec(BaseModel):
    action: DecisionAction
    new_content: str | None = None
    question: str | None = None
    reason: str = "scripted"
    trigger: str | None = None  # alias whose change this answer is written for


class Expectation(BaseModel):
    status: Status | None = None
    content: str | None = None
    version: int | None = None
    deleted: bool = False

    def gold(self) -> GoldState:
        return GoldState(
            status=None if self.status is None else self.status.value,
            content=self.content,
            version=self.version,
            deleted=self.deleted,
        )


class EventSpec(BaseModel):
    update: str | None = None
    new: str | None = None
    advance_days: int | None = None
    answer: str | None = None
    forget: str | None = None
    content: str | None = None
    structured: StructuredFact | None = None
    valid_to_days: int | None = None
    kind: str = "fact"
    links: list[list[str]] = Field(default_factory=list)
    reply: str | None = None  # still_holds | no_longer_holds | correction
    expect: dict[str, Expectation] = Field(default_factory=dict)

    def describe(self) -> str:
        for name in ("update", "new", "answer", "forget"):
            alias = getattr(self, name)
            if alias is not None:
                return f"{name}:{alias}"
        if self.advance_days is not None:
            return f"advance_days:{self.advance_days}"
        return "noop"


class ScenarioSpec(BaseModel):
    name: str
    description: str = ""
    meta: dict[str, Any] = Field(default_factory=dict)
    memories: dict[str, MemorySpec]
    links: list[list[str]] = Field(default_factory=list)
    resolutions: dict[str, ResolutionSpec | list[ResolutionSpec]] = Field(default_factory=dict)
    events: list[EventSpec]

    def resolutions_for(self, alias: str) -> list[ResolutionSpec]:
        entry = self.resolutions.get(alias)
        if entry is None:
            return []
        return entry if isinstance(entry, list) else [entry]


def load_scenario(path: Path) -> ScenarioSpec:
    with path.open(encoding="utf-8") as handle:
        return ScenarioSpec.model_validate(yaml.safe_load(handle))


def validate_scenario(spec: ScenarioSpec) -> list[str]:
    """Static checks a scenario must pass before it is worth running: every alias in
    links, resolutions, actions and expectations is declared (seeded or introduced by
    a `new` event earlier in the timeline), every event carries exactly one action, the
    scenario's `meta.domain` has an adapter and every link type belongs to it.
    A forget cascade is not modelled statically, so a later action on a cascaded
    alias is caught at run time and recorded as an error."""
    problems: list[str] = []
    try:
        registry: LinkTypeRegistry | None = registry_for(domain_of(spec.meta))
    except ConfigurationError as exc:
        problems.append(str(exc))
        registry = None
    known = set(spec.memories)
    for link in spec.links:
        if len(link) != 3:
            problems.append(f"link {link!r} must be [parent, dependent, link_type]")
        elif link[0] not in known or link[1] not in known:
            problems.append(f"link {link!r} names an unknown alias")
        else:
            problems.extend(_unknown_link_type(registry, link))
    for alias in spec.resolutions:
        if alias not in known and not any(e.new == alias for e in spec.events):
            problems.append(f"resolution for unknown alias {alias!r}")
    for number, event in enumerate(spec.events, start=1):
        actions = [
            name
            for name in ("update", "new", "advance_days", "answer", "forget")
            if getattr(event, name) is not None
        ]
        if len(actions) != 1:
            problems.append(f"event {number} must carry exactly one action, has {actions}")
            continue
        for name in ("update", "answer", "forget"):
            alias = getattr(event, name)
            if alias is not None and alias not in known:
                problems.append(f"event {number}: {name} names an unknown alias {alias!r}")
        if event.new is not None:
            if event.new in known:
                problems.append(f"event {number}: alias {event.new!r} already exists")
            known.add(event.new)
            for link in event.links:
                if len(link) != 3 or link[0] not in known or link[1] not in known:
                    problems.append(f"event {number}: link {link!r} names an unknown alias")
                else:
                    problems.extend(
                        f"event {number}: {p}" for p in _unknown_link_type(registry, link)
                    )
        for target in event.expect:
            alias, _, selector = target.partition("@")
            if alias not in known:
                problems.append(f"event {number}: expectation for unknown alias {alias!r}")
            if selector not in ("", "latest"):
                problems.append(f"event {number}: bad selector in {target!r}")
    return problems


def _unknown_link_type(registry: LinkTypeRegistry | None, link: Sequence[str]) -> list[str]:
    if registry is None:
        return []
    try:
        registry.class_of(link[2])
    except UnknownLinkTypeError:
        return [f"link {list(link)!r}: type {link[2]!r} is not a link type of the domain"]
    return []


# ---- runner ------------------------------------------------------------------------


@dataclass
class ScenarioOutcome:
    name: str
    strategy: str = "ripple"
    checks: int = 0
    checks_failed: int = 0  # gold targets with at least one mismatch
    failures: list[str] = field(default_factory=list)  # one line per mismatch, for the report
    errors: list[str] = field(default_factory=list)  # runtime problems, not gold mismatches
    events_run: int = 0
    resolver_calls: int = 0
    llm_calls: int = 0
    trace: ReplayTrace | None = field(default=None, repr=False)
    # The memory metrics of this scenario (bench/metrics.py); None when it did not run.
    metrics: ScenarioMetrics | None = field(default=None, repr=False)

    @property
    def passed(self) -> bool:
        return not self.failures and not self.errors

    @property
    def runnable(self) -> bool:
        return not any(e.startswith("not runnable") for e in self.errors)

    @property
    def problems(self) -> list[str]:
        return [*self.errors, *self.failures]


class AliasResolver:
    """Answers by scenario alias; a new version of an aliased memory gets the same answer.

    With `trigger` on a ResolutionSpec the answer applies only when the ripple was
    started by that alias; entries are tried in order and the first match wins.
    """

    def __init__(self, store: Store, spec: ScenarioSpec) -> None:
        self._store = store
        self._spec = spec
        self._root_to_alias: dict[str, str] = {}  # filled by `register` as rows are written
        self.calls = 0

    @property
    def llm_calls(self) -> int:
        """Calls this resolver made to a language model: none, it reads the scenario's
        scripted answers. bench.run sums this per resolver, so an LLM resolver plugged
        in later reports its own count instead of the oracle's 0 (ADR-0122)."""
        return 0

    async def resolve(self, context: ResolutionContext) -> Resolution:
        self.calls += 1
        alias = await self._alias_of(context.memory.id)
        trigger_alias = await self._alias_of(context.trigger.id)
        for spec in self._spec.resolutions_for(alias):
            if spec.trigger is None or spec.trigger == trigger_alias:
                return Resolution(
                    action=spec.action,
                    reason=spec.reason,
                    new_content=spec.new_content,
                    question=spec.question,
                )
        return Resolution(action=DecisionAction.KEEP, reason="scripted default keep")

    async def _alias_of(self, memory_id: str) -> str:
        root = (await self._store.version_chain(memory_id))[0]
        return self._root_to_alias.get(root.id, "")

    def register(self, alias: str, memory_id: str) -> None:
        self._root_to_alias[memory_id] = alias


class ScenarioRunner:
    def __init__(
        self,
        spec: ScenarioSpec,
        *,
        store: Store | None = None,
        clock: Clock | None = None,
        strategy: str = "ripple",
        engine_factory: type[WaveEngine] | None = None,
        action_layer: ActionLayer | None = None,
        ablation: str | None = None,
        probe_retrieval: bool = True,
    ) -> None:
        self.spec = spec
        self.store: Store = store or InMemoryStore()
        self.clock = clock or FakeClock()
        self.domain = domain_of(spec.meta)
        self.registry = registry_for(self.domain)
        self.ids: dict[str, str] = {}
        self.resolver = AliasResolver(self.store, spec)
        self.strategy: MemoryStrategy = build_strategy(
            strategy,
            store=self.store,
            resolver=self.resolver,
            clock=self.clock,
            engine_factory=engine_factory,
            ablation=ablation,
        )
        self.probe_retrieval = probe_retrieval
        # The retrieval probe's query per alias: the content it was first written with.
        self.queries: dict[str, str] = {alias: m.content for alias, m in spec.memories.items()}
        self.sweep = NightlySweep(
            self.store, as_runner(self.strategy), self.clock, stale_after=timedelta(0)
        )
        self.action_layer: ActionLayer = action_layer or StubActionLayer(self.store)
        self.started_at = self.clock.now()
        self.trace = ReplayTrace(spec.name, self.strategy.name, self.started_at)

    def run(self) -> ScenarioOutcome:
        return asyncio.run(self._run())

    async def _run(self) -> ScenarioOutcome:
        outcome = ScenarioOutcome(self.spec.name, strategy=self.strategy.name)
        await self._seed()
        await self._snapshot(0, "seed", {})
        for number, event in enumerate(self.spec.events, start=1):
            try:
                await self._apply(event)
            except (NotPendingError, MemoryNotFoundError) as exc:
                # The scenario answers a question this strategy never asked, or acts on
                # a row an earlier forget cascaded away. That is the strategy's failure
                # (or the scenario author's), not a crash: record it and go on.
                outcome.errors.append(f"{event.describe()}: {exc}")
            outcome.events_run += 1
            snapshot = await self._snapshot(number, event.describe(), event.expect)
            self._check(snapshot, outcome)
        outcome.resolver_calls = self.strategy.resolver_calls
        outcome.llm_calls = self.resolver.llm_calls
        outcome.trace = self.trace
        outcome.metrics = scenario_metrics(
            self.trace,
            await self.store.change_events_for_user(USER),
            resolver_calls=outcome.resolver_calls,
            llm_calls=outcome.llm_calls,
        )
        return outcome

    async def _seed(self) -> None:
        now = self.clock.now()
        async with self.store.transaction() as tx:
            for alias, spec in self.spec.memories.items():
                memory = Memory(
                    id=alias,
                    user_id=USER,
                    domain=self.domain,
                    kind=spec.kind,
                    content=spec.content,
                    structured=spec.structured,
                    valid_to=now + timedelta(days=spec.valid_to_days)
                    if spec.valid_to_days
                    else None,
                    recorded_at=now,
                    created_by="user" if spec.kind == "fact" else "curator",
                )
                await tx.add_memory(memory)
                self.ids[alias] = memory.id
                self.resolver.register(alias, memory.id)
            for link_spec in self.spec.links:
                await tx.add_link(self._link(link_spec, now))

    def _link(self, spec: Sequence[str], now: datetime) -> Link:
        parent, dependent, link_type = spec
        return Link(
            parent_id=self.ids[parent],
            dependent_id=self.ids[dependent],
            link_type=link_type,
            link_class=self.registry.class_of(link_type),
            created_by=LinkCreator.HUMAN,
            created_at=now,
        )

    async def _apply(self, event: EventSpec) -> None:
        if event.update is not None:
            assert event.content is not None, "update needs content"
            # Fields the event does not restate carry over from the latest version,
            # as a resolver's update does in the core runner.
            latest = await self.store.latest_version(self.ids[event.update])
            valid_to = (
                self.clock.now() + timedelta(days=event.valid_to_days)
                if event.valid_to_days
                else latest.valid_to
            )
            _, change = await update_memory(
                self.store,
                self.clock,
                latest.id,
                content=event.content,
                structured=event.structured or latest.structured,
                valid_to=valid_to,
                created_by="user",
                kind=TriggerKind.USER_EDIT,
            )
            await self.strategy.run(change)
        elif event.new is not None:
            assert event.content is not None, "new needs content"
            now = self.clock.now()
            memory = Memory(
                id=event.new,
                user_id=USER,
                domain=self.domain,
                kind=event.kind,
                content=event.content,
                structured=event.structured,
                valid_from=now,
                valid_to=now + timedelta(days=event.valid_to_days) if event.valid_to_days else None,
                recorded_at=now,
                created_by="user",
            )
            self.ids[event.new] = memory.id
            self.resolver.register(event.new, memory.id)
            self.queries[event.new] = event.content
            links = [self._link(spec, now) for spec in event.links]
            change = await record_memory(
                self.store, self.clock, memory, links, kind=TriggerKind.USER_EDIT
            )
            await self.strategy.run(change)
        elif event.advance_days is not None:
            self.clock.advance(timedelta(days=event.advance_days))  # type: ignore[attr-defined]
            await self.sweep.run(USER)
        elif event.answer is not None:
            latest = await self.store.latest_version(self.ids[event.answer])
            runner = as_runner(self.strategy)
            if event.reply == "still_holds":
                await confirm_still_holds(self.store, self.clock, latest.id)
            elif event.reply == "no_longer_holds":
                await answer_no_longer_holds(self.store, self.clock, runner, latest.id)
            elif event.reply == "correction":
                assert event.content is not None, "correction needs content"
                await answer_with_correction(
                    self.store,
                    self.clock,
                    runner,
                    latest.id,
                    content=event.content,
                    structured=event.structured,
                )
            else:
                raise ValueError(f"unknown reply {event.reply!r}")
        elif event.forget is not None:
            await forget(self.store, self.clock, self.ids[event.forget])
        else:
            raise ValueError("event has no action")

    async def _snapshot(
        self, index: int, action: str, expectations: dict[str, Expectation]
    ) -> EventSnapshot:
        snapshot = await snapshot_after_event(
            self.store,
            self.action_layer,
            user_id=USER,
            ids=self.ids,
            index=index,
            action=action,
            now=self.clock.now(),
            started_at=self.started_at,
            gold={target: e.gold() for target, e in expectations.items()},
            resolver_calls=self.strategy.resolver_calls,
        )
        if self.probe_retrieval and index > 0 and expectations:
            aliases = dict.fromkeys(target.partition("@")[0] for target in expectations)
            queries = [(alias, self.queries[alias]) for alias in aliases if alias in self.queries]
            snapshot = replace(snapshot, retrieved=await retrieval_probe(self.store, USER, queries))
        self.trace.events.append(snapshot)
        return snapshot

    def _check(self, snapshot: EventSnapshot, outcome: ScenarioOutcome) -> None:
        for target, gold in snapshot.gold.items():
            outcome.checks += 1
            mismatches = gold.mismatches(target, snapshot.state_of(target))
            if mismatches:
                outcome.checks_failed += 1
                outcome.failures.extend(mismatches)
