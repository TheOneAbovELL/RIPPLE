# smoke suite, strategy check_everything — 2026-10-31T09:34:41.252297+00:00

Scenarios passed: 8/11 runnable (0 not runnable) · checks failed: 4/40 · errors: 0 · resolver calls: 34 · LLM calls: 0 (scripted oracle resolver).

Memory metrics over 11 runnable scenarios (0 not runnable, left out) (bench/metrics.py; pooled, ADR-0120): update accuracy 92.9% · stale kept per scenario 0.09 · wrongful changes per scenario 0.18 · questions asked per scenario 0.18 (needed 0.18) · stale retrieval 0.0% · stale recommendations 0.0% · never consistent 7.1% · resolver calls per ripple 2.27 · tokens and USD per ripple: n/a (no LLM).

Data: tests/scenarios/*.yaml (hand-written smoke scenarios)

| scenario | runnable | passed | checks failed | resolver calls | problems |
|---|---|---|---|---|---|
| accepted_offer_chain | yes | yes | 0/4 | 5 | - |
| ask_confirmed | yes | no | 1/4 | 2 | recommendation: status VALID, expected SUSPECT |
| ask_unanswered_subtree | yes | no | 2/4 | 4 | recommendation: status RETIRED, expected SUSPECT; recommendation@latest: version 3, expected 2 |
| cgpa_change | yes | yes | 0/5 | 3 | - |
| deadline_extension | yes | yes | 0/2 | 3 | - |
| forget_cascade | yes | yes | 0/5 | 3 | - |
| keep_stops_propagation | yes | yes | 0/2 | 2 | - |
| new_skill_hidden_link | yes | yes | 0/2 | 2 | - |
| resume_version_snapshot | yes | no | 1/3 | 2 | application: status RETIRED, expected VALID |
| temporary_unavailability | yes | yes | 0/6 | 6 | - |
| two_cgpa_changes | yes | yes | 0/3 | 2 | - |
