# Related work and positioning
Checked 2026-10-19. Re-check arXiv monthly; add new work as a baseline, not a blocker.

| Work | What it does | What it leaves open | Ripple |
|---|---|---|---|
| [PACMI](https://arxiv.org/abs/2610.05732v1) (Oct 2026) | Provenance graph, typed edges, cascading invalidation | Edges given by annotation; small benchmark | C1 infers edges; C2 larger, action-level |
| [MemTX](https://arxiv.org/html/2607.23929v2) | Transactional belief commit, typed cascading repair | — | Transactional commit idea; compare if code available |
| [Is agent memory a database? (GEM)](https://arxiv.org/html/2605.26252v1) | Defines dependency consistency for memory | Position/systems paper | Our invariants follow its spirit |
| [Rollback repair](https://arxiv.org/pdf/2608.10502) | Dependency-guided repair of faulty memories | Inferring edges from raw text out of scope | C1 |
| [Zep / Graphiti](https://arxiv.org/abs/2501.13956) | Bi-temporal graph; invalidates contradicted edges | Direct contradictions, not cascades | Baseline candidate |
| [STALE](https://arxiv.org/abs/2605.06527v1) | Benchmark of implicit memory conflicts | — | External benchmark |
| [RECON](https://arxiv.org/pdf/2607.16716) | Benchmark incl. cascade propagation questions | — | Possible external benchmark |
| [Nous](https://www.sota2.com/research/paper/6a3a132f206542251d7c717d) | Bayesian belief memory; F1 vs judge gap | — | Report both metrics |
| ChatGPT memory (Dreaming, June 2026) | Background memory updates to reduce staleness | Mechanism unpublished | Motivation; not comparable |

Positioning sentence: "Recent work showed cascading invalidation helps but assumed
hand-annotated dependency links at small scale. Ripple learns those links from raw
memories and shows, in a deployed agent, that cascades change actions."
