# news_v1 suite, strategy ripple, ablation no_graph, generator seed 20261032 — 2026-10-31T09:35:27.606535+00:00

Scenarios passed: 18/20 runnable (0 not runnable) · checks failed: 2/103 · errors: 0 · resolver calls: 81 · LLM calls: 0 (scripted oracle resolver).

Memory metrics over 20 runnable scenarios (0 not runnable, left out) (bench/metrics.py; pooled, ADR-0120): update accuracy 96.8% · stale kept per scenario 0.10 · wrongful changes per scenario 0.00 · questions asked per scenario 0.10 (needed 0.10) · stale retrieval 0.0% · stale recommendations n/a · never consistent 3.2% · resolver calls per ripple 3.38 · tokens and USD per ripple: n/a (no LLM).

Data: synthetic — generated in memory by bench.generate_news with seeds.generator_seed; the first seed reproduces bench/data/news_v1 (checked against its manifest), data sha256 e9ca624c82f7ef711c9447a8162cda54278b8b64d922b50147ee593fafb6ef8f; invented names, places and companies, no real story or company described

| scenario | runnable | passed | checks failed | resolver calls | problems |
|---|---|---|---|---|---|
| figure_revised__n0_sana | yes | yes | 0/6 | 4 | - |
| other_story_develops__n0_sana | yes | yes | 0/4 | 4 | - |
| road_closure__n0_sana | yes | yes | 0/8 | 6 | - |
| attribution_retracted__n0_sana | yes | yes | 0/5 | 5 | - |
| conflicting_reports__n0_sana | yes | no | 1/4 | 4 | briefing: status VALID, expected SUSPECT |
| shared_note__n0_sana | yes | yes | 0/3 | 2 | - |
| forget_story__n0_sana | yes | yes | 0/5 | 3 | - |
| figure_revised__n1_tara | yes | yes | 0/6 | 4 | - |
| attribution_retracted__n1_tara | yes | yes | 0/5 | 5 | - |
| figure_revised__n2_nikhil | yes | yes | 0/6 | 4 | - |
| other_story_develops__n2_nikhil | yes | yes | 0/4 | 4 | - |
| road_closure__n2_nikhil | yes | yes | 0/8 | 6 | - |
| attribution_retracted__n2_nikhil | yes | yes | 0/5 | 5 | - |
| conflicting_reports__n2_nikhil | yes | no | 1/4 | 2 | briefing: status VALID, expected SUSPECT |
| shared_note__n2_nikhil | yes | yes | 0/3 | 2 | - |
| forget_story__n2_nikhil | yes | yes | 0/5 | 3 | - |
| figure_revised__n3_meera | yes | yes | 0/6 | 4 | - |
| attribution_retracted__n3_meera | yes | yes | 0/5 | 5 | - |
| figure_revised__n4_ravi | yes | yes | 0/6 | 4 | - |
| attribution_retracted__n4_ravi | yes | yes | 0/5 | 5 | - |
