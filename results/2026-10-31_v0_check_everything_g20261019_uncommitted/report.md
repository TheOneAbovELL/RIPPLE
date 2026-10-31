# v0 suite, strategy check_everything, generator seed 20261019 — 2026-10-31T09:34:49.837327+00:00

Scenarios passed: 18/20 runnable (0 not runnable) · checks failed: 2/100 · errors: 0 · resolver calls: 81 · LLM calls: 0 (scripted oracle resolver).

Memory metrics over 20 runnable scenarios (0 not runnable, left out) (bench/metrics.py; pooled, ADR-0120): update accuracy 96.4% · stale kept per scenario 0.10 · wrongful changes per scenario 0.00 · questions asked per scenario 0.10 (needed 0.10) · stale retrieval 0.0% · stale recommendations 0.0% · never consistent 3.6% · resolver calls per ripple 3.38 · tokens and USD per ripple: n/a (no LLM).

Data: synthetic — generated in memory by bench.generate with seeds.generator_seed; the first seed reproduces bench/data/jobs_v0 (checked against its manifest), data sha256 26f01e9ab4d44e9be07348dc0c606a308e0178c40d80998ccd96c75a06097c0e; invented names, places and companies, no real story or company described

| scenario | runnable | passed | checks failed | resolver calls | problems |
|---|---|---|---|---|---|
| cgpa_rise__p0_jay | yes | yes | 0/5 | 3 | - |
| deadline_moved__p0_jay | yes | yes | 0/5 | 5 | - |
| cgpa_rise__p1_dev | yes | yes | 0/5 | 3 | - |
| deadline_moved__p1_dev | yes | yes | 0/5 | 5 | - |
| cgpa_rise__p2_harsh | yes | yes | 0/5 | 3 | - |
| deadline_moved__p2_harsh | yes | yes | 0/5 | 5 | - |
| cgpa_rise__p3_esha | yes | yes | 0/5 | 3 | - |
| deadline_moved__p3_esha | yes | yes | 0/5 | 5 | - |
| exam_block__p3_esha | yes | yes | 0/8 | 6 | - |
| accepted_offer__p3_esha | yes | yes | 0/5 | 5 | - |
| cutoff_unknown__p3_esha | yes | no | 1/4 | 6 | recommendation: status VALID, expected SUSPECT |
| resume_update__p3_esha | yes | yes | 0/3 | 2 | - |
| forget_cgpa__p3_esha | yes | yes | 0/5 | 3 | - |
| cgpa_rise__p4_bharat | yes | yes | 0/5 | 3 | - |
| deadline_moved__p4_bharat | yes | yes | 0/5 | 5 | - |
| exam_block__p4_bharat | yes | yes | 0/8 | 6 | - |
| accepted_offer__p4_bharat | yes | yes | 0/5 | 5 | - |
| cutoff_unknown__p4_bharat | yes | no | 1/4 | 3 | recommendation: status VALID, expected SUSPECT |
| resume_update__p4_bharat | yes | yes | 0/3 | 2 | - |
| forget_cgpa__p4_bharat | yes | yes | 0/5 | 3 | - |
