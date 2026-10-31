"""Static replay of a scenario into snapshots of memory text and links (ADR-0090).

No engine and no store: the scripted resolutions say what each dependent becomes, and
this module applies them the way the real system would, so the pair generator can
read every version a scenario passes through.

- Versioning follows docs/03: a depends_on link follows both endpoints to their new
  versions; a snapshot_of link holds only between the versions it was written between.
- A change ripples in waves along depends_on links, as the WaveEngine contract says:
  a dependent answered `update` or `retire` passes the change on, `keep`, `ask` or no
  answer stops that branch; depth is capped at the engine's DEFAULT_MAX_DEPTH. The
  answer is the first resolution whose trigger is unset or names the alias that
  started the ripple (bench.scenario.AliasResolver).
- Event fields the event does not restate carry over from the latest version, and a
  falsy `valid_to_days` means "keep the current expiry", as bench.scenario's runner does.
- Retire, expiry and forget (cascading along depends_on, I7) remove a memory from
  later snapshots.

tests/training/test_replay.py checks every v0 scenario's own `expect` blocks against
the replay, so drift from the runner shows up as a failing test.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from bench.linkpairs import PairMemory
from bench.scenario import EventSpec, ResolutionSpec, ScenarioSpec

from ripple.core.engine import DEFAULT_MAX_DEPTH
from ripple.core.links import LinkTypeRegistry
from ripple.core.models import DecisionAction, LinkClass, StructuredFact


class ReplayError(ValueError):
    """A scenario the static replay cannot follow; the message names scenario and event."""


@dataclass(frozen=True)
class Snapshot:
    scenario: str
    persona: str
    template: str
    step: int  # 0 = seeded state, n = after event n
    memories: Mapping[str, PairMemory]  # alias -> its current version
    versions: Mapping[str, int]  # alias -> version number of that current version
    links: tuple[tuple[str, str, str], ...]  # (parent alias, dependent alias, link type)


@dataclass
class _LinkState:
    parent: str
    dependent: str
    link_type: str
    link_class: LinkClass
    parent_version: int
    dependent_version: int


def _first_answer(entries: Sequence[ResolutionSpec], trigger: str) -> ResolutionSpec | None:
    for entry in entries:
        if entry.trigger is None or entry.trigger == trigger:
            return entry
    return None


@dataclass
class _Replay:
    spec: ScenarioSpec
    registry: LinkTypeRegistry
    memories: dict[str, PairMemory] = field(default_factory=dict)
    versions: dict[str, int] = field(default_factory=dict)
    valid_to_day: dict[str, int] = field(default_factory=dict)
    links: list[_LinkState] = field(default_factory=list)
    day: int = 0
    where: str = "seed"

    def fail(self, message: str) -> ReplayError:
        return ReplayError(f"{self.spec.name} ({self.where}): {message}")

    def require(self, alias: str) -> None:
        if alias not in self.memories:
            raise self.fail(f"{alias!r} is not live (never seeded, retired or forgotten)")

    def add(self, alias: str, memory: PairMemory, valid_to_days: int | None) -> None:
        self.memories[alias] = memory
        self.versions[alias] = 1
        if valid_to_days:
            self.valid_to_day[alias] = self.day + valid_to_days

    def add_link(self, parent: str, dependent: str, link_type: str) -> None:
        self.require(parent)
        self.require(dependent)
        if any((x.parent, x.dependent) == (parent, dependent) for x in self.links):
            raise self.fail(f"two links {parent} -> {dependent}; a pair carries one type")
        self.links.append(
            _LinkState(
                parent,
                dependent,
                link_type,
                self.registry.class_of(link_type),
                self.versions[parent],
                self.versions[dependent],
            )
        )

    def live_links(self) -> list[_LinkState]:
        return [
            link
            for link in self.links
            if link.parent in self.memories
            and link.dependent in self.memories
            and (
                link.link_class is LinkClass.DEPENDS_ON
                or (
                    self.versions[link.parent] == link.parent_version
                    and self.versions[link.dependent] == link.dependent_version
                )
            )
        ]

    def direct_dependents(self, alias: str) -> list[str]:
        return [
            link.dependent
            for link in self.live_links()
            if link.parent == alias and link.link_class is LinkClass.DEPENDS_ON
        ]

    def rewrite(
        self,
        alias: str,
        content: str,
        structured: StructuredFact | None = None,
        valid_to_days: int | None = None,
    ) -> None:
        self.require(alias)
        old = self.memories[alias]
        self.memories[alias] = PairMemory(
            kind=old.kind, content=content, structured=structured or old.structured
        )
        self.versions[alias] += 1
        if valid_to_days:
            self.valid_to_day[alias] = self.day + valid_to_days

    def remove(self, alias: str) -> None:
        self.memories.pop(alias, None)

    def ripple(self, trigger: str) -> None:
        visited = {trigger}
        wave = [a for a in self.direct_dependents(trigger) if a not in visited]
        depth = 0
        while wave and depth < DEFAULT_MAX_DEPTH:
            depth += 1
            changed: list[str] = []
            retired: list[str] = []
            for alias in wave:
                visited.add(alias)
                if alias not in self.memories:
                    continue
                answer = _first_answer(self.spec.resolutions_for(alias), trigger)
                if answer is None:
                    continue  # default keep: the branch stops here
                if answer.action is DecisionAction.UPDATE and answer.new_content:
                    changed.append(alias)
                    self.rewrite(alias, answer.new_content)
                elif answer.action is DecisionAction.RETIRE:
                    changed.append(alias)
                    retired.append(alias)
            next_wave: list[str] = []
            for alias in changed:  # read before a retired row goes
                for dependent in self.direct_dependents(alias):
                    if dependent not in visited and dependent not in next_wave:
                        next_wave.append(dependent)
            for alias in retired:
                self.remove(alias)
            wave = next_wave

    def snapshot(self, step: int) -> Snapshot:
        meta = self.spec.meta
        return Snapshot(
            scenario=self.spec.name,
            persona=str(meta["persona"]),
            template=str(meta["template"]),
            step=step,
            memories=dict(self.memories),
            versions=dict(self.versions),
            links=tuple((x.parent, x.dependent, x.link_type) for x in self.live_links()),
        )

    def apply(self, event: EventSpec) -> None:
        if event.update is not None:
            if event.content is None:
                raise self.fail("an update needs content")
            self.rewrite(event.update, event.content, event.structured, event.valid_to_days)
            self.ripple(event.update)
        elif event.new is not None:
            if event.content is None:
                raise self.fail("a new memory needs content")
            memory = PairMemory(kind=event.kind, content=event.content, structured=event.structured)
            self.add(event.new, memory, event.valid_to_days)
            for parent, dependent, link_type in event.links:
                self.add_link(parent, dependent, link_type)
            self.ripple(event.new)
        elif event.advance_days is not None:
            self.day += event.advance_days
            # Alias order; v0 never has one expiring memory's ripple touch another
            # expiring memory, where the sweep would skip the stale candidate.
            for alias, day in sorted(self.valid_to_day.items()):
                if alias in self.memories and day <= self.day:
                    self.ripple(alias)
                    self.remove(alias)
        elif event.answer is not None:
            self.require(event.answer)
            if event.reply == "correction":
                if event.content is None:
                    raise self.fail("a correction needs content")
                self.rewrite(event.answer, event.content, event.structured)
                self.ripple(event.answer)
            elif event.reply == "no_longer_holds":
                self.ripple(event.answer)
                self.remove(event.answer)
            elif event.reply != "still_holds":
                raise self.fail(f"unknown reply {event.reply!r}")
        elif event.forget is not None:
            self.require(event.forget)
            doomed = [event.forget]
            for alias in doomed:  # grows while walking: the depends_on cascade (I7)
                doomed.extend(d for d in self.direct_dependents(alias) if d not in doomed)
            for alias in doomed:
                self.remove(alias)
        else:
            raise self.fail("an event needs one action")


def scenario_snapshots(spec: ScenarioSpec, registry: LinkTypeRegistry) -> list[Snapshot]:
    replay = _Replay(spec, registry)
    for alias, memory in spec.memories.items():
        replay.add(
            alias,
            PairMemory(kind=memory.kind, content=memory.content, structured=memory.structured),
            memory.valid_to_days,
        )
    for parent, dependent, link_type in spec.links:
        replay.add_link(parent, dependent, link_type)
    snapshots = [replay.snapshot(0)]
    for step, event in enumerate(spec.events, start=1):
        replay.where = f"event {step} {event.describe()}"
        replay.apply(event)
        snapshots.append(replay.snapshot(step))
    return snapshots
