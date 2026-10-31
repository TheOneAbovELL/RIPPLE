# Link pairs: jobs_v0 · rule · split test

Pairs: 392 from `training/data/jobs_v0_pairs.jsonl` (sha256 cfee9ebb4d98…). Query: the dependent is the new memory, the other the only candidate; ids are opaque. Abstentions (invalid output): 0.

| stratum | n | tp | fp | fn | tn | precision | recall | F1 | typed F1 |
|---|---|---|---|---|---|---|---|---|---|
| overall | 392 | 36 | 26 | 57 | 273 | 0.581 | 0.387 | 0.465 | n/a |
| provenance=rule | 53 | 32 | 0 | 21 | 0 | n/a | 0.604 | n/a | n/a |
| provenance=scenario | 339 | 4 | 26 | 36 | 273 | 0.133 | 0.100 | 0.114 | n/a |
| held_out=both | 100 | 12 | 8 | 10 | 70 | 0.600 | 0.545 | 0.571 | n/a |
| held_out=persona | 140 | 6 | 5 | 32 | 97 | 0.545 | 0.158 | 0.245 | n/a |
| held_out=template | 152 | 18 | 13 | 15 | 106 | 0.581 | 0.545 | 0.562 | n/a |

False positives by negative kind:

- reversed link: 0/93 (0.000)
- same scenario, no link: 26/206 (0.126)

Recall by gold link type (tp / tp+fn; * = no train pair of this type):

- criteria_from*: 10/10 (1.000)
- depends_on_fact: 0/16 (0.000)
- depends_on_time_period: 2/2 (1.000)
- eligibility_of: 22/42 (0.524)
- fit_of: 0/2 (0.000)
- reminder_for: 0/19 (0.000)
- sent_with_resume: 2/2 (1.000)

Precision and F1 are n/a in a stratum without gold negatives (every RULE pair is a positive); read such a stratum for recall. held_out=both is the strict test cell (persona and template unseen). Typed metrics are n/a: this linker proposes one fixed type. Synthetic v0 data: harness numbers on a small regular track, not a headline result; a number is citable only from a run on a committed tree.
