# Link pairs: jobs_v0 · rule · split test

Pairs: 392 from `C:/Users/omjee/OneDrive/Desktop/RIPPLE/training/data/jobs_v0_pairs.jsonl` (sha256 cfee9ebb4d98…). Query: the dependent is the new memory, the other the only candidate.

| stratum | n | tp | fp | fn | tn | precision | recall | F1 | typed F1 |
|---|---|---|---|---|---|---|---|---|---|
| overall | 392 | 36 | 26 | 57 | 273 | 0.581 | 0.387 | 0.465 | 0.000 |
| provenance=rule | 53 | 32 | 0 | 21 | 0 | 1.000 | 0.604 | 0.753 | 0.000 |
| provenance=scenario | 339 | 4 | 26 | 36 | 273 | 0.133 | 0.100 | 0.114 | 0.000 |

Recall by gold link type (tp / tp+fn):

- criteria_from: 10/10 (1.000)
- depends_on_fact: 0/16 (0.000)
- depends_on_time_period: 2/2 (1.000)
- eligibility_of: 22/42 (0.524)
- fit_of: 0/2 (0.000)
- reminder_for: 0/19 (0.000)
- sent_with_resume: 2/2 (1.000)

A RULE-provenance stratum holds only positives (no negatives carry RULE), so its precision is not informative; read it for recall. "n/a" means undefined (no predicted or no gold links in that stratum). Synthetic v0 data: these are harness numbers on a small regular track, not a headline result.
