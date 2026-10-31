# v0 suite, strategy append_only, generator seed 20261019 — 2026-10-31T09:34:45.654695+00:00

Scenarios passed: 0/20 runnable (0 not runnable) · checks failed: 42/100 · errors: 2 · resolver calls: 0 · LLM calls: 0 (scripted oracle resolver).

Memory metrics over 20 runnable scenarios (0 not runnable, left out) (bench/metrics.py; pooled, ADR-0120): update accuracy 23.6% · stale kept per scenario 2.10 · wrongful changes per scenario 0.00 · questions asked per scenario 0.00 (needed 0.10) · stale retrieval 32.8% · stale recommendations 66.7% · never consistent 76.4% · resolver calls per ripple 0.00 · tokens and USD per ripple: n/a (no LLM).

Data: synthetic — generated in memory by bench.generate with seeds.generator_seed; the first seed reproduces bench/data/jobs_v0 (checked against its manifest), data sha256 26f01e9ab4d44e9be07348dc0c606a308e0178c40d80998ccd96c75a06097c0e; invented names, places and companies, no real story or company described

| scenario | runnable | passed | checks failed | resolver calls | problems |
|---|---|---|---|---|---|
| cgpa_rise__p0_jay | yes | no | 3/5 | 0 | cgpa: status VALID, expected RETIRED; eligibility@latest: content 'not eligible for umbrella (7.2 < 7.4)', expected 'eligible for umbrella (7.6 >= 7.4)'; eligibility@latest: version 1, expected 2; criteria@latest: version 1, expected 2 |
| deadline_moved__p0_jay | yes | no | 1/5 | 0 | initech_reminder@latest: content 'remind two days before 2026-11-01', expected 'remind two days before 2026-12-19'; initech_reminder@latest: version 1, expected 2 |
| cgpa_rise__p1_dev | yes | no | 3/5 | 0 | cgpa: status VALID, expected RETIRED; eligibility@latest: content 'not eligible for stark (7.4 < 7.6)', expected 'eligible for stark (7.9 >= 7.6)'; eligibility@latest: version 1, expected 2; criteria@latest: version 1, expected 2 |
| deadline_moved__p1_dev | yes | no | 1/5 | 0 | wonka_reminder@latest: content 'remind two days before 2026-11-12', expected 'remind two days before 2026-12-16'; wonka_reminder@latest: version 1, expected 2 |
| cgpa_rise__p2_harsh | yes | no | 3/5 | 0 | cgpa: status VALID, expected RETIRED; eligibility@latest: content 'not eligible for vandelay (7.1 < 7.3)', expected 'eligible for vandelay (7.4 >= 7.3)'; eligibility@latest: version 1, expected 2; criteria@latest: version 1, expected 2 |
| deadline_moved__p2_harsh | yes | no | 1/5 | 0 | umbrella_reminder@latest: content 'remind two days before 2026-11-19', expected 'remind two days before 2026-12-23'; umbrella_reminder@latest: version 1, expected 2 |
| cgpa_rise__p3_esha | yes | no | 3/5 | 0 | cgpa: status VALID, expected RETIRED; eligibility@latest: content 'not eligible for vandelay (7.5 < 7.7)', expected 'eligible for vandelay (7.9 >= 7.7)'; eligibility@latest: version 1, expected 2; criteria@latest: version 1, expected 2 |
| deadline_moved__p3_esha | yes | no | 1/5 | 0 | hooli_reminder@latest: content 'remind two days before 2026-12-06', expected 'remind two days before 2026-12-16'; hooli_reminder@latest: version 1, expected 2 |
| exam_block__p3_esha | yes | no | 2/8 | 0 | availability@latest: version 1, expected 2; availability@latest: version 1, expected 3 |
| accepted_offer__p3_esha | yes | no | 3/5 | 0 | availability@latest: version 1, expected 2; eligibility: status VALID, expected RETIRED; recommendation: status VALID, expected RETIRED |
| cutoff_unknown__p3_esha | yes | no | 4/4 | 0 | answer:eligibility: memory 'eligibility' is VALID, not PENDING_USER; eligibility: status VALID, expected PENDING_USER; recommendation: status VALID, expected SUSPECT; eligibility: status VALID, expected RETIRED; recommendation@latest: content 'skip vandelay', expected 'apply to vandelay'; recommendation@latest: version 1, expected 2 |
| resume_update__p3_esha | yes | no | 2/3 | 0 | resume: status VALID, expected RETIRED; tailoring@latest: version 1, expected 2 |
| forget_cgpa__p3_esha | yes | no | 1/5 | 0 | eligibility@latest: version 1, expected 2 |
| cgpa_rise__p4_bharat | yes | no | 3/5 | 0 | cgpa: status VALID, expected RETIRED; eligibility@latest: content 'not eligible for umbrella (8.4 < 8.6)', expected 'eligible for umbrella (8.9 >= 8.6)'; eligibility@latest: version 1, expected 2; criteria@latest: version 1, expected 2 |
| deadline_moved__p4_bharat | yes | no | 1/5 | 0 | globex_reminder@latest: content 'remind two days before 2026-11-28', expected 'remind two days before 2026-12-18'; globex_reminder@latest: version 1, expected 2 |
| exam_block__p4_bharat | yes | no | 2/8 | 0 | availability@latest: version 1, expected 2; availability@latest: version 1, expected 3 |
| accepted_offer__p4_bharat | yes | no | 3/5 | 0 | availability@latest: version 1, expected 2; eligibility: status VALID, expected RETIRED; recommendation: status VALID, expected RETIRED |
| cutoff_unknown__p4_bharat | yes | no | 2/4 | 0 | answer:eligibility: memory 'eligibility' is VALID, not PENDING_USER; eligibility: status VALID, expected PENDING_USER; recommendation: status VALID, expected SUSPECT |
| resume_update__p4_bharat | yes | no | 2/3 | 0 | resume: status VALID, expected RETIRED; tailoring@latest: version 1, expected 2 |
| forget_cgpa__p4_bharat | yes | no | 1/5 | 0 | eligibility@latest: version 1, expected 2 |
