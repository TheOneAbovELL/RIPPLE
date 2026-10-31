# news_v1 suite, strategy check_everything, generator seed 20261031 — 2026-10-31T09:35:16.045881+00:00

Scenarios passed: 18/20 runnable (0 not runnable) · checks failed: 2/97 · errors: 0 · resolver calls: 77 · LLM calls: 0 (scripted oracle resolver).

Memory metrics over 20 runnable scenarios (0 not runnable, left out) (bench/metrics.py; pooled, ADR-0120): update accuracy 96.3% · stale kept per scenario 0.10 · wrongful changes per scenario 0.00 · questions asked per scenario 0.10 (needed 0.10) · stale retrieval 0.0% · stale recommendations n/a · never consistent 3.7% · resolver calls per ripple 3.21 · tokens and USD per ripple: n/a (no LLM).

Data: synthetic — generated in memory by bench.generate_news with seeds.generator_seed; the first seed reproduces bench/data/news_v1 (checked against its manifest), data sha256 d9b473dfcb246332962da836a3c528c835e75da15945ff769af8e56ffebfa2d1; invented names, places and companies, no real story or company described

| scenario | runnable | passed | checks failed | resolver calls | problems |
|---|---|---|---|---|---|
| other_story_develops__n0_meera | yes | yes | 0/4 | 4 | - |
| forget_story__n0_meera | yes | yes | 0/5 | 3 | - |
| figure_revised__n1_nikhil | yes | yes | 0/6 | 4 | - |
| other_story_develops__n1_nikhil | yes | yes | 0/4 | 4 | - |
| road_closure__n1_nikhil | yes | yes | 0/8 | 6 | - |
| attribution_retracted__n1_nikhil | yes | yes | 0/5 | 5 | - |
| conflicting_reports__n1_nikhil | yes | no | 1/4 | 4 | briefing: status VALID, expected SUSPECT |
| shared_note__n1_nikhil | yes | yes | 0/3 | 2 | - |
| forget_story__n1_nikhil | yes | yes | 0/5 | 3 | - |
| figure_revised__n2_leo | yes | yes | 0/6 | 4 | - |
| other_story_develops__n2_leo | yes | yes | 0/4 | 4 | - |
| road_closure__n2_leo | yes | yes | 0/8 | 6 | - |
| attribution_retracted__n2_leo | yes | yes | 0/5 | 5 | - |
| conflicting_reports__n2_leo | yes | no | 1/4 | 4 | briefing: status VALID, expected SUSPECT |
| shared_note__n2_leo | yes | yes | 0/3 | 2 | - |
| forget_story__n2_leo | yes | yes | 0/5 | 3 | - |
| other_story_develops__n3_kavya | yes | yes | 0/4 | 4 | - |
| forget_story__n3_kavya | yes | yes | 0/5 | 3 | - |
| other_story_develops__n4_quinn | yes | yes | 0/4 | 4 | - |
| forget_story__n4_quinn | yes | yes | 0/5 | 3 | - |
