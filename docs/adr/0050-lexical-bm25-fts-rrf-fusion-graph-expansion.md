# ADR-0050: Lexical scoring (BM25 / PostgreSQL FTS), reciprocal rank fusion and one-hop graph expansion for retrieval
Status: Accepted under the autonomous mandate · Date: 2026-10-19 (revised 2026-10-20 after
code review) · Workstream WS-5
Refines ADR-0026 (lexical-first retrieval behind an Embedder contract). Applies ADR-0014's
retrieval clauses unchanged (history depends_on links skipped, snapshot_of links shown).

## Context
ADR-0026 fixed the Retriever contract and deferred the dense model, but left three
choices open that the implementation had to make: how the lexical path scores, how the
lexical and dense candidate lists are combined once an Embedder exists, and how graph
expansion and the I1 visibility rule interact. docs/02 (RAG) asks for validity-aware,
graph-expanded, evidence-cited retrieval; docs/04 measures it by stale retrieval rate.
Two backends must behave alike: an offline one for every unit test and scenario, and
PostgreSQL (ADR-0004, ADR-0016). No pgvector Python package is installed and this
workstream may not add dependencies. The WS-5 brief asked for snapshot_of links to be
skipped in expansion; ADR-0014 (author-approved) and docs/03 say retrieval always shows
them. Docs win over chat (CLAUDE.md), so this ADR follows ADR-0014 and flags the
difference in the handover.

## Decision
1. **Lexical scoring.** The in-memory backend scores BM25 (k1 = 1.5, b = 0.75) over a
   deterministic tokeniser (lowercase, `[a-z0-9]+` with decimals kept whole) applied to
   content plus the structured fact's subject, attribute and value. The Postgres backend
   uses the built-in full-text search: `ts_rank_cd(to_tsvector('english', content),
   plainto_tsquery('english', query))`, with a GIN index on exactly that expression.
   Ties are broken by memory id in both.
2. **Fusion.** When an Embedder is configured the retriever asks the backend for dense
   candidates too and fuses the two ranked lists by reciprocal rank fusion with k = 60.
   `via` records the path that ranked the memory best (ties go to lexical).
3. **Candidates before status.** Backends rank every memory they hold, RETIRED included,
   and never read status. The retriever asks for `4k + 16` candidates, loads them,
   keeps the first k that visibility allows as direct hits, expands the graph, and runs
   `visible_for_retrieval` over the whole result last as the I1 guarantee. Visibility
   is also consulted while choosing seeds and neighbours, so an invisible memory never
   seeds expansion, spends the neighbour budget or appears as evidence.
4. **Graph expansion.** One hop by default, in both link directions, from visible direct
   hits only. depends_on links whose parent is superseded are history (ADR-0014) and are
   skipped; snapshot_of links are followed (ADR-0014: retrieval always shows them), which
   lets an application cite the resume version it was sent with while that version is
   visible; once superseded it is RETIRED and I1 hides it. A neighbour scores half its
   seed's score, carries `via=GRAPH` and the originating direct hit's id in its evidence
   (also across several hops, per the C2 contract comment), and at most k neighbours are
   added per query. `graph_hops` is configurable; `expand_graph=False` turns it off.
5. **Result size.** Up to k direct hits plus up to k neighbours. With k = 1 the parent of
   a derived belief must still be showable, so neighbours are not counted against k.
   The C2 docstring says "top-k"; the handover asks the coordinator to make it explicit.
6. **Schema and module placement.** Migration 0004 adds `embedding vector(1024)`
   (nullable; 1024 is BGE-M3's size, defined once in `ripple.storage.search_schema.
   EMBEDDING_DIMENSIONS` and pinned to the migration's copy by a test), an HNSW cosine
   index on it and the GIN index above. `search_schema` extends the shared table metadata
   with the same objects and a minimal `vector` type so Alembic's drift comparison can
   see them without a pgvector package. The Postgres backend lives in
   `ripple.retrieval.postgres_search`, not in `ripple.storage`, because docs/02 has
   retrieval depending on storage and never the reverse; storage gains only the
   schema extension, which imports core alone.
7. **Errors.** Wrong Embedder dimension and invalid constructor arguments raise
   `ConfigurationError` (ripple.core.errors); a bad per-call argument raises ValueError.

## Alternatives considered
- **TF-IDF instead of BM25** in memory — simpler, but it has no term-frequency saturation,
  so "python python python" would always beat a short exact fact; BM25 is the standard
  lexical baseline the bench will compare against and costs the same twenty lines.
- **Score-level fusion (weighted sum of normalised scores)** — needs per-query
  normalisation and a weight to tune before any retrieval metric exists; RRF has one
  well-studied constant and is robust to the unbounded BM25 scale.
- **Filter status inside the backend SQL / dict scan** — fewer candidates to load, but it
  puts the I1 rule in two more places and makes a backend bug a correctness bug. Rejected;
  oversampling pays a small, bounded cost instead.
- **Skip snapshot_of links in expansion** (the brief's wording) — saves nothing visible,
  since a superseded snapshot parent is hidden by I1 anyway, and silently reverses an
  author-approved ADR. Rejected; if the author prefers it, it is a one-line change plus an
  amendment to ADR-0014.
- **Stored generated tsvector column** instead of an expression index — cleaner queries,
  but Alembic cannot compare the generation expression, so the drift test would be blind
  to it. The expression index compares cleanly after Alembic's normalisation.
- **Index structured values in Postgres too** (`content || structured->>...`) — parity
  with the in-memory tokeniser, but a long expression index that Alembic's string
  comparison would flag as drift. Deferred; the write flow puts values in content.
- **IVFFlat index** — needs training data on an empty table; HNSW builds incrementally.
- **Postgres backend in ripple.storage** (the brief's path) — would make storage import a
  retrieval type, inverting docs/02's dependency table. Rejected in review.
- **Return exactly k items including neighbours** — bounds context better, but with k = 1
  the parent of a derived belief could never be shown.

## Consequences
- The product and the bench run on the lexical path today; the dense path is exercised
  only by the deterministic fake embedder until the Phase 3 embedder ADR.
- Known parity gap: the Postgres lexical path searches content only, the in-memory one
  content plus structured parts. A fact whose value appears only in `structured` is found
  offline and missed on Postgres. Tracked in the WS-5 handover as an open problem.
- A dense backend returns the k nearest memories whatever their similarity, so with an
  embedder a query always fills k direct hits; a similarity floor is a Phase 3 tuning.
- Agents that size prompts for k receive up to 2k rows; WS-4's fake retriever must
  follow the same rule (handover request).
- Forgotten memories must be removed from the in-memory backend explicitly (`remove`);
  the retriever tolerates a stale id with a warning. Postgres has no such state.
- Once `search_schema` is imported, `select(memories)` in PostgresStore fetches the
  1024-float text literal per row; negligible until embeddings are written, but a
  reason for PostgresStore to select explicit columns later (handover note).
- The slow Postgres tests and the Alembic drift test could not run on the author's
  machine (no Docker); they run in CI.

## Revisit if
RippleBench shows the lexical path's recall too low to assess H2 (then the dense path
and the Phase 3 embedder become the priority); the drift test flags the HNSW index's
operator class (then exclude that index by name in the comparison); or the Phase 3
embedder work finds the HNSW scan under a `user_id` filter plus a secondary `ORDER BY id`
returning fewer than k rows or planning badly (pgvector iterative scans, 0.8+, or a
per-user partial index are the known remedies).
