# v0 suite, strategy newest_wins, generator seed 20261021 — 2026-10-31T09:35:02.109935+00:00

Scenarios passed: 0/35 runnable (0 not runnable) · checks failed: 68/175 · errors: 5 · resolver calls: 0 · LLM calls: 0 (scripted oracle resolver).

Memory metrics over 35 runnable scenarios (0 not runnable, left out) (bench/metrics.py; pooled, ADR-0120): update accuracy 34.0% · stale kept per scenario 1.94 · wrongful changes per scenario 0.00 · questions asked per scenario 0.00 (needed 0.14) · stale retrieval 31.9% · stale recommendations 50.0% · never consistent 66.0% · resolver calls per ripple 0.00 · tokens and USD per ripple: n/a (no LLM).

Data: synthetic — generated in memory by bench.generate with seeds.generator_seed; the first seed reproduces bench/data/jobs_v0 (checked against its manifest), data sha256 3658001907a3a683f146e31960171b3c532ccb84e5d893c8164dddca3a3e0164; invented names, places and companies, no real story or company described

| scenario | runnable | passed | checks failed | resolver calls | problems |
|---|---|---|---|---|---|
| cgpa_rise__p0_jay | yes | no | 2/5 | 0 | eligibility@latest: content 'not eligible for acme (7.3 < 7.5)', expected 'eligible for acme (7.8 >= 7.5)'; eligibility@latest: version 1, expected 2; criteria@latest: version 1, expected 2 |
| deadline_moved__p0_jay | yes | no | 1/5 | 0 | stark_reminder@latest: content 'remind two days before 2026-11-22', expected 'remind two days before 2026-12-17'; stark_reminder@latest: version 1, expected 2 |
| exam_block__p0_jay | yes | no | 2/8 | 0 | availability@latest: version 1, expected 2; availability@latest: version 1, expected 3 |
| accepted_offer__p0_jay | yes | no | 3/5 | 0 | availability@latest: version 1, expected 2; eligibility: status VALID, expected RETIRED; recommendation: status VALID, expected RETIRED |
| cutoff_unknown__p0_jay | yes | no | 4/4 | 0 | answer:eligibility: memory 'eligibility' is VALID, not PENDING_USER; eligibility: status VALID, expected PENDING_USER; recommendation: status VALID, expected SUSPECT; eligibility: status VALID, expected RETIRED; recommendation@latest: content 'skip acme', expected 'apply to acme'; recommendation@latest: version 1, expected 2 |
| resume_update__p0_jay | yes | no | 1/3 | 0 | tailoring@latest: version 1, expected 2 |
| forget_cgpa__p0_jay | yes | no | 1/5 | 0 | eligibility@latest: version 1, expected 2 |
| cgpa_rise__p1_asha | yes | no | 2/5 | 0 | eligibility@latest: content 'not eligible for vandelay (7.4 < 7.6)', expected 'eligible for vandelay (7.8 >= 7.6)'; eligibility@latest: version 1, expected 2; criteria@latest: version 1, expected 2 |
| deadline_moved__p1_asha | yes | no | 1/5 | 0 | stark_reminder@latest: content 'remind two days before 2026-12-19', expected 'remind two days before 2026-12-24'; stark_reminder@latest: version 1, expected 2 |
| exam_block__p1_asha | yes | no | 2/8 | 0 | availability@latest: version 1, expected 2; availability@latest: version 1, expected 3 |
| accepted_offer__p1_asha | yes | no | 3/5 | 0 | availability@latest: version 1, expected 2; eligibility: status VALID, expected RETIRED; recommendation: status VALID, expected RETIRED |
| cutoff_unknown__p1_asha | yes | no | 4/4 | 0 | answer:eligibility: memory 'eligibility' is VALID, not PENDING_USER; eligibility: status VALID, expected PENDING_USER; recommendation: status VALID, expected SUSPECT; eligibility: status VALID, expected RETIRED; recommendation@latest: content 'skip vandelay', expected 'apply to vandelay'; recommendation@latest: version 1, expected 2 |
| resume_update__p1_asha | yes | no | 1/3 | 0 | tailoring@latest: version 1, expected 2 |
| forget_cgpa__p1_asha | yes | no | 1/5 | 0 | eligibility@latest: version 1, expected 2 |
| cgpa_rise__p2_esha | yes | no | 2/5 | 0 | eligibility@latest: content 'not eligible for vandelay (8.4 < 8.6)', expected 'eligible for vandelay (8.9 >= 8.6)'; eligibility@latest: version 1, expected 2; criteria@latest: version 1, expected 2 |
| deadline_moved__p2_esha | yes | no | 1/5 | 0 | acme_reminder@latest: content 'remind two days before 2026-12-12', expected 'remind two days before 2026-12-17'; acme_reminder@latest: version 1, expected 2 |
| exam_block__p2_esha | yes | no | 2/8 | 0 | availability@latest: version 1, expected 2; availability@latest: version 1, expected 3 |
| accepted_offer__p2_esha | yes | no | 3/5 | 0 | availability@latest: version 1, expected 2; eligibility: status VALID, expected RETIRED; recommendation: status VALID, expected RETIRED |
| cutoff_unknown__p2_esha | yes | no | 4/4 | 0 | answer:eligibility: memory 'eligibility' is VALID, not PENDING_USER; eligibility: status VALID, expected PENDING_USER; recommendation: status VALID, expected SUSPECT; eligibility@latest: content 'not eligible for vandelay', expected 'eligible for vandelay (cutoff lowered to 8.5)'; eligibility@latest: version 1, expected 2; recommendation@latest: content 'skip vandelay', expected 'apply to vandelay'; recommendation@latest: version 1, expected 2 |
| resume_update__p2_esha | yes | no | 1/3 | 0 | tailoring@latest: version 1, expected 2 |
| forget_cgpa__p2_esha | yes | no | 1/5 | 0 | eligibility@latest: version 1, expected 2 |
| cgpa_rise__p3_chitra | yes | no | 2/5 | 0 | eligibility@latest: content 'not eligible for hooli (6.9 < 7.1)', expected 'eligible for hooli (7.3 >= 7.1)'; eligibility@latest: version 1, expected 2; criteria@latest: version 1, expected 2 |
| deadline_moved__p3_chitra | yes | no | 1/5 | 0 | initech_reminder@latest: content 'remind two days before 2026-11-16', expected 'remind two days before 2026-12-17'; initech_reminder@latest: version 1, expected 2 |
| exam_block__p3_chitra | yes | no | 2/8 | 0 | availability@latest: version 1, expected 2; availability@latest: version 1, expected 3 |
| accepted_offer__p3_chitra | yes | no | 3/5 | 0 | availability@latest: version 1, expected 2; eligibility: status VALID, expected RETIRED; recommendation: status VALID, expected RETIRED |
| cutoff_unknown__p3_chitra | yes | no | 4/4 | 0 | answer:eligibility: memory 'eligibility' is VALID, not PENDING_USER; eligibility: status VALID, expected PENDING_USER; recommendation: status VALID, expected SUSPECT; eligibility: status VALID, expected RETIRED; recommendation@latest: content 'skip hooli', expected 'apply to hooli'; recommendation@latest: version 1, expected 2 |
| resume_update__p3_chitra | yes | no | 1/3 | 0 | tailoring@latest: version 1, expected 2 |
| forget_cgpa__p3_chitra | yes | no | 1/5 | 0 | eligibility@latest: version 1, expected 2 |
| cgpa_rise__p4_bharat | yes | no | 2/5 | 0 | eligibility@latest: content 'not eligible for globex (8.1 < 8.3)', expected 'eligible for globex (8.6 >= 8.3)'; eligibility@latest: version 1, expected 2; criteria@latest: version 1, expected 2 |
| deadline_moved__p4_bharat | yes | no | 1/5 | 0 | umbrella_reminder@latest: content 'remind two days before 2026-12-13', expected 'remind two days before 2026-12-27'; umbrella_reminder@latest: version 1, expected 2 |
| exam_block__p4_bharat | yes | no | 2/8 | 0 | availability@latest: version 1, expected 2; availability@latest: version 1, expected 3 |
| accepted_offer__p4_bharat | yes | no | 3/5 | 0 | availability@latest: version 1, expected 2; eligibility: status VALID, expected RETIRED; recommendation: status VALID, expected RETIRED |
| cutoff_unknown__p4_bharat | yes | no | 2/4 | 0 | answer:eligibility: memory 'eligibility' is VALID, not PENDING_USER; eligibility: status VALID, expected PENDING_USER; recommendation: status VALID, expected SUSPECT |
| resume_update__p4_bharat | yes | no | 1/3 | 0 | tailoring@latest: version 1, expected 2 |
| forget_cgpa__p4_bharat | yes | no | 1/5 | 0 | eligibility@latest: version 1, expected 2 |
