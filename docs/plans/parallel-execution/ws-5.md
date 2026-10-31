# WS-5 handover — Retrieval: lexical, dense wiring, graph expansion, evidence
Session of 2026-10-19/20. Status: **Locally verified** (offline); Postgres backend and
migration 0004 are **integration blocked** (no database on the author's machine; CI).

## What was built
- `SearchBackend` protocol + `SearchHit` (src/ripple/retrieval/backend.py).
- `InMemorySearchBackend`: BM25 over content + structured parts, cosine over a vector
  dict, `remove()` for forget (src/ripple/retrieval/inmemory_search.py).
- `PostgresSearchBackend`: PostgreSQL FTS (`ts_rank_cd`, `plainto_tsquery`, GIN
  expression index) and pgvector cosine (`<=>`, HNSW)
  (src/ripple/retrieval/postgres_search.py; see "Deviations from the brief").
- `ripple.storage.search_schema`: `EMBEDDING_DIMENSIONS = 1024`, a minimal `Vector`
  type, and the in-place extension of `tables.memories` metadata with the column and
  both indexes so the Alembic drift test can compare them. Imports core and storage only.
- `HybridRetriever(store, backend, embedder=None, *, k=10, graph_hops=1)` implementing
  the C2 `Retriever`: lexical (+ dense) candidates, reciprocal rank fusion, graph
  expansion along depends_on (history links skipped) and snapshot_of (ADR-0014),
  neighbours pre-filtered for visibility, `visible_for_retrieval` applied last,
  deterministic order (src/ripple/retrieval/hybrid.py, fusion.py).
- `index_memory(backend, embedder, memory)` and `DeterministicFakeEmbedder`
  (src/ripple/retrieval/indexing.py, tests/fakes/embedder.py).
- Migration `0004_embeddings` (down_revision "0003"): `embedding vector(1024)` nullable,
  `ix_memories_embedding_hnsw` (vector_cosine_ops), `ix_memories_content_fts`
  (GIN on `to_tsvector('english', content)`).
- ADR-0050 (docs/adr/0050-lexical-bm25-fts-rrf-fusion-graph-expansion.md),
  docs/learning/retrieval.md.

## Deviations from the brief (each recorded in ADR-0050)
1. **snapshot_of links are followed, not skipped.** The brief said skip; ADR-0014
   (author-approved) and docs/03 line 112-114 say retrieval always shows them. Docs win
   over chat. Effect: an application can cite the resume version it was sent with while
   that version is visible; once superseded it is RETIRED and hidden by I1. If the
   author wants the brief's behaviour, it is a one-line change in `_linked_ids` plus an
   amendment to ADR-0014.
2. **The Postgres backend is `ripple.retrieval.postgres_search`, not
   `ripple.storage.search`.** It needs the retrieval `SearchHit` type, and docs/02 has
   retrieval depending on storage, never the reverse (raised by the code reviewer).
   `src/ripple/storage/search_schema.py` is the only new storage module.
3. `EMBEDDING_DIMENSIONS` lives in `ripple.storage.search_schema` (a schema fact), not
   in the retrieval package.

## Files (all new; nothing outside WS-5 ownership touched)
| Purpose | Files |
|---|---|
| Retrieval package | src/ripple/retrieval/{__init__,backend,text,fusion,inmemory_search,indexing,hybrid,postgres_search}.py |
| Schema extension | src/ripple/storage/search_schema.py |
| Migration | infra/migrations/versions/0004_embeddings.py |
| Test fake | tests/fakes/embedder.py |
| Tests | tests/retrieval/{__init__,conftest,test_inmemory_search,test_fusion,test_fake_embedder,test_indexing,test_hybrid_retriever,test_invariants,test_migration_0004,test_postgres_search}.py |
| Records | docs/adr/0050-…md, docs/learning/retrieval.md, this file |

## Verification (real output, 2026-10-20, after the review fixes)
```
$ uv run ruff check <paths>
All checks passed!

$ uv run ruff format --check <paths>
21 files already formatted

$ uv run pyright <paths>
0 errors, 0 warnings, 0 informations

$ uv run pytest tests/retrieval -q
SKIPPED [10] tests\retrieval\test_postgres_search.py: TEST_DATABASE_URL/DATABASE_URL not set
66 passed, 10 skipped in 2.45s
```
`<paths>` = src/ripple/retrieval src/ripple/storage/search_schema.py
infra/migrations/versions/0004_embeddings.py tests/retrieval tests/fakes/embedder.py.
tests/core/test_boundaries.py and test_visibility.py were also run: 8 passed.

Not run here: the ten slow Postgres tests, `alembic upgrade head` with 0004, and
tests/storage/test_postgres_store.py::test_migrations_match_table_metadata against the
extended metadata. The SQL the backend emits and the DDL the extended metadata renders
were compiled with the PostgreSQL dialect and compared against the migration by eye
(they match: `CREATE INDEX ix_memories_content_fts ON memories USING gin
(to_tsvector('english', content))`, `... USING hnsw (embedding vector_cosine_ops)`,
`embedding vector(1024)`). That check caught a real bug: `1 - (embedding <=> probe)`
bound the `1` as a vector until the operator was declared `return_type=Float`.

## Review (code-reviewer subagent, 2026-10-20)
Verdict: no I1 leak, I3 untouched, BM25/RRF correct, ordering deterministic. Findings
and what was done:
- B1 snapshot_of skip silently reversed ADR-0014 → **fixed**: links followed; ADR-0050
  records it (deviation 1).
- B2 Postgres end-to-end test could not pass with an embedder (dense returns every row,
  so the neighbour arrives as a direct hit) → **fixed**: GRAPH asserted without an
  embedder; the embedder variant asserts I1 only.
- M1 invisible neighbours consumed the budget and seeded hop 2 → **fixed** with a
  visibility pre-filter and two new tests.
- M2 the history and snapshot tests passed without the code they covered → **fixed**:
  history test uses an artificially VALID superseded parent; snapshot test uses a VALID
  snapshot parent.
- M3 storage imported retrieval → **fixed** (deviation 2 and 3).
- M4 Alembic env.py and the drift test do not import `search_schema` → coordinator
  request 1 below.
- M5 result size (k direct + k neighbours) invisible to WS-4 → coordinator request 3.
- Minor: `_Collected` dataclass instead of tuples, memoised liveness and one
  `get_memories` call per search, evidence cites the originating direct hit across
  hops, `ConfigurationError` for configuration mistakes, `_table=` guard test, fusion
  test now proves fusion (score 2/(k+1)), multi-behaviour tests split, HNSW caveat in
  ADR "Revisit if" — all **done**. Not done: nothing from the review is outstanding.

## Contract change requests (coordinator)
1. **Drift test and Alembic env must see the extended metadata.** Both
   tests/storage/test_postgres_store.py and infra/migrations/env.py use `Base.metadata`
   without importing `ripple.storage.search_schema`; after migration 0004 the drift test
   reports the embedding column and two indexes unless something imported it first (in
   one pytest session, collecting tests/retrieval happens to do so, which is luck), and
   `alembic revision --autogenerate` would propose dropping them. Request: one line
   `import ripple.storage.search_schema  # noqa: F401` in `src/ripple/storage/__init__.py`
   (covers both). If CI then reports `ix_memories_embedding_hnsw` as drift (operator
   class comparison is the one piece I could not verify by reading), exclude that index
   by name via `include_object` in the drift test.
2. **Where indexing is called.** `index_memory` must run after the memory row is
   committed (Postgres `UPDATE` on the row); the write flow (`ripple.core.writes` /
   intake) does not call it yet, and forget should call `InMemorySearchBackend.remove`.
   Suggest: the write flow takes an optional `SearchBackend`/`Embedder` pair or emits a
   post-commit hook; WS-4 agents construct `HybridRetriever(store, backend, embedder)`.
3. **C2 docstring and WS-4's fake.** `Retriever.search` says "Top-k visible memories";
   the implementation returns up to k direct hits plus up to k one-hop neighbours
   (ADR-0050 §5). Request: say so in the docstring and ask WS-4 to make
   `tests/fakes/retriever.py` follow the same rule, or cap total rows in the agents.
4. **Search signature.** `HybridRetriever.search` accepts `k: int | None = None`
   (None = the constructor's k), a widening of the protocol's `k: int = 10`; pyright
   accepts it. If preferred, widen the protocol to match.
5. **docs/03 wording check.** docs/03 line 112-114 already matches what was built; no
   change needed unless the author chooses the brief's snapshot behaviour (deviation 1).
6. **Migration chain.** 0004 declares `down_revision = "0003"`; WS-3's 0003_users must
   exist before `alembic upgrade head` runs.

## Open problems
- Parity gap: Postgres FTS indexes `content` only; in-memory BM25 also indexes the
  structured subject/attribute/value (ADR-0050 explains why). A value that is only in
  `structured` is found offline and missed on Postgres.
- The dense path returns the k nearest memories regardless of similarity (as any ANN
  index does); a similarity floor is a Phase 3 tuning once a real Embedder exists.
- `PostgresSearchBackend.index` opens its own transaction; it is not atomic with the
  memory write it follows (see request 2).
- Once `search_schema` is imported, `PostgresStore`'s `select(memories)` fetches the
  1024-float text literal per row (Pydantic ignores the extra key). Negligible until
  embeddings exist; PostgresStore could select explicit columns (coordinator-owned).
- HNSW requires pgvector ≥ 0.5 (compose image pgvector/pgvector:pg17 has it); CI's
  Postgres service must use the same image. HNSW under a `user_id` filter is unverified
  under load (ADR-0050 "Revisit if").

## Suggested commit message
retrieval: hybrid retriever, in-memory and Postgres search backends, migration 0004 — implements the C2 Retriever (ADR-0026) with BM25/FTS, RRF fusion, ADR-0014 graph expansion and I1 filtering last (ADR-0050)
