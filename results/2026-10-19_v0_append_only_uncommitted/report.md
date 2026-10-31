# v0 suite, strategy append_only — 2026-10-19T04:57:29.925564+00:00

Scenarios passed: 0/35 runnable (0 not runnable) · checks failed: 96/175 · resolver calls: 0 · LLM calls: 0 (scripted oracle resolver).

Memory metrics: TBD (pending run): bench/metrics.py is TODO(human).

| scenario | runnable | passed | checks | resolver calls | failures |
|---|---|---|---|---|---|
| cgpa_rise__p0_jay | yes | no | 5 | 0 | cgpa: status VALID, expected RETIRED; eligibility@latest: content 'not eligible for umbrella (7.2 < 7.4)', expected 'eligible for umbrella (7.6 >= 7.4)'; eligibility@latest: version 1, expected 2; criteria@latest: version 1, expected 2 |
| deadline_moved__p0_jay | yes | no | 5 | 0 | initech_reminder@latest: content 'remind two days before 2026-11-01', expected 'remind two days before 2026-12-19'; initech_reminder@latest: version 1, expected 2 |
| exam_block__p0_jay | yes | no | 8 | 0 | availability@latest: version 1, expected 2; availability@latest: version 1, expected 3 |
| accepted_offer__p0_jay | yes | no | 5 | 0 | availability@latest: version 1, expected 2; eligibility: status VALID, expected RETIRED; recommendation: status VALID, expected RETIRED |
| cutoff_unknown__p0_jay | yes | no | 4 | 0 | eligibility: status VALID, expected PENDING_USER; recommendation: status VALID, expected SUSPECT; answer:eligibility: memory 'eligibility' is VALID, not PENDING_USER; eligibility@latest: content 'not eligible for umbrella', expected 'eligible for umbrella (cutoff lowered to 7.3)'; eligibility@latest: version 1, expected 2; recommendation@latest: content 'skip umbrella', expected 'apply to umbrella'; recommendation@latest: version 1, expected 2 |
| resume_update__p0_jay | yes | no | 3 | 0 | resume: status VALID, expected RETIRED; tailoring@latest: version 1, expected 2 |
| forget_cgpa__p0_jay | yes | no | 5 | 0 | eligibility@latest: version 1, expected 2 |
| cgpa_rise__p1_dev | yes | no | 5 | 0 | cgpa: status VALID, expected RETIRED; eligibility@latest: content 'not eligible for stark (7.4 < 7.6)', expected 'eligible for stark (7.9 >= 7.6)'; eligibility@latest: version 1, expected 2; criteria@latest: version 1, expected 2 |
| deadline_moved__p1_dev | yes | no | 5 | 0 | wonka_reminder@latest: content 'remind two days before 2026-11-12', expected 'remind two days before 2026-12-16'; wonka_reminder@latest: version 1, expected 2 |
| exam_block__p1_dev | yes | no | 8 | 0 | availability@latest: version 1, expected 2; availability@latest: version 1, expected 3 |
| accepted_offer__p1_dev | yes | no | 5 | 0 | availability@latest: version 1, expected 2; eligibility: status VALID, expected RETIRED; recommendation: status VALID, expected RETIRED |
| cutoff_unknown__p1_dev | yes | no | 4 | 0 | eligibility: status VALID, expected PENDING_USER; recommendation: status VALID, expected SUSPECT; answer:eligibility: memory 'eligibility' is VALID, not PENDING_USER |
| resume_update__p1_dev | yes | no | 3 | 0 | resume: status VALID, expected RETIRED; tailoring@latest: version 1, expected 2 |
| forget_cgpa__p1_dev | yes | no | 5 | 0 | eligibility@latest: version 1, expected 2 |
| cgpa_rise__p2_harsh | yes | no | 5 | 0 | cgpa: status VALID, expected RETIRED; eligibility@latest: content 'not eligible for vandelay (7.1 < 7.3)', expected 'eligible for vandelay (7.4 >= 7.3)'; eligibility@latest: version 1, expected 2; criteria@latest: version 1, expected 2 |
| deadline_moved__p2_harsh | yes | no | 5 | 0 | umbrella_reminder@latest: content 'remind two days before 2026-11-19', expected 'remind two days before 2026-12-23'; umbrella_reminder@latest: version 1, expected 2 |
| exam_block__p2_harsh | yes | no | 8 | 0 | availability@latest: version 1, expected 2; availability@latest: version 1, expected 3 |
| accepted_offer__p2_harsh | yes | no | 5 | 0 | availability@latest: version 1, expected 2; eligibility: status VALID, expected RETIRED; recommendation: status VALID, expected RETIRED |
| cutoff_unknown__p2_harsh | yes | no | 4 | 0 | eligibility: status VALID, expected PENDING_USER; recommendation: status VALID, expected SUSPECT; answer:eligibility: memory 'eligibility' is VALID, not PENDING_USER; eligibility@latest: content 'not eligible for vandelay', expected 'eligible for vandelay (cutoff lowered to 7.2)'; eligibility@latest: version 1, expected 2; recommendation@latest: content 'skip vandelay', expected 'apply to vandelay'; recommendation@latest: version 1, expected 2 |
| resume_update__p2_harsh | yes | no | 3 | 0 | resume: status VALID, expected RETIRED; tailoring@latest: version 1, expected 2 |
| forget_cgpa__p2_harsh | yes | no | 5 | 0 | eligibility@latest: version 1, expected 2 |
| cgpa_rise__p3_esha | yes | no | 5 | 0 | cgpa: status VALID, expected RETIRED; eligibility@latest: content 'not eligible for vandelay (7.5 < 7.7)', expected 'eligible for vandelay (7.9 >= 7.7)'; eligibility@latest: version 1, expected 2; criteria@latest: version 1, expected 2 |
| deadline_moved__p3_esha | yes | no | 5 | 0 | hooli_reminder@latest: content 'remind two days before 2026-12-06', expected 'remind two days before 2026-12-16'; hooli_reminder@latest: version 1, expected 2 |
| exam_block__p3_esha | yes | no | 8 | 0 | availability@latest: version 1, expected 2; availability@latest: version 1, expected 3 |
| accepted_offer__p3_esha | yes | no | 5 | 0 | availability@latest: version 1, expected 2; eligibility: status VALID, expected RETIRED; recommendation: status VALID, expected RETIRED |
| cutoff_unknown__p3_esha | yes | no | 4 | 0 | eligibility: status VALID, expected PENDING_USER; recommendation: status VALID, expected SUSPECT; answer:eligibility: memory 'eligibility' is VALID, not PENDING_USER; eligibility: status VALID, expected RETIRED; recommendation@latest: content 'skip vandelay', expected 'apply to vandelay'; recommendation@latest: version 1, expected 2 |
| resume_update__p3_esha | yes | no | 3 | 0 | resume: status VALID, expected RETIRED; tailoring@latest: version 1, expected 2 |
| forget_cgpa__p3_esha | yes | no | 5 | 0 | eligibility@latest: version 1, expected 2 |
| cgpa_rise__p4_bharat | yes | no | 5 | 0 | cgpa: status VALID, expected RETIRED; eligibility@latest: content 'not eligible for umbrella (8.4 < 8.6)', expected 'eligible for umbrella (8.9 >= 8.6)'; eligibility@latest: version 1, expected 2; criteria@latest: version 1, expected 2 |
| deadline_moved__p4_bharat | yes | no | 5 | 0 | globex_reminder@latest: content 'remind two days before 2026-11-28', expected 'remind two days before 2026-12-18'; globex_reminder@latest: version 1, expected 2 |
| exam_block__p4_bharat | yes | no | 8 | 0 | availability@latest: version 1, expected 2; availability@latest: version 1, expected 3 |
| accepted_offer__p4_bharat | yes | no | 5 | 0 | availability@latest: version 1, expected 2; eligibility: status VALID, expected RETIRED; recommendation: status VALID, expected RETIRED |
| cutoff_unknown__p4_bharat | yes | no | 4 | 0 | eligibility: status VALID, expected PENDING_USER; recommendation: status VALID, expected SUSPECT; answer:eligibility: memory 'eligibility' is VALID, not PENDING_USER |
| resume_update__p4_bharat | yes | no | 3 | 0 | resume: status VALID, expected RETIRED; tailoring@latest: version 1, expected 2 |
| forget_cgpa__p4_bharat | yes | no | 5 | 0 | eligibility@latest: version 1, expected 2 |
