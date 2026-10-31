# finance_v1 suite, strategy ripple, ablation no_ask_user, generator seed 20261033 — 2026-10-31T09:35:49.509085+00:00

Scenarios passed: 30/35 runnable (0 not runnable) · checks failed: 16/175 · errors: 5 · resolver calls: 65 · LLM calls: 0 (scripted oracle resolver).

Memory metrics over 35 runnable scenarios (0 not runnable, left out) (bench/metrics.py; pooled, ADR-0120): update accuracy 84.2% · stale kept per scenario 0.46 · wrongful changes per scenario 0.00 · questions asked per scenario 0.00 (needed 0.14) · stale retrieval 2.1% · stale recommendations n/a · never consistent 15.8% · resolver calls per ripple 1.62 · tokens and USD per ripple: n/a (no LLM).

Data: synthetic — generated in memory by bench.generate_finance with seeds.generator_seed; the first seed reproduces bench/data/finance_v1 (checked against its manifest), data sha256 183c3f95127fc7e65f13c4863c4c47f57823a399ae65fe6069d73a9274fa9c4d; invented names, places and companies, no real story or company described

| scenario | runnable | passed | checks failed | resolver calls | problems |
|---|---|---|---|---|---|
| guidance_cut__f0_bela | yes | yes | 0/6 | 2 | - |
| peer_margin__f0_bela | yes | yes | 0/4 | 1 | - |
| trading_halt__f0_bela | yes | yes | 0/8 | 4 | - |
| ceo_departure__f0_bela | yes | yes | 0/5 | 3 | - |
| rate_edge__f0_bela | yes | no | 4/4 | 1 | answer:thesis: memory 'thesis' is VALID, not PENDING_USER; thesis: status VALID, expected PENDING_USER; alert: status VALID, expected SUSPECT; thesis@latest: content 'KRVL thesis holds while the policy rate stays below 5.0%', expected 'KRVL thesis holds while the policy rate stays below 5.5%'; thesis@latest: version 1, expected 2; alert@latest: content 'review KRVL monthly', expected 'review KRVL now: rate thesis under question'; alert@latest: version 1, expected 2 |
| journal_entry__f0_bela | yes | yes | 0/3 | 1 | - |
| forget_holding__f0_bela | yes | yes | 0/5 | 1 | - |
| guidance_cut__f1_divya | yes | yes | 0/6 | 2 | - |
| peer_margin__f1_divya | yes | yes | 0/4 | 1 | - |
| trading_halt__f1_divya | yes | yes | 0/8 | 4 | - |
| ceo_departure__f1_divya | yes | yes | 0/5 | 3 | - |
| rate_edge__f1_divya | yes | no | 2/4 | 1 | answer:thesis: memory 'thesis' is VALID, not PENDING_USER; thesis: status VALID, expected PENDING_USER; alert: status VALID, expected SUSPECT |
| journal_entry__f1_divya | yes | yes | 0/3 | 1 | - |
| forget_holding__f1_divya | yes | yes | 0/5 | 1 | - |
| guidance_cut__f2_zoya | yes | yes | 0/6 | 2 | - |
| peer_margin__f2_zoya | yes | yes | 0/4 | 1 | - |
| trading_halt__f2_zoya | yes | yes | 0/8 | 4 | - |
| ceo_departure__f2_zoya | yes | yes | 0/5 | 3 | - |
| rate_edge__f2_zoya | yes | no | 2/4 | 1 | answer:thesis: memory 'thesis' is VALID, not PENDING_USER; thesis: status VALID, expected PENDING_USER; alert: status VALID, expected SUSPECT |
| journal_entry__f2_zoya | yes | yes | 0/3 | 1 | - |
| forget_holding__f2_zoya | yes | yes | 0/5 | 1 | - |
| guidance_cut__f3_uma | yes | yes | 0/6 | 2 | - |
| peer_margin__f3_uma | yes | yes | 0/4 | 1 | - |
| trading_halt__f3_uma | yes | yes | 0/8 | 4 | - |
| ceo_departure__f3_uma | yes | yes | 0/5 | 3 | - |
| rate_edge__f3_uma | yes | no | 4/4 | 1 | answer:thesis: memory 'thesis' is VALID, not PENDING_USER; thesis: status VALID, expected PENDING_USER; alert: status VALID, expected SUSPECT; thesis@latest: content 'MPLW thesis holds while the policy rate stays below 5.5%', expected 'MPLW thesis holds while the policy rate stays below 6.0%'; thesis@latest: version 1, expected 2; alert@latest: content 'review MPLW monthly', expected 'review MPLW now: rate thesis under question'; alert@latest: version 1, expected 2 |
| journal_entry__f3_uma | yes | yes | 0/3 | 1 | - |
| forget_holding__f3_uma | yes | yes | 0/5 | 1 | - |
| guidance_cut__f4_yamini | yes | yes | 0/6 | 2 | - |
| peer_margin__f4_yamini | yes | yes | 0/4 | 1 | - |
| trading_halt__f4_yamini | yes | yes | 0/8 | 4 | - |
| ceo_departure__f4_yamini | yes | yes | 0/5 | 3 | - |
| rate_edge__f4_yamini | yes | no | 4/4 | 1 | answer:thesis: memory 'thesis' is VALID, not PENDING_USER; thesis: status VALID, expected PENDING_USER; alert: status VALID, expected SUSPECT; thesis@latest: content 'QUIL thesis holds while the policy rate stays below 5.1%', expected 'QUIL thesis holds while the policy rate stays below 5.6%'; thesis@latest: version 1, expected 2; alert@latest: content 'review QUIL monthly', expected 'review QUIL now: rate thesis under question'; alert@latest: version 1, expected 2 |
| journal_entry__f4_yamini | yes | yes | 0/3 | 1 | - |
| forget_holding__f4_yamini | yes | yes | 0/5 | 1 | - |
