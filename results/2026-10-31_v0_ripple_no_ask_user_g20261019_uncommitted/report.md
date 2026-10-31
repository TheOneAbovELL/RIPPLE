# v0 suite, strategy ripple, ablation no_ask_user, generator seed 20261019 — 2026-10-31T09:35:07.708216+00:00

Scenarios passed: 18/20 runnable (0 not runnable) · checks failed: 6/100 · errors: 2 · resolver calls: 35 · LLM calls: 0 (scripted oracle resolver).

Memory metrics over 20 runnable scenarios (0 not runnable, left out) (bench/metrics.py; pooled, ADR-0120): update accuracy 89.1% · stale kept per scenario 0.30 · wrongful changes per scenario 0.00 · questions asked per scenario 0.00 (needed 0.10) · stale retrieval 1.2% · stale recommendations 0.0% · never consistent 10.9% · resolver calls per ripple 1.59 · tokens and USD per ripple: n/a (no LLM).

Data: synthetic — generated in memory by bench.generate with seeds.generator_seed; the first seed reproduces bench/data/jobs_v0 (checked against its manifest), data sha256 26f01e9ab4d44e9be07348dc0c606a308e0178c40d80998ccd96c75a06097c0e; invented names, places and companies, no real story or company described

| scenario | runnable | passed | checks failed | resolver calls | problems |
|---|---|---|---|---|---|
| cgpa_rise__p0_jay | yes | yes | 0/5 | 2 | - |
| deadline_moved__p0_jay | yes | yes | 0/5 | 1 | - |
| cgpa_rise__p1_dev | yes | yes | 0/5 | 2 | - |
| deadline_moved__p1_dev | yes | yes | 0/5 | 1 | - |
| cgpa_rise__p2_harsh | yes | yes | 0/5 | 2 | - |
| deadline_moved__p2_harsh | yes | yes | 0/5 | 1 | - |
| cgpa_rise__p3_esha | yes | yes | 0/5 | 2 | - |
| deadline_moved__p3_esha | yes | yes | 0/5 | 1 | - |
| exam_block__p3_esha | yes | yes | 0/8 | 4 | - |
| accepted_offer__p3_esha | yes | yes | 0/5 | 3 | - |
| cutoff_unknown__p3_esha | yes | no | 4/4 | 1 | answer:eligibility: memory 'eligibility' is VALID, not PENDING_USER; eligibility: status VALID, expected PENDING_USER; recommendation: status VALID, expected SUSPECT; eligibility: status VALID, expected RETIRED; recommendation@latest: content 'skip vandelay', expected 'apply to vandelay'; recommendation@latest: version 1, expected 2 |
| resume_update__p3_esha | yes | yes | 0/3 | 1 | - |
| forget_cgpa__p3_esha | yes | yes | 0/5 | 1 | - |
| cgpa_rise__p4_bharat | yes | yes | 0/5 | 2 | - |
| deadline_moved__p4_bharat | yes | yes | 0/5 | 1 | - |
| exam_block__p4_bharat | yes | yes | 0/8 | 4 | - |
| accepted_offer__p4_bharat | yes | yes | 0/5 | 3 | - |
| cutoff_unknown__p4_bharat | yes | no | 2/4 | 1 | answer:eligibility: memory 'eligibility' is VALID, not PENDING_USER; eligibility: status VALID, expected PENDING_USER; recommendation: status VALID, expected SUSPECT |
| resume_update__p4_bharat | yes | yes | 0/3 | 1 | - |
| forget_cgpa__p4_bharat | yes | yes | 0/5 | 1 | - |
