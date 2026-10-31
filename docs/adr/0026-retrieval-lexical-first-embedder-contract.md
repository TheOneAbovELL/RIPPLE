# ADR-0026: Retrieval is lexical-first behind an Embedder contract; dense model decided at integration
Status: Accepted · Date: 2026-10-19 (under the autonomous mandate)

## Context
docs/02 asks for validity-aware hybrid retrieval with graph expansion and evidence
citations (I1, FR-10). The proposal names BGE-M3. Running BGE-M3 locally means
PyTorch and a multi-gigabyte download on the author's Windows machine, which has no
GPU, and a pinned model version per eval run (NFR-5).

## Decision
1. `ripple.core.retrieval_contract` fixes the interface: `Retriever.search` returns
   `RetrievedMemory` items that passed `visible_for_retrieval`; `Embedder` is the
   dense-vector provider.
2. `ripple.retrieval` ships now with a lexical path (PostgreSQL full-text search in the
   Postgres store, a tokenised scorer in the in-memory store), graph expansion of one
   hop, evidence refs, and the dense path wired to any `Embedder`. The pgvector column
   lands in migration 0004 with a configurable dimension.
3. The production Embedder is chosen at the Phase 3 integration checkpoint after a
   measured comparison on RippleBench v0 of (a) BGE-M3 via sentence-transformers,
   (b) a hosted embedding API through the Router's provider. Until then tests use a
   deterministic fake embedder and the lexical path carries the product.

## Alternatives considered
- Decide BGE-M3 now and add torch — commits gigabytes before any retrieval metric
  exists; lost on evidence.
- Hosted embeddings only — cheapest to start, but a vendor dependency for the one
  component that should be reproducible offline. Kept as candidate (b).
- Dense only, no lexical — exact tokens (company names, skill names) matter in this
  domain; hybrid is the standard and the lexical half is free.

## Consequences
- Stale retrieval rate (H2) can be measured on the lexical path immediately.
- The Embedder decision gets its own ADR with the numbers that justified it.

## Revisit if
The lexical path's recall on the jobs track is so low that H2 cannot be assessed
without dense retrieval.
