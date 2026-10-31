# Link pairs: jobs_v0 · trained · split test

Pairs: 392 from `training/data/jobs_v0_pairs.jsonl` (sha256 cfee9ebb4d98…). Query: the dependent is the new memory, the other the only candidate; ids are opaque. Abstentions (invalid output): 0.

Model: `answerdotai/ModernBERT-base`, seed 20261031, threshold 0.5 (validation personas), chosen epoch 9; fitted on 128 pairs, validated on 72 pairs of personas ['p2_harsh']; training took 934.2 s wall.
Validation at the chosen epoch: F1 0.973, precision 0.947, recall 1.000.
Validation per epoch (best threshold each): epoch 1: F1 0.541 at threshold 0.25; epoch 2: F1 0.549 at threshold 0.4; epoch 3: F1 0.850 at threshold 0.45; epoch 4: F1 0.848 at threshold 0.45; epoch 5: F1 0.900 at threshold 0.5; epoch 6: F1 0.923 at threshold 0.8; epoch 7: F1 0.944 at threshold 0.65; epoch 8: F1 0.919 at threshold 0.9; epoch 9: F1 0.973 at threshold 0.5; epoch 10: F1 0.973 at threshold 0.45.

Cost: 0.247472 s wall and 1.641462 s process CPU per linker call (392 calls, 0 LLM calls).

| stratum | n | tp | fp | fn | tn | precision | recall | F1 | typed F1 |
|---|---|---|---|---|---|---|---|---|---|
| overall | 392 | 58 | 19 | 35 | 280 | 0.753 | 0.624 | 0.682 | 0.682 |
| provenance=rule | 53 | 28 | 0 | 25 | 0 | n/a | 0.528 | n/a | n/a |
| provenance=scenario | 339 | 30 | 19 | 10 | 280 | 0.612 | 0.750 | 0.674 | 0.674 |
| held_out=both | 100 | 11 | 9 | 11 | 69 | 0.550 | 0.500 | 0.524 | 0.524 |
| held_out=persona | 140 | 31 | 1 | 7 | 101 | 0.969 | 0.816 | 0.886 | 0.886 |
| held_out=template | 152 | 16 | 9 | 17 | 110 | 0.640 | 0.485 | 0.552 | 0.552 |

False positives by negative kind:

- reversed link: 0/93 (0.000)
- same scenario, no link: 19/206 (0.092)

Recall by gold link type (tp / tp+fn; * = no train pair of this type):

- criteria_from*: 0/10 (0.000)
- depends_on_fact: 10/16 (0.625)
- depends_on_time_period: 2/2 (1.000)
- eligibility_of: 39/42 (0.929)
- fit_of: 1/2 (0.500)
- reminder_for: 4/19 (0.211)
- sent_with_resume: 2/2 (1.000)

Precision and F1 are n/a in a stratum without gold negatives (every RULE pair is a positive); read such a stratum for recall. held_out=both is the strict test cell (persona and template unseen). Synthetic v0 data: harness numbers on a small regular track, not a headline result; a number is citable only from a run on a committed tree.
