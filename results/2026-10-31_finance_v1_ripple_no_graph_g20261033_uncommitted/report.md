# finance_v1 suite, strategy ripple, ablation no_graph, generator seed 20261033 — 2026-10-31T09:35:45.952708+00:00

Scenarios passed: 30/35 runnable (0 not runnable) · checks failed: 5/175 · errors: 0 · resolver calls: 136 · LLM calls: 0 (scripted oracle resolver).

Memory metrics over 35 runnable scenarios (0 not runnable, left out) (bench/metrics.py; pooled, ADR-0120): update accuracy 95.1% · stale kept per scenario 0.14 · wrongful changes per scenario 0.00 · questions asked per scenario 0.14 (needed 0.14) · stale retrieval 0.0% · stale recommendations n/a · never consistent 4.9% · resolver calls per ripple 3.02 · tokens and USD per ripple: n/a (no LLM).

Data: synthetic — generated in memory by bench.generate_finance with seeds.generator_seed; the first seed reproduces bench/data/finance_v1 (checked against its manifest), data sha256 183c3f95127fc7e65f13c4863c4c47f57823a399ae65fe6069d73a9274fa9c4d; invented names, places and companies, no real story or company described

| scenario | runnable | passed | checks failed | resolver calls | problems |
|---|---|---|---|---|---|
| guidance_cut__f0_bela | yes | yes | 0/6 | 4 | - |
| peer_margin__f0_bela | yes | yes | 0/4 | 4 | - |
| trading_halt__f0_bela | yes | yes | 0/8 | 6 | - |
| ceo_departure__f0_bela | yes | yes | 0/5 | 5 | - |
| rate_edge__f0_bela | yes | no | 1/4 | 4 | alert: status VALID, expected SUSPECT |
| journal_entry__f0_bela | yes | yes | 0/3 | 2 | - |
| forget_holding__f0_bela | yes | yes | 0/5 | 3 | - |
| guidance_cut__f1_divya | yes | yes | 0/6 | 4 | - |
| peer_margin__f1_divya | yes | yes | 0/4 | 4 | - |
| trading_halt__f1_divya | yes | yes | 0/8 | 6 | - |
| ceo_departure__f1_divya | yes | yes | 0/5 | 5 | - |
| rate_edge__f1_divya | yes | no | 1/4 | 2 | alert: status VALID, expected SUSPECT |
| journal_entry__f1_divya | yes | yes | 0/3 | 2 | - |
| forget_holding__f1_divya | yes | yes | 0/5 | 3 | - |
| guidance_cut__f2_zoya | yes | yes | 0/6 | 4 | - |
| peer_margin__f2_zoya | yes | yes | 0/4 | 4 | - |
| trading_halt__f2_zoya | yes | yes | 0/8 | 6 | - |
| ceo_departure__f2_zoya | yes | yes | 0/5 | 5 | - |
| rate_edge__f2_zoya | yes | no | 1/4 | 2 | alert: status VALID, expected SUSPECT |
| journal_entry__f2_zoya | yes | yes | 0/3 | 2 | - |
| forget_holding__f2_zoya | yes | yes | 0/5 | 3 | - |
| guidance_cut__f3_uma | yes | yes | 0/6 | 4 | - |
| peer_margin__f3_uma | yes | yes | 0/4 | 4 | - |
| trading_halt__f3_uma | yes | yes | 0/8 | 6 | - |
| ceo_departure__f3_uma | yes | yes | 0/5 | 5 | - |
| rate_edge__f3_uma | yes | no | 1/4 | 4 | alert: status VALID, expected SUSPECT |
| journal_entry__f3_uma | yes | yes | 0/3 | 2 | - |
| forget_holding__f3_uma | yes | yes | 0/5 | 3 | - |
| guidance_cut__f4_yamini | yes | yes | 0/6 | 4 | - |
| peer_margin__f4_yamini | yes | yes | 0/4 | 4 | - |
| trading_halt__f4_yamini | yes | yes | 0/8 | 6 | - |
| ceo_departure__f4_yamini | yes | yes | 0/5 | 5 | - |
| rate_edge__f4_yamini | yes | no | 1/4 | 4 | alert: status VALID, expected SUSPECT |
| journal_entry__f4_yamini | yes | yes | 0/3 | 2 | - |
| forget_holding__f4_yamini | yes | yes | 0/5 | 3 | - |
