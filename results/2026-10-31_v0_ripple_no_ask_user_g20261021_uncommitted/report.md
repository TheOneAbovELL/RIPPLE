# v0 suite, strategy ripple, ablation no_ask_user, generator seed 20261021 — 2026-10-31T09:35:08.562351+00:00

Scenarios passed: 18/20 runnable (0 not runnable) · checks failed: 8/100 · errors: 2 · resolver calls: 38 · LLM calls: 0 (scripted oracle resolver).

Memory metrics over 20 runnable scenarios (0 not runnable, left out) (bench/metrics.py; pooled, ADR-0120): update accuracy 85.2% · stale kept per scenario 0.40 · wrongful changes per scenario 0.00 · questions asked per scenario 0.00 (needed 0.10) · stale retrieval 2.4% · stale recommendations 0.0% · never consistent 14.8% · resolver calls per ripple 1.73 · tokens and USD per ripple: n/a (no LLM).

Data: synthetic — generated in memory by bench.generate with seeds.generator_seed; the first seed reproduces bench/data/jobs_v0 (checked against its manifest), data sha256 3658001907a3a683f146e31960171b3c532ccb84e5d893c8164dddca3a3e0164; invented names, places and companies, no real story or company described

| scenario | runnable | passed | checks failed | resolver calls | problems |
|---|---|---|---|---|---|
| deadline_moved__p0_jay | yes | yes | 0/5 | 1 | - |
| accepted_offer__p0_jay | yes | yes | 0/5 | 3 | - |
| cgpa_rise__p1_asha | yes | yes | 0/5 | 2 | - |
| deadline_moved__p1_asha | yes | yes | 0/5 | 1 | - |
| exam_block__p1_asha | yes | yes | 0/8 | 4 | - |
| accepted_offer__p1_asha | yes | yes | 0/5 | 3 | - |
| cutoff_unknown__p1_asha | yes | no | 4/4 | 1 | answer:eligibility: memory 'eligibility' is VALID, not PENDING_USER; eligibility: status VALID, expected PENDING_USER; recommendation: status VALID, expected SUSPECT; eligibility: status VALID, expected RETIRED; recommendation@latest: content 'skip vandelay', expected 'apply to vandelay'; recommendation@latest: version 1, expected 2 |
| resume_update__p1_asha | yes | yes | 0/3 | 1 | - |
| forget_cgpa__p1_asha | yes | yes | 0/5 | 1 | - |
| cgpa_rise__p2_esha | yes | yes | 0/5 | 2 | - |
| deadline_moved__p2_esha | yes | yes | 0/5 | 1 | - |
| exam_block__p2_esha | yes | yes | 0/8 | 4 | - |
| accepted_offer__p2_esha | yes | yes | 0/5 | 3 | - |
| cutoff_unknown__p2_esha | yes | no | 4/4 | 1 | answer:eligibility: memory 'eligibility' is VALID, not PENDING_USER; eligibility: status VALID, expected PENDING_USER; recommendation: status VALID, expected SUSPECT; eligibility@latest: content 'not eligible for vandelay', expected 'eligible for vandelay (cutoff lowered to 8.5)'; eligibility@latest: version 1, expected 2; recommendation@latest: content 'skip vandelay', expected 'apply to vandelay'; recommendation@latest: version 1, expected 2 |
| resume_update__p2_esha | yes | yes | 0/3 | 1 | - |
| forget_cgpa__p2_esha | yes | yes | 0/5 | 1 | - |
| deadline_moved__p3_chitra | yes | yes | 0/5 | 1 | - |
| accepted_offer__p3_chitra | yes | yes | 0/5 | 3 | - |
| deadline_moved__p4_bharat | yes | yes | 0/5 | 1 | - |
| accepted_offer__p4_bharat | yes | yes | 0/5 | 3 | - |
