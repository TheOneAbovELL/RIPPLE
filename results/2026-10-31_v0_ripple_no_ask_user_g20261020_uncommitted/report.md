# v0 suite, strategy ripple, ablation no_ask_user, generator seed 20261020 — 2026-10-31T09:35:08.099966+00:00

Scenarios passed: 15/20 runnable (0 not runnable) · checks failed: 16/97 · errors: 5 · resolver calls: 38 · LLM calls: 0 (scripted oracle resolver).

Memory metrics over 20 runnable scenarios (0 not runnable, left out) (bench/metrics.py; pooled, ADR-0120): update accuracy 72.9% · stale kept per scenario 0.80 · wrongful changes per scenario 0.00 · questions asked per scenario 0.00 (needed 0.25) · stale retrieval 3.8% · stale recommendations 0.0% · never consistent 27.1% · resolver calls per ripple 1.73 · tokens and USD per ripple: n/a (no LLM).

Data: synthetic — generated in memory by bench.generate with seeds.generator_seed; the first seed reproduces bench/data/jobs_v0 (checked against its manifest), data sha256 ee71a9af90cea3325e67a7482b0c82acee12071699e8d52ed13232b496d5d913; invented names, places and companies, no real story or company described

| scenario | runnable | passed | checks failed | resolver calls | problems |
|---|---|---|---|---|---|
| accepted_offer__p0_dev | yes | yes | 0/5 | 3 | - |
| cutoff_unknown__p0_dev | yes | no | 4/4 | 1 | answer:eligibility: memory 'eligibility' is VALID, not PENDING_USER; eligibility: status VALID, expected PENDING_USER; recommendation: status VALID, expected SUSPECT; eligibility@latest: content 'not eligible for initech', expected 'eligible for initech (cutoff lowered to 6.7)'; eligibility@latest: version 1, expected 2; recommendation@latest: content 'skip initech', expected 'apply to initech'; recommendation@latest: version 1, expected 2 |
| cgpa_rise__p1_farhan | yes | yes | 0/5 | 2 | - |
| deadline_moved__p1_farhan | yes | yes | 0/5 | 1 | - |
| exam_block__p1_farhan | yes | yes | 0/8 | 4 | - |
| accepted_offer__p1_farhan | yes | yes | 0/5 | 3 | - |
| cutoff_unknown__p1_farhan | yes | no | 4/4 | 1 | answer:eligibility: memory 'eligibility' is VALID, not PENDING_USER; eligibility: status VALID, expected PENDING_USER; recommendation: status VALID, expected SUSPECT; eligibility: status VALID, expected RETIRED; recommendation@latest: content 'skip hooli', expected 'apply to hooli'; recommendation@latest: version 1, expected 2 |
| resume_update__p1_farhan | yes | yes | 0/3 | 1 | - |
| forget_cgpa__p1_farhan | yes | yes | 0/5 | 1 | - |
| accepted_offer__p2_bharat | yes | yes | 0/5 | 3 | - |
| cutoff_unknown__p2_bharat | yes | no | 4/4 | 1 | answer:eligibility: memory 'eligibility' is VALID, not PENDING_USER; eligibility: status VALID, expected PENDING_USER; recommendation: status VALID, expected SUSPECT; eligibility: status VALID, expected RETIRED; recommendation@latest: content 'skip initech', expected 'apply to initech'; recommendation@latest: version 1, expected 2 |
| cgpa_rise__p3_chitra | yes | yes | 0/5 | 2 | - |
| deadline_moved__p3_chitra | yes | yes | 0/5 | 1 | - |
| exam_block__p3_chitra | yes | yes | 0/8 | 4 | - |
| accepted_offer__p3_chitra | yes | yes | 0/5 | 3 | - |
| cutoff_unknown__p3_chitra | yes | no | 2/4 | 1 | answer:eligibility: memory 'eligibility' is VALID, not PENDING_USER; eligibility: status VALID, expected PENDING_USER; recommendation: status VALID, expected SUSPECT |
| resume_update__p3_chitra | yes | yes | 0/3 | 1 | - |
| forget_cgpa__p3_chitra | yes | yes | 0/5 | 1 | - |
| accepted_offer__p4_gauri | yes | yes | 0/5 | 3 | - |
| cutoff_unknown__p4_gauri | yes | no | 2/4 | 1 | answer:eligibility: memory 'eligibility' is VALID, not PENDING_USER; eligibility: status VALID, expected PENDING_USER; recommendation: status VALID, expected SUSPECT |
