# ripple.core.engine — the ripple engine
Written 2026-10-19 as the author's recipe; updated 2026-10-31 when the collaborator
implemented `WaveEngine` on the author's request. Sections 3–6 describe the code as it
now is; section 7's exercise still works as a way to re-derive it: delete the two method
bodies and rebuild them against tests/core/test_engine.py.

The implementation in one paragraph: `first_wave` marks the seeds visited, collects
their unvisited dependents in first-seen order and emits them as wave 1. `next_wave`
keeps only changed outcomes, uses each one's `frontier_id` (the successor version for
an update), marks those visited, and collects their unvisited dependents. `_emit`
returns None for an empty wave and, when a non-empty wave would exceed `max_depth`,
sets `truncated` and returns None, so truncation is reported only when work is cut off.

## 1. What it does
Given a snapshot of the dependency graph and the memories that just changed, the engine
says which memories must be re-examined next, one wave at a time. It never decides what
happens to them; that is the Resolver's job. It never does I/O and never calls an LLM.

## 2. Why it exists
ADR-0003: the graph decides scope, the LLM decides action. ADR-0013: scope is computed
wave by wave, and a `keep` halts its branch, so a chain only costs LLM calls as far as
it actually changes. I3 is the invariant: this module must not call an LLM, and
tests/core/test_boundaries.py plus test_invariants.py enforce that it cannot import one.

## 3. How it works (what you implement)
- `DependencyGraph.from_links(links)` keeps only links whose class propagates
  (depends_on, not snapshot_of) and maps parent id to a tuple of dependent ids in link
  creation order. `dependents(id)` and `descendants(id)` are yours to call.
- `first_wave(graph, seeds)`: collect the affected set (everything reachable from the
  seeds along propagating links, seeds excluded) and give each member a level, the
  longest path to it from a seed (Kahn's order; a cycle is broken in discovery order).
  Members whose parent changed are *due*; the seeds' dependents are due from the start.
  Wave 1 is the due members of the lowest level. Return None when nothing is due.
- `next_wave(graph, outcomes)`: record the outcomes; a `changed=True` outcome (update or
  retire) makes the dependents of its `memory_id` and its `frontier_id` (the new
  version, which carries the copied links) due. A keep or ask changes nothing, so it
  halts only its own branch. The next wave is the lowest level with a due, unresolved
  member; each memory is emitted at most once. Wave numbers count emitted waves; past
  `max_depth`, set `truncated=True` and return None (ADR-0119 amends ADR-0013).
- The runner calls you like this: `wave = engine.first_wave(graph, [trigger.id])`,
  then after each resolution round `wave = engine.next_wave(fresh_graph, outcomes)`.
  The graph is rebuilt from the store between waves because updates add links.

## 4. Trade-offs you should be able to argue
- Wave-by-wave versus full closure: closure is simpler to write but re-checks memories
  whose parent turned out unchanged, costing LLM calls and causing over-correction.
- Resolve once, after every affected parent (ADR-0119): the engine levels the whole
  affected set by longest path from the trigger, so a memory reached both directly and
  through another affected memory (cgpa -> eligibility -> recommendation, plus
  cgpa -> recommendation) waits until the eligibility is decided. The first version
  emitted it in wave 1 beside the eligibility and could decide it against the
  eligibility's old value; a code review found the case on 2026-10-31. Each memory is
  still resolved at most once, which is also why cycles terminate.
- Depth limit: a safety net, not a design parameter; a truncated ripple is logged and
  shows up as "stale kept" in the bench, which is the honest place for it.
- Why the graph is rebuilt per wave rather than patched: simplicity and correctness;
  per-user graphs are small (ADR-0004).

## 5. Failure modes and tests
Every rule has one test in tests/core/test_engine.py: level-ordered waves (a memory
waits for every affected parent; a keep halts only its own branch; an empty level is
skipped), no seeds in a wave, keep halts, successor
followed after update, no revisits, cycles terminate, depth limit sets `truncated`,
determinism. Then the eleven scenarios in tests/scenarios/*.yaml run end to end, and
`uv run python -m bench.run --suite smoke` reports them in results/.

## 6. Interview questions
1. *Why is the engine pure and synchronous?* Determinism and testability: same graph,
   same outcomes, same wave, with no clock or network to mock.
2. *How does an update's new version get into the next wave?* Through
   `WaveOutcome.successor_id`; versioning copied the old version's dependents to it.
3. *What stops an infinite loop on a cycle?* The visited set: a memory is emitted once
   per ripple.
4. *What does the engine do with an `ask`?* Nothing: it is `changed=False`, so the
   branch halts; the runner separately marks the subtree SUSPECT using `descendants`.
5. *What is I3 and how is it enforced?* The engine never calls an LLM; a boundary test
   forbids any import of ripple.llm in core and an invariant test checks the engine
   object holds no client.

## 7. Exercise
Implement `first_wave` only, run `uv run pytest tests/core/test_engine.py -q`, and watch
exactly three tests flip from xfail to XPASS (and fail the suite because the marker is
strict). Remove the marker from those three, then implement `next_wave`.
