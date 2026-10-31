# ADR-0014: Memory versions are rows; dependency links are copied to the new version
Status: Accepted · Date: 2026-10-19 (approved by the author the same day)

## Context
ADR-0007 keeps history: an update creates a new version. Dependents' links pointed at
the old row, so the next change to the new version would find no dependents and the
graph would silently die after one ripple. Decided with the author in the kickoff
interview; the outgoing-link rule and the "history" definition came from the
architecture-guardian review.

## Decision
Every version is its own Memory row with supersedes_id; there is no supersedes link.
An update, inside one transaction, writes the new row, retires the old one, and:
- copies every **incoming** depends_on link to the new row, so it has the same
  dependents;
- copies every **outgoing** depends_on link to the new row, re-pointed at each parent's
  latest version, so a second change to a parent still reaches the new version even if
  the Linker misses the link; the Linker may add links, never replace these;
- leaves snapshot_of links on the old row, which is how a past application keeps the
  resume version it was sent with.
A link is **history** when its parent is superseded. The inspector and retrieval graph
expansion skip history depends_on links and always show snapshot_of links. The ripple
engine applies no status filter: it traverses from an explicit seed set, and the
dependents of a retired or expired memory are exactly what such a ripple must reach.
Forget deletes a whole version chain, so a copied link never dangles.

## Alternatives considered
- Stable identity (one id across versions, versions in a history table, links always
  reference the stable id) — no copying at all and simpler "latest" queries. The
  collaborator recommended it. Lost because the author prefers one table and explicit
  version rows, and because the copy rule gives snapshot semantics for free.
- Move (re-point) instead of copy — no history on the old row; "what did this belief
  depend on at the time" would need the ChangeEvent instead.
- Leave outgoing links to the Linker only — one missed link silently detaches the new
  version from its parents, the exact failure this ADR exists to prevent; the
  Phase 1 scenario "two consecutive CGPA changes" guards it.
- Overwrite in place — rejected already by ADR-0007.

## Consequences
- Every update is a small graph rewrite; it must be transactional (NFR-4) and is covered
  by a test that fails mid-update and asserts nothing changed.
- "Latest version of X" needs a query on supersedes_id or status.
- Link rows grow with every update; the retention policy noted in ADR-0007 applies.
- The inspector and retrieval filter on "parent superseded"; the in-memory store must
  implement the same filter as Postgres.

## Revisit if
Link-copy bugs appear in the pilot, or update latency exceeds its NFR target; then
supersede with the stable-identity design.
