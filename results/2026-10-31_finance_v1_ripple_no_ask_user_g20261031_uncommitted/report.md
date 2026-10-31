# finance_v1 suite, strategy ripple, ablation no_ask_user, generator seed 20261031 — 2026-10-31T09:35:47.321331+00:00

Scenarios passed: 30/35 runnable (0 not runnable) · checks failed: 18/175 · errors: 5 · resolver calls: 65 · LLM calls: 0 (scripted oracle resolver).

Memory metrics over 35 runnable scenarios (0 not runnable, left out) (bench/metrics.py; pooled, ADR-0120): update accuracy 82.5% · stale kept per scenario 0.51 · wrongful changes per scenario 0.00 · questions asked per scenario 0.00 (needed 0.14) · stale retrieval 2.8% · stale recommendations n/a · never consistent 17.5% · resolver calls per ripple 1.62 · tokens and USD per ripple: n/a (no LLM).

Data: synthetic — generated in memory by bench.generate_finance with seeds.generator_seed; the first seed reproduces bench/data/finance_v1 (checked against its manifest), data sha256 8b514dc76e0a577264e73fa956b9e727b28c3589005484dbf1ac3c7cf59ad037; invented names, places and companies, no real story or company described

| scenario | runnable | passed | checks failed | resolver calls | problems |
|---|---|---|---|---|---|
| guidance_cut__f0_wen | yes | yes | 0/6 | 2 | - |
| peer_margin__f0_wen | yes | yes | 0/4 | 1 | - |
| trading_halt__f0_wen | yes | yes | 0/8 | 4 | - |
| ceo_departure__f0_wen | yes | yes | 0/5 | 3 | - |
| rate_edge__f0_wen | yes | no | 4/4 | 1 | answer:thesis: memory 'thesis' is VALID, not PENDING_USER; thesis: status VALID, expected PENDING_USER; alert: status VALID, expected SUSPECT; thesis@latest: content 'ORBX thesis holds while the policy rate stays below 6.0%', expected 'ORBX thesis holds while the policy rate stays below 6.5%'; thesis@latest: version 1, expected 2; alert@latest: content 'review ORBX monthly', expected 'review ORBX now: rate thesis under question'; alert@latest: version 1, expected 2 |
| journal_entry__f0_wen | yes | yes | 0/3 | 1 | - |
| forget_holding__f0_wen | yes | yes | 0/5 | 1 | - |
| guidance_cut__f1_xavier | yes | yes | 0/6 | 2 | - |
| peer_margin__f1_xavier | yes | yes | 0/4 | 1 | - |
| trading_halt__f1_xavier | yes | yes | 0/8 | 4 | - |
| ceo_departure__f1_xavier | yes | yes | 0/5 | 3 | - |
| rate_edge__f1_xavier | yes | no | 4/4 | 1 | answer:thesis: memory 'thesis' is VALID, not PENDING_USER; thesis: status VALID, expected PENDING_USER; alert: status VALID, expected SUSPECT; thesis: status VALID, expected RETIRED; alert@latest: content 'review KRVL monthly', expected 'review KRVL now: rate thesis under question'; alert@latest: version 1, expected 2 |
| journal_entry__f1_xavier | yes | yes | 0/3 | 1 | - |
| forget_holding__f1_xavier | yes | yes | 0/5 | 1 | - |
| guidance_cut__f2_vikram | yes | yes | 0/6 | 2 | - |
| peer_margin__f2_vikram | yes | yes | 0/4 | 1 | - |
| trading_halt__f2_vikram | yes | yes | 0/8 | 4 | - |
| ceo_departure__f2_vikram | yes | yes | 0/5 | 3 | - |
| rate_edge__f2_vikram | yes | no | 4/4 | 1 | answer:thesis: memory 'thesis' is VALID, not PENDING_USER; thesis: status VALID, expected PENDING_USER; alert: status VALID, expected SUSPECT; thesis@latest: content 'ZNTH thesis holds while the policy rate stays below 5.7%', expected 'ZNTH thesis holds while the policy rate stays below 6.2%'; thesis@latest: version 1, expected 2; alert@latest: content 'review ZNTH monthly', expected 'review ZNTH now: rate thesis under question'; alert@latest: version 1, expected 2 |
| journal_entry__f2_vikram | yes | yes | 0/3 | 1 | - |
| forget_holding__f2_vikram | yes | yes | 0/5 | 1 | - |
| guidance_cut__f3_uma | yes | yes | 0/6 | 2 | - |
| peer_margin__f3_uma | yes | yes | 0/4 | 1 | - |
| trading_halt__f3_uma | yes | yes | 0/8 | 4 | - |
| ceo_departure__f3_uma | yes | yes | 0/5 | 3 | - |
| rate_edge__f3_uma | yes | no | 4/4 | 1 | answer:thesis: memory 'thesis' is VALID, not PENDING_USER; thesis: status VALID, expected PENDING_USER; alert: status VALID, expected SUSPECT; thesis@latest: content 'TALN thesis holds while the policy rate stays below 5.2%', expected 'TALN thesis holds while the policy rate stays below 5.7%'; thesis@latest: version 1, expected 2; alert@latest: content 'review TALN monthly', expected 'review TALN now: rate thesis under question'; alert@latest: version 1, expected 2 |
| journal_entry__f3_uma | yes | yes | 0/3 | 1 | - |
| forget_holding__f3_uma | yes | yes | 0/5 | 1 | - |
| guidance_cut__f4_arjun | yes | yes | 0/6 | 2 | - |
| peer_margin__f4_arjun | yes | yes | 0/4 | 1 | - |
| trading_halt__f4_arjun | yes | yes | 0/8 | 4 | - |
| ceo_departure__f4_arjun | yes | yes | 0/5 | 3 | - |
| rate_edge__f4_arjun | yes | no | 2/4 | 1 | answer:thesis: memory 'thesis' is VALID, not PENDING_USER; thesis: status VALID, expected PENDING_USER; alert: status VALID, expected SUSPECT |
| journal_entry__f4_arjun | yes | yes | 0/3 | 1 | - |
| forget_holding__f4_arjun | yes | yes | 0/5 | 1 | - |
