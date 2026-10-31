# smoke suite, strategy ripple — 2026-10-31T09:34:40.034175+00:00

Scenarios passed: 11/11 runnable (0 not runnable) · checks failed: 0/40 · errors: 0 · resolver calls: 20 · LLM calls: 0 (scripted oracle resolver).

Memory metrics over 11 runnable scenarios (0 not runnable, left out) (bench/metrics.py; pooled, ADR-0120): update accuracy 100.0% · stale kept per scenario 0.00 · wrongful changes per scenario 0.00 · questions asked per scenario 0.18 (needed 0.18) · stale retrieval 0.0% · stale recommendations 0.0% · never consistent 0.0% · resolver calls per ripple 1.33 · tokens and USD per ripple: n/a (no LLM).

Data: tests/scenarios/*.yaml (hand-written smoke scenarios)

| scenario | runnable | passed | checks failed | resolver calls | problems |
|---|---|---|---|---|---|
| accepted_offer_chain | yes | yes | 0/4 | 3 | - |
| ask_confirmed | yes | yes | 0/4 | 1 | - |
| ask_unanswered_subtree | yes | yes | 0/4 | 2 | - |
| cgpa_change | yes | yes | 0/5 | 2 | - |
| deadline_extension | yes | yes | 0/2 | 1 | - |
| forget_cascade | yes | yes | 0/5 | 1 | - |
| keep_stops_propagation | yes | yes | 0/2 | 2 | - |
| new_skill_hidden_link | yes | yes | 0/2 | 1 | - |
| resume_version_snapshot | yes | yes | 0/3 | 1 | - |
| temporary_unavailability | yes | yes | 0/6 | 4 | - |
| two_cgpa_changes | yes | yes | 0/3 | 2 | - |
