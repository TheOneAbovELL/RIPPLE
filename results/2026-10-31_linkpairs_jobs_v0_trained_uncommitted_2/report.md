# Link pairs: jobs_v0 · trained · split test

Pairs: 392 from `training/data/jobs_v0_pairs.jsonl` (sha256 cfee9ebb4d98…). Query: the dependent is the new memory, the other the only candidate; ids are opaque. Abstentions (invalid output): 0.

Model: `answerdotai/ModernBERT-base`, seed 20261032, threshold 0.5 (validation personas), chosen epoch 9; fitted on 128 pairs, validated on 72 pairs of personas ['p2_harsh']; training took 777.8 s wall.
Validation at the chosen epoch: F1 1.000, precision 1.000, recall 1.000.
Validation per epoch (best threshold each): epoch 1: F1 0.560 at threshold 0.1; epoch 2: F1 0.667 at threshold 0.4; epoch 3: F1 0.872 at threshold 0.9; epoch 4: F1 0.889 at threshold 0.5; epoch 5: F1 0.914 at threshold 0.8; epoch 6: F1 0.923 at threshold 0.5; epoch 7: F1 0.973 at threshold 0.35; epoch 8: F1 0.947 at threshold 0.5; epoch 9: F1 1.000 at threshold 0.5; epoch 10: F1 1.000 at threshold 0.5.

Cost: 0.214084 s wall and 1.582948 s process CPU per linker call (392 calls, 0 LLM calls).

| stratum | n | tp | fp | fn | tn | precision | recall | F1 | typed F1 |
|---|---|---|---|---|---|---|---|---|---|
| overall | 392 | 71 | 24 | 22 | 275 | 0.747 | 0.763 | 0.755 | 0.617 |
| provenance=rule | 53 | 41 | 0 | 12 | 0 | n/a | 0.774 | n/a | n/a |
| provenance=scenario | 339 | 30 | 24 | 10 | 275 | 0.556 | 0.750 | 0.638 | 0.638 |
| held_out=both | 100 | 17 | 9 | 5 | 69 | 0.654 | 0.773 | 0.708 | 0.458 |
| held_out=persona | 140 | 32 | 1 | 6 | 101 | 0.970 | 0.842 | 0.901 | 0.901 |
| held_out=template | 152 | 22 | 14 | 11 | 105 | 0.611 | 0.667 | 0.638 | 0.435 |

False positives by negative kind:

- reversed link: 0/93 (0.000)
- same scenario, no link: 24/206 (0.117)

Recall by gold link type (tp / tp+fn; * = no train pair of this type):

- criteria_from*: 8/10 (0.800)
- depends_on_fact: 10/16 (0.625)
- depends_on_time_period: 2/2 (1.000)
- eligibility_of: 38/42 (0.905)
- fit_of: 2/2 (1.000)
- reminder_for: 9/19 (0.474)
- sent_with_resume: 2/2 (1.000)

Precision and F1 are n/a in a stratum without gold negatives (every RULE pair is a positive); read such a stratum for recall. held_out=both is the strict test cell (persona and template unseen). Synthetic v0 data: harness numbers on a small regular track, not a headline result; a number is citable only from a run on a committed tree.
