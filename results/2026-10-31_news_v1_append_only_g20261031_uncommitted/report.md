# news_v1 suite, strategy append_only, generator seed 20261031 — 2026-10-31T09:35:11.892961+00:00

Scenarios passed: 0/20 runnable (0 not runnable) · checks failed: 38/97 · errors: 2 · resolver calls: 0 · LLM calls: 0 (scripted oracle resolver).

Memory metrics over 20 runnable scenarios (0 not runnable, left out) (bench/metrics.py; pooled, ADR-0120): update accuracy 29.6% · stale kept per scenario 1.90 · wrongful changes per scenario 0.00 · questions asked per scenario 0.00 (needed 0.10) · stale retrieval 30.1% · stale recommendations n/a · never consistent 70.4% · resolver calls per ripple 0.00 · tokens and USD per ripple: n/a (no LLM).

Data: synthetic — generated in memory by bench.generate_news with seeds.generator_seed; the first seed reproduces bench/data/news_v1 (checked against its manifest), data sha256 d9b473dfcb246332962da836a3c528c835e75da15945ff769af8e56ffebfa2d1; invented names, places and companies, no real story or company described

| scenario | runnable | passed | checks failed | resolver calls | problems |
|---|---|---|---|---|---|
| other_story_develops__n0_meera | yes | no | 1/4 | 0 | summary@latest: content 'Duncliff data breach: awaiting a decision', expected 'Duncliff data breach: inquiry opened'; summary@latest: version 1, expected 2 |
| forget_story__n0_meera | yes | no | 1/5 | 0 | summary@latest: version 1, expected 2 |
| figure_revised__n1_nikhil | yes | no | 3/6 | 0 | claim: status VALID, expected RETIRED; summary@latest: content 'Larkspur power outage: 141 homes without power', expected 'Larkspur power outage: 113 homes without power'; summary@latest: version 1, expected 2; briefing@latest: content 'today: Larkspur power outage: 141 homes without power; Hollowbay data breach: 236 accounts exposed', expected 'today: Larkspur power outage: 113 homes without power; Hollowbay data breach: 236 accounts exposed'; briefing@latest: version 1, expected 2 |
| other_story_develops__n1_nikhil | yes | no | 1/4 | 0 | summary@latest: content 'Hollowbay data breach: awaiting a decision', expected 'Hollowbay data breach: compensation agreed'; summary@latest: version 1, expected 2 |
| road_closure__n1_nikhil | yes | no | 2/8 | 0 | travel_advice@latest: version 1, expected 2; travel_advice@latest: version 1, expected 3 |
| attribution_retracted__n1_nikhil | yes | no | 3/5 | 0 | analysis@latest: version 1, expected 2; follow_up: status VALID, expected RETIRED; briefing_item: status VALID, expected RETIRED |
| conflicting_reports__n1_nikhil | yes | no | 4/4 | 0 | answer:summary: memory 'summary' is VALID, not PENDING_USER; summary: status VALID, expected PENDING_USER; briefing: status VALID, expected SUSPECT; summary: status VALID, expected RETIRED; briefing@latest: content 'briefing: Larkspur power outage: 141 homes without power', expected 'briefing: Larkspur power outage, figure disputed'; briefing@latest: version 1, expected 2 |
| shared_note__n1_nikhil | yes | no | 2/3 | 0 | claim: status VALID, expected RETIRED; summary@latest: content 'Ashgrove ferry accident: 131 passengers rescued', expected 'Ashgrove ferry accident: 157 passengers rescued'; summary@latest: version 1, expected 2 |
| forget_story__n1_nikhil | yes | no | 1/5 | 0 | summary@latest: version 1, expected 2 |
| figure_revised__n2_leo | yes | no | 3/6 | 0 | claim: status VALID, expected RETIRED; summary@latest: content 'Riverton power outage: 77 homes without power', expected 'Riverton power outage: 102 homes without power'; summary@latest: version 1, expected 2; briefing@latest: content 'today: Riverton power outage: 77 homes without power; Ashgrove factory fire: 83 workers evacuated', expected 'today: Riverton power outage: 102 homes without power; Ashgrove factory fire: 83 workers evacuated'; briefing@latest: version 1, expected 2 |
| other_story_develops__n2_leo | yes | no | 1/4 | 0 | summary@latest: content 'Ashgrove factory fire: awaiting a decision', expected 'Ashgrove factory fire: compensation agreed'; summary@latest: version 1, expected 2 |
| road_closure__n2_leo | yes | no | 2/8 | 0 | travel_advice@latest: version 1, expected 2; travel_advice@latest: version 1, expected 3 |
| attribution_retracted__n2_leo | yes | no | 3/5 | 0 | analysis@latest: version 1, expected 2; follow_up: status VALID, expected RETIRED; briefing_item: status VALID, expected RETIRED |
| conflicting_reports__n2_leo | yes | no | 4/4 | 0 | answer:summary: memory 'summary' is VALID, not PENDING_USER; summary: status VALID, expected PENDING_USER; briefing: status VALID, expected SUSPECT; summary: status VALID, expected RETIRED; briefing@latest: content 'briefing: Riverton power outage: 77 homes without power', expected 'briefing: Riverton power outage, figure disputed'; briefing@latest: version 1, expected 2 |
| shared_note__n2_leo | yes | no | 2/3 | 0 | claim: status VALID, expected RETIRED; summary@latest: content 'Kestrel data breach: 164 accounts exposed', expected 'Kestrel data breach: 196 accounts exposed'; summary@latest: version 1, expected 2 |
| forget_story__n2_leo | yes | no | 1/5 | 0 | summary@latest: version 1, expected 2 |
| other_story_develops__n3_kavya | yes | no | 1/4 | 0 | summary@latest: content 'Ashgrove power outage: awaiting a decision', expected 'Ashgrove power outage: repairs approved'; summary@latest: version 1, expected 2 |
| forget_story__n3_kavya | yes | no | 1/5 | 0 | summary@latest: version 1, expected 2 |
| other_story_develops__n4_quinn | yes | no | 1/4 | 0 | summary@latest: content 'Larkspur factory fire: awaiting a decision', expected 'Larkspur factory fire: compensation agreed'; summary@latest: version 1, expected 2 |
| forget_story__n4_quinn | yes | no | 1/5 | 0 | summary@latest: version 1, expected 2 |
