# finance_v1 suite, strategy ripple, ablation no_ask_user, generator seed 20261032 — 2026-10-31T09:35:48.482794+00:00

Scenarios passed: 30/35 runnable (0 not runnable) · checks failed: 20/175 · errors: 5 · resolver calls: 65 · LLM calls: 0 (scripted oracle resolver).

Memory metrics over 35 runnable scenarios (0 not runnable, left out) (bench/metrics.py; pooled, ADR-0120): update accuracy 81.0% · stale kept per scenario 0.57 · wrongful changes per scenario 0.00 · questions asked per scenario 0.00 (needed 0.14) · stale retrieval 3.5% · stale recommendations n/a · never consistent 19.0% · resolver calls per ripple 1.62 · tokens and USD per ripple: n/a (no LLM).

Data: synthetic — generated in memory by bench.generate_finance with seeds.generator_seed; the first seed reproduces bench/data/finance_v1 (checked against its manifest), data sha256 cde3be083e5560cb595f1ea334cf27d530bbe44b4c1d920dc65583f4c6a8429b; invented names, places and companies, no real story or company described

| scenario | runnable | passed | checks failed | resolver calls | problems |
|---|---|---|---|---|---|
| guidance_cut__f0_chen | yes | yes | 0/6 | 2 | - |
| peer_margin__f0_chen | yes | yes | 0/4 | 1 | - |
| trading_halt__f0_chen | yes | yes | 0/8 | 4 | - |
| ceo_departure__f0_chen | yes | yes | 0/5 | 3 | - |
| rate_edge__f0_chen | yes | no | 4/4 | 1 | answer:thesis: memory 'thesis' is VALID, not PENDING_USER; thesis: status VALID, expected PENDING_USER; alert: status VALID, expected SUSPECT; thesis@latest: content 'VSTR thesis holds while the policy rate stays below 5.8%', expected 'VSTR thesis holds while the policy rate stays below 6.3%'; thesis@latest: version 1, expected 2; alert@latest: content 'review VSTR monthly', expected 'review VSTR now: rate thesis under question'; alert@latest: version 1, expected 2 |
| journal_entry__f0_chen | yes | yes | 0/3 | 1 | - |
| forget_holding__f0_chen | yes | yes | 0/5 | 1 | - |
| guidance_cut__f1_divya | yes | yes | 0/6 | 2 | - |
| peer_margin__f1_divya | yes | yes | 0/4 | 1 | - |
| trading_halt__f1_divya | yes | yes | 0/8 | 4 | - |
| ceo_departure__f1_divya | yes | yes | 0/5 | 3 | - |
| rate_edge__f1_divya | yes | no | 4/4 | 1 | answer:thesis: memory 'thesis' is VALID, not PENDING_USER; thesis: status VALID, expected PENDING_USER; alert: status VALID, expected SUSPECT; thesis@latest: content 'VSTR thesis holds while the policy rate stays below 5.1%', expected 'VSTR thesis holds while the policy rate stays below 5.6%'; thesis@latest: version 1, expected 2; alert@latest: content 'review VSTR monthly', expected 'review VSTR now: rate thesis under question'; alert@latest: version 1, expected 2 |
| journal_entry__f1_divya | yes | yes | 0/3 | 1 | - |
| forget_holding__f1_divya | yes | yes | 0/5 | 1 | - |
| guidance_cut__f2_xavier | yes | yes | 0/6 | 2 | - |
| peer_margin__f2_xavier | yes | yes | 0/4 | 1 | - |
| trading_halt__f2_xavier | yes | yes | 0/8 | 4 | - |
| ceo_departure__f2_xavier | yes | yes | 0/5 | 3 | - |
| rate_edge__f2_xavier | yes | no | 4/4 | 1 | answer:thesis: memory 'thesis' is VALID, not PENDING_USER; thesis: status VALID, expected PENDING_USER; alert: status VALID, expected SUSPECT; thesis: status VALID, expected RETIRED; alert@latest: content 'review VSTR monthly', expected 'review VSTR now: rate thesis under question'; alert@latest: version 1, expected 2 |
| journal_entry__f2_xavier | yes | yes | 0/3 | 1 | - |
| forget_holding__f2_xavier | yes | yes | 0/5 | 1 | - |
| guidance_cut__f3_wen | yes | yes | 0/6 | 2 | - |
| peer_margin__f3_wen | yes | yes | 0/4 | 1 | - |
| trading_halt__f3_wen | yes | yes | 0/8 | 4 | - |
| ceo_departure__f3_wen | yes | yes | 0/5 | 3 | - |
| rate_edge__f3_wen | yes | no | 4/4 | 1 | answer:thesis: memory 'thesis' is VALID, not PENDING_USER; thesis: status VALID, expected PENDING_USER; alert: status VALID, expected SUSPECT; thesis: status VALID, expected RETIRED; alert@latest: content 'review VSTR monthly', expected 'review VSTR now: rate thesis under question'; alert@latest: version 1, expected 2 |
| journal_entry__f3_wen | yes | yes | 0/3 | 1 | - |
| forget_holding__f3_wen | yes | yes | 0/5 | 1 | - |
| guidance_cut__f4_bela | yes | yes | 0/6 | 2 | - |
| peer_margin__f4_bela | yes | yes | 0/4 | 1 | - |
| trading_halt__f4_bela | yes | yes | 0/8 | 4 | - |
| ceo_departure__f4_bela | yes | yes | 0/5 | 3 | - |
| rate_edge__f4_bela | yes | no | 4/4 | 1 | answer:thesis: memory 'thesis' is VALID, not PENDING_USER; thesis: status VALID, expected PENDING_USER; alert: status VALID, expected SUSPECT; thesis@latest: content 'VSTR thesis holds while the policy rate stays below 6.1%', expected 'VSTR thesis holds while the policy rate stays below 6.6%'; thesis@latest: version 1, expected 2; alert@latest: content 'review VSTR monthly', expected 'review VSTR now: rate thesis under question'; alert@latest: version 1, expected 2 |
| journal_entry__f4_bela | yes | yes | 0/3 | 1 | - |
| forget_holding__f4_bela | yes | yes | 0/5 | 1 | - |
