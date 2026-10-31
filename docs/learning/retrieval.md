# ripple.retrieval — hybrid search, graph expansion, I1 filtering
Written 2026-10-19, revised 2026-10-20, by workstream WS-5 for src/ripple/retrieval and
src/ripple/storage/search_schema.py as built under ADR-0026 and ADR-0050.

## 1. What it does
Answers "what does this user's memory say about X" with a ranked, cited list that never
contains a retired memory and marks every suspect one. It finds candidates lexically
(and densely once an Embedder exists), pulls in the live facts each hit depends on and
the snapshots it was taken with, and filters everything through the one visibility rule
in core.

## 2. Why it exists
docs/02 RAG flow and FR-10: the Conversation and Tailor agents answer from memory with
citations. I1 is the invariant that makes Ripple's consistency work visible: a belief
that a ripple retired must vanish from answers at once, and one still under review must
be shown as such. docs/04's headline retrieval metric, stale retrieval rate, is measured
on exactly this path. ADR-0026 chose lexical-first with the dense model deferred, so the
code had to make the dense path pluggable without depending on a model. ADR-0014 fixes
what graph expansion may follow.

## 3. How it works
- `backend.SearchBackend` (protocol): `lexical(user_id, query, k)`, `dense(user_id,
  vector, k)`, `index(memory, embedding)`. Returns `SearchHit(memory_id, score)` lists,
  best first. Backends do not know about status.
- `inmemory_search.InMemorySearchBackend`: BM25 over `text.tokenise(searchable_text(m))`
  per user, cosine over a dict of vectors. `remove(id)` for forget. Fully deterministic,
  ties by id.
- `postgres_search.PostgresSearchBackend`: the memories table is the index.
  Lexical = `ts_rank_cd(to_tsvector('english', content), plainto_tsquery(...))` filtered by
  `@@`; dense = `embedding <=> CAST(:vec AS vector)` ascending, score = 1 − distance
  (the operator is declared Float so `1 - distance` does not bind the 1 as a vector).
  `index` runs `UPDATE memories SET embedding = ...` on the committed row. It lives in
  retrieval, importing storage, because that is the dependency direction docs/02 allows.
- `ripple.storage.search_schema`: `EMBEDDING_DIMENSIONS = 1024`, a minimal SQLAlchemy
  `Vector` type (DDL, reflection registration, text-literal binding) and the in-place
  extension of `tables.memories` with the embedding column and both indexes, mirroring
  migration 0004. Imports core and storage only.
- `fusion.reciprocal_rank_fusion`: score = Σ 1 / (60 + rank) over the lists an item
  appears in; `via` = the path that ranked it best.
- `hybrid.HybridRetriever.search` (the C2 `Retriever`):
  1. empty query → `[]`; `k < 1` → ValueError (constructor misuse → ConfigurationError);
  2. backend lexical (+ dense via `embedder.embed([query])`) for `4k + 16` candidates,
     fused;
  3. load candidates in one `get_memories` call (per-id fallback that logs and skips a
     missing row), keep the first k that pass visibility as direct hits;
  4. expand `graph_hops` hops from those seeds: `parents_of` (depends_on only if the
     parent is its own latest version, memoised per search; snapshot_of always) and
     `dependents_of` (the seed is the parent and visible, hence live); a neighbour is
     collected only if visible, ≤ k neighbours in total, score = seed × 0.5, `via=GRAPH`,
     evidence = (source_ref?, originating direct hit id);
  5. sort by (−score, id), run `visible_for_retrieval(..., include_flagged)` over all of it
     last, return `RetrievedMemory` items with the flag.
- `indexing.index_memory(backend, embedder | None, memory)`: embeds `searchable_text` and
  calls `backend.index`. `tests/fakes/embedder.DeterministicFakeEmbedder` hashes tokens
  into unit vectors so tests exercise the dense path without a model.
- Migration `0004_embeddings` (down_revision 0003): `ALTER TABLE memories ADD COLUMN
  embedding vector(1024)`, HNSW cosine index, GIN expression index. Constants are copied,
  not imported, and a test pins them to `search_schema`.

## 4. Trade-offs
- Status is read in one function, after everything else, and consulted earlier only to
  choose seeds and neighbours. Price: oversampling and loading candidates the filter will
  drop. Gain: a backend can only lose recall, never leak.
- Rank fusion over score fusion: nothing to calibrate before a metric exists.
- Half-score damping for neighbours is a heuristic, not a learned weight; it only has to
  keep neighbours below their seed and ordered by seed quality.
- Up to k direct hits plus up to k neighbours, not k in total: a parent must be showable
  even at k = 1; the agents must size prompts for 2k.
- Postgres lexical over content only (indexable, drift-checkable) versus in-memory over
  content + structured parts: a known parity gap, documented in ADR-0050.
- No pgvector Python package: the `Vector` type is twenty lines and a text literal; the
  cost is reimplementing what the package would give for free if Phase 3 adds it.

## 5. Failure modes and tests
| Failure | Test |
|---|---|
| RETIRED leaks or SUSPECT unflagged via any path | tests/retrieval/test_invariants.py::test_invariant_I1_retriever_never_returns_retired_and_flags_suspect; test_search_hides_flagged_memories_unless_asked_and_then_flags_them; test_search_graph_neighbour_that_is_retired_is_never_shown |
| Expansion follows a history link | test_search_graph_expansion_skips_history_links_even_when_their_parent_is_visible (an artificially VALID superseded parent, since versioning retires one) |
| Expansion ignores snapshot_of (ADR-0014) | test_search_graph_expansion_follows_snapshot_links_to_a_visible_parent; …_hides_a_superseded_snapshot_parent |
| Invisible neighbours eat the budget or seed hop 2 | test_search_invisible_neighbours_do_not_spend_the_neighbour_budget; …_do_not_seed_the_next_hop |
| Retired candidates starve valid ones | test_search_oversamples_so_retired_top_matches_do_not_starve_valid_ones |
| Stale in-memory index entry crashes a search | test_search_tolerates_an_index_entry_whose_memory_was_forgotten |
| Hop-2 result cites the hop, not the direct hit | test_search_graph_hops_two_reaches_the_grandchild_citing_the_direct_hit |
| Non-deterministic order | test_search_ordering_is_deterministic_across_runs, test_lexical_breaks_ties_by_memory_id |
| Fusion favours one list's scale / not really fused | tests/retrieval/test_fusion.py; test_search_with_embedder_fuses_dense_and_lexical_ranks (asserts the 2/(k+1) score only both lists can produce) |
| Migration and code constants drift; functional index silently detached | tests/retrieval/test_migration_0004.py |
| Postgres SQL wrong | tests/retrieval/test_postgres_search.py (slow; CI) |

## 6. Interview questions
1. *Where is status checked?* `visible_for_retrieval`, called last as the guarantee, and
   the same function to pick seeds and neighbours; backends and fusion never see it.
2. *Why ask the backend for more than k?* It ranks retired versions too; k candidates
   could all be filtered away.
3. *How do you avoid showing the superseded CGPA when expanding from an eligibility
   belief?* A depends_on link whose parent is not its own latest version is history
   (ADR-0014) and is skipped; and the old version is RETIRED anyway.
4. *Why follow snapshot_of links at all?* ADR-0014: an application should be able to cite
   the resume version it was sent with; when that version is superseded I1 hides it.
5. *Why RRF?* BM25 and cosine are on different scales; rank fusion needs no calibration.
6. *Why is the Postgres backend not in ripple.storage?* It needs the retrieval `SearchHit`
   type; docs/02 lets retrieval import storage, never the reverse.

## 7. Exercise
Write a scenario: fact cgpa v1 → eligibility depends on it → cgpa v2 written (links copied
per ADR-0014). Query "eligible" with and without `include_flagged` while eligibility is
SUSPECT mid-ripple, and predict every `via`, `flagged` and `evidence` before running.
