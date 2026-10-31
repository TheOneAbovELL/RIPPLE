"""The ripple engine: deterministic, wave-by-wave traversal (ADR-0013, FR-6, I3).

Two parts:
- DependencyGraph: an immutable adjacency view built from Link rows, aware of which
  link classes propagate. Written by the collaborator.
- WaveEngine: the traversal itself (roadmap Phase 1, "[human] Ripple engine"),
  implemented by the collaborator on the author's explicit request of 2026-10-31. The
  contract is in the docstrings and in tests/core/test_engine.py.

The engine never does I/O and never calls an LLM. It receives a graph snapshot and the
outcomes of the previous wave, and returns the next set of memory ids to resolve.
"""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field

from ripple.core.links import policy_for
from ripple.core.models import Link

DEFAULT_MAX_DEPTH = 8


@dataclass(frozen=True)
class DependencyGraph:
    """parent id -> dependent ids along propagating links, in link creation order."""

    _dependents: Mapping[str, tuple[str, ...]]

    @classmethod
    def from_links(cls, links: Iterable[Link]) -> "DependencyGraph":
        adjacency: dict[str, list[str]] = {}
        for link in links:
            if not policy_for(link.link_class).propagates:
                continue
            bucket = adjacency.setdefault(link.parent_id, [])
            if link.dependent_id not in bucket:
                bucket.append(link.dependent_id)
        return cls({parent: tuple(deps) for parent, deps in adjacency.items()})

    def dependents(self, memory_id: str) -> tuple[str, ...]:
        """Direct dependents reachable through a propagating link."""
        return self._dependents.get(memory_id, ())

    def descendants(self, memory_id: str) -> tuple[str, ...]:
        """Every memory below `memory_id`, breadth-first, cycle-safe, excluding itself.

        Used when an `ask` parks a memory: its whole subtree is marked SUSPECT without
        resolution (ADR-0013).
        """
        seen: set[str] = {memory_id}
        order: list[str] = []
        frontier: list[str] = [memory_id]
        while frontier:
            next_frontier: list[str] = []
            for parent in frontier:
                for dependent in self.dependents(parent):
                    if dependent not in seen:
                        seen.add(dependent)
                        order.append(dependent)
                        next_frontier.append(dependent)
            frontier = next_frontier
        return tuple(order)


@dataclass(frozen=True)
class Wave:
    number: int
    memory_ids: tuple[str, ...]


@dataclass(frozen=True)
class WaveOutcome:
    """What the resolver did to one memory of the previous wave.

    `changed` is True for update and retire, False for keep and ask. For an update,
    `successor_id` is the new version's id: its dependents (copied links, ADR-0014)
    are what the next wave must reach.
    """

    memory_id: str
    changed: bool
    successor_id: str | None = None

    @property
    def frontier_id(self) -> str:
        return self.successor_id or self.memory_id


@dataclass
class WaveEngine:
    """Wave-by-wave traversal.

    Contract (ADR-0013 as amended by ADR-0119; every rule has a test in
    tests/core/test_engine.py):
    1. `first_wave(graph, seeds)` computes the *affected set*: every memory reachable
       from the seeds along propagating links, seeds excluded. Each member gets a
       *level*, the length of the longest path to it from a seed inside that set (a
       cycle is broken in discovery order). Wave 1 is the level-1 members, in
       first-seen order. Returns None when nothing is due.
    2. A member is *due* once one of its parents changed: a seed, or a member whose
       outcome had `changed=True` (through its `memory_id` or its `frontier_id`, the new
       version for an update). `next_wave(graph, outcomes)` records the previous wave's
       outcomes and returns the members of the lowest level that has a due, unresolved
       member. A keep or ask halts its own branch only: a member with another changed
       parent is still due.
    3. Every member is resolved at most once, and only after every affected parent of
       it has been resolved or skipped, so it is decided against their current values.
       A dependent that a new version's copied links reach outside the affected set is
       scheduled one level below its parent. A memory already resolved is never
       emitted again (cycle safety).
    4. The wave number increases by one per emitted wave. When it would exceed
       `max_depth`, `next_wave` returns None and sets `truncated` to True so the runner
       can log it.
    5. Both methods are pure over their arguments and this object's state: no I/O,
       no clock, no LLM (I3). Determinism: same inputs, same output, always.
    """

    max_depth: int = DEFAULT_MAX_DEPTH
    truncated: bool = False
    _resolved: set[str] = field(default_factory=set[str], repr=False, init=False)
    _level: dict[str, int] = field(default_factory=dict[str, int], repr=False, init=False)
    _order: list[str] = field(default_factory=list[str], repr=False, init=False)
    _due: set[str] = field(default_factory=set[str], repr=False, init=False)
    _current_level: int = field(default=0, init=False)
    _wave_number: int = field(default=0, init=False)

    def first_wave(self, graph: DependencyGraph, seeds: Sequence[str]) -> Wave | None:
        # Seeds are resolved by definition: a seed that is also a dependent of another
        # seed (a cycle between triggers) is never resolved again.
        self._resolved.update(seeds)
        self._schedule(graph, seeds)
        self._mark_due(graph, seeds)
        return self._next_due_wave()

    def next_wave(self, graph: DependencyGraph, outcomes: Sequence[WaveOutcome]) -> Wave | None:
        changed: list[str] = []
        for outcome in outcomes:
            self._resolved.add(outcome.memory_id)
            if outcome.changed:
                # An update's new version carries the copied links (ADR-0014); it is
                # resolved by construction, so a cycle back to it ends.
                self._resolved.add(outcome.frontier_id)
                changed.extend(dict.fromkeys([outcome.memory_id, outcome.frontier_id]))
        for parent in changed:
            for dependent in graph.dependents(parent):
                if dependent not in self._level and dependent not in self._resolved:
                    self._level[dependent] = self._current_level + 1
                    self._order.append(dependent)
        self._mark_due(graph, changed)
        return self._next_due_wave()

    def _schedule(self, graph: DependencyGraph, seeds: Sequence[str]) -> None:
        """Level every affected memory by its longest path from a seed (Kahn's order
        inside the affected set; members left on a cycle get one more than their
        deepest already-levelled parent, in discovery order)."""
        seed_set = set(seeds)
        parents: dict[str, list[str]] = {}
        frontier = list(seeds)
        while frontier:
            next_frontier: list[str] = []
            for parent in frontier:
                for dependent in graph.dependents(parent):
                    if dependent in seed_set:
                        continue
                    if dependent not in parents:
                        parents[dependent] = []
                        self._order.append(dependent)
                        next_frontier.append(dependent)
                    if parent not in parents[dependent]:
                        parents[dependent].append(parent)
            frontier = next_frontier
        level: dict[str, int] = dict.fromkeys(seed_set, 0)
        waiting = {m: sum(p not in seed_set for p in ps) for m, ps in parents.items()}
        ready = [m for m in self._order if waiting[m] == 0]
        while ready:
            member = ready.pop(0)
            level[member] = 1 + max(level[p] for p in parents[member])
            for dependent in graph.dependents(member):
                if dependent in waiting and dependent not in level:
                    waiting[dependent] -= 1
                    if waiting[dependent] == 0:
                        ready.append(dependent)
        for member in self._order:
            if member not in level:
                levelled = [level[p] for p in parents[member] if p in level]
                level[member] = 1 + max(levelled, default=0)
        self._level.update({m: level[m] for m in self._order})

    def _mark_due(self, graph: DependencyGraph, changed: Sequence[str]) -> None:
        for parent in changed:
            self._due.update(graph.dependents(parent))

    def _next_due_wave(self) -> Wave | None:
        # A member due only through a cycle's back edge may sit at a lower level than
        # the wave just resolved; it is still emitted, once.
        pending = [m for m in self._order if m in self._due and m not in self._resolved]
        if not pending:
            return None
        lowest = min(self._level[m] for m in pending)
        members = [m for m in pending if self._level[m] == lowest]
        if self._wave_number + 1 > self.max_depth:
            # Truncation only when real work is cut off; an exhausted ripple is complete.
            self.truncated = True
            return None
        self._current_level = max(self._current_level, lowest)
        self._wave_number += 1
        self._resolved.update(members)
        return Wave(number=self._wave_number, memory_ids=tuple(members))
