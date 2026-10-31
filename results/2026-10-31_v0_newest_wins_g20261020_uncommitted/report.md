# v0 suite, strategy newest_wins, generator seed 20261020 — 2026-10-31T09:34:48.116317+00:00

Scenarios passed: 0/20 runnable (0 not runnable) · checks failed: 45/97 · errors: 5 · resolver calls: 0 · LLM calls: 0 (scripted oracle resolver).

Memory metrics over 20 runnable scenarios (0 not runnable, left out) (bench/metrics.py; pooled, ADR-0120): update accuracy 23.7% · stale kept per scenario 2.25 · wrongful changes per scenario 0.00 · questions asked per scenario 0.00 (needed 0.25) · stale retrieval 33.4% · stale recommendations 50.0% · never consistent 76.3% · resolver calls per ripple 0.00 · tokens and USD per ripple: n/a (no LLM).

Data: synthetic — generated in memory by bench.generate with seeds.generator_seed; the first seed reproduces bench/data/jobs_v0 (checked against its manifest), data sha256 ee71a9af90cea3325e67a7482b0c82acee12071699e8d52ed13232b496d5d913; invented names, places and companies, no real story or company described

| scenario | runnable | passed | checks failed | resolver calls | problems |
|---|---|---|---|---|---|
| accepted_offer__p0_dev | yes | no | 3/5 | 0 | availability@latest: version 1, expected 2; eligibility: status VALID, expected RETIRED; recommendation: status VALID, expected RETIRED |
| cutoff_unknown__p0_dev | yes | no | 4/4 | 0 | answer:eligibility: memory 'eligibility' is VALID, not PENDING_USER; eligibility: status VALID, expected PENDING_USER; recommendation: status VALID, expected SUSPECT; eligibility@latest: content 'not eligible for initech', expected 'eligible for initech (cutoff lowered to 6.7)'; eligibility@latest: version 1, expected 2; recommendation@latest: content 'skip initech', expected 'apply to initech'; recommendation@latest: version 1, expected 2 |
| cgpa_rise__p1_farhan | yes | no | 2/5 | 0 | eligibility@latest: content 'not eligible for hooli (8.1 < 8.3)', expected 'eligible for hooli (8.4 >= 8.3)'; eligibility@latest: version 1, expected 2; criteria@latest: version 1, expected 2 |
| deadline_moved__p1_farhan | yes | no | 1/5 | 0 | stark_reminder@latest: content 'remind two days before 2026-11-04', expected 'remind two days before 2026-12-15'; stark_reminder@latest: version 1, expected 2 |
| exam_block__p1_farhan | yes | no | 2/8 | 0 | availability@latest: version 1, expected 2; availability@latest: version 1, expected 3 |
| accepted_offer__p1_farhan | yes | no | 3/5 | 0 | availability@latest: version 1, expected 2; eligibility: status VALID, expected RETIRED; recommendation: status VALID, expected RETIRED |
| cutoff_unknown__p1_farhan | yes | no | 4/4 | 0 | answer:eligibility: memory 'eligibility' is VALID, not PENDING_USER; eligibility: status VALID, expected PENDING_USER; recommendation: status VALID, expected SUSPECT; eligibility: status VALID, expected RETIRED; recommendation@latest: content 'skip hooli', expected 'apply to hooli'; recommendation@latest: version 1, expected 2 |
| resume_update__p1_farhan | yes | no | 1/3 | 0 | tailoring@latest: version 1, expected 2 |
| forget_cgpa__p1_farhan | yes | no | 1/5 | 0 | eligibility@latest: version 1, expected 2 |
| accepted_offer__p2_bharat | yes | no | 3/5 | 0 | availability@latest: version 1, expected 2; eligibility: status VALID, expected RETIRED; recommendation: status VALID, expected RETIRED |
| cutoff_unknown__p2_bharat | yes | no | 4/4 | 0 | answer:eligibility: memory 'eligibility' is VALID, not PENDING_USER; eligibility: status VALID, expected PENDING_USER; recommendation: status VALID, expected SUSPECT; eligibility: status VALID, expected RETIRED; recommendation@latest: content 'skip initech', expected 'apply to initech'; recommendation@latest: version 1, expected 2 |
| cgpa_rise__p3_chitra | yes | no | 2/5 | 0 | eligibility@latest: content 'not eligible for acme (7.2 < 7.4)', expected 'eligible for acme (7.5 >= 7.4)'; eligibility@latest: version 1, expected 2; criteria@latest: version 1, expected 2 |
| deadline_moved__p3_chitra | yes | no | 1/5 | 0 | wonka_reminder@latest: content 'remind two days before 2026-11-14', expected 'remind two days before 2026-12-16'; wonka_reminder@latest: version 1, expected 2 |
| exam_block__p3_chitra | yes | no | 2/8 | 0 | availability@latest: version 1, expected 2; availability@latest: version 1, expected 3 |
| accepted_offer__p3_chitra | yes | no | 3/5 | 0 | availability@latest: version 1, expected 2; eligibility: status VALID, expected RETIRED; recommendation: status VALID, expected RETIRED |
| cutoff_unknown__p3_chitra | yes | no | 2/4 | 0 | answer:eligibility: memory 'eligibility' is VALID, not PENDING_USER; eligibility: status VALID, expected PENDING_USER; recommendation: status VALID, expected SUSPECT |
| resume_update__p3_chitra | yes | no | 1/3 | 0 | tailoring@latest: version 1, expected 2 |
| forget_cgpa__p3_chitra | yes | no | 1/5 | 0 | eligibility@latest: version 1, expected 2 |
| accepted_offer__p4_gauri | yes | no | 3/5 | 0 | availability@latest: version 1, expected 2; eligibility: status VALID, expected RETIRED; recommendation: status VALID, expected RETIRED |
| cutoff_unknown__p4_gauri | yes | no | 2/4 | 0 | answer:eligibility: memory 'eligibility' is VALID, not PENDING_USER; eligibility: status VALID, expected PENDING_USER; recommendation: status VALID, expected SUSPECT |
