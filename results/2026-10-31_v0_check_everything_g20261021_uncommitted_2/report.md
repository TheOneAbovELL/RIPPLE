# v0 suite, strategy check_everything, generator seed 20261021 — 2026-10-31T09:35:05.363344+00:00

Scenarios passed: 30/35 runnable (0 not runnable) · checks failed: 5/175 · errors: 0 · resolver calls: 147 · LLM calls: 0 (scripted oracle resolver).

Memory metrics over 35 runnable scenarios (0 not runnable, left out) (bench/metrics.py; pooled, ADR-0120): update accuracy 95.2% · stale kept per scenario 0.14 · wrongful changes per scenario 0.00 · questions asked per scenario 0.14 (needed 0.14) · stale retrieval 0.0% · stale recommendations 0.0% · never consistent 4.8% · resolver calls per ripple 3.27 · tokens and USD per ripple: n/a (no LLM).

Data: synthetic — generated in memory by bench.generate with seeds.generator_seed; the first seed reproduces bench/data/jobs_v0 (checked against its manifest), data sha256 3658001907a3a683f146e31960171b3c532ccb84e5d893c8164dddca3a3e0164; invented names, places and companies, no real story or company described

| scenario | runnable | passed | checks failed | resolver calls | problems |
|---|---|---|---|---|---|
| cgpa_rise__p0_jay | yes | yes | 0/5 | 3 | - |
| deadline_moved__p0_jay | yes | yes | 0/5 | 5 | - |
| exam_block__p0_jay | yes | yes | 0/8 | 6 | - |
| accepted_offer__p0_jay | yes | yes | 0/5 | 5 | - |
| cutoff_unknown__p0_jay | yes | no | 1/4 | 6 | recommendation: status VALID, expected SUSPECT |
| resume_update__p0_jay | yes | yes | 0/3 | 2 | - |
| forget_cgpa__p0_jay | yes | yes | 0/5 | 3 | - |
| cgpa_rise__p1_asha | yes | yes | 0/5 | 3 | - |
| deadline_moved__p1_asha | yes | yes | 0/5 | 5 | - |
| exam_block__p1_asha | yes | yes | 0/8 | 6 | - |
| accepted_offer__p1_asha | yes | yes | 0/5 | 5 | - |
| cutoff_unknown__p1_asha | yes | no | 1/4 | 6 | recommendation: status VALID, expected SUSPECT |
| resume_update__p1_asha | yes | yes | 0/3 | 2 | - |
| forget_cgpa__p1_asha | yes | yes | 0/5 | 3 | - |
| cgpa_rise__p2_esha | yes | yes | 0/5 | 3 | - |
| deadline_moved__p2_esha | yes | yes | 0/5 | 5 | - |
| exam_block__p2_esha | yes | yes | 0/8 | 6 | - |
| accepted_offer__p2_esha | yes | yes | 0/5 | 5 | - |
| cutoff_unknown__p2_esha | yes | no | 1/4 | 6 | recommendation: status VALID, expected SUSPECT |
| resume_update__p2_esha | yes | yes | 0/3 | 2 | - |
| forget_cgpa__p2_esha | yes | yes | 0/5 | 3 | - |
| cgpa_rise__p3_chitra | yes | yes | 0/5 | 3 | - |
| deadline_moved__p3_chitra | yes | yes | 0/5 | 5 | - |
| exam_block__p3_chitra | yes | yes | 0/8 | 6 | - |
| accepted_offer__p3_chitra | yes | yes | 0/5 | 5 | - |
| cutoff_unknown__p3_chitra | yes | no | 1/4 | 6 | recommendation: status VALID, expected SUSPECT |
| resume_update__p3_chitra | yes | yes | 0/3 | 2 | - |
| forget_cgpa__p3_chitra | yes | yes | 0/5 | 3 | - |
| cgpa_rise__p4_bharat | yes | yes | 0/5 | 3 | - |
| deadline_moved__p4_bharat | yes | yes | 0/5 | 5 | - |
| exam_block__p4_bharat | yes | yes | 0/8 | 6 | - |
| accepted_offer__p4_bharat | yes | yes | 0/5 | 5 | - |
| cutoff_unknown__p4_bharat | yes | no | 1/4 | 3 | recommendation: status VALID, expected SUSPECT |
| resume_update__p4_bharat | yes | yes | 0/3 | 2 | - |
| forget_cgpa__p4_bharat | yes | yes | 0/5 | 3 | - |
