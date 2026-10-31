# v0 suite, strategy append_only, generator seed 20261020 — 2026-10-31T09:34:55.752193+00:00

Scenarios passed: 0/35 runnable (0 not runnable) · checks failed: 76/175 · errors: 5 · resolver calls: 0 · LLM calls: 0 (scripted oracle resolver).

Memory metrics over 35 runnable scenarios (0 not runnable, left out) (bench/metrics.py; pooled, ADR-0120): update accuracy 24.8% · stale kept per scenario 2.17 · wrongful changes per scenario 0.00 · questions asked per scenario 0.00 (needed 0.14) · stale retrieval 32.9% · stale recommendations 66.7% · never consistent 75.2% · resolver calls per ripple 0.00 · tokens and USD per ripple: n/a (no LLM).

Data: synthetic — generated in memory by bench.generate with seeds.generator_seed; the first seed reproduces bench/data/jobs_v0 (checked against its manifest), data sha256 ee71a9af90cea3325e67a7482b0c82acee12071699e8d52ed13232b496d5d913; invented names, places and companies, no real story or company described

| scenario | runnable | passed | checks failed | resolver calls | problems |
|---|---|---|---|---|---|
| cgpa_rise__p0_dev | yes | no | 3/5 | 0 | cgpa: status VALID, expected RETIRED; eligibility@latest: content 'not eligible for initech (6.6 < 6.8)', expected 'eligible for initech (7.1 >= 6.8)'; eligibility@latest: version 1, expected 2; criteria@latest: version 1, expected 2 |
| deadline_moved__p0_dev | yes | no | 1/5 | 0 | stark_reminder@latest: content 'remind two days before 2026-11-09', expected 'remind two days before 2026-12-23'; stark_reminder@latest: version 1, expected 2 |
| exam_block__p0_dev | yes | no | 2/8 | 0 | availability@latest: version 1, expected 2; availability@latest: version 1, expected 3 |
| accepted_offer__p0_dev | yes | no | 3/5 | 0 | availability@latest: version 1, expected 2; eligibility: status VALID, expected RETIRED; recommendation: status VALID, expected RETIRED |
| cutoff_unknown__p0_dev | yes | no | 4/4 | 0 | answer:eligibility: memory 'eligibility' is VALID, not PENDING_USER; eligibility: status VALID, expected PENDING_USER; recommendation: status VALID, expected SUSPECT; eligibility@latest: content 'not eligible for initech', expected 'eligible for initech (cutoff lowered to 6.7)'; eligibility@latest: version 1, expected 2; recommendation@latest: content 'skip initech', expected 'apply to initech'; recommendation@latest: version 1, expected 2 |
| resume_update__p0_dev | yes | no | 2/3 | 0 | resume: status VALID, expected RETIRED; tailoring@latest: version 1, expected 2 |
| forget_cgpa__p0_dev | yes | no | 1/5 | 0 | eligibility@latest: version 1, expected 2 |
| cgpa_rise__p1_farhan | yes | no | 3/5 | 0 | cgpa: status VALID, expected RETIRED; eligibility@latest: content 'not eligible for hooli (8.1 < 8.3)', expected 'eligible for hooli (8.4 >= 8.3)'; eligibility@latest: version 1, expected 2; criteria@latest: version 1, expected 2 |
| deadline_moved__p1_farhan | yes | no | 1/5 | 0 | stark_reminder@latest: content 'remind two days before 2026-11-04', expected 'remind two days before 2026-12-15'; stark_reminder@latest: version 1, expected 2 |
| exam_block__p1_farhan | yes | no | 2/8 | 0 | availability@latest: version 1, expected 2; availability@latest: version 1, expected 3 |
| accepted_offer__p1_farhan | yes | no | 3/5 | 0 | availability@latest: version 1, expected 2; eligibility: status VALID, expected RETIRED; recommendation: status VALID, expected RETIRED |
| cutoff_unknown__p1_farhan | yes | no | 4/4 | 0 | answer:eligibility: memory 'eligibility' is VALID, not PENDING_USER; eligibility: status VALID, expected PENDING_USER; recommendation: status VALID, expected SUSPECT; eligibility: status VALID, expected RETIRED; recommendation@latest: content 'skip hooli', expected 'apply to hooli'; recommendation@latest: version 1, expected 2 |
| resume_update__p1_farhan | yes | no | 2/3 | 0 | resume: status VALID, expected RETIRED; tailoring@latest: version 1, expected 2 |
| forget_cgpa__p1_farhan | yes | no | 1/5 | 0 | eligibility@latest: version 1, expected 2 |
| cgpa_rise__p2_bharat | yes | no | 3/5 | 0 | cgpa: status VALID, expected RETIRED; eligibility@latest: content 'not eligible for initech (8.5 < 8.7)', expected 'eligible for initech (9.0 >= 8.7)'; eligibility@latest: version 1, expected 2; criteria@latest: version 1, expected 2 |
| deadline_moved__p2_bharat | yes | no | 1/5 | 0 | wonka_reminder@latest: content 'remind two days before 2026-12-04', expected 'remind two days before 2026-12-17'; wonka_reminder@latest: version 1, expected 2 |
| exam_block__p2_bharat | yes | no | 2/8 | 0 | availability@latest: version 1, expected 2; availability@latest: version 1, expected 3 |
| accepted_offer__p2_bharat | yes | no | 3/5 | 0 | availability@latest: version 1, expected 2; eligibility: status VALID, expected RETIRED; recommendation: status VALID, expected RETIRED |
| cutoff_unknown__p2_bharat | yes | no | 4/4 | 0 | answer:eligibility: memory 'eligibility' is VALID, not PENDING_USER; eligibility: status VALID, expected PENDING_USER; recommendation: status VALID, expected SUSPECT; eligibility: status VALID, expected RETIRED; recommendation@latest: content 'skip initech', expected 'apply to initech'; recommendation@latest: version 1, expected 2 |
| resume_update__p2_bharat | yes | no | 2/3 | 0 | resume: status VALID, expected RETIRED; tailoring@latest: version 1, expected 2 |
| forget_cgpa__p2_bharat | yes | no | 1/5 | 0 | eligibility@latest: version 1, expected 2 |
| cgpa_rise__p3_chitra | yes | no | 3/5 | 0 | cgpa: status VALID, expected RETIRED; eligibility@latest: content 'not eligible for acme (7.2 < 7.4)', expected 'eligible for acme (7.5 >= 7.4)'; eligibility@latest: version 1, expected 2; criteria@latest: version 1, expected 2 |
| deadline_moved__p3_chitra | yes | no | 1/5 | 0 | wonka_reminder@latest: content 'remind two days before 2026-11-14', expected 'remind two days before 2026-12-16'; wonka_reminder@latest: version 1, expected 2 |
| exam_block__p3_chitra | yes | no | 2/8 | 0 | availability@latest: version 1, expected 2; availability@latest: version 1, expected 3 |
| accepted_offer__p3_chitra | yes | no | 3/5 | 0 | availability@latest: version 1, expected 2; eligibility: status VALID, expected RETIRED; recommendation: status VALID, expected RETIRED |
| cutoff_unknown__p3_chitra | yes | no | 2/4 | 0 | answer:eligibility: memory 'eligibility' is VALID, not PENDING_USER; eligibility: status VALID, expected PENDING_USER; recommendation: status VALID, expected SUSPECT |
| resume_update__p3_chitra | yes | no | 2/3 | 0 | resume: status VALID, expected RETIRED; tailoring@latest: version 1, expected 2 |
| forget_cgpa__p3_chitra | yes | no | 1/5 | 0 | eligibility@latest: version 1, expected 2 |
| cgpa_rise__p4_gauri | yes | no | 3/5 | 0 | cgpa: status VALID, expected RETIRED; eligibility@latest: content 'not eligible for wonka (8.5 < 8.7)', expected 'eligible for wonka (9.0 >= 8.7)'; eligibility@latest: version 1, expected 2; criteria@latest: version 1, expected 2 |
| deadline_moved__p4_gauri | yes | no | 1/5 | 0 | acme_reminder@latest: content 'remind two days before 2026-12-09', expected 'remind two days before 2026-12-18'; acme_reminder@latest: version 1, expected 2 |
| exam_block__p4_gauri | yes | no | 2/8 | 0 | availability@latest: version 1, expected 2; availability@latest: version 1, expected 3 |
| accepted_offer__p4_gauri | yes | no | 3/5 | 0 | availability@latest: version 1, expected 2; eligibility: status VALID, expected RETIRED; recommendation: status VALID, expected RETIRED |
| cutoff_unknown__p4_gauri | yes | no | 2/4 | 0 | answer:eligibility: memory 'eligibility' is VALID, not PENDING_USER; eligibility: status VALID, expected PENDING_USER; recommendation: status VALID, expected SUSPECT |
| resume_update__p4_gauri | yes | no | 2/3 | 0 | resume: status VALID, expected RETIRED; tailoring@latest: version 1, expected 2 |
| forget_cgpa__p4_gauri | yes | no | 1/5 | 0 | eligibility@latest: version 1, expected 2 |
