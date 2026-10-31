# Link pairs: jobs_v0 · fake_llm · split test

**PLUMBING CHECK: the LLM linker ran on FakeLLM scripted to propose nothing. These counts show the harness runs end to end; they measure no model.**

Pairs: 392 from `training/data/jobs_v0_pairs.jsonl` (sha256 cfee9ebb4d98…). Query: the dependent is the new memory, the other the only candidate.

| stratum | n | tp | fp | fn | tn | precision | recall | F1 | typed F1 |
|---|---|---|---|---|---|---|---|---|---|
| overall | 392 | 0 | 0 | 93 | 299 | n/a | 0.000 | 0.000 | 0.000 |
| provenance=rule | 53 | 0 | 0 | 53 | 0 | n/a | 0.000 | 0.000 | 0.000 |
| provenance=scenario | 339 | 0 | 0 | 40 | 299 | n/a | 0.000 | 0.000 | 0.000 |

Recall by gold link type (tp / tp+fn):

- criteria_from: 0/10 (0.000)
- depends_on_fact: 0/16 (0.000)
- depends_on_time_period: 0/2 (0.000)
- eligibility_of: 0/42 (0.000)
- fit_of: 0/2 (0.000)
- reminder_for: 0/19 (0.000)
- sent_with_resume: 0/2 (0.000)

A RULE-provenance stratum holds only positives (no negatives carry RULE), so its precision is not informative; read it for recall. "n/a" means undefined (no predicted or no gold links in that stratum). Synthetic v0 data: these are harness numbers on a small regular track, not a headline result.
