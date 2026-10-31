# news_v1 suite, strategy ripple, ablation no_ask_user, generator seed 20261032 — 2026-10-31T09:35:29.514931+00:00

Scenarios passed: 18/20 runnable (0 not runnable) · checks failed: 6/103 · errors: 2 · resolver calls: 41 · LLM calls: 0 (scripted oracle resolver).

Memory metrics over 20 runnable scenarios (0 not runnable, left out) (bench/metrics.py; pooled, ADR-0120): update accuracy 90.2% · stale kept per scenario 0.30 · wrongful changes per scenario 0.00 · questions asked per scenario 0.00 (needed 0.10) · stale retrieval 1.2% · stale recommendations n/a · never consistent 9.8% · resolver calls per ripple 1.86 · tokens and USD per ripple: n/a (no LLM).

Data: synthetic — generated in memory by bench.generate_news with seeds.generator_seed; the first seed reproduces bench/data/news_v1 (checked against its manifest), data sha256 e9ca624c82f7ef711c9447a8162cda54278b8b64d922b50147ee593fafb6ef8f; invented names, places and companies, no real story or company described

| scenario | runnable | passed | checks failed | resolver calls | problems |
|---|---|---|---|---|---|
| figure_revised__n0_sana | yes | yes | 0/6 | 2 | - |
| other_story_develops__n0_sana | yes | yes | 0/4 | 1 | - |
| road_closure__n0_sana | yes | yes | 0/8 | 4 | - |
| attribution_retracted__n0_sana | yes | yes | 0/5 | 3 | - |
| conflicting_reports__n0_sana | yes | no | 4/4 | 1 | answer:summary: memory 'summary' is VALID, not PENDING_USER; summary: status VALID, expected PENDING_USER; briefing: status VALID, expected SUSPECT; summary: status VALID, expected RETIRED; briefing@latest: content 'briefing: Duncliff bridge collapse: 203 people injured', expected 'briefing: Duncliff bridge collapse, figure disputed'; briefing@latest: version 1, expected 2 |
| shared_note__n0_sana | yes | yes | 0/3 | 1 | - |
| forget_story__n0_sana | yes | yes | 0/5 | 1 | - |
| figure_revised__n1_tara | yes | yes | 0/6 | 2 | - |
| attribution_retracted__n1_tara | yes | yes | 0/5 | 3 | - |
| figure_revised__n2_nikhil | yes | yes | 0/6 | 2 | - |
| other_story_develops__n2_nikhil | yes | yes | 0/4 | 1 | - |
| road_closure__n2_nikhil | yes | yes | 0/8 | 4 | - |
| attribution_retracted__n2_nikhil | yes | yes | 0/5 | 3 | - |
| conflicting_reports__n2_nikhil | yes | no | 2/4 | 1 | answer:summary: memory 'summary' is VALID, not PENDING_USER; summary: status VALID, expected PENDING_USER; briefing: status VALID, expected SUSPECT |
| shared_note__n2_nikhil | yes | yes | 0/3 | 1 | - |
| forget_story__n2_nikhil | yes | yes | 0/5 | 1 | - |
| figure_revised__n3_meera | yes | yes | 0/6 | 2 | - |
| attribution_retracted__n3_meera | yes | yes | 0/5 | 3 | - |
| figure_revised__n4_ravi | yes | yes | 0/6 | 2 | - |
| attribution_retracted__n4_ravi | yes | yes | 0/5 | 3 | - |
