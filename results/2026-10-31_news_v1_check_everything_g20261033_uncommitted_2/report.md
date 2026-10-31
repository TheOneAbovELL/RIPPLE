# news_v1 suite, strategy check_everything, generator seed 20261033 — 2026-10-31T09:35:26.238489+00:00

Scenarios passed: 30/35 runnable (0 not runnable) · checks failed: 5/175 · errors: 0 · resolver calls: 136 · LLM calls: 0 (scripted oracle resolver).

Memory metrics over 35 runnable scenarios (0 not runnable, left out) (bench/metrics.py; pooled, ADR-0120): update accuracy 95.1% · stale kept per scenario 0.14 · wrongful changes per scenario 0.00 · questions asked per scenario 0.14 (needed 0.14) · stale retrieval 0.0% · stale recommendations n/a · never consistent 4.9% · resolver calls per ripple 3.02 · tokens and USD per ripple: n/a (no LLM).

Data: synthetic — generated in memory by bench.generate_news with seeds.generator_seed; the first seed reproduces bench/data/news_v1 (checked against its manifest), data sha256 849175dae613dc40586b890a9252d6f2b48abfca112ee10be98685462a823b94; invented names, places and companies, no real story or company described

| scenario | runnable | passed | checks failed | resolver calls | problems |
|---|---|---|---|---|---|
| figure_revised__n0_ravi | yes | yes | 0/6 | 4 | - |
| other_story_develops__n0_ravi | yes | yes | 0/4 | 4 | - |
| road_closure__n0_ravi | yes | yes | 0/8 | 6 | - |
| attribution_retracted__n0_ravi | yes | yes | 0/5 | 5 | - |
| conflicting_reports__n0_ravi | yes | no | 1/4 | 4 | briefing: status VALID, expected SUSPECT |
| shared_note__n0_ravi | yes | yes | 0/3 | 2 | - |
| forget_story__n0_ravi | yes | yes | 0/5 | 3 | - |
| figure_revised__n1_tara | yes | yes | 0/6 | 4 | - |
| other_story_develops__n1_tara | yes | yes | 0/4 | 4 | - |
| road_closure__n1_tara | yes | yes | 0/8 | 6 | - |
| attribution_retracted__n1_tara | yes | yes | 0/5 | 5 | - |
| conflicting_reports__n1_tara | yes | no | 1/4 | 2 | briefing: status VALID, expected SUSPECT |
| shared_note__n1_tara | yes | yes | 0/3 | 2 | - |
| forget_story__n1_tara | yes | yes | 0/5 | 3 | - |
| figure_revised__n2_priya | yes | yes | 0/6 | 4 | - |
| other_story_develops__n2_priya | yes | yes | 0/4 | 4 | - |
| road_closure__n2_priya | yes | yes | 0/8 | 6 | - |
| attribution_retracted__n2_priya | yes | yes | 0/5 | 5 | - |
| conflicting_reports__n2_priya | yes | no | 1/4 | 2 | briefing: status VALID, expected SUSPECT |
| shared_note__n2_priya | yes | yes | 0/3 | 2 | - |
| forget_story__n2_priya | yes | yes | 0/5 | 3 | - |
| figure_revised__n3_kavya | yes | yes | 0/6 | 4 | - |
| other_story_develops__n3_kavya | yes | yes | 0/4 | 4 | - |
| road_closure__n3_kavya | yes | yes | 0/8 | 6 | - |
| attribution_retracted__n3_kavya | yes | yes | 0/5 | 5 | - |
| conflicting_reports__n3_kavya | yes | no | 1/4 | 4 | briefing: status VALID, expected SUSPECT |
| shared_note__n3_kavya | yes | yes | 0/3 | 2 | - |
| forget_story__n3_kavya | yes | yes | 0/5 | 3 | - |
| figure_revised__n4_omar | yes | yes | 0/6 | 4 | - |
| other_story_develops__n4_omar | yes | yes | 0/4 | 4 | - |
| road_closure__n4_omar | yes | yes | 0/8 | 6 | - |
| attribution_retracted__n4_omar | yes | yes | 0/5 | 5 | - |
| conflicting_reports__n4_omar | yes | no | 1/4 | 4 | briefing: status VALID, expected SUSPECT |
| shared_note__n4_omar | yes | yes | 0/3 | 2 | - |
| forget_story__n4_omar | yes | yes | 0/5 | 3 | - |
