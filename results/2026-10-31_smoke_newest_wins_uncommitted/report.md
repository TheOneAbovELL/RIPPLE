# smoke suite, strategy newest_wins — 2026-10-31T09:34:40.858913+00:00

Scenarios passed: 0/11 runnable (0 not runnable) · checks failed: 20/40 · errors: 2 · resolver calls: 0 · LLM calls: 0 (scripted oracle resolver).

Memory metrics over 11 runnable scenarios (0 not runnable, left out) (bench/metrics.py; pooled, ADR-0120): update accuracy 28.6% · stale kept per scenario 1.82 · wrongful changes per scenario 0.00 · questions asked per scenario 0.00 (needed 0.18) · stale retrieval 34.7% · stale recommendations 50.0% · never consistent 71.4% · resolver calls per ripple 0.00 · tokens and USD per ripple: n/a (no LLM).

Data: tests/scenarios/*.yaml (hand-written smoke scenarios)

| scenario | runnable | passed | checks failed | resolver calls | problems |
|---|---|---|---|---|---|
| accepted_offer_chain | yes | no | 3/4 | 0 | availability@latest: version 1, expected 2; eligibility: status VALID, expected RETIRED; recommendation: status VALID, expected RETIRED |
| ask_confirmed | yes | no | 2/4 | 0 | answer:eligibility: memory 'eligibility' is VALID, not PENDING_USER; eligibility: status VALID, expected PENDING_USER; recommendation: status VALID, expected SUSPECT |
| ask_unanswered_subtree | yes | no | 4/4 | 0 | answer:eligibility: memory 'eligibility' is VALID, not PENDING_USER; eligibility: status VALID, expected PENDING_USER; recommendation: status VALID, expected SUSPECT; eligibility: status VALID, expected RETIRED; recommendation@latest: content 'skip Acme', expected 'apply to Acme'; recommendation@latest: version 1, expected 2 |
| cgpa_change | yes | no | 2/5 | 0 | eligibility@latest: content 'not eligible for Acme (7.6 < 7.8)', expected 'eligible for Acme (7.9 >= 7.8)'; eligibility@latest: version 1, expected 2; criteria@latest: version 1, expected 2 |
| deadline_extension | yes | no | 1/2 | 0 | acme_reminder@latest: content 'remind on 2026-11-03 about Acme', expected 'remind on 2026-11-17 about Acme'; acme_reminder@latest: version 1, expected 2 |
| forget_cascade | yes | no | 1/5 | 0 | eligibility@latest: version 1, expected 2 |
| keep_stops_propagation | yes | no | 1/2 | 0 | ranking@latest: content 'Jane Street ranked first', expected 'Jane Street ranked fortieth'; ranking@latest: version 1, expected 2 |
| new_skill_hidden_link | yes | no | 1/2 | 0 | globex_fit@latest: content 'weak fit for Globex, which asks for PyTorch', expected 'strong fit for Globex now that the PyTorch project is done'; globex_fit@latest: version 1, expected 2 |
| resume_version_snapshot | yes | no | 1/3 | 0 | tailoring@latest: version 1, expected 2 |
| temporary_unavailability | yes | no | 2/6 | 0 | availability@latest: version 1, expected 2; availability@latest: version 1, expected 3 |
| two_cgpa_changes | yes | no | 2/3 | 0 | eligibility@latest: content 'not eligible for Acme', expected 'eligibility recomputed'; eligibility@latest: version 1, expected 2; eligibility@latest: version 1, expected 3 |
