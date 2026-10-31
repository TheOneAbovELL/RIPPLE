# news_v1 suite, strategy ripple, ablation no_ask_user, generator seed 20261031 — 2026-10-31T09:35:28.869778+00:00

Scenarios passed: 18/20 runnable (0 not runnable) · checks failed: 8/97 · errors: 2 · resolver calls: 32 · LLM calls: 0 (scripted oracle resolver).

Memory metrics over 20 runnable scenarios (0 not runnable, left out) (bench/metrics.py; pooled, ADR-0120): update accuracy 85.2% · stale kept per scenario 0.40 · wrongful changes per scenario 0.00 · questions asked per scenario 0.00 (needed 0.10) · stale retrieval 2.8% · stale recommendations n/a · never consistent 14.8% · resolver calls per ripple 1.45 · tokens and USD per ripple: n/a (no LLM).

Data: synthetic — generated in memory by bench.generate_news with seeds.generator_seed; the first seed reproduces bench/data/news_v1 (checked against its manifest), data sha256 d9b473dfcb246332962da836a3c528c835e75da15945ff769af8e56ffebfa2d1; invented names, places and companies, no real story or company described

| scenario | runnable | passed | checks failed | resolver calls | problems |
|---|---|---|---|---|---|
| other_story_develops__n0_meera | yes | yes | 0/4 | 1 | - |
| forget_story__n0_meera | yes | yes | 0/5 | 1 | - |
| figure_revised__n1_nikhil | yes | yes | 0/6 | 2 | - |
| other_story_develops__n1_nikhil | yes | yes | 0/4 | 1 | - |
| road_closure__n1_nikhil | yes | yes | 0/8 | 4 | - |
| attribution_retracted__n1_nikhil | yes | yes | 0/5 | 3 | - |
| conflicting_reports__n1_nikhil | yes | no | 4/4 | 1 | answer:summary: memory 'summary' is VALID, not PENDING_USER; summary: status VALID, expected PENDING_USER; briefing: status VALID, expected SUSPECT; summary: status VALID, expected RETIRED; briefing@latest: content 'briefing: Larkspur power outage: 141 homes without power', expected 'briefing: Larkspur power outage, figure disputed'; briefing@latest: version 1, expected 2 |
| shared_note__n1_nikhil | yes | yes | 0/3 | 1 | - |
| forget_story__n1_nikhil | yes | yes | 0/5 | 1 | - |
| figure_revised__n2_leo | yes | yes | 0/6 | 2 | - |
| other_story_develops__n2_leo | yes | yes | 0/4 | 1 | - |
| road_closure__n2_leo | yes | yes | 0/8 | 4 | - |
| attribution_retracted__n2_leo | yes | yes | 0/5 | 3 | - |
| conflicting_reports__n2_leo | yes | no | 4/4 | 1 | answer:summary: memory 'summary' is VALID, not PENDING_USER; summary: status VALID, expected PENDING_USER; briefing: status VALID, expected SUSPECT; summary: status VALID, expected RETIRED; briefing@latest: content 'briefing: Riverton power outage: 77 homes without power', expected 'briefing: Riverton power outage, figure disputed'; briefing@latest: version 1, expected 2 |
| shared_note__n2_leo | yes | yes | 0/3 | 1 | - |
| forget_story__n2_leo | yes | yes | 0/5 | 1 | - |
| other_story_develops__n3_kavya | yes | yes | 0/4 | 1 | - |
| forget_story__n3_kavya | yes | yes | 0/5 | 1 | - |
| other_story_develops__n4_quinn | yes | yes | 0/4 | 1 | - |
| forget_story__n4_quinn | yes | yes | 0/5 | 1 | - |
