# v0 suite, strategy check_everything, generator seed 20261020 — 2026-10-31T09:34:50.461213+00:00

Scenarios passed: 15/20 runnable (0 not runnable) · checks failed: 5/97 · errors: 0 · resolver calls: 87 · LLM calls: 0 (scripted oracle resolver).

Memory metrics over 20 runnable scenarios (0 not runnable, left out) (bench/metrics.py; pooled, ADR-0120): update accuracy 91.8% · stale kept per scenario 0.25 · wrongful changes per scenario 0.00 · questions asked per scenario 0.25 (needed 0.25) · stale retrieval 0.0% · stale recommendations 0.0% · never consistent 8.2% · resolver calls per ripple 3.22 · tokens and USD per ripple: n/a (no LLM).

Data: synthetic — generated in memory by bench.generate with seeds.generator_seed; the first seed reproduces bench/data/jobs_v0 (checked against its manifest), data sha256 ee71a9af90cea3325e67a7482b0c82acee12071699e8d52ed13232b496d5d913; invented names, places and companies, no real story or company described

| scenario | runnable | passed | checks failed | resolver calls | problems |
|---|---|---|---|---|---|
| accepted_offer__p0_dev | yes | yes | 0/5 | 5 | - |
| cutoff_unknown__p0_dev | yes | no | 1/4 | 6 | recommendation: status VALID, expected SUSPECT |
| cgpa_rise__p1_farhan | yes | yes | 0/5 | 3 | - |
| deadline_moved__p1_farhan | yes | yes | 0/5 | 5 | - |
| exam_block__p1_farhan | yes | yes | 0/8 | 6 | - |
| accepted_offer__p1_farhan | yes | yes | 0/5 | 5 | - |
| cutoff_unknown__p1_farhan | yes | no | 1/4 | 6 | recommendation: status VALID, expected SUSPECT |
| resume_update__p1_farhan | yes | yes | 0/3 | 2 | - |
| forget_cgpa__p1_farhan | yes | yes | 0/5 | 3 | - |
| accepted_offer__p2_bharat | yes | yes | 0/5 | 5 | - |
| cutoff_unknown__p2_bharat | yes | no | 1/4 | 6 | recommendation: status VALID, expected SUSPECT |
| cgpa_rise__p3_chitra | yes | yes | 0/5 | 3 | - |
| deadline_moved__p3_chitra | yes | yes | 0/5 | 5 | - |
| exam_block__p3_chitra | yes | yes | 0/8 | 6 | - |
| accepted_offer__p3_chitra | yes | yes | 0/5 | 5 | - |
| cutoff_unknown__p3_chitra | yes | no | 1/4 | 3 | recommendation: status VALID, expected SUSPECT |
| resume_update__p3_chitra | yes | yes | 0/3 | 2 | - |
| forget_cgpa__p3_chitra | yes | yes | 0/5 | 3 | - |
| accepted_offer__p4_gauri | yes | yes | 0/5 | 5 | - |
| cutoff_unknown__p4_gauri | yes | no | 1/4 | 3 | recommendation: status VALID, expected SUSPECT |
