# Link pairs: jobs_v0 · fake_llm · split test

**PLUMBING CHECK: the LLM linker ran on FakeLLM scripted to propose nothing. These counts show the harness runs end to end; they measure no model.**

Pairs: 392 from `training/data/jobs_v0_pairs.jsonl` (sha256 cfee9ebb4d98…). Query: the dependent is the new memory, the other the only candidate; ids are opaque. Abstentions (invalid output): 0.

| stratum | n | tp | fp | fn | tn | precision | recall | F1 | typed F1 |
|---|---|---|---|---|---|---|---|---|---|
| overall | 392 | 0 | 0 | 93 | 299 | n/a | 0.000 | 0.000 | 0.000 |
| provenance=rule | 53 | 0 | 0 | 53 | 0 | n/a | 0.000 | n/a | n/a |
| provenance=scenario | 339 | 0 | 0 | 40 | 299 | n/a | 0.000 | 0.000 | 0.000 |
| held_out=both | 100 | 0 | 0 | 22 | 78 | n/a | 0.000 | 0.000 | 0.000 |
| held_out=persona | 140 | 0 | 0 | 38 | 102 | n/a | 0.000 | 0.000 | 0.000 |
| held_out=template | 152 | 0 | 0 | 33 | 119 | n/a | 0.000 | 0.000 | 0.000 |

False positives by negative kind:

- reversed link: 0/93 (0.000)
- same scenario, no link: 0/206 (0.000)

Recall by gold link type (tp / tp+fn; * = no train pair of this type):

- criteria_from*: 0/10 (0.000)
- depends_on_fact: 0/16 (0.000)
- depends_on_time_period: 0/2 (0.000)
- eligibility_of: 0/42 (0.000)
- fit_of: 0/2 (0.000)
- reminder_for: 0/19 (0.000)
- sent_with_resume: 0/2 (0.000)

Precision and F1 are n/a in a stratum without gold negatives (every RULE pair is a positive); read such a stratum for recall. held_out=both is the strict test cell (persona and template unseen). Synthetic v0 data: harness numbers on a small regular track, not a headline result; a number is citable only from a run on a committed tree.
