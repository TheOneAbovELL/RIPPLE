# ADR-0013: Wave-by-wave ripple over core link classes
Status: Accepted · Date: 2026-10-19 (approved by the author the same day)
Amends ADR-0003 (scope is computed per wave and pruned by keep decisions), ADR-0004
(a ripple commits per wave, not as one atomic unit; each update is still atomic) and
the wording of ADR-0007 / I7 (the dependency class along which forget cascades is
named depends_on). Per ADR-0001 the amended ADRs are not edited; the index marks them.

## Context
ADR-0003 says the graph decides scope and the LLM decides action, but left two things
open: how far a ripple travels, and how core can treat domain-specific link types
differently (sent_with_resume must not propagate; eligibility_of must) without importing
domains. FR-6 needs chains of three or more hops; the "correct non-update" case needs a
link that never propagates. Decided with the author in the kickoff interview; the
transaction boundary and the two-class reduction came from the architecture-guardian
review of the first draft.

## Decision
1. **Wave by wave.** The trigger write creates the ChangeEvent. The engine takes an
   explicit seed set (the new version, or the retired memory for expiry and retire) and
   emits wave 1: direct dependents along depends_on links, with no status filter. They
   become SUSPECT and that commits. The Resolver decides for each; the wave's decisions
   and state changes commit as one transaction appended to the ChangeEvent. Only
   memories that were updated or retired seed the next wave; a keep halts its branch;
   an ask parks the memory in PENDING_USER and the engine marks its depends_on subtree
   SUSPECT without resolving it; a later answer that changes the memory starts a new
   ripple (trigger_kind=user_answer), and a "still holds" answer restores the subtree
   deterministically. Stop at an empty wave or the depth limit, then set completed_at;
   a visited set gives cycle safety. The engine is an iterator that takes decisions in
   and gives the next wave out; it never calls an LLM (I3).
2. **Two link classes in core:** depends_on (propagates, copied on update, forget
   cascades) and snapshot_of (never propagates, never copied, forget removes the link).
   Every domain link type maps to exactly one class; the mapping is a domain-adapter
   object applied in the write flow. Core validates only the class.
3. **Forget** applies to a whole version chain and hard-deletes along depends_on links.
   This is what ADR-0007 and I7 call "cascading along derived_from links"; I7's wording
   now names the class.

## Alternatives considered
- Full transitive closure first, then resolve everything — simpler engine, but on a
  chain the LLM re-checks memories whose parent turned out unchanged: more cost and
  more over-correction, which is a measured failure. Lost on both metrics.
- One transaction per ripple — impossible once a wave waits on an LLM call or on a user
  for days; would also make SUSPECT unobservable to retrieval, killing I1's flag.
- Policy registry per link type (each adapter registers flags) — maximally flexible, but
  policy lives in many places and every type is a new combination to test. Lost on
  testability; can be reintroduced later as a mapping to richer classes.
- Separate depends_on and derived_from classes (retire vs delete on forget) — no
  requirement distinguishes them, and retiring a dependent leaves the forgotten value
  inside its content, against ADR-0007's "forget must truly delete".
- Fixed generic types only, no domain types — loses the typed signal the link finder
  (ADR-0009) is trained to predict.

## Consequences
- Each wave is one Resolver round trip; latency grows with chain depth. Acceptable:
  per-user graphs are small (ADR-0004).
- A keep that is wrong stops propagation early; "stale kept" is already a headline
  metric, and the check-everything baseline measures the cost of this pruning.
- A crash between commits leaves SUSPECT rows and an open ChangeEvent (no
  completed_at); the nightly sweep resumes open ChangeEvents older than a configurable
  age.
- While a user has not answered an ask, the whole subtree below it is SUSPECT and
  therefore flagged in retrieval (I1), at zero LLM cost but at the risk of flagging
  memories that would have been kept. The FR-6 acceptance test covers it. The author
  may instead choose to leave the subtree VALID; that is the one line to change.
- Adding a domain type is one line of mapping. Adding a class is an ADR.
- The [human] engine task becomes: implement the iterator, cycle safety and depth limit.

## Revisit if
Chain scenarios in RippleBench show the wave approach misses dependents that
closure-first would catch, or a domain needs a behaviour neither class expresses.
